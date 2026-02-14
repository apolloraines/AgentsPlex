"""
CodeForge Review - AI-powered code review tool.

A Python CLI tool and library that runs multiple AI reviewers against a GitHub PR,
aggregates their findings, resolves conflicts between reviewers, and posts a
consolidated review.
"""

__version__ = "0.1.0"

from codeforge.models import Finding, ReviewResult, PRContext

__all__ = [
    "Finding",
    "ReviewResult",
    "PRContext",
    "__version__",
]