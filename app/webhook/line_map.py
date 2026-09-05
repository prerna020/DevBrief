from __future__ import annotations

import re

HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def build_line_map(patch: str) -> set[int]:
    """Return new-file lines that GitHub accepts as inline-comment targets."""
    valid_lines: set[int] = set()
    old_line = new_line = 0
    in_hunk = False
    for line in patch.splitlines():
        header = HUNK_HEADER.match(line)
        if header:
            old_line = int(header.group(1))
            new_line = int(header.group(3))
            in_hunk = True
            continue
        if not in_hunk:
            continue
        if line.startswith("+"):
            valid_lines.add(new_line)
            new_line += 1
        elif line.startswith("-"):
            old_line += 1
        elif line.startswith(" "):
            valid_lines.add(new_line)
            old_line += 1
            new_line += 1
    return valid_lines


def find_nearest_valid_line(requested: int, valid_lines: set[int], window: int = 3) -> int | None:
    if requested in valid_lines:
        return requested
    for distance in range(1, window + 1):
        if requested - distance in valid_lines:
            return requested - distance
        if requested + distance in valid_lines:
            return requested + distance
    return None

