import json
import math
import os
import re
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union

VALID_RELATIONSHIP_TYPES = {"required", "recommended", "optional"}


# --- AI Engine Exceptions ---

class AIEngineError(Exception):
    """Base exception for all AI Engine operations."""
    pass


class AIAuthenticationError(AIEngineError):
    """Raised when API credentials are missing, invalid, or unauthorized."""
    pass


class AIConfigurationError(AIAuthenticationError):
    """Raised when API credentials are not configured or missing from the environment."""
    pass


class AIRateLimitError(AIEngineError):
    """Raised when API rate limits or quota thresholds are exceeded."""
    pass


class AITimeoutError(AIEngineError):
    """Raised when an AI API request exceeds the configured timeout."""
    pass


class AIConnectionError(AIEngineError):
    """Raised when network connectivity errors prevent reaching the API."""
    pass


class AIServiceError(AIEngineError):
    """Raised when an upstream AI service returns an API error or is unavailable."""
    pass


class AIResponseValidationError(AIEngineError):
    """Raised when the AI model returns malformed, unparseable, or schema-violating output."""

    def __init__(self, message: str, validation_errors: Optional[List[str]] = None):
        super().__init__(message)
        self.validation_errors: List[str] = validation_errors or []


# --- Client Factory ---

def _get_configured_api_key(api_key: Optional[str] = None) -> Optional[str]:
    """Retrieves the API key from argument, environment, or settings without logging secrets."""
    if api_key and api_key.strip():
        return api_key.strip()
    env_key = os.getenv("GEMINI_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()
    try:
        from backend.core_engine.config import settings
        return settings.gemini_api_key
    except Exception:
        return None


def _get_configured_model(model: Optional[str] = None) -> str:
    """Retrieves the configured model identifier from argument, environment, or settings."""
    if model and model.strip():
        return model.strip()
    env_model = os.getenv("GEMINI_MODEL")
    if env_model and env_model.strip():
        return env_model.strip()
    try:
        from backend.core_engine.config import settings
        if settings.gemini_model and settings.gemini_model.strip():
            return settings.gemini_model.strip()
    except Exception:
        pass
    return "gemini-3.5-flash-lite"


def get_genai_client(api_key: Optional[str] = None, timeout_ms: Optional[int] = None) -> Any:
    """Initializes and returns a Google Gen AI client with configured credentials and timeout.

    Raises AIConfigurationError if the API key is missing or blank.
    Never prints or logs the API key.
    """
    raw_env_key = os.getenv("GEMINI_API_KEY")
    if (api_key is not None and not api_key.strip()) or (raw_env_key is not None and not raw_env_key.strip()):
        raise AIConfigurationError(
            "GEMINI_API_KEY is configured but empty. "
            "Please provide a valid Gemini API key in your environment or project .env file."
        )

    key = _get_configured_api_key(api_key)
    if not key or not key.strip():
        raise AIConfigurationError(
            "GEMINI_API_KEY environment variable is not configured. "
            "Please configure GEMINI_API_KEY in your environment or project .env file."
        )

    try:
        from google import genai
        from google.genai import types

        http_opts = types.HttpOptions(timeout=timeout_ms) if timeout_ms else None
        return genai.Client(api_key=key.strip(), http_options=http_opts)
    except Exception as exc:
        raise AIServiceError(f"Failed to initialize Google Gen AI client: {exc}") from exc


def _extract_response_text(response: Any) -> str:
    """Safely extracts text content from a model completion response."""
    content = getattr(response, "text", None)
    if content is None:
        if isinstance(response, str):
            content = response
        elif isinstance(response, dict) and "text" in response:
            content = response["text"]
        else:
            raise AIResponseValidationError("Malformed completion response from Gemini API provider.")

    if not content or not str(content).strip():
        raise AIResponseValidationError("Gemini model returned an empty response.")

    return str(content)


def _handle_gemini_exception(exc: Exception, timeout_sec: float, timeout_ms: int) -> None:
    """Maps Google Gen AI SDK exceptions into domain-specific exception types without leaking credentials."""
    exc_type = type(exc).__name__
    exc_str = str(exc).lower()
    code = getattr(exc, "code", None)

    if code in (401, 403) or any(
        term in exc_type.lower() or term in exc_str
        for term in ["unauthenticated", "auth", "permissiondenied", "api_key_invalid", "401", "403"]
    ):
        raise AIAuthenticationError("Gemini API authentication failed: invalid or unauthorized API credentials.") from exc
    elif code == 429 or any(
        term in exc_type.lower() or term in exc_str
        for term in ["resourceexhausted", "ratelimit", "quota", "429"]
    ):
        raise AIRateLimitError("Gemini API rate limit or quota exceeded.") from exc
    elif code == 504 or any(
        term in exc_type.lower() or term in exc_str
        for term in ["timeout", "deadlineexceeded", "504"]
    ):
        raise AITimeoutError(f"Gemini API request timed out after {timeout_sec}s ({timeout_ms}ms).") from exc
    elif code == 404 or any(
        term in exc_str
        for term in ["not found", "is not found", "no longer available"]
    ):
        raise AIServiceError(f"Configured Gemini model is not supported or not found: {exc}") from exc
    elif code == 503 or any(
        term in exc_str or term in exc_type.lower()
        for term in ["unavailable", "high demand", "serviceunavailable"]
    ):
        raise AIServiceError(f"Gemini API service is temporarily unavailable (high demand / capacity): {exc}") from exc
    elif any(
        term in exc_type.lower() or term in exc_str
        for term in ["connect", "network", "socket", "connectionerror", "connecterror"]
    ):
        raise AIConnectionError(f"Failed to connect to Gemini API endpoint: {exc}") from exc
    else:
        raise AIServiceError(f"Unexpected error communicating with Gemini API: {exc}") from exc


# --- Course Evaluation Builder & Validator (for Unknown Courses) ---

def build_course_evaluation_prompt(
    queries: List[str],
    learning_goal: Optional[str] = None,
    other_courses: Optional[List[str]] = None,
    curated_candidates: Optional[Dict[str, List[Dict[str, str]]]] = None,
) -> Dict[str, str]:
    """Constructs system and user prompts to evaluate unrecognized course queries.

    When learning_goal, other_courses, and curated_candidates are provided,
    the prompt enables context-aware disambiguation: the model can pick the
    best-matching curated course instead of simply declaring ambiguity.
    """
    # Build context-aware disambiguation instructions when context is available
    has_context = bool(learning_goal or other_courses or curated_candidates)

    system_prompt = (
        "You are an academic curriculum advisor and computer science education expert.\n"
        "Your task is to evaluate user course queries that were not recognized in the university knowledge base,\n"
        "and determine whether each query plausibly refers to a legitimate academic course or technical subject.\n\n"
        "MANDATORY INSTRUCTIONS:\n"
        "1. Return ONLY a valid JSON object matching this exact schema:\n"
        "{\n"
        '  "evaluations": [\n'
        "    {\n"
        '      "query": "<original query string exactly as provided>",\n'
        '      "is_plausible": true | false,\n'
        '      "is_ambiguous": true | false,\n'
        '      "resolved_from_context": true | false,\n'
        '      "canonical_name": "<formal title-cased academic course title or Not Applicable>",\n'
        '      "course_id": "<concise snake_case identifier, letters and numbers only, e.g. quantum_computing>",\n'
        '      "category": "<academic field/discipline>",\n'
        '      "difficulty": "beginner" | "intermediate" | "advanced",\n'
        '      "description": "<concise 1-2 sentence academic summary>",\n'
        '      "clarification": "<explanation if ambiguous, or null>",\n'
        '      "selected_candidate_id": "<course_id from curated candidates if picking one, or null>"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "2. If the query is gibberish, non-academic (e.g. random letters, offensive terms, unrelated topics), "
        "set is_plausible to false.\n"
        "3. CONTEXTUAL DISAMBIGUATION: When a learning goal and other selected courses are provided, "
        "use them to infer the most likely meaning of an ambiguous query. For example, 'English' combined "
        "with a goal of 'NLP Research' most likely means 'English Composition' or 'English Linguistics'. "
        "If curated candidates are listed for a query, prefer picking one of those candidates and set "
        "selected_candidate_id to that candidate's course_id, set resolved_from_context to true, and "
        "set is_ambiguous to false.\n"
        "4. ONLY set is_ambiguous to true if the query is genuinely too broad to resolve even with context "
        "(e.g. 'Science' with no relevant learning goal). Provide a clarification message in that case.\n"
        "5. Output pure JSON without markdown fences or conversational text."
    )

    # Build user prompt with context information
    user_lines = ["Evaluate the following course queries:"]
    user_lines.extend(f"- {q}" for q in queries)

    if learning_goal:
        user_lines.append(f"\nStudent's Learning Goal: {learning_goal}")

    if other_courses:
        user_lines.append("\nOther courses the student selected:")
        user_lines.extend(f"- {c}" for c in other_courses)

    if curated_candidates:
        user_lines.append("\nCurated course candidates from the knowledge base (prefer these when applicable):")
        for query, candidates in curated_candidates.items():
            cand_strs = [f"{c.get('course_id', '?')}: {c.get('name', '?')}" for c in candidates]
            user_lines.append(f"  For '{query}': {', '.join(cand_strs)}")

    user_prompt = "\n".join(user_lines)
    return {"system": system_prompt, "user": user_prompt}


def validate_course_evaluations(
    raw_data: Union[str, Dict[str, Any], List[Any]],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Validates raw model output for unknown course evaluations."""
    errors: List[str] = []
    valid_evaluations: List[Dict[str, Any]] = []

    # 1. Parse JSON if string
    if isinstance(raw_data, str):
        text = raw_data.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            return [], [f"Failed to parse course evaluation response as JSON: {exc}"]
    elif isinstance(raw_data, (dict, list)):
        data = raw_data
    else:
        return [], [f"Unexpected evaluation response type: {type(raw_data).__name__}"]

    # 2. Extract list of evaluations
    if isinstance(data, dict):
        if "evaluations" not in data:
            return [], ["Missing required root key 'evaluations' in AI response"]
        raw_list = data["evaluations"]
    elif isinstance(data, list):
        raw_list = data
    else:
        return [], [f"Root of AI course evaluation must be a dict with 'evaluations' key, got {type(data).__name__}"]

    if not isinstance(raw_list, list):
        return [], [f"'evaluations' must be a list, got {type(raw_list).__name__}"]

    for idx, item in enumerate(raw_list):
        if not isinstance(item, dict):
            errors.append(f"Evaluation at index {idx} must be a dict, got {type(item).__name__}")
            continue

        query = item.get("query")
        if query is None or not isinstance(query, str) or not query.strip():
            errors.append(f"Evaluation at index {idx} missing or invalid 'query'")
            continue

        is_plausible = item.get("is_plausible")
        if not isinstance(is_plausible, bool):
            errors.append(f"Evaluation at index {idx} has non-boolean 'is_plausible'")
            continue

        is_ambiguous = item.get("is_ambiguous", False)
        if not isinstance(is_ambiguous, bool):
            errors.append(f"Evaluation at index {idx} has non-boolean 'is_ambiguous'")
            continue

        canonical_name = item.get("canonical_name", query)
        if not isinstance(canonical_name, str) or not canonical_name.strip():
            canonical_name = query.strip()

        raw_cid = item.get("course_id", "")
        if not isinstance(raw_cid, str) or not raw_cid.strip():
            raw_cid = re.sub(r"[^a-z0-9_]+", "_", canonical_name.lower()).strip("_")
        course_id = re.sub(r"[^a-z0-9_]+", "_", raw_cid.lower()).strip("_")
        if not course_id:
            course_id = f"course_{idx+1}"

        difficulty = str(item.get("difficulty", "intermediate")).lower().strip()
        if difficulty not in ("beginner", "intermediate", "advanced"):
            difficulty = "intermediate"

        category = item.get("category", "General Computer Science")
        if not isinstance(category, str) or not category.strip():
            category = "General Computer Science"

        description = item.get("description", "")
        if not isinstance(description, str) or not description.strip():
            description = f"Academic course: {canonical_name}"

        clarification = item.get("clarification")
        if clarification is not None and not isinstance(clarification, str):
            clarification = str(clarification)

        resolved_from_context = item.get("resolved_from_context", False)
        if not isinstance(resolved_from_context, bool):
            resolved_from_context = False

        selected_candidate_id = item.get("selected_candidate_id")
        if selected_candidate_id is not None and not isinstance(selected_candidate_id, str):
            selected_candidate_id = None

        valid_evaluations.append({
            "query": query.strip(),
            "is_plausible": is_plausible,
            "is_ambiguous": is_ambiguous,
            "resolved_from_context": resolved_from_context,
            "canonical_name": canonical_name.strip(),
            "course_id": course_id,
            "category": category.strip(),
            "difficulty": difficulty,
            "description": description.strip(),
            "clarification": clarification.strip() if clarification else None,
            "selected_candidate_id": selected_candidate_id.strip() if selected_candidate_id else None,
        })

    return valid_evaluations, errors


def evaluate_unknown_courses(
    queries: List[str],
    client: Optional[Any] = None,
    model: Optional[str] = None,
    timeout: Optional[float] = None,
    learning_goal: Optional[str] = None,
    other_courses: Optional[List[str]] = None,
    curated_candidates: Optional[Dict[str, List[Dict[str, str]]]] = None,
) -> List[Dict[str, Any]]:
    """Evaluates unrecognized course queries with Google Gemini to identify plausible courses.

    When learning_goal, other_courses, and curated_candidates are provided,
    the AI receives context that enables it to disambiguate broad queries
    (e.g., 'English' → 'English Composition') instead of rejecting them.
    """
    if not queries:
        return []

    model_name = _get_configured_model(model)
    timeout_sec, timeout_ms = validate_and_convert_timeout(timeout)

    if client is None:
        client = get_genai_client(timeout_ms=timeout_ms)

    prompt = build_course_evaluation_prompt(
        queries,
        learning_goal=learning_goal,
        other_courses=other_courses,
        curated_candidates=curated_candidates,
    )

    try:
        from backend.core_engine.config import settings
        max_attempts = settings.gemini_max_retries
    except Exception:
        max_attempts = 2
    response = None
    for attempt in range(1, max_attempts + 1):
        try:
            try:
                from google.genai import types

                config = types.GenerateContentConfig(
                    system_instruction=prompt["system"],
                    response_mime_type="application/json",
                    temperature=0.0,
                )
            except Exception:
                config = {"response_mime_type": "application/json", "temperature": 0.0}

            response = client.models.generate_content(
                model=model_name,
                contents=prompt["user"],
                config=config,
            )
            break
        except Exception as exc:
            exc_str = str(exc).lower()
            code = getattr(exc, "code", None)
            is_transient = code == 503 or "unavailable" in exc_str or "high demand" in exc_str
            if is_transient and attempt < max_attempts:
                import time
                time.sleep(1.0)
                continue
            _handle_gemini_exception(exc, timeout_sec, timeout_ms)

    content = _extract_response_text(response)
    valid_evaluations, validation_errors = validate_course_evaluations(content)
    if validation_errors:
        raise AIResponseValidationError(
            f"AI course evaluation failed schema validation with {len(validation_errors)} error(s): {'; '.join(validation_errors)}",
            validation_errors=validation_errors,
        )

    return valid_evaluations


# --- Prerequisite Proposal Builder & Validator ---

def build_prerequisite_prompt(
    learning_goal: str,
    courses: List[Dict[str, Any]],
    existing_prerequisites: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, str]:
    """Constructs system and user prompts requesting structured prerequisite proposals."""
    system_prompt = (
        "You are an academic curriculum advisor and computer science education expert.\n"
        "Your task is to analyze a student's selected courses and learning goal to propose "
        "POTENTIALLY MISSING prerequisite relationships between the selected courses.\n\n"
        "MANDATORY INSTRUCTIONS:\n"
        "1. Return ONLY a valid JSON object matching this exact schema:\n"
        "{\n"
        '  "proposals": [\n'
        "    {\n"
        '      "source_course_id": "<prerequisite_course_id>",\n'
        '      "target_course_id": "<dependent_course_id>",\n'
        '      "relationship_type": "required" | "recommended" | "optional",\n'
        '      "confidence": <float between 0.0 and 1.0>,\n'
        '      "explanation": "<concise educational reason>"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "2. Use ONLY course IDs provided in the user's course list. NEVER invent or hallucinate course IDs.\n"
        "3. Relationship direction MUST strictly be: source_course_id (prerequisite) -> target_course_id (dependent).\n"
        "4. Do NOT propose relationships that are already listed in the existing prerequisites.\n"
        "5. If no additional prerequisite relationships are justified among the selected courses, return {\"proposals\": []}.\n"
        "6. Confidence must be a numeric float between 0.0 and 1.0 (do NOT use boolean values).\n"
        "7. Output pure JSON without markdown code fences or conversational prose."
    )

    course_lines = []
    for c in courses:
        cid = c.get("course_id", "")
        name = c.get("name", "")
        desc = c.get("description", "")
        course_lines.append(f"- {cid}: {name} ({desc})")

    existing_lines = []
    for r in (existing_prerequisites or []):
        src = r.get("source_course_id") or r.get("from", "")
        tgt = r.get("target_course_id") or r.get("to", "")
        rel_type = r.get("relationship_type", "prerequisite")
        if src and tgt:
            existing_lines.append(f"- {src} -> {tgt} [{rel_type}]")

    user_prompt = (
        f"Learning Goal: {learning_goal.strip() if learning_goal else 'General Computer Science'}\n\n"
        "Selected Courses:\n"
        + ("\n".join(course_lines) if course_lines else "- (No courses supplied)")
        + "\n\nExisting Known Prerequisites (do NOT repeat these):\n"
        + ("\n".join(existing_lines) if existing_lines else "- (None)")
        + "\n\nPropose any missing prerequisite relationships among these selected courses."
    )

    return {"system": system_prompt, "user": user_prompt}


def validate_ai_proposals(
    raw_data: Union[str, Dict[str, Any], List[Any]],
    allowed_course_ids: Set[str],
    existing_relationships: Optional[Iterable[Tuple[str, str]]] = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Validates raw model output against the structured proposal schema."""
    errors: List[str] = []
    valid_proposals: List[Dict[str, Any]] = []

    # 1. Parse JSON if string
    if isinstance(raw_data, str):
        text = raw_data.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            return [], [f"Failed to parse model response as JSON: {exc}"]
    elif isinstance(raw_data, (dict, list)):
        data = raw_data
    else:
        return [], [f"Unexpected response type: {type(raw_data).__name__} (expected JSON string or dict)"]

    # 2. Extract list of proposals
    if isinstance(data, dict):
        if "proposals" not in data:
            return [], ["Missing required root key 'proposals' in AI response"]
        raw_list = data["proposals"]
    elif isinstance(data, list):
        raw_list = data
    else:
        return [], [f"Root of AI response must be a dict with 'proposals' key, got {type(data).__name__}"]

    if not isinstance(raw_list, list):
        return [], [f"'proposals' must be a list, got {type(raw_list).__name__}"]

    # 3. Validate each proposal item
    seen_pairs: Set[Tuple[str, str]] = set()
    existing_pairs: Set[Tuple[str, str]] = set(existing_relationships or [])

    for idx, item in enumerate(raw_list):
        if not isinstance(item, dict):
            errors.append(f"Proposal at index {idx} must be a dict, got {type(item).__name__}")
            continue

        src = item.get("source_course_id")
        tgt = item.get("target_course_id")

        if src is None or not isinstance(src, str) or isinstance(src, bool) or not src.strip():
            errors.append(f"Proposal at index {idx} missing or invalid 'source_course_id'")
            continue

        if tgt is None or not isinstance(tgt, str) or isinstance(tgt, bool) or not tgt.strip():
            errors.append(f"Proposal at index {idx} missing or invalid 'target_course_id'")
            continue

        src = src.strip()
        tgt = tgt.strip()

        if src not in allowed_course_ids:
            errors.append(f"Proposal at index {idx} references unknown source_course_id: '{src}'")
            continue

        if tgt not in allowed_course_ids:
            errors.append(f"Proposal at index {idx} references unknown target_course_id: '{tgt}'")
            continue

        if src == tgt:
            errors.append(f"Proposal at index {idx} is self-referential: '{src}' -> '{tgt}'")
            continue

        rel_type = item.get("relationship_type")
        if rel_type is None or not isinstance(rel_type, str) or isinstance(rel_type, bool) or rel_type not in VALID_RELATIONSHIP_TYPES:
            errors.append(
                f"Proposal at index {idx} has invalid relationship_type '{rel_type}' "
                f"(expected one of {sorted(VALID_RELATIONSHIP_TYPES)})"
            )
            continue

        conf = item.get("confidence")
        if isinstance(conf, bool):
            errors.append(f"Proposal at index {idx} confidence cannot be a boolean value")
            continue
        if not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
            errors.append(f"Proposal at index {idx} has invalid confidence '{conf}' (must be float between 0.0 and 1.0)")
            continue

        explanation = item.get("explanation")
        if explanation is None or not isinstance(explanation, str) or isinstance(explanation, bool) or not explanation.strip():
            errors.append(f"Proposal at index {idx} missing or invalid 'explanation'")
            continue

        pair = (src, tgt)
        if pair in existing_pairs:
            errors.append(f"Proposal '{src}' -> '{tgt}' already exists in Knowledge Base")
            continue

        if pair in seen_pairs:
            errors.append(f"Duplicate proposal pair in AI response: '{src}' -> '{tgt}'")
            continue

        seen_pairs.add(pair)
        valid_proposals.append({
            "source_course_id": src,
            "target_course_id": tgt,
            "relationship_type": rel_type,
            "confidence": float(conf),
            "explanation": explanation.strip(),
        })

    return valid_proposals, errors


# --- Timeout Helper ---

def validate_and_convert_timeout(timeout_seconds: Union[int, float, str, None] = None) -> Tuple[float, int]:
    """Validates timeout in seconds and converts it to milliseconds for the SDK."""
    if timeout_seconds is None:
        raw_env = os.getenv("GEMINI_TIMEOUT")
        if raw_env is not None:
            try:
                val = float(raw_env)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Invalid GEMINI_TIMEOUT environment value '{raw_env}': must be a positive number of seconds.") from exc
        else:
            try:
                from backend.core_engine.config import settings
                val = settings.gemini_timeout
            except Exception:
                val = 15.0
    else:
        try:
            val = float(timeout_seconds)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid timeout value '{timeout_seconds}': must be a positive number of seconds.") from exc

    if math.isnan(val) or math.isinf(val) or val <= 0.0:
        raise ValueError(f"Invalid timeout value '{val}': timeout must be a finite, positive number of seconds.")

    timeout_ms = int(round(val * 1000))
    return val, timeout_ms


# --- Prerequisite Proposals Execution Interface ---

class ProposalList(list):
    """List of valid proposals carrying validation diagnostics and metrics."""

    def __init__(
        self,
        items: Optional[Iterable[Dict[str, Any]]] = None,
        validation_errors: Optional[List[str]] = None,
        total_received: int = 0,
    ):
        super().__init__(items or [])
        self.validation_errors: List[str] = validation_errors or []
        self.total_received: int = total_received


def request_prerequisite_proposals(
    learning_goal: str,
    courses: List[Dict[str, Any]],
    existing_prerequisites: Optional[List[Dict[str, Any]]] = None,
    client: Optional[Any] = None,
    model: Optional[str] = None,
    timeout: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Requests and validates prerequisite proposals from Google Gemini."""
    model_name = _get_configured_model(model)
    timeout_sec, timeout_ms = validate_and_convert_timeout(timeout)

    # Initialize client if not injected
    if client is None:
        client = get_genai_client(timeout_ms=timeout_ms)

    # Build prompt
    prompt = build_prerequisite_prompt(learning_goal, courses, existing_prerequisites)

    try:
        from backend.core_engine.config import settings
        max_attempts = settings.gemini_max_retries
    except Exception:
        max_attempts = 2
    response = None
    for attempt in range(1, max_attempts + 1):
        try:
            try:
                from google.genai import types

                config = types.GenerateContentConfig(
                    system_instruction=prompt["system"],
                    response_mime_type="application/json",
                    temperature=0.0,
                )
            except Exception:
                config = {"response_mime_type": "application/json", "temperature": 0.0}

            response = client.models.generate_content(
                model=model_name,
                contents=prompt["user"],
                config=config,
            )
            break
        except Exception as exc:
            exc_str = str(exc).lower()
            code = getattr(exc, "code", None)
            is_transient = code == 503 or "unavailable" in exc_str or "high demand" in exc_str
            if is_transient and attempt < max_attempts:
                import time
                time.sleep(1.0)
                continue
            _handle_gemini_exception(exc, timeout_sec, timeout_ms)

    content = _extract_response_text(response)

    allowed_ids = {c["course_id"] for c in courses if isinstance(c, dict) and "course_id" in c}
    existing_pairs = set()
    for r in (existing_prerequisites or []):
        if isinstance(r, dict):
            src = r.get("source_course_id") or r.get("from")
            tgt = r.get("target_course_id") or r.get("to")
            if src and tgt:
                existing_pairs.add((src, tgt))

    valid_proposals, validation_errors = validate_ai_proposals(content, allowed_ids, existing_pairs)
    total_received = len(valid_proposals) + len(validation_errors)

    # If proposals were returned but none were valid, raise validation error
    if validation_errors and not valid_proposals:
        raise AIResponseValidationError(
            f"AI proposal validation failed with {len(validation_errors)} error(s): {'; '.join(validation_errors)}",
            validation_errors=validation_errors,
        )

    return ProposalList(valid_proposals, validation_errors=validation_errors, total_received=total_received)
