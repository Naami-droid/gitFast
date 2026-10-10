"""
CLI entry point for GitFast.

Provides two subcommands:
    gitfast commit  — Generate a Conventional Commit message from staged changes
    gitfast review  — Generate an AI code review for a GitHub Pull Request
"""

import argparse
import asyncio
import sys

# Ensure UTF-8 output on Windows consoles to prevent UnicodeEncodeError
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from . import __version__


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="gitfast",
        description="⚡ GitFast — AI-powered commit messages & PR reviews at lightning speed.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  gitfast commit              Generate a commit message from staged changes\n"
            "  gitfast commit --auto       Generate and immediately commit\n"
            "  gitfast commit --copy       Generate and copy to clipboard\n"
            "  gitfast review              Auto-detect PR in GitHub Actions\n"
            "  gitfast review --pr-url URL Review a specific PR locally\n"
        ),
    )
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"gitfast {__version__}",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Enable verbose/debug output.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show prompts and diff without calling the API.",
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        help="Override the LLM model (default: llama-3.1-8b-instant).",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── commit subcommand ───────────────────────────────────────────────
    commit_parser = subparsers.add_parser(
        "commit",
        help="Generate a Conventional Commit message from staged changes.",
    )
    commit_parser.add_argument(
        "--auto", "-a",
        action="store_true",
        default=False,
        help="Automatically run `git commit` with the generated message.",
    )
    commit_parser.add_argument(
        "--copy", "-c",
        action="store_true",
        default=False,
        help="Copy the generated message to the clipboard.",
    )

    # ── review subcommand ───────────────────────────────────────────────
    review_parser = subparsers.add_parser(
        "review",
        help="Generate an AI code review for a GitHub Pull Request.",
    )
    review_parser.add_argument(
        "--pr-url",
        type=str,
        default=None,
        help="GitHub PR URL (e.g., https://github.com/owner/repo/pull/42).",
    )
    review_parser.add_argument(
        "--post-comment",
        action="store_true",
        default=True,
        help="Post the review as a PR comment (default: True).",
    )
    review_parser.add_argument(
        "--no-comment",
        action="store_true",
        default=False,
        help="Print review to stdout instead of posting a comment.",
    )

    return parser


def main() -> None:
    """CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "commit":
        from .commit_mode import generate_commit_message

        asyncio.run(
            generate_commit_message(
                auto_commit=args.auto,
                copy_to_clipboard=args.copy,
                model_override=args.model,
                verbose=args.verbose,
                dry_run=args.dry_run,
            )
        )

    elif args.command == "review":
        from .review_mode import review_pull_request

        post_comment = not args.no_comment

        asyncio.run(
            review_pull_request(
                pr_url=args.pr_url,
                post_comment=post_comment,
                model_override=args.model,
                verbose=args.verbose,
                dry_run=args.dry_run,
            )
        )

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
