"""
Diff processing and sanitization.

Handles cleaning raw git diffs before sending them to the LLM:
- Strips binary file diffs
- Removes lock file noise
- Collapses oversized hunks
- Truncates to token budget
"""

import re

# Files whose diffs are pure noise and should be stripped entirely
IGNORED_FILE_PATTERNS = [
    r"package-lock\.json",
    r"yarn\.lock",
    r"poetry\.lock",
    r"Pipfile\.lock",
    r"pnpm-lock\.yaml",
    r"Cargo\.lock",
    r"go\.sum",
    r"\.min\.js$",
    r"\.min\.css$",
    r"\.map$",
    r"\.snap$",
]

# Regex to match diff file headers like "diff --git a/foo.py b/foo.py"
DIFF_HEADER_RE = re.compile(r"^diff --git a/(.*?) b/(.*?)$", re.MULTILINE)

# Regex to match binary file notices
BINARY_RE = re.compile(
    r"^Binary files .* and .* differ$",
    re.MULTILINE,
)

# Max lines in a single hunk before collapsing
MAX_HUNK_LINES = 200


def _should_ignore_file(filepath: str) -> bool:
    """Check if a file path matches any ignored pattern."""
    return any(re.search(pat, filepath) for pat in IGNORED_FILE_PATTERNS)


def _split_into_file_diffs(raw_diff: str) -> list[dict]:
    """
    Split a unified diff into per-file chunks.

    Returns a list of dicts: {"filepath": str, "content": str}
    """
    parts = re.split(r"(?=^diff --git )", raw_diff, flags=re.MULTILINE)
    file_diffs = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        match = DIFF_HEADER_RE.match(part)
        if match:
            filepath = match.group(2)  # Use the "b/" path (destination)
            file_diffs.append({"filepath": filepath, "content": part})
        elif part:
            # Preamble or non-standard diff chunk — keep it
            file_diffs.append({"filepath": "__preamble__", "content": part})

    return file_diffs


def _collapse_large_hunks(file_diff: str, filepath: str) -> str:
    """
    If a single file diff has too many lines, collapse it to a summary.
    """
    lines = file_diff.split("\n")
    added = sum(1 for ln in lines if ln.startswith("+") and not ln.startswith("+++"))
    removed = sum(1 for ln in lines if ln.startswith("-") and not ln.startswith("---"))

    if len(lines) > MAX_HUNK_LINES:
        return (
            f"diff --git a/{filepath} b/{filepath}\n"
            f"[Large diff collapsed: +{added}/-{removed} lines in {filepath}]"
        )
    return file_diff


def process_diff(raw_diff: str, max_chars: int = 12000) -> str:
    """
    Clean and truncate a git diff for LLM consumption.

    Steps:
        1. Strip binary file diffs
        2. Remove lock/generated file diffs
        3. Collapse oversized hunks to summaries
        4. Truncate to max_chars with a trailing marker

    Args:
        raw_diff: Raw unified diff string from git.
        max_chars: Maximum character budget for the processed diff.

    Returns:
        Cleaned diff string, or empty string if nothing meaningful remains.
    """
    if not raw_diff or not raw_diff.strip():
        return ""

    # Remove binary file notices
    cleaned = BINARY_RE.sub("", raw_diff)

    # Split into per-file diffs
    file_diffs = _split_into_file_diffs(cleaned)

    # Filter and process each file diff
    processed_parts = []
    for fd in file_diffs:
        filepath = fd["filepath"]

        # Skip ignored files (lock files, minified assets, etc.)
        if filepath != "__preamble__" and _should_ignore_file(filepath):
            continue

        # Collapse oversized hunks
        content = _collapse_large_hunks(fd["content"], filepath)
        if content.strip():
            processed_parts.append(content)

    result = "\n".join(processed_parts)

    # Hard truncate if needed
    if len(result) > max_chars:
        result = result[:max_chars].rstrip()
        result += "\n\n... (diff truncated — showing first ~{} chars)".format(max_chars)

    return result.strip()
