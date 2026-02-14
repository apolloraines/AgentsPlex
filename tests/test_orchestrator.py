import pytest
from unittest.mock import patch, MagicMock
from codeforge.orchestrator import ReviewOrchestrator
from codeforge.models import PRContext, ReviewResult, Finding
from codeforge.config import CodeForgeConfig

@pytest.fixture
def mock_config():
    return CodeForgeConfig(
        reviewers=["security", "performance", "style"],
        llm_provider="openai",
        llm_model="gpt-3.5-turbo",
        max_findings=20,
        severity_threshold="low",
        github_token="fake_token",
        llm_api_key="fake_api_key"
    )

@pytest.fixture
def mock_pr_context():
    return PRContext(
        repo="owner/repo",
        pr_number=123,
        title="Test PR",
        description="This is a test PR",
        diff="--- a/file.py\n+++ b/file.py\n",
        files_changed=["file.py"],
        base_branch="main",
        head_branch="feature"
    )

@pytest.fixture
def orchestrator(mock_config):
    return ReviewOrchestrator(mock_config)

@patch('codeforge.github_client.GitHubClient')
def test_review_pr_happy_path(mock_github_client, orchestrator, mock_pr_context):
    mock_github_client.return_value.get_pr.return_value = mock_pr_context

    mock_review_result = ReviewResult(
        reviewer_name="SecurityReviewer",
        reviewer_type="security",
        decision="approve",
        findings=[Finding(file="file.py", line=1, severity="low", category="style", title="Good style", description="Good style found.")],
        summary="Looks good.",
        execution_time=0.5
    )

    with patch('codeforge.reviewer.SecurityReviewer.review', return_value=mock_review_result) as mock_security_review, \
         patch('codeforge.reviewer.PerformanceReviewer.review', return_value=mock_review_result) as mock_performance_review, \
         patch('codeforge.reviewer.StyleReviewer.review', return_value=mock_review_result) as mock_style_review:

        result = orchestrator.review_pr("owner/repo", 123)

        assert result is not None
        assert len(result.findings) == 1
        assert result.findings[0].title == "Good style"
        assert mock_security_review.called
        assert mock_performance_review.called
        assert mock_style_review.called

@patch('codeforge.github_client.GitHubClient')
def test_review_pr_error_fetch_pr(mock_github_client, orchestrator):
    mock_github_client.return_value.get_pr.side_effect = Exception("GitHub API Error")

    with pytest.raises(Exception, match="GitHub API Error"):
        orchestrator.review_pr("owner/repo", 123)

@patch('codeforge.github_client.GitHubClient')
def test_review_pr_no_findings(mock_github_client, orchestrator, mock_pr_context):
    mock_github_client.return_value.get_pr.return_value = mock_pr_context

    with patch('codeforge.reviewer.SecurityReviewer.review', return_value=ReviewResult(
            reviewer_name="SecurityReviewer",
            reviewer_type="security",
            decision="approve",
            findings=[],
            summary="No findings.",
            execution_time=0.5)) as mock_security_review:

        result = orchestrator.review_pr("owner/repo", 123)

        assert result is not None
        assert len(result.findings) == 0
        assert mock_security_review.called

@patch('codeforge.github_client.GitHubClient')
def test_review_pr_conflicting_findings(mock_github_client, orchestrator, mock_pr_context):
    mock_github_client.return_value.get_pr.return_value = mock_pr_context

    mock_findings_1 = [Finding(file="file.py", line=1, severity="high", category="security", title="Security issue", description="Description of security issue.")]
    mock_findings_2 = [Finding(file="file.py", line=1, severity="medium", category="style", title="Style issue", description="Description of style issue.")]

    mock_security_review_result = ReviewResult(
        reviewer_name="SecurityReviewer",
        reviewer_type="security",
        decision="request_changes",
        findings=mock_findings_1,
        summary="Security issues found.",
        execution_time=0.5
    )

    mock_style_review_result = ReviewResult(
        reviewer_name="StyleReviewer",
        reviewer_type="style",
        decision="approve",
        findings=mock_findings_2,
        summary="Style looks good.",
        execution_time=0.5
    )

    with patch('codeforge.reviewer.SecurityReviewer.review', return_value=mock_security_review_result), \
         patch('codeforge.reviewer.StyleReviewer.review', return_value=mock_style_review_result):

        result = orchestrator.review_pr("owner/repo", 123)

        assert result is not None
        assert len(result.findings) == 2  # Two conflicting findings
        assert result.findings[0].title == "Security issue"
        assert result.findings[1].title == "Style issue"

@patch('codeforge.github_client.GitHubClient')
def test_review_pr_with_empty_reviewers(mock_github_client, orchestrator, mock_pr_context):
    orchestrator.config.reviewers = []

    mock_github_client.return_value.get_pr.return_value = mock_pr_context

    with pytest.raises(ValueError, match="No reviewers provided"):
        orchestrator.review_pr("owner/repo", 123)