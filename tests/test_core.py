"""Tests for the core API client module."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import httpx

from gitfast.core import APIConfig, generate_response, GenerationResult


class TestAPIConfig:
    """Tests for APIConfig.from_env()."""

    def test_missing_api_key_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(EnvironmentError, match="GROQ_API_KEY"):
                APIConfig.from_env()

    def test_defaults_with_key(self):
        with patch.dict("os.environ", {"GROQ_API_KEY": "test_key"}, clear=True):
            config = APIConfig.from_env()
            assert config.api_key == "test_key"
            assert config.model == "openai/gpt-oss-20b"
            assert "groq.com" in config.api_base

    def test_custom_model_from_env(self):
        env = {"GROQ_API_KEY": "test_key", "GITFAST_MODEL": "custom-model"}
        with patch.dict("os.environ", env, clear=True):
            config = APIConfig.from_env()
            assert config.model == "custom-model"

    def test_model_override_takes_precedence(self):
        env = {"GROQ_API_KEY": "test_key", "GITFAST_MODEL": "env-model"}
        with patch.dict("os.environ", env, clear=True):
            config = APIConfig.from_env(model_override="override-model")
            assert config.model == "override-model"

    def test_custom_api_base(self):
        env = {
            "GROQ_API_KEY": "test_key",
            "GITFAST_API_BASE": "https://custom.api.com/v1/",
        }
        with patch.dict("os.environ", env, clear=True):
            config = APIConfig.from_env()
            assert config.api_base == "https://custom.api.com/v1"  # trailing slash stripped


class TestGenerateResponse:
    """Tests for generate_response()."""

    @pytest.mark.asyncio
    async def test_successful_response(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "feat(auth): add login"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 10},
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        config = APIConfig(api_key="test", api_base="https://api.test.com", model="test-model")

        with patch("gitfast.core.httpx.AsyncClient", return_value=mock_client):
            result = await generate_response(
                diff="some diff",
                system_prompt="some prompt",
                config=config,
            )

        assert isinstance(result, GenerationResult)
        assert result.text == "feat(auth): add login"
        assert result.model == "test-model"
        assert result.prompt_tokens == 100
        assert result.completion_tokens == 10
