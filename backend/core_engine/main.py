from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.ai_engine.client import (
    AIAuthenticationError,
    AIConfigurationError,
    AIConnectionError,
    AIEngineError,
    AIRateLimitError,
    AIServiceError,
    AITimeoutError,
)
from backend.core_engine.analysis_service import (
    CourseResolutionError,
    CurricularConstraintError,
    CycleConflictError,
    LearningPathError,
    generate_learning_path,
)
from backend.core_engine.config import settings
from backend.knowledge_base.knowledge_base import get_default_knowledge_base

app = FastAPI(
    title="DAA Course Learning Path API",
    description="Backend API for AI-assisted prerequisite-aware course learning path generator.",
    version=settings.version,
    redirect_slashes=False,
)

# Enable CORS for frontend integration
_allowed_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins if _allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class AIStatusResponse(BaseModel):
    configured: bool
    key_present: bool
    key_empty: bool
    key_source: str
    model: str
    timeout_seconds: float
    max_retries: int
    client_initializable: bool
    error: Optional[str] = None


class LearningPathRequest(BaseModel):
    courses: List[str] = Field(
        ...,
        min_length=1,
        description="List of course names, IDs, or recognizable aliases.",
        examples=[["Python Programming", "Data Structures", "Algorithms"]],
    )
    learning_goal: Optional[str] = Field(
        default="General Computer Science",
        description="Student learning objective or career goal.",
        examples=["Master Software Engineering Foundations"],
    )
    use_ai: Optional[bool] = Field(
        default=True,
        description="Whether to query the AI Engine for prerequisite proposals.",
    )
    fallback_on_ai_failure: Optional[bool] = Field(
        default=True,
        description="If True, gracefully fall back to curated KB prerequisites if AI is unavailable.",
    )
    max_courses_per_semester: Optional[int] = Field(
        default=None,
        description="Optional maximum number of courses permitted per semester or wave (must be >= 1).",
        examples=[3],
    )
    max_semesters: Optional[int] = Field(
        default=None,
        description="Optional maximum number of semesters permitted (must be >= 1).",
        examples=[4],
    )


class PrerequisiteRecord(BaseModel):
    source_course_id: str
    target_course_id: str
    relationship_type: str
    explanation: Optional[str] = None
    source: str = Field(
        default="curated",
        description="Origin of relationship: 'curated' (Knowledge Base) or 'ai_proposed' (Google Gemini).",
    )
    is_ai_proposed: bool = Field(
        default=False,
        description="Whether this relationship was proposed by AI.",
    )
    confidence: Optional[float] = Field(
        default=None,
        description="Confidence score between 0.0 and 1.0 when available.",
    )
    evidence_type: Optional[str] = Field(
        default=None,
        description="Evidence classification (e.g., 'expert_curated' or 'llm_proposed').",
    )


class SemesterGroup(BaseModel):
    semester_number: int = Field(..., description="1-indexed sequence number of the semester or wave.")
    courses: List[Dict[str, Any]] = Field(..., description="Courses assigned to this semester or wave.")
    course_count: int = Field(..., description="Number of courses in this semester or wave.")


class AISummary(BaseModel):
    requested: bool = Field(default=False, description="Whether AI was requested for this path generation.")
    course_resolution_status: str = Field(
        default="curated_only",
        description="Status of course resolution: 'curated_only', 'ai_inferred', 'ai_disambiguated'.",
    )
    unknown_courses_evaluated: int = Field(default=0, description="Number of unrecognized course queries evaluated via AI.")
    ambiguous_courses_evaluated: int = Field(default=0, description="Number of ambiguous course queries evaluated via AI.")
    proposal_request_status: str = Field(
        default="disabled",
        description="Status of AI prerequisite proposal request: 'disabled', 'skipped', 'succeeded', 'failed'.",
    )
    proposals_received: int = Field(default=0, description="Total prerequisite proposals received from AI.")
    proposals_accepted: int = Field(default=0, description="Number of valid proposals accepted into the graph.")
    proposals_rejected: int = Field(default=0, description="Number of invalid proposals rejected during validation.")
    relationships_added: int = Field(default=0, description="Number of AI-proposed relationships added to final graph.")
    model: Optional[str] = Field(default=None, description="Configured Gemini model identifier used for analysis.")
    message: str = Field(default="", description="Safe, transparent user-readable diagnostic summary.")


class LearningPathResponse(BaseModel):
    learning_goal: str
    selected_courses: List[Dict[str, Any]]
    ordered_courses: List[Dict[str, Any]]
    semesters: List[SemesterGroup] = Field(
        default_factory=list,
        description="Wave-based or semester-based course grouping respecting prerequisite constraints and capacity limits.",
    )
    prerequisites: List[PrerequisiteRecord]
    ai_proposals_used: bool
    warnings: List[str] = []
    ai_summary: Optional[AISummary] = Field(
        default=None,
        description="Transparent diagnostic execution metadata for AI course resolution and prerequisite analysis.",
    )


