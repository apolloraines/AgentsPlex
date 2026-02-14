"""
Review orchestrator - main pipeline for running reviewers and aggregating results.

Fetches PR data, runs all reviewers in parallel, collects results, passes to
consensus engine, and formats output.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

from .models import PRContext, ReviewResult
from .reviewer import (
    BaseReviewer,
    SecurityReviewer,
    CorrectnessReviewer,
    PerformanceReviewer,
    StyleReviewer
)
from .consensus import ConsensusEngine, ConsensusResult
from .github_client import GitHubClient
from .formatter import format_github_review, format_terminal, format_json
from .config import CodeForgeConfig


class ReviewOrchestrator:
    """
    Main orchestration pipeline for CodeForge Review.
    
    Coordinates fetching PR data, running multiple reviewers in parallel,
    aggregating results through consensus, and formatting output.
    """
    
    # Map reviewer type names to reviewer classes
    REVIEWER_TYPES = {
        "security": SecurityReviewer,
        "correctness": CorrectnessReviewer,
        "performance": PerformanceReviewer,
        "style": StyleReviewer
    }
    
    def __init__(self, config: CodeForgeConfig):
        """
        Initialize orchestrator with configuration.
        
        Args:
            config: CodeForgeConfig with reviewer settings and API keys
        """
        self.config = config
        self.github_client = GitHubClient(config.github_token) if config.github_token else None
        self.consensus_engine = ConsensusEngine()
        
        # Initialize reviewers based on config
        self.reviewers = self._initialize_reviewers()
    
    def _initialize_reviewers(self) -> List[BaseReviewer]:
        """
        Create reviewer instances based on configuration.
        
        Returns:
            List of initialized reviewer objects
        """
        reviewers = []
        
        for reviewer_type in self.config.reviewers:
            reviewer_type_lower = reviewer_type.lower()
            
            if reviewer_type_lower == "all":
                # Run all available reviewers
                for reviewer_class in self.REVIEWER_TYPES.values():
                    reviewers.append(reviewer_class())
                break
            elif reviewer_type_lower in self.REVIEWER_TYPES:
                reviewer_class = self.REVIEWER_TYPES[reviewer_type_lower]
                reviewers.append(reviewer_class())
        
        return reviewers
    
    def review_pr(self, repo: str, pr_number: int) -> ConsensusResult:
        """
        Review a GitHub pull request.
        
        Fetches PR data from GitHub, runs all configured reviewers in parallel,
        aggregates results through consensus engine.
        
        Args:
            repo: Repository in "owner/repo" format
            pr_number: Pull request number
            
        Returns:
            ConsensusResult with aggregated findings and verdict
            
        Raises:
            ValueError: If GitHub client is not configured
            requests.HTTPError: If GitHub API request fails
        """
        if not self.github_client:
            raise ValueError(
                "GitHub client not configured. Set GITHUB_TOKEN environment variable."
            )
        
        # Fetch PR context from GitHub
        pr_context = self.github_client.get_pr(repo, pr_number)
        
        # Run reviewers and aggregate
        return self._run_reviewers(pr_context)
    
    def review_diff(self, diff_text: str) -> ConsensusResult:
        """
        Review a local diff without GitHub integration.
        
        Creates a minimal PRContext from the diff and runs reviewers.
        
        Args:
            diff_text: Unified diff text
            
        Returns:
            ConsensusResult with aggregated findings and verdict
        """
        # Parse files from diff
        files_changed = self._parse_files_from_diff(diff_text)
        
        # Create minimal PR context
        pr_context = PRContext(
            repo="local/review",
            pr_number=0,
            title="Local diff review",
            description="Review of local changes",
            diff=diff_text,
            files_changed=files_changed,
            base_branch="main",
            head_branch="local"
        )
        
        # Run reviewers and aggregate
        return self._run_reviewers(pr_context)
    
    def _parse_files_from_diff(self, diff_text: str) -> List[str]:
        """
        Extract list of changed files from unified diff.
        
        Args:
            diff_text: Unified diff text
            
        Returns:
            List of file paths
        """
        files = []
        for line in diff_text.split('\n'):
            if line.startswith('--- ') or line.startswith('+++ '):
                # Extract filename from diff header
                # Format: "--- a/path/to/file" or "+++ b/path/to/file"
                parts = line.split(None, 1)
                if len(parts) == 2:
                    path = parts[1]
                    # Remove a/ or b/ prefix
                    if path.startswith('a/') or path.startswith('b/'):
                        path = path[2:]
                    # Skip /dev/null (deleted/new files)
                    if path != '/dev/null' and path not in files:
                        files.append(path)
        
        return files
    
    def _run_reviewers(self, pr_context: PRContext) -> ConsensusResult:
        """
        Run all reviewers in parallel and aggregate results.
        
        Args:
            pr_context: Pull request context to review
            
        Returns:
            ConsensusResult with aggregated findings
        """
        if not self.reviewers:
            # No reviewers configured, return empty result
            return self.consensus_engine.aggregate([])
        
        results = []
        
        # Run reviewers in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=len(self.reviewers)) as executor:
            # Submit all reviewer tasks
            future_to_reviewer = {
                executor.submit(self._run_single_reviewer, reviewer, pr_context): reviewer
                for reviewer in self.reviewers
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_reviewer):
                reviewer = future_to_reviewer[future]
                try:
                    result = future.result()
                    if result:
                        # Apply max_findings limit
                        if len(result.findings) > self.config.max_findings:
                            result.findings = result.findings[:self.config.max_findings]
                        
                        # Apply severity threshold
                        result.findings = self._filter_by_severity(result.findings)
                        
                        results.append(result)
                except Exception as e:
                    # Log error but continue with other reviewers
                    print(f"Warning: {reviewer.name} failed with error: {e}")
        
        # Aggregate results through consensus engine
        consensus = self.consensus_engine.aggregate(results)
        
        return consensus
    
    def _run_single_reviewer(
        self,
        reviewer: BaseReviewer,
        pr_context: PRContext
    ) -> Optional[ReviewResult]:
        """
        Run a single reviewer and measure execution time.
        
        Args:
            reviewer: Reviewer instance to run
            pr_context: Pull request context
            
        Returns:
            ReviewResult or None if reviewer fails
        """
        start_time = time.time()
        
        try:
            result = reviewer.review(pr_context, self.config)
            result.execution_time = time.time() - start_time
            return result
        except Exception as e:
            print(f"Error running {reviewer.name}: {e}")
            return None
    
    def _filter_by_severity(self, findings: List) -> List:
        """
        Filter findings based on severity threshold.
        
        Args:
            findings: List of Finding objects
            
        Returns:
            Filtered list of findings
        """
        severity_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
            "info": 4
        }
        
        threshold = self.config.severity_threshold.lower()
        threshold_level = severity_order.get(threshold, 3)
        
        return [
            f for f in findings
            if severity_order.get(f.severity, 4) <= threshold_level
        ]
    
    def format_output(
        self,
        consensus: ConsensusResult,
        format_type: str = "terminal"
    ) -> str:
        """
        Format consensus result for output.
        
        Args:
            consensus: ConsensusResult to format
            format_type: Output format - "terminal", "github", or "json"
            
        Returns:
            Formatted string
        """
        if format_type == "github":
            return format_github_review(consensus)
        elif format_type == "json":
            return format_json(consensus)
        else:
            return format_terminal(consensus)
    
    def post_github_review(
        self,
        repo: str,
        pr_number: int,
        consensus: ConsensusResult
    ) -> None:
        """
        Post consensus result as a GitHub review.
        
        Args:
            repo: Repository in "owner/repo" format
            pr_number: Pull request number
            consensus: ConsensusResult to post
            
        Raises:
            ValueError: If GitHub client is not configured
        """
        if not self.github_client:
            raise ValueError(
                "GitHub client not configured. Set GITHUB_TOKEN environment variable."
            )
        
        # Format as GitHub review
        body = format_github_review(consensus)
        
        # Map consensus decision to GitHub review event
        event_map = {
            "approve": "APPROVE",
            "request_changes": "REQUEST_CHANGES",
            "comment": "COMMENT"
        }
        event = event_map.get(consensus.decision, "COMMENT")
        
        # Post review
        self.github_client.post_review(repo, pr_number, body, event)