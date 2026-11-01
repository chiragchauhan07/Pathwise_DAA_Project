"""Knowledge Base package for course catalog and prerequisite records."""

from backend.knowledge_base.knowledge_base import (
    CourseResolution,
    KnowledgeBase,
    ResolutionStatus,
    get_default_knowledge_base,
    load_knowledge_base,
    normalize_course_name,
    resolve_course,
)

__all__ = [
    "CourseResolution",
    "KnowledgeBase",
    "ResolutionStatus",
    "get_default_knowledge_base",
    "load_knowledge_base",
    "normalize_course_name",
    "resolve_course",
]
