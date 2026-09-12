# pyrefly: ignore [missing-import]
from app.webhook.line_map import build_line_map, find_nearest_valid_line


def test_single_hunk_tracks_context_and_additions_not_deletions() -> None:
    patch = """@@ -10,4 +10,5 @@
 context one
-removed line
+added one
 context two
+added two
 context three"""
    # New lines are: context=10, added=11, context=12, added=13, context=14.
    assert build_line_map(patch) == {10, 11, 12, 13, 14}


def test_multiple_hunks_reset_to_each_new_start() -> None:
    patch = """@@ -1,2 +1,3 @@
 alpha
+beta
 gamma
@@ -20,2 +21,1 @@
-old
 kept"""
    # First hunk yields 1,2,3. Second starts at new line 21; deletion is invalid, context is 21.
    assert build_line_map(patch) == {1, 2, 3, 21}


def test_nearest_valid_line_prefers_lower_line_then_honours_window() -> None:
    valid_lines = {4, 8, 12}
    assert find_nearest_valid_line(8, valid_lines) == 8
    assert find_nearest_valid_line(6, valid_lines) == 4
    assert find_nearest_valid_line(10, valid_lines, window=1) is None
    assert find_nearest_valid_line(10, valid_lines, window=2) == 8
