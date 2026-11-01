from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
import difflib
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Union


class ResolutionStatus(str, Enum):
    """Status outcomes for course resolution."""

    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"
    CORRECTED = "corrected"


@dataclass
class CourseResolution:
    """Represents the outcome of resolving a course query."""

    query: str
    status: ResolutionStatus
    course_id: Optional[str] = None
    canonical_name: Optional[str] = None
    course: Optional[Dict[str, Any]] = None
    candidates: List[str] = field(default_factory=list)
    error_message: Optional[str] = None

    @property
    def is_resolved(self) -> bool:
        return self.status in (ResolutionStatus.RESOLVED, ResolutionStatus.CORRECTED)

    @property
    def is_corrected(self) -> bool:
        return self.status == ResolutionStatus.CORRECTED

    @property
    def is_ambiguous(self) -> bool:
        return self.status == ResolutionStatus.AMBIGUOUS

    @property
    def is_unknown(self) -> bool:
        return self.status == ResolutionStatus.UNKNOWN


def normalize_course_name(name: str) -> str:
    """Normalizes a course name or alias by trimming, collapsing spaces, and lowercasing."""
    if not name:
        return ""
    return " ".join(name.strip().split()).lower()


class KnowledgeBase:
    """Loads, queries, and resolves courses from the knowledge base."""

    def __init__(self, source: Optional[Union[str, Path, Dict[str, Any]]] = None):
        self.source_path: Optional[Path] = None
        self.raw_data: Dict[str, Any] = self._load_data(source)

        self.courses_by_id: Dict[str, Dict[str, Any]] = {}
        self.prerequisites: List[Dict[str, Any]] = self.raw_data.get("prerequisites", [])
        self.canonical_names: Dict[str, str] = {}
        self.alias_to_ids: Dict[str, Set[str]] = defaultdict(set)
        self.course_id_index: Dict[str, str] = {}
        self.word_to_ids: Dict[str, Set[str]] = defaultdict(set)

        self._build_indexes()

    def _load_data(self, source: Optional[Union[str, Path, Dict[str, Any]]]) -> Dict[str, Any]:
        if isinstance(source, dict):
            return source

        if source is not None:
            path = Path(source)
        else:
            path = Path(__file__).resolve().parent / "courses.json"

        self.source_path = path

        if not path.is_file():
            raise FileNotFoundError(f"Knowledge Base file not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSON in knowledge base file {path}: {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError(f"Knowledge base root must be a JSON object, got {type(data).__name__}")

        return data

    def _build_indexes(self) -> None:
        for course in self.raw_data.get("courses", []):
            if not isinstance(course, dict):
                continue

            cid = course.get("course_id")
            if not cid or not isinstance(cid, str):
                continue

            self.courses_by_id[cid] = course
            self.course_id_index[cid.lower()] = cid

            c_name = course.get("name")
            if isinstance(c_name, str) and c_name.strip():
                norm_name = normalize_course_name(c_name)
                self.canonical_names[norm_name] = cid
                self.alias_to_ids[norm_name].add(cid)

                # Index significant individual words for whole-word ambiguity detection
                for raw_w in norm_name.split():
                    w = raw_w.strip(".,;:!?\"'()[]{}")
                    if len(w) >= 3 and w not in {"and", "of", "to", "in", "for", "the", "an", "a", "intro", "introduction"}:
                        self.word_to_ids[w].add(cid)

            aliases = course.get("aliases", [])
            if isinstance(aliases, list):
                for alias in aliases:
                    if isinstance(alias, str) and alias.strip():
                        norm_alias = normalize_course_name(alias)
                        self.alias_to_ids[norm_alias].add(cid)

    def get_course(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a course record by exact course_id."""
        return self.courses_by_id.get(course_id)

    def get_all_courses(self) -> List[Dict[str, Any]]:
        """Returns all courses in the catalog."""
        return list(self.courses_by_id.values())

    def get_prerequisites(self) -> List[Dict[str, Any]]:
        """Returns all prerequisite records."""
        return list(self.prerequisites)

    def resolve_course(self, query: str) -> CourseResolution:
        """Resolves a raw user input string to a canonical course."""
        if not query or not query.strip():
            return CourseResolution(
                query=query,
                status=ResolutionStatus.UNKNOWN,
                error_message="Course query string is empty.",
            )

        norm_query = normalize_course_name(query)

        # 1. Exact match on normalized course_id
        if norm_query in self.course_id_index:
            cid = self.course_id_index[norm_query]
            course = self.courses_by_id[cid]
            return CourseResolution(
                query=query,
                status=ResolutionStatus.RESOLVED,
                course_id=cid,
                canonical_name=course["name"],
                course=course,
            )

        # 2. Match against canonical names and aliases
        if norm_query in self.alias_to_ids:
            matching_ids = self.alias_to_ids[norm_query]
            if len(matching_ids) == 1:
                cid = next(iter(matching_ids))
                course = self.courses_by_id[cid]
                return CourseResolution(
                    query=query,
                    status=ResolutionStatus.RESOLVED,
                    course_id=cid,
                    canonical_name=course["name"],
                    course=course,
                )
            else:
                candidate_names = [self.courses_by_id[c]["name"] for c in sorted(matching_ids) if c in self.courses_by_id]
                return CourseResolution(
                    query=query,
                    status=ResolutionStatus.AMBIGUOUS,
                    candidates=sorted(matching_ids),
                    error_message=(
                        f"Course query '{query.strip()}' is ambiguous and matches multiple courses: "
                        f"{', '.join(candidate_names) if candidate_names else ', '.join(sorted(matching_ids))}"
                    ),
                )

        # 3. Safe normalization (strip punctuation, convert & -> and, remove hyphens/underscores)
        clean_str = norm_query.strip(".,;:!?'\"()[]{}")
        clean_variants = [
            clean_str,
            clean_str.replace("&", "and"),
            clean_str.replace("-", " "),
            clean_str.replace("_", " "),
            " ".join(clean_str.replace("-", " ").replace("&", "and").split()),
        ]
        for variant in clean_variants:
            v = " ".join(variant.strip().split())
            if v in self.alias_to_ids:
                m_ids = self.alias_to_ids[v]
                if len(m_ids) == 1:
                    cid = next(iter(m_ids))
                    course = self.courses_by_id[cid]
                    return CourseResolution(
                        query=query,
                        status=ResolutionStatus.RESOLVED,
                        course_id=cid,
                        canonical_name=course["name"],
                        course=course,
                    )
            if v in self.course_id_index:
                cid = self.course_id_index[v]
                course = self.courses_by_id[cid]
                return CourseResolution(
                    query=query,
                    status=ResolutionStatus.RESOLVED,
                    course_id=cid,
                    canonical_name=course["name"],
                    course=course,
                )

        # 4. Singular / Plural inflection check
        plural_try = [clean_str + "s", clean_str + "es"]
        if clean_str.endswith("s"):
            plural_try.append(clean_str[:-1])
        if clean_str.endswith("es"):
            plural_try.append(clean_str[:-2])

        for cand in plural_try:
            if cand in self.alias_to_ids:
                m_ids = self.alias_to_ids[cand]
                if len(m_ids) == 1:
                    cid = next(iter(m_ids))
                    course = self.courses_by_id[cid]
                    return CourseResolution(
                        query=query,
                        status=ResolutionStatus.RESOLVED,
                        course_id=cid,
                        canonical_name=course["name"],
                        course=course,
                    )

        # 4.5 Whole-word / broad discipline ambiguity check
        # If the input is a single word or generic keyword that appears across multiple curated courses
        # and did not resolve to an exact alias, treat it as ambiguous rather than falsely autocorrecting.
        if clean_str in self.word_to_ids and len(self.word_to_ids[clean_str]) > 1:
            matching_cids = sorted(self.word_to_ids[clean_str])
            candidate_names = [self.courses_by_id[c]["name"] for c in matching_cids if c in self.courses_by_id]
            return CourseResolution(
                query=query,
                status=ResolutionStatus.AMBIGUOUS,
                candidates=matching_cids,
                error_message=(
                    f"Course query '{query.strip()}' is ambiguous and matches multiple courses: "
                    f"{', '.join(candidate_names)}"
                ),
            )

        # 5. High-confidence spelling correction and candidate suggestions
        candidates_scored = []
        for alias_key, id_set in self.alias_to_ids.items():
            # Exclude short acronyms from fuzzy matching longer full words (e.g. do not compare 'data' with 'daa')
            if len(alias_key) <= 3 and len(clean_str) > len(alias_key):
                continue
            ratio = difflib.SequenceMatcher(None, clean_str, alias_key).ratio()
            if ratio >= 0.70:
                candidates_scored.append((ratio, alias_key, id_set))

        candidates_scored.sort(key=lambda x: x[0], reverse=True)

        # High similarity (>= 0.88), query is long enough (>= 6 chars), and clear lead
        if candidates_scored and candidates_scored[0][0] >= 0.88 and len(clean_str) >= 6:
            best_ratio, best_alias, best_ids = candidates_scored[0]

            # Guard: ensure candidate is a genuine character typo, not an extra whole word added/omitted
            best_words = best_alias.split()
            query_words = clean_str.split()
            is_valid_typo = (len(best_words) == len(query_words)) or (len(query_words) > 1 and abs(len(best_words) - len(query_words)) <= 1)

            if is_valid_typo:
                second_diff = True
                if len(candidates_scored) > 1:
                    second_ratio, _, second_ids = candidates_scored[1]
                    if best_ids != second_ids and (best_ratio - second_ratio) < 0.08:
                        second_diff = False

                if second_diff and len(best_ids) == 1:
                    cid = next(iter(best_ids))
                    course = self.courses_by_id[cid]
                    return CourseResolution(
                        query=query,
                        status=ResolutionStatus.CORRECTED,
                        course_id=cid,
                        canonical_name=course["name"],
                        course=course,
                    )

        # Candidates exist between 0.70 and 0.88 -> provide suggestions in error_message
        if candidates_scored:
            suggested_cids = []
            seen_sug = set()
            for _, _, id_set in candidates_scored[:3]:
                for sug_id in sorted(id_set):
                    if sug_id not in seen_sug and sug_id in self.courses_by_id and len(suggested_cids) < 3:
                        seen_sug.add(sug_id)
                        suggested_cids.append(self.courses_by_id[sug_id]["name"])

            sug_text = ", ".join(f"'{name}'" for name in suggested_cids)
            return CourseResolution(
                query=query,
                status=ResolutionStatus.UNKNOWN,
                candidates=list(seen_sug),
                error_message=(
                    f"Course '{query.strip()}' is not recognized in the knowledge base. "
                    f"Did you mean: {sug_text}?"
                ),
            )

        # 6. Completely unrecognized
        return CourseResolution(
            query=query,
            status=ResolutionStatus.UNKNOWN,
            error_message=f"Course '{query.strip()}' is not recognized in the knowledge base.",
        )

    def resolve_courses(self, queries: List[str]) -> List[CourseResolution]:
        """Resolves a list of raw user input course strings."""
        return [self.resolve_course(q) for q in queries]


_default_kb: Optional[KnowledgeBase] = None


def get_default_knowledge_base() -> KnowledgeBase:
    """Returns a singleton KnowledgeBase instance loaded from the default path."""
    global _default_kb
    if _default_kb is None:
        _default_kb = KnowledgeBase()
    return _default_kb


def load_knowledge_base(source: Optional[Union[str, Path, Dict[str, Any]]] = None) -> KnowledgeBase:
    """Factory function to load a KnowledgeBase instance."""
    return KnowledgeBase(source=source)


def resolve_course(query: str, kb: Optional[KnowledgeBase] = None) -> CourseResolution:
    """Convenience function to resolve a course using default or provided KnowledgeBase."""
    target_kb = kb or get_default_knowledge_base()
    return target_kb.resolve_course(query)
