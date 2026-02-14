# CodeForge Review — Architecture

## What We're Building

A Python CLI tool and library that runs multiple AI reviewers against a GitHub PR,
aggregates their findings, resolves conflicts between reviewers, and posts a
consolidated review. Think "hostile QA as a service" — adversarial agents that
try to break your code before it merges.

## Usage (target)

```bash
# Review a PR
codeforge review --repo owner/repo --pr 123

# Review local diff
codeforge review --diff ./changes.patch

# Run specific reviewer types
codeforge review --repo owner/repo --pr 123 --reviewers security,performance
```

## Directory Structure

```
codeforge/
    __init__.py              # Package init, version
    models.py                # Data classes: Finding, ReviewResult, PRContext
    reviewer.py              # BaseReviewer + built-in reviewer types
    orchestrator.py          # Runs reviewers, collects results
    consensus.py             # Aggregates findings, deduplicates, resolves conflicts
    github_client.py         # Fetch PR diff/files, post review comments
    formatter.py             # Format findings as markdown, terminal output
    cli.py                   # Click CLI entry point
    config.py                # Load config from pyproject.toml or .codeforge.yaml
tests/
    __init__.py
    test_models.py           # Test data models and serialization
    test_reviewer.py         # Test reviewer implementations
    test_orchestrator.py     # Test orchestration flow
    test_consensus.py        # Test finding aggregation and conflict resolution
    test_formatter.py        # Test output formatting
    test_github_client.py    # Test GitHub API interactions (mocked)
    conftest.py              # Shared fixtures
pyproject.toml               # Project metadata, dependencies, tool config
README.md                    # Project readme (already exists)
```

## Module Dependency Order

Build modules in this order. Each module may only import from modules above it.

```
1. models.py          — no internal imports (only stdlib + dataclasses)
2. config.py          — imports models
3. reviewer.py        — imports models
4. github_client.py   — imports models
5. consensus.py       — imports models
6. formatter.py       — imports models
7. orchestrator.py    — imports models, reviewer, consensus, github_client, formatter
8. cli.py             — imports orchestrator, config, models
9. tests/*            — imports from codeforge package
10. pyproject.toml    — project metadata
```

## Module Specifications

### 1. `codeforge/models.py`

Pure data classes. No business logic. No external dependencies.

```python
@dataclass
class Finding:
    file: str                    # e.g. "src/auth.py"
    line: int                    # line number
    severity: str                # "critical", "high", "medium", "low", "info"
    category: str                # "security", "bug", "performance", "style"
    title: str                   # short summary
    description: str             # detailed explanation
    suggested_fix: str = ""      # optional code suggestion
    reviewer: str = ""           # which reviewer found this
    confidence: float = 1.0      # 0.0-1.0

@dataclass
class ReviewResult:
    reviewer_name: str
    reviewer_type: str           # "security", "correctness", "performance", "style"
    decision: str                # "approve", "request_changes", "comment"
    findings: list[Finding]
    summary: str
    execution_time: float        # seconds

@dataclass
class PRContext:
    repo: str                    # "owner/repo"
    pr_number: int
    title: str
    description: str
    diff: str                    # unified diff
    files_changed: list[str]     # list of file paths
    base_branch: str
    head_branch: str
```

### 2. `codeforge/config.py`

Load configuration from `.codeforge.yaml` or `pyproject.toml [tool.codeforge]`.
Falls back to sensible defaults.

```python
@dataclass
class CodeForgeConfig:
    reviewers: list[str]         # which reviewer types to run
    llm_provider: str            # "openai" or "anthropic"
    llm_model: str               # model name
    max_findings: int            # cap per reviewer (default 20)
    severity_threshold: str      # minimum severity to report (default "low")
    github_token: str            # from env GITHUB_TOKEN
    llm_api_key: str             # from env

def load_config(config_path=None) -> CodeForgeConfig: ...
```

### 3. `codeforge/reviewer.py`

Base class + four built-in reviewer types. Each reviewer takes a PRContext and
returns a ReviewResult. Reviewers call an LLM with role-specific system prompts.

```python
class BaseReviewer:
    name: str
    reviewer_type: str
    system_prompt: str

    def review(self, ctx: PRContext, config: CodeForgeConfig) -> ReviewResult:
        """Send diff to LLM with system prompt, parse findings."""

class SecurityReviewer(BaseReviewer):      # injection, auth, crypto, data exposure
class CorrectnessReviewer(BaseReviewer):   # bugs, logic errors, edge cases
class PerformanceReviewer(BaseReviewer):   # O(n^2), memory leaks, blocking I/O
class StyleReviewer(BaseReviewer):         # naming, structure, readability
```

### 4. `codeforge/github_client.py`

Fetch PR data from GitHub API. Post review comments. Uses `requests` library.

```python
class GitHubClient:
    def __init__(self, token: str): ...
    def get_pr(self, repo: str, pr_number: int) -> PRContext: ...
    def post_review(self, repo: str, pr_number: int, body: str, event: str): ...
    def post_comment(self, repo: str, pr_number: int, body: str): ...
```

### 5. `codeforge/consensus.py`

Takes multiple ReviewResults, deduplicates findings, resolves conflicts
(e.g. two reviewers flag same line differently), produces final verdict.

```python
class ConsensusEngine:
    def aggregate(self, results: list[ReviewResult]) -> ConsensusResult: ...
    def deduplicate(self, findings: list[Finding]) -> list[Finding]: ...
    def resolve_conflicts(self, findings: list[Finding]) -> list[Finding]: ...
    def compute_verdict(self, results: list[ReviewResult]) -> str: ...
```

### 6. `codeforge/formatter.py`

Turn findings into readable output — markdown for GitHub, colored text for terminal.

```python
def format_github_review(consensus: ConsensusResult) -> str: ...
def format_terminal(consensus: ConsensusResult) -> str: ...
def format_json(consensus: ConsensusResult) -> str: ...
```

### 7. `codeforge/orchestrator.py`

The main pipeline. Fetches PR, runs reviewers in parallel, aggregates via
consensus, formats output, optionally posts to GitHub.

```python
class ReviewOrchestrator:
    def __init__(self, config: CodeForgeConfig): ...
    def review_pr(self, repo: str, pr_number: int) -> ConsensusResult: ...
    def review_diff(self, diff: str) -> ConsensusResult: ...
```

### 8. `codeforge/cli.py`

Click-based CLI. Subcommands: `review`, `config`, `version`.

```python
@click.group()
def main(): ...

@main.command()
@click.option("--repo", required=True)
@click.option("--pr", type=int, required=True)
@click.option("--reviewers", default="all")
@click.option("--output", type=click.Choice(["terminal", "json", "github"]))
def review(repo, pr, reviewers, output): ...
```

## Rules for All Agents

1. **Read this file before writing any code.** Your module must match these specs.
2. **Only import from modules listed above yours** in the dependency order.
3. **Use the exact class/function names** specified here.
4. **Use dataclasses** for models, not dicts or NamedTuples.
5. **No placeholder code.** Every function must have a real implementation.
6. **Include docstrings** on public classes and functions.
7. **Follow existing patterns** — if models.py uses `@dataclass`, your code should too.
8. **Test files** should use pytest with descriptive test names.
