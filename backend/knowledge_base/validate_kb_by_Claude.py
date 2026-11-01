import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Tuple, Union

VALID_DIFFICULTIES = {"beginner", "intermediate", "advanced"}
VALID_RELATIONSHIP_TYPES = {"required", "recommended", "optional"}
VALID_EVIDENCE_TYPES = {"expert_curated", "llm_proposed"}
COURSE_ID_REGEX = re.compile(r"^[a-z][a-z0-9_]*$")


def validate_kb_data(kb: Any) -> Tuple[List[str], Dict[str, Any]]:
    """Validates knowledge base data structure and integrity rules safely.

    Returns a tuple of (errors_list, stats_dict).
    """
    errors: List[str] = []
    stats: Dict[str, Any] = {
        "courses_count": 0,
        "relationships_count": 0,
        "isolated_courses": [],
        "transitive_relationships": [],
    }

    if not isinstance(kb, dict):
        return [f"Knowledge base root must be a JSON object (dict), got {type(kb).__name__}"], stats

    if "courses" not in kb:
        errors.append("Missing required root key: 'courses'")
    elif not isinstance(kb["courses"], list):
        errors.append(f"'courses' must be a list, got {type(kb['courses']).__name__}")

    if "prerequisites" not in kb:
        errors.append("Missing required root key: 'prerequisites'")
    elif not isinstance(kb["prerequisites"], list):
        errors.append(f"'prerequisites' must be a list, got {type(kb['prerequisites']).__name__}")

    if errors:
        return errors, stats

    course_list = kb["courses"]
    prereq_list = kb["prerequisites"]

    course_ids: set[str] = set()
    seen_names_and_aliases: Dict[str, set[str]] = {}

    # 1. Course validation
    for idx, c in enumerate(course_list):
        if not isinstance(c, dict):
            errors.append(f"Course at index {idx} must be a dict, got {type(c).__name__}")
            continue

        cid = c.get("course_id")
        if cid is None or not isinstance(cid, str) or isinstance(cid, bool) or not cid.strip():
            errors.append(f"Course at index {idx} has invalid 'course_id' (expected non-empty string, got {type(cid).__name__})")
            continue

        if not COURSE_ID_REGEX.fullmatch(cid):
            errors.append(f"Course '{cid}' has invalid ID format (must match ^[a-z][a-z0-9_]*$)")

        if cid in course_ids:
            errors.append(f"Duplicate course_id: '{cid}'")
        course_ids.add(cid)

        for field in ("name", "category", "description"):
            val = c.get(field)
            if val is None or not isinstance(val, str) or isinstance(val, bool) or not val.strip():
                errors.append(f"Course '{cid}' missing or invalid string field '{field}' (got {type(val).__name__})")

        difficulty = c.get("difficulty")
        if difficulty is None or not isinstance(difficulty, str) or isinstance(difficulty, bool):
            errors.append(f"Course '{cid}' missing or invalid difficulty (expected string, got {type(difficulty).__name__})")
        elif difficulty not in VALID_DIFFICULTIES:
            errors.append(
                f"Course '{cid}' has invalid difficulty '{difficulty}' (expected one of {sorted(VALID_DIFFICULTIES)})"
            )

        aliases = c.get("aliases")
        if aliases is None or not isinstance(aliases, list):
            errors.append(f"Course '{cid}' 'aliases' must be a list, got {type(aliases).__name__}")
            aliases = []

        names_to_check: List[str] = []
        c_name = c.get("name")
        if isinstance(c_name, str) and not isinstance(c_name, bool) and c_name.strip():
            names_to_check.append(c_name)

        for a in aliases:
            if a is None or not isinstance(a, str) or isinstance(a, bool) or not a.strip():
                errors.append(f"Course '{cid}' contains empty or non-string alias (got {type(a).__name__})")
            else:
                if a != a.strip():
                    errors.append(f"Course '{cid}' alias '{a}' contains leading/trailing whitespace")
                names_to_check.append(a)

        for n in names_to_check:
            normalized = " ".join(n.strip().split()).lower()
            if normalized not in seen_names_and_aliases:
                seen_names_and_aliases[normalized] = set()
            seen_names_and_aliases[normalized].add(cid)

    # Check ambiguous aliases/names across courses
    for normalized_name, matching_ids in seen_names_and_aliases.items():
        if len(matching_ids) > 1:
            errors.append(
                f"Ambiguous alias/name '{normalized_name}' shared by multiple courses: {sorted(matching_ids)}"
            )

    # 2. Relationship validation
    rel_ids: set[str] = set()
    pairs: set[Tuple[str, str]] = set()
    adj: Dict[str, List[str]] = {cid: [] for cid in course_ids}
    indeg: Dict[str, int] = {cid: 0 for cid in course_ids}

    for idx, r in enumerate(prereq_list):
        if not isinstance(r, dict):
            errors.append(f"Prerequisite at index {idx} must be a dict, got {type(r).__name__}")
            continue

        rid = r.get("relationship_id")
        if rid is None or not isinstance(rid, str) or isinstance(rid, bool) or not rid.strip():
            errors.append(f"Prerequisite at index {idx} missing or invalid 'relationship_id' (got {type(rid).__name__})")
            continue

        if rid in rel_ids:
            errors.append(f"Duplicate relationship_id: '{rid}'")
        rel_ids.add(rid)

        src = r.get("source_course_id")
        tgt = r.get("target_course_id")

        src_valid = True
        tgt_valid = True

        if src is None or not isinstance(src, str) or isinstance(src, bool) or not src.strip():
            errors.append(f"Relationship '{rid}' source_course_id must be a non-empty string, got {type(src).__name__}")
            src_valid = False
        elif src not in course_ids:
            errors.append(f"Relationship '{rid}' has unknown source_course_id: '{src}'")
            src_valid = False

        if tgt is None or not isinstance(tgt, str) or isinstance(tgt, bool) or not tgt.strip():
            errors.append(f"Relationship '{rid}' target_course_id must be a non-empty string, got {type(tgt).__name__}")
            tgt_valid = False
        elif tgt not in course_ids:
            errors.append(f"Relationship '{rid}' has unknown target_course_id: '{tgt}'")
            tgt_valid = False

        if src_valid and tgt_valid:
            if src == tgt:
                errors.append(f"Relationship '{rid}' is a self-loop: '{src}' -> '{tgt}'")
            else:
                pair = (src, tgt)
                if pair in pairs:
                    errors.append(f"Duplicate relationship pair: '{src}' -> '{tgt}'")
                pairs.add(pair)
                adj[src].append(tgt)
                indeg[tgt] += 1

        rel_type = r.get("relationship_type")
        if rel_type is None or not isinstance(rel_type, str) or isinstance(rel_type, bool):
            errors.append(f"Relationship '{rid}' missing or invalid relationship_type (expected string, got {type(rel_type).__name__})")
        elif rel_type not in VALID_RELATIONSHIP_TYPES:
            errors.append(
                f"Relationship '{rid}' has invalid relationship_type '{rel_type}' (expected {sorted(VALID_RELATIONSHIP_TYPES)})"
            )

        ev_type = r.get("evidence_type")
        if ev_type is None or not isinstance(ev_type, str) or isinstance(ev_type, bool):
            errors.append(f"Relationship '{rid}' missing or invalid evidence_type (expected string, got {type(ev_type).__name__})")
        elif ev_type not in VALID_EVIDENCE_TYPES:
            errors.append(
                f"Relationship '{rid}' has invalid evidence_type '{ev_type}' (expected {sorted(VALID_EVIDENCE_TYPES)})"
            )

        conf = r.get("confidence")
        if isinstance(conf, bool):
            errors.append(f"Relationship '{rid}' confidence cannot be a boolean value (must be float or int)")
        elif not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
            errors.append(
                f"Relationship '{rid}' has invalid confidence '{conf}' (must be number between 0.0 and 1.0, got {type(conf).__name__})"
            )

        explanation = r.get("explanation")
        if explanation is None or not isinstance(explanation, str) or isinstance(explanation, bool) or not explanation.strip():
            errors.append(f"Relationship '{rid}' missing or invalid 'explanation' (expected non-empty string, got {type(explanation).__name__})")

    # 3. Cycle detection using Kahn's algorithm
    if not errors:
        zero_indeg = [cid for cid, deg in indeg.items() if deg == 0]
        queue = list(zero_indeg)
        processed_count = 0
        temp_indeg = dict(indeg)

        while queue:
            u = queue.pop(0)
            processed_count += 1
            for v in adj[u]:
                temp_indeg[v] -= 1
                if temp_indeg[v] == 0:
                    queue.append(v)

        if processed_count != len(course_ids):
            cycle_nodes = [cid for cid, deg in temp_indeg.items() if deg > 0]
            errors.append(f"Graph contains a cycle involving nodes: {sorted(cycle_nodes)}")

    # 4. Transitive/redundant edges (informational only; not an error, never deleted)
    def is_reachable(a: str, b: str, skip_edge: Tuple[str, str]) -> bool:
        stack = [a]
        visited = set()
        while stack:
            curr = stack.pop()
            for neighbor in adj[curr]:
                if (curr, neighbor) == skip_edge or neighbor in visited:
                    continue
                if neighbor == b:
                    return True
                visited.add(neighbor)
                stack.append(neighbor)
        return False

    transitive = [f"{s}->{t}" for s, t in pairs if is_reachable(s, t, (s, t))]

    stats["courses_count"] = len(course_ids)
    stats["relationships_count"] = len(pairs)
    stats["isolated_courses"] = [cid for cid in course_ids if indeg[cid] == 0 and not adj[cid]]
    stats["transitive_relationships"] = transitive

    return errors, stats


def validate_kb_file(file_path: Union[str, Path]) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Loads and validates a Knowledge Base JSON file.

    Returns (is_valid, errors, stats).
    """
    path = Path(file_path)
    if not path.is_file():
        return False, [f"Knowledge Base file not found: {path}"], {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        return False, [f"Malformed JSON in {path}: {exc}"], {}
    except Exception as exc:
        return False, [f"Error reading {path}: {exc}"], {}

    errors, stats = validate_kb_data(data)
    return len(errors) == 0, errors, stats


def main() -> int:
    default_path = Path(__file__).resolve().parent / "courses.json"
    target_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path

    is_valid, errors, stats = validate_kb_file(target_path)
    if is_valid:
        print(
            f"Validation successful: {stats['courses_count']} courses, "
            f"{stats['relationships_count']} prerequisite relationships validated."
        )
        if stats.get("isolated_courses"):
            print(f"Isolated courses: {stats['isolated_courses']}")
        if stats.get("transitive_relationships"):
            print(f"Informational - Transitive relationships detected: {stats['transitive_relationships']}")
        return 0
    else:
        print(f"VALIDATION FAILED ({len(errors)} error(s) found):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