@app.get("/", tags=["General"])
def read_root():
    return {
        "service": settings.service_name,
        "version": settings.version,
        "message": "AI-Assisted Prerequisite-Aware Course Learning Path API",
        "docs_url": "/docs",
        "health_url": "/api/v1/health",
        "learning_path_url": "/api/v1/learning-path",
    }


@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
@app.get("/api/health", response_model=HealthResponse, tags=["Health"], include_in_schema=False)
@app.get("/v1/health", response_model=HealthResponse, tags=["Health"], include_in_schema=False)
@app.get("/health", response_model=HealthResponse, tags=["Health"], include_in_schema=False)
def get_health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service=settings.service_name,
        version=settings.version,
    )


@app.get("/api/v1/courses", tags=["Courses"])
@app.get("/api/courses", tags=["Courses"], include_in_schema=False)
@app.get("/v1/courses", tags=["Courses"], include_in_schema=False)
@app.get("/courses", tags=["Courses"], include_in_schema=False)
def get_curated_courses() -> List[Dict[str, Any]]:
    """Returns the complete curated catalog of courses from the Knowledge Base."""
    kb = get_default_knowledge_base()
    return kb.get_all_courses()


@app.get("/api/v1/ai/status", response_model=AIStatusResponse, tags=["AI Engine"])
@app.get("/api/ai/status", response_model=AIStatusResponse, tags=["AI Engine"], include_in_schema=False)
@app.get("/v1/ai/status", response_model=AIStatusResponse, tags=["AI Engine"], include_in_schema=False)
@app.get("/ai/status", response_model=AIStatusResponse, tags=["AI Engine"], include_in_schema=False)
def get_ai_status() -> AIStatusResponse:
    """Safe diagnostic endpoint reporting AI configuration status without secrets."""
    diag = settings.get_ai_diagnostic()
    can_init = False
    init_err = None
    if diag["is_configured"]:
        try:
            from backend.ai_engine.client import get_genai_client

            client = get_genai_client()
            can_init = client is not None
        except Exception as exc:
            can_init = False
            init_err = type(exc).__name__
    return AIStatusResponse(
        configured=diag["is_configured"],
        key_present=diag["is_configured"],
        key_empty=diag["is_empty"],
        key_source=diag["key_source"],
        model=diag["model"],
        timeout_seconds=diag["timeout_seconds"],
        max_retries=diag["max_retries"],
        client_initializable=can_init,
        error=init_err,
    )


@app.post(
    "/api/v1/learning-path",
    response_model=LearningPathResponse,
    status_code=status.HTTP_200_OK,
    tags=["Learning Path"],
    summary="Generate a validated, prerequisite-aware course learning path",
)
@app.post(
    "/api/learning-path",
    response_model=LearningPathResponse,
    status_code=status.HTTP_200_OK,
    tags=["Learning Path"],
    include_in_schema=False,
)
@app.post(
    "/v1/learning-path",
    response_model=LearningPathResponse,
    status_code=status.HTTP_200_OK,
    tags=["Learning Path"],
    include_in_schema=False,
)
@app.post(
    "/learning-path",
    response_model=LearningPathResponse,
    status_code=status.HTTP_200_OK,
    tags=["Learning Path"],
    include_in_schema=False,
)
def create_learning_path(payload: LearningPathRequest) -> LearningPathResponse:
    """Accepts selected courses and learning goal, resolves canonical records,
    incorporates validated AI proposals, detects graph cycles, and returns a
    deterministic topologically sorted sequence using Kahn's algorithm.
    """
    try:
        result = generate_learning_path(
            course_names=payload.courses,
            learning_goal=payload.learning_goal,
            use_ai=bool(payload.use_ai),
            fallback_on_ai_failure=bool(payload.fallback_on_ai_failure),
            max_courses_per_semester=payload.max_courses_per_semester,
            max_semesters=payload.max_semesters,
        )
        return LearningPathResponse(**result)
    except CourseResolutionError as exc:
        err_detail: Dict[str, Any] = {"error": "course_resolution_error", "message": str(exc)}
        if getattr(exc, "needs_clarification", False):
            err_detail["needs_clarification"] = True
            err_detail["query"] = getattr(exc, "query", None)
            err_detail["clarification"] = getattr(exc, "clarification", None)
            err_detail["candidates"] = getattr(exc, "candidates", [])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_detail,
        )
    except CycleConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "cyclic_dependency_error",
                "message": str(exc),
                "cycle_path": exc.cycle_path,
            },
        )
    except CurricularConstraintError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "curricular_constraint_error",
                "message": str(exc),
                "required_semesters": getattr(exc, "required_semesters", None),
                "max_semesters": getattr(exc, "max_semesters", None),
            },
        )
    except AIEngineError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "ai_service_error",
                "sub_error": type(exc).__name__,
                "message": str(exc),
            },
        )
    except LearningPathError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "learning_path_error", "message": str(exc)},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(exc)},
        )

