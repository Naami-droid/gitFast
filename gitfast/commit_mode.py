"""
Local commit mode — generates Conventional Commit messages from staged changes.

Usage:
    gitfast commit [--auto] [--copy] [--model MODEL]
"""

import asyncio
import subprocess
import sys

from .core import APIConfig, GenerationResult, generate_response
from .diff_processor import process_diff
from .prompts import COMMIT_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# ANSI color helpers (zero-dependency)
# ---------------------------------------------------------------------------

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
RED = "\033[31m"
RESET = "\033[0m"


def _supports_color() -> bool:
    """Check whether the terminal supports ANSI colors."""
    if sys.platform == "win32":
        return "ANSICON" in __import__("os").environ or "WT_SESSION" in __import__("os").environ
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    """Wrap text in an ANSI color code if the terminal supports it."""
    if _supports_color():
        return f"{code}{text}{RESET}"
    return text


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def get_staged_diff() -> str:
    """
    Run `git diff --staged` and capture the output.

    Returns:
        The raw unified diff string of staged changes.

    Raises:
        SystemExit: If not inside a git repository or git is not installed.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--staged"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except FileNotFoundError:
        print(_c(RED, "✗ Error: git is not installed or not in PATH."))
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(_c(RED, "✗ Error: `git diff --staged` timed out."))
        sys.exit(1)

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "not a git repository" in stderr.lower():
            print(_c(RED, "✗ Error: Not inside a git repository."))
        else:
            print(_c(RED, f"✗ git error: {stderr}"))
        sys.exit(1)

    return result.stdout


def run_git_commit(message: str) -> bool:
    """
    Execute `git commit -m <message>`.

    Returns:
        True if the commit succeeded, False otherwise.
    """
    result = subprocess.run(
        ["git", "commit", "-m", message],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(_c(RED, f"✗ Commit failed: {result.stderr.strip()}"))
        return False

    print(_c(GREEN, "✓ Committed successfully!"))
    return True


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def generate_commit_message(
    auto_commit: bool = False,
    copy_to_clipboard: bool = False,
    model_override: str | None = None,
    verbose: bool = False,
    dry_run: bool = False,
) -> str:
    """
    Full pipeline: get staged diff → process → generate → present.

    Args:
        auto_commit: If True, immediately run `git commit -m <message>`.
        copy_to_clipboard: If True, copy the message to the clipboard.
        model_override: Override the default LLM model.
        verbose: Print debug information (processed diff, prompt, etc.).
        dry_run: Show the prompt without calling the API.

    Returns:
        The generated commit message string.
    """
    # 1. Get staged diff
    raw_diff = get_staged_diff()

    if not raw_diff.strip():
        print()
        print(_c(YELLOW, "⚠ No staged changes found."))
        print(_c(DIM, "  Run `git add <files>` to stage your changes first."))
        print()
        sys.exit(0)

    # 2. Process the diff
    processed = process_diff(raw_diff)

    if verbose:
        print(_c(DIM, f"── Processed diff ({len(processed)} chars) ──"))
        print(_c(DIM, processed[:500]))
        if len(processed) > 500:
            print(_c(DIM, f"  ... ({len(processed) - 500} more chars)"))
        print()

    if dry_run:
        print(_c(CYAN, "── Dry run: System Prompt ──"))
        print(COMMIT_SYSTEM_PROMPT)
        print(_c(CYAN, "── Dry run: Diff (processed) ──"))
        print(processed)
        return ""

    # 3. Call the LLM
    config = APIConfig.from_env(model_override=model_override)
    result: GenerationResult = await generate_response(
        diff=processed,
        system_prompt=COMMIT_SYSTEM_PROMPT,
        config=config,
        max_tokens=256,
        temperature=0.2,
    )

    # 4. Present the result
    message = result.text.strip().strip('"').strip("'").strip("`")

    print()
    print(f"  {_c(BOLD + GREEN, '⚡')} {_c(DIM, f'Generated in {result.elapsed_seconds}s')} "
          f"{_c(DIM, f'({result.model})')}")
    print()
    print(f"  {_c(BOLD + CYAN, message)}")
    print()

    # 5. Optional: copy to clipboard
    if copy_to_clipboard:
        try:
            import pyperclip  # type: ignore
            pyperclip.copy(message)
            print(_c(GREEN, "  ✓ Copied to clipboard"))
        except ImportError:
            print(_c(YELLOW, "  ⚠ pyperclip not installed — skipping clipboard copy"))
            print(_c(DIM, "    pip install pyperclip"))

    # 6. Optional: auto-commit
    if auto_commit:
        print(_c(DIM, f'  Running: git commit -m "{message}"'))
        run_git_commit(message)

    return message
