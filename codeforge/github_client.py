"""GitHub API client for fetching PR data and posting reviews."""

import time
from typing import Optional
import requests

from .models import PRContext


class GitHubClient:
    """Client for interacting with GitHub REST API v3."""

    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: str):
        """Initialize GitHub client with authentication token.
        
        Args:
            token: GitHub personal access token or OAuth token
        """
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        })
    
    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make a request with rate limiting and retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL or path relative to BASE_URL
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Response object
            
        Raises:
            requests.HTTPError: If request fails after retries
        """
        if not url.startswith("http"):
            url = f"{self.BASE_URL}{url}"
        
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            response = self.session.request(method, url, **kwargs)
            
            # Handle rate limiting
            if response.status_code == 403 and "rate limit" in response.text.lower():
                reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                if reset_time:
                    wait_time = max(reset_time - time.time(), 0) + 1
                    if wait_time < 300:  # Only wait up to 5 minutes
                        time.sleep(wait_time)
                        continue
            
            # Handle secondary rate limiting (abuse detection)
            if response.status_code == 403 and "retry-after" in response.headers:
                retry_after = int(response.headers.get("Retry-After", retry_delay))
                if retry_after < 60:  # Only wait up to 1 minute
                    time.sleep(retry_after)
                    continue
            
            # Retry on server errors
            if response.status_code >= 500 and attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            
            response.raise_for_status()
            return response
        
        # Final attempt
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response
    
    def _paginate(self, url: str, params: Optional[dict] = None) -> list:
        """Fetch all pages of a paginated endpoint.
        
        Args:
            url: API endpoint URL
            params: Query parameters
            
        Returns:
            List of all items from all pages
        """
        items = []
        params = params or {}
        params["per_page"] = 100
        
        while url:
            response = self._request("GET", url, params=params)
            data = response.json()
            
            if isinstance(data, list):
                items.extend(data)
            else:
                # Some endpoints return objects with items in a field
                items.append(data)
            
            # Get next page URL from Link header
            link_header = response.headers.get("Link", "")
            url = None
            for link in link_header.split(","):
                if 'rel="next"' in link:
                    url = link[link.find("<") + 1:link.find(">")]
                    params = {}  # URL already has params
                    break
        
        return items
    
    def get_pr(self, repo: str, pr_number: int) -> PRContext:
        """Fetch pull request data from GitHub.
        
        Args:
            repo: Repository in format "owner/repo"
            pr_number: Pull request number
            
        Returns:
            PRContext with PR data
            
        Raises:
            requests.HTTPError: If PR not found or API error
        """
        # Fetch PR metadata
        pr_url = f"/repos/{repo}/pulls/{pr_number}"
        pr_response = self._request("GET", pr_url)
        pr_data = pr_response.json()
        
        # Fetch PR diff
        diff_response = self._request(
            "GET",
            pr_url,
            headers={"Accept": "application/vnd.github.v3.diff"}
        )
        diff = diff_response.text
        
        # Fetch list of changed files
        files_url = f"/repos/{repo}/pulls/{pr_number}/files"
        files_data = self._paginate(files_url)
        files_changed = [f["filename"] for f in files_data]
        
        return PRContext(
            repo=repo,
            pr_number=pr_number,
            title=pr_data["title"],
            description=pr_data.get("body") or "",
            diff=diff,
            files_changed=files_changed,
            base_branch=pr_data["base"]["ref"],
            head_branch=pr_data["head"]["ref"]
        )
    
    def post_review(self, repo: str, pr_number: int, body: str, event: str) -> dict:
        """Submit a review on a pull request.
        
        Args:
            repo: Repository in format "owner/repo"
            pr_number: Pull request number
            body: Review comment body (markdown)
            event: Review event type - "APPROVE", "REQUEST_CHANGES", or "COMMENT"
            
        Returns:
            API response data
            
        Raises:
            requests.HTTPError: If review submission fails
        """
        url = f"/repos/{repo}/pulls/{pr_number}/reviews"
        
        payload = {
            "body": body,
            "event": event
        }
        
        response = self._request("POST", url, json=payload)
        return response.json()
    
    def post_comment(self, repo: str, pr_number: int, body: str) -> dict:
        """Add a comment to a pull request.
        
        Args:
            repo: Repository in format "owner/repo"
            pr_number: Pull request number
            body: Comment body (markdown)
            
        Returns:
            API response data
            
        Raises:
            requests.HTTPError: If comment submission fails
        """
        url = f"/repos/{repo}/issues/{pr_number}/comments"
        
        payload = {
            "body": body
        }
        
        response = self._request("POST", url, json=payload)
        return response.json()