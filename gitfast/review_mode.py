"""
CI/CD review mode — fetches PR diffs and generates structured code reviews.

Usage:
    gitfast review [--pr-url URL] [--post-comment] [--model MODEL]
"""

import asyncio
import os
import sys

from .core import APIConfig, GenerationResult, generate_response
from .diff_processor import process_diff
from .github_client import GitHubClient, GitHubClientError
from .prompts import REVIEW_SYSTEM_PROMPT, REVIEW_TITLE_INJECTION, REVIEW_NO_TITLE


# ---------------------------------------------------------------------------
# ANSI color helpers
# ---------------------------------------------------------------------------

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"
RESET = "\033[0m"


def _c(code: str, text: str) -> str:
    if sys.platform == "win32" and "WT_SESSION" not in os.environ:
        return text
    return f"{code}{text}{RESET}"


# ---------------------------------------------------------------------------
# Review comment formatting
# ---------------------------------------------------------------------------

COMMENT_HEADER = """\
## 🔍 GitFast Code Review

> **Model**: `{model}` · **Speed**: {elapsed}s · **Tokens**: {tokens}

---

"""

COMMENT_FOOTER = """

---
*Powered by [GitFast](https://github.com/gitfast/gitfast) ⚡ Sub-second AI code reviews*
"""


def _format_review_comment(result: GenerationResult) -> str:
    """Wrap the raw LLM review in GitFast branding."""
    header = COMMENT_HEADER.format(
        model=result.model,
        elapsed=result.elapsed_seconds,
        tokens=result.prompt_tokens + result.completion_tokens,
    )
    return header + result.text + COMMENT_FOOTER


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def review_pull_request(
    pr_url: str | None = None,
    post_comment: bool = True,
    model_override: str | None = None,
    verbose: bool = False,
    dry_run: bool = False,
) -> str:
    """
    Full pipeline: resolve PR → fetch diff → process → review → post.

    Context detection:
        1. If running in GitHub Actions (GITHUB_EVENT_PATH is set), auto-detect PR.
        2. If --pr-url is provided, parse it for owner/repo/number.
        3. Otherwise, error with helpful guidance.

    Args:
        pr_url: Optional GitHub PR URL (e.g., https://github.com/o/r/pull/42).
        post_comment: If True, post the review as a PR comment.
        model_override: Override the default LLM model.
        verbose: Print debug information.
        dry_run: Show the prompt without calling the API.

    Returns:
        The generated review text.
    """
    # ── Step 1: Resolve PR context ──────────────────────────────────────
    pr_number: int | None = None
    gh_client: GitHubClient | None = None

    if pr_url:
        # Local mode: parse the URL
        try:
            repo, pr_number = GitHubClient.parse_pr_url(pr_url)
        except ValueError as exc:
            print(_c(RED, f"✗ {exc}"))
            sys.exit(1)

        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            print(_c(RED, "✗ GITHUB_TOKEN is not set."))
            print(_c(DIM, "  Export a Personal Access Token with repo scope:"))
            print(_c(DIM, "    export GITHUB_TOKEN=ghp_..."))
            sys.exit(1)

        gh_client = GitHubClient(token=token, repo=repo)
    else:
        # CI mode: auto-detect from GitHub Actions event
        pr_number = GitHubClient.get_pr_number_from_event()

        if pr_number is None:
            print(_c(RED, "✗ Could not detect PR context."))
            print(_c(DIM, "  In GitHub Actions, ensure the workflow triggers on pull_request."))
            print(_c(DIM, "  For local use, provide --pr-url:"))
            print(_c(DIM, "    gitfast review --pr-url https://github.com/owner/repo/pull/42"))
            sys.exit(1)

        try:
            gh_client = GitHubClient.from_env()
        except GitHubClientError as exc:
            print(_c(RED, f"✗ {exc}"))
            sys.exit(1)

    assert gh_client is not None
    assert pr_number is not None

    print(_c(CYAN, f"  ● Reviewing PR #{pr_number} in {gh_client.repo}..."))

    # ── Step 2: Fetch PR diff and title ─────────────────────────────────
    try:
        raw_diff = await gh_client.get_pr_diff(pr_number)
        pr_title = await gh_client.get_pr_title(pr_number)
    except GitHubClientError as exc:
        print(_c(RED, f"✗ {exc}"))
        sys.exit(1)
    except Exception as exc:
        print(_c(RED, f"✗ Failed to fetch PR data: {exc}"))
        sys.exit(1)

    if not raw_diff.strip():
        msg = "PR has no diff — nothing to review."
        print(_c(YELLOW, f"  ⚠ {msg}"))
        if post_comment:
            await gh_client.post_comment(
                pr_number, "## 🔍 GitFast Code Review\n\n*No changes detected in this PR.*"
            )
        return msg

    # ── Step 3: Process the diff ────────────────────────────────────────
    max_diff_chars = int(os.environ.get("GITFAST_MAX_DIFF_CHARS", "12000"))
    processed = process_diff(raw_diff, max_chars=max_diff_chars)

    if verbose:
        print(_c(DIM, f"  ── Processed diff ({len(processed)} chars) ──"))
        print(_c(DIM, processed[:300]))
        print()

    # ── Step 4: Build the prompt ────────────────────────────────────────
    system_prompt = REVIEW_SYSTEM_PROMPT
    if pr_title:
        system_prompt += REVIEW_TITLE_INJECTION.format(title=pr_title)
    else:
        system_prompt += REVIEW_NO_TITLE

    if dry_run:
        print(_c(CYAN, "── Dry run: System Prompt ──"))
        print(system_prompt)
        print(_c(CYAN, "── Dry run: Diff (processed) ──"))
        print(processed[:500])
        return ""

    # ── Step 5: Call the LLM ────────────────────────────────────────────
    config = APIConfig.from_env(model_override=model_override)
    result: GenerationResult = await generate_response(
        diff=processed,
        system_prompt=system_prompt,
        config=config,
        max_tokens=1024,
        temperature=0.3,
    )

    print(f"  {_c(GREEN, '⚡')} {_c(DIM, f'Review generated in {result.elapsed_seconds}s')}")

    # ── Step 6: Format and post ─────────────────────────────────────────
    comment_body = _format_review_comment(result)

    if post_comment:
        try:
            comment_url = await gh_client.post_comment(pr_number, comment_body)
            print(f"  {_c(GREEN, '✓')} Comment posted: {comment_url}")
        except Exception as exc:
            print(_c(RED, f"  ✗ Failed to post comment: {exc}"))
            print(_c(DIM, "  Printing review to stdout instead:"))
            print()
            print(comment_body)
    else:
        print()
        print(comment_body)

    return result.text
