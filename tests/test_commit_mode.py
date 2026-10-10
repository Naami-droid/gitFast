"""Tests for the commit mode module."""

import pytest
from unittest.mock import patch, MagicMock

from gitfast.commit_mode import get_staged_diff


class TestGetStagedDiff:
    """Tests for get_staged_diff()."""

    def test_successful_diff(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "diff --git a/test.py b/test.py\n+new line\n"

        with patch("gitfast.commit_mode.subprocess.run", return_value=mock_result):
            result = get_staged_diff()
            assert "test.py" in result

    def test_not_a_git_repo(self):
        mock_result = MagicMock()
        mock_result.returncode = 128
        mock_result.stderr = "fatal: not a git repository"

        with patch("gitfast.commit_mode.subprocess.run", return_value=mock_result):
            with pytest.raises(SystemExit):
                get_staged_diff()

    def test_git_not_installed(self):
        with patch(
            "gitfast.commit_mode.subprocess.run",
            side_effect=FileNotFoundError("git not found"),
        ):
            with pytest.raises(SystemExit):
                get_staged_diff()
