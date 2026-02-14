import pytest
from codeforge.models import Finding, ReviewResult, PRContext

def test_finding_creation():
    finding = Finding(
        file="src/auth.py",
        line=10,
        severity="high",
        category="security",
        title="Potential SQL Injection",
        description="This query can lead to SQL injection if user input is not sanitized."
    )
    assert finding.file == "src/auth.py"
    assert finding.line == 10
    assert finding.severity == "high"
    assert finding.category == "security"
    assert finding.title == "Potential SQL Injection"
    assert finding.description == "This query can lead to SQL injection if user input is not sanitized."
    assert finding.suggested_fix == ""
    assert finding.reviewer == ""
    assert finding.confidence == 1.0

def test_finding_default_values():
    finding = Finding(
        file="src/auth.py",
        line=10,
        severity="medium",
        category="bug",
        title="Missing error handling",
        description="Error handling is not implemented for this function."
    )
    assert finding.suggested_fix == ""
    assert finding.reviewer == ""
    assert finding.confidence == 1.0

def test_finding_edge_cases():
    with pytest.raises(ValueError):
        Finding(file="", line=10, severity="high", category="bug", title="Empty file", description="Description")
    
    with pytest.raises(ValueError):
        Finding(file="src/auth.py", line=-5, severity="high", category="bug", title="Negative line number", description="Description")

    with pytest.raises(ValueError):
        Finding(file="src/auth.py", line=10, severity="invalid_severity", category="bug", title="Invalid severity", description="Description")

def test_review_result_creation():
    finding = Finding(
        file="src/auth.py",
        line=10,
        severity="high",
        category="security",
        title="Potential SQL Injection",
        description="This query can lead to SQL injection if user input is not sanitized."
    )
    review_result = ReviewResult(
        reviewer_name="Reviewer1",
        reviewer_type="security",
        decision="request_changes",
        findings=[finding],
        summary="Found potential issues.",
        execution_time=2.5
    )
    assert review_result.reviewer_name == "Reviewer1"
    assert review_result.reviewer_type == "security"
    assert review_result.decision == "request_changes"
    assert len(review_result.findings) == 1
    assert review_result.findings[0].title == "Potential SQL Injection"
    assert review_result.summary == "Found potential issues."
    assert review_result.execution_time == 2.5

def test_pr_context_creation():
    pr_context = PRContext(
        repo="owner/repo",
        pr_number=123,
        title="Fix security vulnerabilities",
        description="This PR addresses several security issues.",
        diff="diff content",
        files_changed=["src/auth.py", "src/utils.py"],
        base_branch="main",
        head_branch="feature/secure-fix"
    )
    assert pr_context.repo == "owner/repo"
    assert pr_context.pr_number == 123
    assert pr_context.title == "Fix security vulnerabilities"
    assert pr_context.description == "This PR addresses several security issues."
    assert pr_context.diff == "diff content"
    assert pr_context.files_changed == ["src/auth.py", "src/utils.py"]
    assert pr_context.base_branch == "main"
    assert pr_context.head_branch == "feature/secure-fix"