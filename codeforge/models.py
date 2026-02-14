"""
CodeForge Review - Data Models.

Pure data classes for findings, review results, and PR context.
No business logic. No external dependencies.
"""

from dataclasses import dataclass, field


VALID_SEVERITIES = ("critical", "high", "medium", "low", "info")
VALID_DECISIONS = ("approve", "request_changes", "comment")


@dataclass
class Finding:
    """A single code review finding."""
    file: str
    line: int
    severity: str
    category: str
    title: str
    description: str
    suggested_fix: str = ""
    reviewer: str = ""
    confidence: float = 1.0

    def __post_init__(self):
        if not self.file:
            raise ValueError("file must not be empty")
        if self.line < 0:
            raise ValueError(f"line must be non-negative, got {self.line}")
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(
                f"severity must be one of {VALID_SEVERITIES}, got '{self.severity}'"
            )


@dataclass
class ReviewResult:
    """Result from a single reviewer."""
    reviewer_name: str
    reviewer_type: str
    decision: str
    findings: list[Finding]
    summary: str
    execution_time: float

    def __post_init__(self):
        if self.decision not in VALID_DECISIONS:
            raise ValueError(
                f"decision must be one of {VALID_DECISIONS}, got '{self.decision}'"
            )


@dataclass
class PRContext:
    """Context for a pull request under review."""
    repo: str
    pr_number: int
    title: str
    description: str
    diff: str
    files_changed: list[str]
    base_branch: str
    head_branch: str

    def __post_init__(self):
        if "/" not in self.repo:
            raise ValueError(
                f"repo must be in 'owner/repo' format, got '{self.repo}'"
            )
