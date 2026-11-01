"""AI Engine: LLM API integration, prompt generation, structured proposal validation, and error handling."""

from backend.ai_engine.client import (
    AIAuthenticationError,
    AIConfigurationError,
    AIConnectionError,
    AIEngineError,
    AIRateLimitError,
    AIResponseValidationError,
    AIServiceError,
    AITimeoutError,
    build_course_evaluation_prompt,
    build_prerequisite_prompt,
    evaluate_unknown_courses,
    get_genai_client,
    request_prerequisite_proposals,
    validate_ai_proposals,
    validate_and_convert_timeout,
    validate_course_evaluations,
)

__all__ = [
    "AIAuthenticationError",
    "AIConfigurationError",
    "AIConnectionError",
    "AIEngineError",
    "AIRateLimitError",
    "AIResponseValidationError",
    "AIServiceError",
    "AITimeoutError",
    "build_course_evaluation_prompt",
    "build_prerequisite_prompt",
    "evaluate_unknown_courses",
    "get_genai_client",
    "request_prerequisite_proposals",
    "validate_ai_proposals",
    "validate_and_convert_timeout",
    "validate_course_evaluations",
]
