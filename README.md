# ⚡ GitFast

**AI-powered commit messages & PR reviews at lightning speed.**

GitFast is a dual-mode Git copilot that uses blazing-fast 8B models (via [Groq](https://groq.com)) to solve two problems developers hate:

1. **Writing commit messages** → `gitfast commit` generates perfect Conventional Commits from your staged changes in under 1 second
2. **Reviewing PRs manually** → Drop a GitHub Action that auto-reviews every PR for code smells in under 2 seconds

> One tool. Two modes. Same 8B model. Different prompts. Sub-second speed.

---

## 🚀 Quick Start (3 Commands)

```bash
# Install
pip install -e .

# Set your Groq API key
export GROQ_API_KEY=gsk_your_key_here

# Generate a commit message
git add .
gitfast commit
```

That's it. You'll see something like:

```
  ⚡ Generated in 0.3s (llama-3.1-8b-instant)

  feat(auth): add JWT refresh token rotation
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
      - uses: your-username/gitfast@main
        with:
          groq_api_key: ${{ secrets.GROQ_API_KEY }}
```

**5 lines of config. Zero maintenance. Every PR gets an AI review in <2 seconds.**

---

## 🏗️ Architecture

```
                    ┌─────────────────────────┐
                    │    generate_response()   │
                    │  (shared core engine)    │
                    └─────────┬───────────────┘
                              │
                    ┌─────────┴───────────┐
                    │   diff_processor()   │
                    │  (clean & truncate)  │
                    └─────────┬───────────┘
                              │
              ┌───────────────┼───────────────┐
              │                               │
     ┌────────▼────────┐            ┌─────────▼────────┐
     │  commit_mode    │            │   review_mode    │
     │  git diff       │            │  GitHub API      │
     │  --staged       │            │  PR diff + post  │
     └─────────────────┘            └──────────────────┘
```

80% of the code is shared. The two modes only differ in:
- **Input source**: `git diff --staged` vs. GitHub PR API
- **System prompt**: "generate a commit" vs. "review this code"
- **Output target**: terminal vs. PR comment

---

## 🔑 Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | ✅ | — | Groq API key |
| `GITHUB_TOKEN` | CI only | Auto-injected | GitHub token for PR ops |
| `GITFAST_MODEL` | ❌ | `llama-3.1-8b-instant` | LLM model override |
| `GITFAST_API_BASE` | ❌ | `https://api.groq.com/openai/v1` | Custom API endpoint |
| `GITFAST_MAX_DIFF_CHARS` | ❌ | `12000` | Max diff size |

---

## 🧠 Why 8B Models?

GitFast is built on a key insight: **commit messages and code reviews don't need GPT-4.**

| Task | Model | Speed | Quality |
|---|---|---|---|
| Commit message | `llama-3.1-8b` on Groq | ~0.3s | ✅ Excellent |
| PR review | `llama-3.1-8b` on Groq | ~0.8s | ✅ Good enough |
| Same tasks | GPT-4o | ~3-8s | ✅ Slightly better |

The speed difference is the entire product. A 0.3s commit message feels instant. An 8s one feels broken. Hosted 8B models on Groq/Cerebras make real-time git tooling possible where frontier models cannot.

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
# From source (recommended for hackathon)
git clone https://github.com/your-username/gitfast.git
cd gitfast
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
