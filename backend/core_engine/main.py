from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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
    title="DAA Course Registration Assistant API",
    description="Dependency-Aware Course Registration Assistant with Graph Theory & Topological Sorting.",
    version=settings.version,
    redirect_slashes=False,
)

# Enable CORS for local dev and frontend integration
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


class LearningPathRequest(BaseModel):
    courses: List[str] = Field(
        ...,
        min_length=1,
        description="List of course names, IDs, or recognizable aliases from the catalog.",
        examples=[["Python Programming", "Data Structures", "Design and Analysis of Algorithms"]],
    )
    learning_goal: Optional[str] = Field(
        default="General Computer Science",
        description="Student learning objective or career goal.",
        examples=["Master Software Engineering Foundations"],
    )
    max_courses_per_semester: Optional[int] = Field(
        default=None,
        description="Optional maximum number of courses permitted per semester (must be >= 1).",
        examples=[3],
    )
    max_semesters: Optional[int] = Field(
        default=None,
        description="Optional maximum number of semesters permitted (must be >= 1).",
        examples=[4],
    )
    # Optional legacy flags accepted gracefully
    use_ai: Optional[bool] = Field(default=False, description="Legacy parameter (AI removed).")
    fallback_on_ai_failure: Optional[bool] = Field(default=True, description="Legacy parameter.")


class PrerequisiteRecord(BaseModel):
    source_course_id: str
    target_course_id: str
    relationship_type: str = "required"
    explanation: Optional[str] = None
    source: str = "curated"
    is_ai_proposed: bool = False
    evidence_type: Optional[str] = "expert_curated"


class SemesterGroup(BaseModel):
    semester_number: int = Field(..., description="1-indexed sequence number of the academic semester.")
    courses: List[Dict[str, Any]] = Field(..., description="Courses assigned to this semester wave.")
    course_count: int = Field(..., description="Number of courses in this semester.")


class LearningPathResponse(BaseModel):
    learning_goal: str
    selected_courses: List[Dict[str, Any]]
    ordered_courses: List[Dict[str, Any]]
    semesters: List[SemesterGroup]
    prerequisites: List[PrerequisiteRecord]
    ai_proposals_used: bool = False
    warnings: List[str] = []
    total_courses: int
    total_prerequisites: int
    total_semesters: int


@app.get("/", tags=["General"])
def read_root():
    return {
        "service": settings.service_name,
        "version": settings.version,
        "message": "Dependency-Aware Course Registration Assistant API (Pure DAA Engine)",
        "docs_url": "/docs",
        "health_url": "/api/v1/health",
        "courses_url": "/api/v1/courses",
        "learning_path_url": "/api/v1/learning-path",
    }


@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
@app.get("/api/health", response_model=HealthResponse, tags=["Health"], include_in_schema=False)
@app.get("/health", response_model=HealthResponse, tags=["Health"], include_in_schema=False)
def get_health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service=settings.service_name,
        version=settings.version,
    )


@app.get("/api/v1/courses", tags=["Courses"])
@app.get("/api/courses", tags=["Courses"], include_in_schema=False)
@app.get("/courses", tags=["Courses"], include_in_schema=False)
def get_curated_courses() -> List[Dict[str, Any]]:
    """Returns the complete catalog of courses from the Knowledge Base."""
    kb = get_default_knowledge_base()
    return kb.get_all_courses()


@app.post(
    "/api/v1/learning-path",
    response_model=LearningPathResponse,
    status_code=status.HTTP_200_OK,
    tags=["Learning Path"],
    summary="Generate a topologically sorted, prerequisite-aware course learning path",
)
@app.post(
    "/api/learning-path",
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
    """Accepts selected courses and constraints, resolves catalog records, detects
    graph cycles, and computes a deterministic topologically sorted sequence using Kahn's algorithm.
    """
    try:
        result = generate_learning_path(
            course_names=payload.courses,
            learning_goal=payload.learning_goal,
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
