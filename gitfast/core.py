"""
Core API client for GitFast.

Provides the shared generate_response() function used by both
local commit mode and CI/CD review mode. Communicates with
Groq/Cerebras-compatible OpenAI-style chat completion APIs.
"""

import asyncio
import os
import time
from dataclasses import dataclass

import httpx
from dotenv import load_dotenv

# Load .env file for local development
load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "openai/gpt-oss-20b"
DEFAULT_API_BASE = "https://api.groq.com/openai/v1"
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 0.5


@dataclass
class APIConfig:
    """Resolved API configuration from environment variables."""

    api_key: str
    api_base: str
    model: str

    @classmethod
    def from_env(cls, model_override: str | None = None) -> "APIConfig":
        """
        Build config from environment variables.

        Environment variables:
            GROQ_API_KEY        — Required. API key for Groq / Cerebras.
            GITFAST_API_BASE    — Optional. Override the API base URL.
            GITFAST_MODEL       — Optional. Override the default model.
        """
        api_key = os.environ.get("CEREBRAS_API_KEY") or os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise EnvironmentError(
                "Neither CEREBRAS_API_KEY nor GROQ_API_KEY is set. "
                "Export one in your shell or add it to your .env file.\n"
                "  export GROQ_API_KEY=gsk_... or CEREBRAS_API_KEY=csk-..."
            )

        api_base = os.environ.get("GITFAST_API_BASE", DEFAULT_API_BASE).rstrip("/")
        model = model_override or os.environ.get("GITFAST_MODEL", DEFAULT_MODEL)

        return cls(api_key=api_key, api_base=api_base, model=model)


# ---------------------------------------------------------------------------
# Core generation function
# ---------------------------------------------------------------------------


@dataclass
class GenerationResult:
    """Wraps a generation response with timing metadata."""

    text: str
    model: str
    elapsed_seconds: float
    prompt_tokens: int
    completion_tokens: int


async def generate_response(
    diff: str,
    system_prompt: str,
    config: APIConfig | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> GenerationResult:
    """
    Send a diff + system prompt to the LLM and return the generated text.

    This is the shared engine that powers both commit message generation
    and PR review. It uses the OpenAI-compatible chat completions endpoint
    exposed by Groq, Cerebras, and similar providers.

    Args:
        diff: Processed git diff string.
        system_prompt: The system instruction (commit vs. review).
        config: API configuration. Resolved from env if not provided.
        max_tokens: Maximum tokens in the response.
        temperature: Sampling temperature (lower = more deterministic).

    Returns:
        GenerationResult with the text, model used, and timing info.

    Raises:
        httpx.HTTPStatusError: On non-retryable API errors.
        EnvironmentError: If GROQ_API_KEY is not set.
    """
    if config is None:
        config = APIConfig.from_env()

    url = f"{config.api_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Here is the git diff to analyze:\n\n```diff\n{diff}\n```"},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }

    last_error: Exception | None = None
    start_time = time.perf_counter()

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(MAX_RETRIES):
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

                elapsed = time.perf_counter() - start_time
                choice = data["choices"][0]["message"]["content"].strip()
                usage = data.get("usage", {})

                return GenerationResult(
                    text=choice,
                    model=config.model,
                    elapsed_seconds=round(elapsed, 2),
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                )

            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 401:
                    raise RuntimeError(
                        "API key is invalid or expired (401 Unauthorized).\n"
                        "Check your GROQ_API_KEY in .env or environment."
                    )
                if status == 403:
                    raise RuntimeError(
                        "Access denied (403 Forbidden). Your API key may "
                        "lack permissions for this model."
                    )
                # Don't retry on client errors (except 429 rate limit)
                if status != 429 and 400 <= status < 500:
                    raise
                last_error = exc

            except (httpx.ConnectError, httpx.ReadTimeout) as exc:
                last_error = exc

            # Exponential backoff
            if attempt < MAX_RETRIES - 1:
                backoff = INITIAL_BACKOFF_SECONDS * (2 ** attempt)
                await asyncio.sleep(backoff)

    # All retries exhausted
    raise RuntimeError(
        f"GitFast API call failed after {MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )
