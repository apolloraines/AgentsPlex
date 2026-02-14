import pytest
from unittest.mock import patch, MagicMock
from codeforge.models import PRContext, ReviewResult, Finding
from codeforge.reviewer import (
    SecurityReviewer,
    CorrectnessReviewer,
    PerformanceReviewer,
    StyleReviewer
)

@pytest.fixture
def pr_context():
    return PRContext(
        repo="owner/repo",
        pr_number=123,
        title="Sample PR",
        description="This is a sample pull request.",
        diff="diff output here",
        files_changed=["src/auth.py", "src/utils.py"],
        base_branch="main",
        head_branch="feature"
    )

@pytest.fixture
def config():
    class Config:
        max_findings = 20
        llm_provider = "openai"
        llm_model = "gpt-4"
        llm_api_key = "fake_api_key"

    return Config()

@pytest.fixture
def mock_llm_response():
    return json.dumps([
        {
            "file": "src/auth.py",
            "line": 10,
            "severity": "high",
            "category": "security",
            "title": "Potential SQL Injection",
            "description": "User input is not sanitized before being used in SQL query.",
            "suggested_fix": "Use parameterized queries.",
            "confidence": 0.9
        }
    ])

def test_security_reviewer_happy_path(pr_context, config, mock_llm_response):
    reviewer = SecurityReviewer("Security Reviewer", "security", "Analyze security issues.")
    
    with patch.object(reviewer, '_call_llm', return_value=mock_llm_response):
        result = reviewer.review(pr_context, config)

    assert isinstance(result, ReviewResult)
    assert result.reviewer_name == "Security Reviewer"
    assert result.reviewer_type == "security"
    assert result.decision == "request_changes"
    assert len(result.findings) == 1
    assert result.findings[0].title == "Potential SQL Injection"

def test_correctness_reviewer_happy_path(pr_context, config, mock_llm_response):
    reviewer = CorrectnessReviewer("Correctness Reviewer", "correctness", "Analyze correctness issues.")
    
    with patch.object(reviewer, '_call_llm', return_value=mock_llm_response):
        result = reviewer.review(pr_context, config)

    assert isinstance(result, ReviewResult)
    assert result.reviewer_name == "Correctness Reviewer"
    assert result.reviewer_type == "correctness"
    assert result.decision == "request_changes"
    assert len(result.findings) == 1
    assert result.findings[0].title == "Potential SQL Injection"

def test_performance_reviewer_happy_path(pr_context, config, mock_llm_response):
    reviewer = PerformanceReviewer("Performance Reviewer", "performance", "Analyze performance issues.")
    
    with patch.object(reviewer, '_call_llm', return_value=mock_llm_response):
        result = reviewer.review(pr_context, config)

    assert isinstance(result, ReviewResult)
    assert result.reviewer_name == "Performance Reviewer"
    assert result.reviewer_type == "performance"
    assert result.decision == "request_changes"
    assert len(result.findings) == 1
    assert result.findings[0].title == "Potential SQL Injection"

def test_style_reviewer_happy_path(pr_context, config, mock_llm_response):
    reviewer = StyleReviewer("Style Reviewer", "style", "Analyze code style issues.")
    
    with patch.object(reviewer, '_call_llm', return_value=mock_llm_response):
        result = reviewer.review(pr_context, config)

    assert isinstance(result, ReviewResult)
    assert result.reviewer_name == "Style Reviewer"
    assert result.reviewer_type == "style"
    assert result.decision == "request_changes"
    assert len(result.findings) == 1
    assert result.findings[0].title == "Potential SQL Injection"

def test_reviewer_error_handling(pr_context, config):
    reviewer = SecurityReviewer("Security Reviewer", "security", "Analyze security issues.")
    
    with patch.object(reviewer, '_call_llm', return_value="garbage response"):
        with pytest.raises(ValueError):
            reviewer.review(pr_context, config)

def test_reviewer_empty_findings(pr_context, config):
    reviewer = SecurityReviewer("Security Reviewer", "security", "Analyze security issues.")
    
    with patch.object(reviewer, '_call_llm', return_value=json.dumps([])):
        result = reviewer.review(pr_context, config)

    assert isinstance(result, ReviewResult)
    assert result.findings == []
    assert result.decision == "approve"  # Assuming no findings means approval

def test_reviewer_exceeding_max_findings(pr_context, config):
    mock_llm_response = json.dumps([
        {
            "file": "src/auth.py",
            "line": 10,
            "severity": "high",
            "category": "security",
            "title": "Potential SQL Injection",
            "description": "User input is not sanitized before being used in SQL query.",
            "suggested_fix": "Use parameterized queries.",
            "confidence": 0.9
        },
        {
            "file": "src/utils.py",
            "line": 15,
            "severity": "medium",
            "category": "style",
            "title": "Variable naming issue",
            "description": "Variable names should be descriptive.",
            "suggested_fix": "Rename variables to be more descriptive.",
            "confidence": 0.85
        }
    ])

    reviewer = SecurityReviewer("Security Reviewer", "security", "Analyze security issues.")
    
    with patch.object(reviewer, '_call_llm', return_value=mock_llm_response):
        result = reviewer.review(pr_context, config)

    assert len(result.findings) == 2  # Should return all findings
    config.max_findings = 1  # Setting max findings to 1
    result = reviewer.review(pr_context, config)
    assert len(result.findings) == 1  # Should cap findings to 1