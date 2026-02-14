import pytest
from unittest.mock import patch, Mock
from codeforge.github_client import GitHubClient
from codeforge.models import PRContext

@pytest.fixture
def github_client():
    """Fixture to create a GitHubClient instance with a mock token."""
    return GitHubClient(token="mock_token")

def test_get_pr_success(github_client):
    """Test successful retrieval of a PRContext."""
    repo = "owner/repo"
    pr_number = 123
    expected_response = {
        "title": "Mock PR Title",
        "body": "Mock PR Description",
        "diff": "Mock diff content",
        "files_changed": ["file1.py", "file2.py"],
        "base_branch": "main",
        "head_branch": "feature-branch"
    }

    with patch.object(github_client, '_request', return_value=Mock(status_code=200, json=Mock(return_value=expected_response))):
        pr_context = github_client.get_pr(repo, pr_number)

    assert isinstance(pr_context, PRContext)
    assert pr_context.repo == repo
    assert pr_context.pr_number == pr_number
    assert pr_context.title == expected_response["title"]
    assert pr_context.description == expected_response["body"]
    assert pr_context.diff == expected_response["diff"]
    assert pr_context.files_changed == expected_response["files_changed"]
    assert pr_context.base_branch == expected_response["base_branch"]
    assert pr_context.head_branch == expected_response["head_branch"]

def test_post_review_success(github_client):
    """Test posting a review sends the correct payload."""
    repo = "owner/repo"
    pr_number = 123
    body = "This is a review comment."
    event = "COMMENT"

    with patch.object(github_client, '_request') as mock_request:
        github_client.post_review(repo, pr_number, body, event)

    mock_request.assert_called_once_with("POST", f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews", json={"body": body, "event": event})

def test_get_pr_not_found(github_client):
    """Test handling of a 404 Not Found error when fetching PR."""
    repo = "owner/repo"
    pr_number = 999  # Assuming this PR does not exist

    with patch.object(github_client, '_request', side_effect=Mock(status_code=404)):
        with pytest.raises(requests.HTTPError):
            github_client.get_pr(repo, pr_number)

def test_post_review_forbidden(github_client):
    """Test handling of a 403 Forbidden error when posting a review."""
    repo = "owner/repo"
    pr_number = 123
    body = "This is a review comment."
    event = "COMMENT"

    with patch.object(github_client, '_request', side_effect=Mock(status_code=403)):
        with pytest.raises(requests.HTTPError):
            github_client.post_review(repo, pr_number, body, event)

def test_get_pr_rate_limit(github_client):
    """Test handling of rate limit reached when fetching PR."""
    repo = "owner/repo"
    pr_number = 123

    mock_response = Mock(status_code=403, headers={"X-RateLimit-Reset": str(int(time.time()) + 10)})
    with patch.object(github_client, '_request', return_value=mock_response):
        with pytest.raises(requests.HTTPError):
            github_client.get_pr(repo, pr_number)