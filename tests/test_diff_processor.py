"""Tests for the diff processor module."""

from gitfast.diff_processor import process_diff


class TestProcessDiff:
    """Tests for process_diff()."""

    def test_empty_diff_returns_empty(self):
        assert process_diff("") == ""
        assert process_diff("   ") == ""
        assert process_diff(None) == ""  # type: ignore

    def test_simple_diff_passes_through(self):
        diff = (
            "diff --git a/hello.py b/hello.py\n"
            "--- a/hello.py\n"
            "+++ b/hello.py\n"
            "@@ -1,3 +1,4 @@\n"
            " def hello():\n"
            "-    print('hello')\n"
            "+    print('hello world')\n"
            "+    return True\n"
        )
        result = process_diff(diff)
        assert "hello.py" in result
        assert "hello world" in result

    def test_binary_files_stripped(self):
        diff = (
            "diff --git a/image.png b/image.png\n"
            "Binary files a/image.png and b/image.png differ\n"
            "diff --git a/code.py b/code.py\n"
            "--- a/code.py\n"
            "+++ b/code.py\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new\n"
        )
        result = process_diff(diff)
        assert "Binary" not in result
        assert "code.py" in result

    def test_lock_files_stripped(self):
        diff = (
            "diff --git a/package-lock.json b/package-lock.json\n"
            "--- a/package-lock.json\n"
            "+++ b/package-lock.json\n"
            "@@ -1,100 +1,100 @@\n"
            "-old lock content\n"
            "+new lock content\n"
            "diff --git a/src/app.js b/src/app.js\n"
            "--- a/src/app.js\n"
            "+++ b/src/app.js\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new\n"
        )
        result = process_diff(diff)
        assert "package-lock" not in result
        assert "app.js" in result

    def test_truncation(self):
        # Create a diff that exceeds 100 chars
        long_diff = (
            "diff --git a/big.py b/big.py\n"
            "--- a/big.py\n"
            "+++ b/big.py\n"
            "@@ -1,1 +1,1 @@\n"
            "+" + "x" * 200 + "\n"
        )
        result = process_diff(long_diff, max_chars=100)
        assert "truncated" in result
        assert len(result) < 200  # Should be truncated

    def test_yarn_lock_stripped(self):
        diff = (
            "diff --git a/yarn.lock b/yarn.lock\n"
            "--- a/yarn.lock\n"
            "+++ b/yarn.lock\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new\n"
        )
        result = process_diff(diff)
        assert result == "" or "yarn.lock" not in result


class TestLargeHunkCollapse:
    """Tests for large hunk collapsing."""

    def test_small_hunk_preserved(self):
        diff = (
            "diff --git a/small.py b/small.py\n"
            "--- a/small.py\n"
            "+++ b/small.py\n"
            "@@ -1,5 +1,5 @@\n"
            " line1\n"
            "-line2\n"
            "+line2_modified\n"
            " line3\n"
        )
        result = process_diff(diff)
        assert "line2_modified" in result
        assert "collapsed" not in result.lower()

    def test_huge_hunk_collapsed(self):
        lines = ["+line_{}\n".format(i) for i in range(250)]
        diff = (
            "diff --git a/huge.py b/huge.py\n"
            "--- a/huge.py\n"
            "+++ b/huge.py\n"
            "@@ -1,1 +1,250 @@\n"
            + "".join(lines)
        )
        result = process_diff(diff)
        assert "collapsed" in result.lower() or "Large diff" in result
