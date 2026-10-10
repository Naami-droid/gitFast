"""
GitHub API client for GitFast.

Handles fetching PR diffs and posting review comments.
Designed to work both locally (with a PAT) and in GitHub Actions
(with the auto-injected GITHUB_TOKEN).
"""

import json
import os

import httpx


class GitHubClientError(Exception):
    """Raised when a GitHub API call fails."""


class GitHubClient:
    """
    Minimal async GitHub REST API client.

    Supports:
        - Fetching PR diffs as raw unified diff text
        - Fetching PR metadata (title, author, etc.)
        - Posting / updating issue comments on PRs
    """

    BASE_URL = "https://api.github.com"
    GITFAST_COMMENT_SIGNATURE = "<!-- gitfast-review -->"

    def __init__(self, token: str, repo: str):
        """
        Args:
            token: GitHub token (PAT or GITHUB_TOKEN).
            repo: Repository in "owner/repo" format.
        """
        self.token = token
        self.repo = repo
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    @classmethod
    def from_env(cls) -> "GitHubClient":
        """
        Build a GitHubClient from environment variables.

        In GitHub Actions, GITHUB_TOKEN and GITHUB_REPOSITORY
        are automatically available.
        """
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            raise GitHubClientError(
                "GITHUB_TOKEN is not set. "
                "In GitHub Actions this is automatic. "
                "For local use, export a Personal Access Token."
            )

        repo = os.environ.get("GITHUB_REPOSITORY", "")
        if not repo:
            raise GitHubClientError(
                "GITHUB_REPOSITORY is not set. "
                "Provide it as an env var or use --pr-url instead."
            )

        return cls(token=token, repo=repo)

    async def get_pr_diff(self, pr_number: int) -> str:
        """
        Fetch the unified diff for a pull request.

        Uses the `application/vnd.github.v3.diff` media type
        to get raw diff text instead of JSON.

        Args:
            pr_number: The PR number.

        Returns:
            Raw unified diff string.
        """
        url = f"{self.BASE_URL}/repos/{self.repo}/pulls/{pr_number}"
        headers = {**self.headers, "Accept": "application/vnd.github.v3.diff"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)

            if resp.status_code == 404:
                raise GitHubClientError(
                    f"PR #{pr_number} not found in {self.repo}. "
                    "Check the PR number and repository."
                )
            resp.raise_for_status()
            return resp.text

    async def get_pr_title(self, pr_number: int) -> str:
        """
        Fetch the title of a pull request.

        Args:
            pr_number: The PR number.

        Returns:
            The PR title string.
        """
        url = f"{self.BASE_URL}/repos/{self.repo}/pulls/{pr_number}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            return resp.json().get("title", "")

    async def post_comment(self, pr_number: int, body: str) -> str:
        """
        Post a review comment on a PR.

        Implements idempotency: if GitFast has already commented on
        the PR, the existing comment is updated instead of creating
        a new one (avoids spamming the PR timeline).

        Args:
            pr_number: The PR number.
            body: The markdown body of the comment.

        Returns:
            The URL of the created or updated comment.
        """
        # Prepend our signature for idempotency detection
        signed_body = f"{self.GITFAST_COMMENT_SIGNATURE}\n{body}"

        # Check for existing GitFast comment
        existing_comment_id = await self._find_existing_comment(pr_number)

        async with httpx.AsyncClient(timeout=30.0) as client:
            if existing_comment_id:
                # Update existing comment
                url = f"{self.BASE_URL}/repos/{self.repo}/issues/comments/{existing_comment_id}"
                resp = await client.patch(
                    url, json={"body": signed_body}, headers=self.headers
                )
            else:
                # Create new comment
                url = f"{self.BASE_URL}/repos/{self.repo}/issues/{pr_number}/comments"
                resp = await client.post(
                    url, json={"body": signed_body}, headers=self.headers
                )

            resp.raise_for_status()
            return resp.json().get("html_url", "")

    async def _find_existing_comment(self, pr_number: int) -> int | None:
        """
        Search for an existing GitFast comment on a PR.

        Returns the comment ID if found, None otherwise.
        """
        url = f"{self.BASE_URL}/repos/{self.repo}/issues/{pr_number}/comments"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self.headers, params={"per_page": 100})
            resp.raise_for_status()

            for comment in resp.json():
                if self.GITFAST_COMMENT_SIGNATURE in comment.get("body", ""):
                    return comment["id"]

        return None

    @staticmethod
    def get_pr_number_from_event() -> int | None:
        """
        Extract the PR number from the GitHub Actions event payload.

        In GitHub Actions, `GITHUB_EVENT_PATH` points to a JSON file
        containing the webhook event data.

        Returns:
            The PR number, or None if not in a PR context.
        """
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if not event_path:
            return None

        try:
            with open(event_path, "r", encoding="utf-8") as f:
                event = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

        # pull_request events have the PR data nested
        pr_data = event.get("pull_request") or event.get("issue", {})
        return pr_data.get("number")

    @staticmethod
    def parse_pr_url(url: str) -> tuple[str, int]:
        """
        Parse a GitHub PR URL into (repo, pr_number).

        Supports URLs like:
            https://github.com/owner/repo/pull/42
            github.com/owner/repo/pull/42

        Args:
            url: The PR URL string.

        Returns:
            Tuple of (owner/repo, pr_number).

        Raises:
            ValueError: If the URL format is invalid.
        """
        # Strip protocol and domain
        path = url.replace("https://", "").replace("http://", "")
        if path.startswith("github.com/"):
            path = path[len("github.com/"):]

        parts = path.strip("/").split("/")
        if len(parts) < 4 or parts[2] != "pull":
            raise ValueError(
                f"Invalid PR URL: {url}\n"
                "Expected format: https://github.com/owner/repo/pull/NUMBER"
            )

        repo = f"{parts[0]}/{parts[1]}"
        try:
            pr_number = int(parts[3])
        except ValueError:
            raise ValueError(f"Invalid PR number in URL: {parts[3]}")

        return repo, pr_number
