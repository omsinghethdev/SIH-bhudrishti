"""One-off surgery on frontend/App.js: turn the hardcoded demo constants into
mutable globals that api.js hydrates from the backend.

Run once:  python scripts/wire_frontend.py
It is idempotent — re-running reports "already wired" and changes nothing.
"""
import re
import sys
from pathlib import Path

APP_JS = Path(__file__).resolve().parents[2] / "frontend" / "App.js"

# name -> the empty initializer that replaces the hardcoded literal
BLANK = {
    "LEVELS": "[]",
    "UNIT_402": "{}",
    "LEVEL_DETAIL": "{}",
    "BUILDINGS_EXTRA": "{}",
    "LAKEVIEW_META": "{ infra: {} }",
    "INFRA_PROFILES": "{}",
    "LOCALITY": "{ buildings: [], genericBuildings: [], metro: { stations: [] }, rail: {}, parks: [] }",
    "CONFLICTS": "[]",
    "APPROVAL_COLUMNS": "[]",
    "DATASETS": "[]",
    "FLOOR_REVIEW": "[]",
    "REPORTS": "[]",
    "ACTIVITY": "[]",
    "PERMISSION_MATRIX": "[]",
    "DEMO_USERS": "[]",
    "SEARCH_RESULTS": "[]",
    "LADM_MAPPING": "[]",
    "LEGACY_MAPPING": "[]",
    "VSTACK_ROAD_INFO": "{}",
}

OPEN = {"{": "}", "[": "]", "(": ")"}


def find_literal_end(text: str, start: int) -> int:
    """Index just past the literal beginning at `start` (a [ { or ( )."""
    depth = 0
    i = start
    in_str = None
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == in_str:
                in_str = None
        elif ch in "\"'`":
            in_str = ch
        elif ch in OPEN:
            depth += 1
        elif ch in OPEN.values():
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced literal")


def main() -> int:
    text = APP_JS.read_text(encoding="utf-8")
    if "/* hydrated by api.js */" in text:
        print("App.js already wired — nothing to do.")
        return 0

    replaced = []
    for name, empty in BLANK.items():
        match = re.search(rf"^const {name} = ", text, re.MULTILINE)
        if match is None:
            print(f"  ! {name}: declaration not found, skipped")
            continue
        value_start = match.end()
        if text[value_start] not in OPEN:
            print(f"  ! {name}: value is not a literal, skipped")
            continue
        end = find_literal_end(text, value_start)
        # keep a trailing semicolon if there was one
        tail = ";" if text[end : end + 1] == ";" else ""
        text = (
            text[: match.start()]
            + f"let {name} = {empty};{'' if tail else ''} /* hydrated by api.js */"
            + text[end + len(tail) :]
        )
        replaced.append(name)

    APP_JS.write_text(text, encoding="utf-8")
    print(f"Wired {len(replaced)} constants for hydration: {', '.join(replaced)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
