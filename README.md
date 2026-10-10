# ⚡ GitFast

**AI-powered commit messages & PR reviews at lightning speed.**

GitFast is a dual-mode Git copilot that uses blazing-fast sub-8B models (via [Groq](https://groq.com) or [Cerebras](https://cerebras.ai)) to solve two problems developers hate:

1. **Writing commit messages** → `gitfast commit` generates perfect Conventional Commits from your staged changes in under 1.5 seconds
2. **Reviewing PRs manually** → Drop a GitHub Action that auto-reviews every PR for code smells in under 2 seconds

> One tool. Two modes. Same fast model. Sub-second speed.

---

## 🚀 Quick Start (3 Commands)

```bash
# Install
pip install git+https://github.com/Naami-droid/gitFast.git

# Set your Groq API key
export GROQ_API_KEY=gsk_your_key_here

# Generate a commit message
git add .
gitfast commit
```

That's it. You'll see:

```
  ⚡ Generated in 1.07s (allam-2-7b)

  feat(cli): add support for generating commit messages from staged changes
```

---

## 🎯 Two Modes, One Tool

### Mode 1: Local Commit Messages

```bash
# Stage your changes
git add src/auth.py

# Generate a commit message
gitfast commit

# Or auto-commit directly
gitfast commit --auto

# Or copy to clipboard
gitfast commit --copy
```

### Mode 2: GitHub PR Reviews

**Locally** (review any PR):
```bash
export GITHUB_TOKEN=ghp_your_token
gitfast review --pr-url https://github.com/owner/repo/pull/42
```

**In GitHub Actions** (automatic on every PR):

Add this to `.github/workflows/review.yml`:

```yaml
name: AI Code Review
on:
  pull_request:
    types: [opened, synchronize]

permissions:
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Naami-droid/gitFast@main
        with:
          groq_api_key: ${{ secrets.GROQ_API_KEY }}
          model: allam-2-7b
```

**5 lines of config. Zero maintenance. Every PR gets an AI review in <2 seconds.**

---

## ⚡ Supported Models & Providers

GitFast supports any OpenAI-compatible API, optimized for fast models:

| Provider | Model ID | Parameters | Latency | Status / Best For |
|---|---|---|---|---|
| **Groq** | `allam-2-7b` | **7 Billion** | ~1.0s | ✅ **Active on Groq (Default sub-8B)** |
| **Groq** | `openai/gpt-oss-20b` | 20 Billion | ~1.4s | ✅ High reasoning & accuracy |
| **Groq** | `qwen/qwen3.8-27b` | 27 Billion | ~1.5s | ✅ Coding & complex diffs |
| **Cerebras** | `llama3.1-8b` | **8 Billion** | ~0.5s | ⚡ 1,800+ tokens/sec |
| **Ollama** | `llama3.1:8b` / `qwen2.5-coder:7b` | **7-8 Billion** | Local | 🔒 100% offline & local |

To switch models, use the `--model` flag or set `GITFAST_MODEL`:
```bash
gitfast commit --model allam-2-7b
gitfast commit --model openai/gpt-oss-20b
```

---

## 🔑 Configuration

Configure via environment variables or a local `.env` file:

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | ✅ (or Cerebras) | — | Groq API key (`gsk_...`) |
| `CEREBRAS_API_KEY` | Optional | — | Cerebras API key (`csk-...`) |
| `GITFAST_MODEL` | ❌ | `allam-2-7b` | LLM model override |
| `GITFAST_API_BASE` | ❌ | `https://api.groq.com/openai/v1` | Custom endpoint (e.g., `https://api.cerebras.ai/v1`) |
| `GITFAST_MAX_DIFF_CHARS` | ❌ | `12000` | Max diff size for truncation |
| `GITHUB_TOKEN` | CI only | Auto-injected | GitHub token for PR comments |

---

## 🧠 Why Sub-8B Models?

GitFast is built on a key insight: **commit messages and code reviews don't need GPT-4.**

| Task | Model | Speed | Quality |
|---|---|---|---|
| Commit message | `allam-2-7b` / `llama3.1-8b` | ~1.0s | ✅ Excellent |
| PR review | `allam-2-7b` / `openai/gpt-oss-20b` | ~1.7s | ✅ Thorough & structured |
| Same tasks | GPT-4o / Claude 3.5 | ~5-15s | ⚠️ Too slow for local flow |

The speed difference is the entire product. A 1.0s commit message feels instant in your terminal workflow. A 10s delay breaks developer flow. Fast models make real-time git hygiene painless.

---

## 🛠️ CLI Reference

```
Usage: gitfast [-h] [--version] [--verbose] [--dry-run] [--model MODEL]
               {commit,review} ...

Commands:
  commit    Generate a Conventional Commit message from staged changes
  review    Generate an AI code review for a GitHub Pull Request

Commit options:
  --auto, -a          Auto-commit with the generated message
  --copy, -c          Copy message to clipboard

Review options:
  --pr-url URL        GitHub PR URL for local review
  --no-comment        Print to stdout instead of posting
```

---

## 📦 Installation

```bash
# From source
git clone https://github.com/Naami-droid/gitFast.git
cd gitFast
pip install -e .

# With clipboard support
pip install -e ".[clipboard]"
```

---

## 🧪 Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check .
```

---

## 📄 License

MIT — see [LICENSE](./LICENSE).

---

<p align="center">
  <b>⚡ GitFast</b> — Because developers shouldn't waste brain cycles on commit messages.
</p>
