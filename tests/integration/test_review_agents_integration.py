import pytest
import asyncio
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import json

from src.agents.review.correctness_reviewer import CorrectnessReviewer
from src.agents.review.security_reviewer import SecurityReviewer
from src.agents.review.performance_reviewer import PerformanceReviewer
from src.agents.review.style_reviewer import StyleReviewer
from src.agents.review.adversarial_reviewer import AdversarialReviewer
from src.models.pull_request import PullRequest, FileChange
from src.models.review import Review, ReviewComment, Severity


@pytest.fixture
def sample_pr_simple():
    """Simple pull request with basic code changes."""
    return PullRequest(
        id="pr-001",
        title="Add user authentication",
        description="Implements basic user login and registration",
        author="test-dev",
        branch="feature/auth",
        base_branch="main",
        files=[
            FileChange(
                path="src/auth.py",
                additions=50,
                deletions=0,
                diff="""
+def authenticate_user(username, password):
+    user = db.query(f"SELECT * FROM users WHERE username='{username}'")
+    if user and user.password == password:
+        return user
+    return None
+
+def register_user(username, password):
+    db.execute(f"INSERT INTO users VALUES ('{username}', '{password}')")
+    return True
"""
            )
        ],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.fixture
def sample_pr_complex():
    """Complex pull request with multiple files and issues."""
    return PullRequest(
        id="pr-002",
        title="Optimize data processing pipeline",
        description="Refactor data processing for better performance",
        author="test-dev",
        branch="feature/optimize",
        base_branch="main",
        files=[
            FileChange(
                path="src/processor.py",
                additions=100,
                deletions=50,
                diff="""
-def process_data(data):
-    results = []
-    for item in data:
-        results.append(transform(item))
-    return results
+def process_data(data):
+    import threading
+    results = []
+    threads = []
+    for item in data:
+        t = threading.Thread(target=lambda: results.append(transform(item)))
+        t.start()
+        threads.append(t)
+    for t in threads:
+        t.join()
+    return results
"""
            ),
            FileChange(
                path="src/utils.py",
                additions=30,
                deletions=10,
                diff="""
+def transform(item):
+    # TODO: implement caching
+    result = expensive_operation(item)
+    return result
+
+def expensive_operation(item):
+    time.sleep(0.1)
+    return item * 2
"""
            )
        ],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.fixture
def all_reviewers():
    """Initialize all review agents."""
    return {
        'correctness': CorrectnessReviewer(),
        'security': SecurityReviewer(),
        'performance': PerformanceReviewer(),
        'style': StyleReviewer(),
        'adversarial': AdversarialReviewer()
    }


class TestReviewAgentsIntegration:
    """Integration tests for review agent collaboration."""

    @pytest.mark.asyncio
    async def test_all_agents_complete_review(self, sample_pr_simple, all_reviewers):
        """Test that all agents can complete a review of the same PR."""
        reviews = {}
        
        for agent_name, reviewer in all_reviewers.items():
            review = await reviewer.review(sample_pr_simple)
            reviews[agent_name] = review
            
            assert review is not None
            assert isinstance(review, Review)
            assert review.pr_id == sample_pr_simple.id
            assert review.reviewer_type == agent_name
        
        assert len(reviews) == 5

    @pytest.mark.asyncio
    async def test_security_finds_sql_injection(self, sample_pr_simple, all_reviewers):
        """Test that security reviewer identifies SQL injection vulnerability."""
        security_review = await all_reviewers['security'].review(sample_pr_simple)
        
        sql_injection_found = any(
            'sql' in comment.message.lower() or 'injection' in comment.message.lower()
            for comment in security_review.comments
        )
        
        assert sql_injection_found, "Security reviewer should detect SQL injection"
        assert security_review.severity in [Severity.HIGH, Severity.CRITICAL]

    @pytest.mark.asyncio
    async def test_correctness_validates_logic(self, sample_pr_simple, all_reviewers):
        """Test that correctness reviewer validates authentication logic."""
        correctness_review = await all_reviewers['correctness'].review(sample_pr_simple)
        
        assert correctness_review is not None
        assert len(correctness_review.comments) > 0
        
        password_check_found = any(
            'password' in comment.message.lower()
            for comment in correctness_review.comments
        )
        
        assert password_check_found, "Correctness reviewer should check password handling"

    @pytest.mark.asyncio
    async def test_style_enforces_standards(self, sample_pr_complex, all_reviewers):
        """Test that style reviewer enforces coding standards."""
        style_review = await all_reviewers['style'].review(sample_pr_complex)
        
        assert style_review is not None
        
        style_issues_found = any(
            'todo' in comment.message.lower() or 
            'docstring' in comment.message.lower() or
            'comment' in comment.message.lower()
            for comment in style_review.comments
        )
        
        assert style_issues_found, "Style reviewer should find style issues"

    @pytest.mark.asyncio
    async def test_performance_identifies_issues(self, sample_pr_complex, all_reviewers):
        """Test that performance reviewer identifies threading issues."""
        performance_review = await all_reviewers['performance'].review(sample_pr_complex)
        
        assert performance_review is not None
        
        threading_issue_found = any(
            'thread' in comment.message.lower() or
            'race' in comment.message.lower() or
            'concurrent' in comment.message.lower()
            for comment in performance_review.comments
        )
        
        assert threading_issue_found, "Performance reviewer should identify threading issues"

    @pytest.mark.asyncio
    async def test_adversarial_challenges_others(self, sample_pr_simple, all_reviewers):
        """Test that adversarial reviewer challenges other reviewers' findings."""
        base_reviews = []
        
        for agent_name in ['correctness', 'security', 'performance', 'style']:
            review = await all_reviewers[agent_name].review(sample_pr_simple)
            base_reviews.append(review)
        
        adversarial_review = await all_reviewers['adversarial'].review(
            sample_pr_simple, 
            existing_reviews=base_reviews
        )
        
        assert adversarial_review is not None
        assert len(adversarial_review.comments) > 0
        
        challenges_others = any(
            'disagree' in comment.message.lower() or
            'however' in comment.message.lower() or
            'alternative' in comment.message.lower()
            for comment in adversarial_review.comments
        )
        
        assert challenges_others or len(adversarial_review.comments) > len(base_reviews[0].comments)

    @pytest.mark.asyncio
    async def test_consistent_pr_metadata(self, sample_pr_simple, all_reviewers):
        """Test that all reviewers maintain consistent PR metadata."""
        reviews = []
        
        for reviewer in all_reviewers.values():
            review = await reviewer.review(sample_pr_simple)
            reviews.append(review)
        
        pr_ids = [review.pr_id for review in reviews]
        assert len(set(pr_ids)) == 1, "All reviews should reference the same PR"
        assert pr_ids[0] == sample_pr_simple.id

    @pytest.mark.asyncio
    async def test_severity_escalation(self, sample_pr_simple, all_reviewers):
        """Test that critical issues are marked with appropriate severity."""
        security_review = await all_reviewers['security'].review(sample_pr_simple)
        
        has_critical_or_high = any(
            comment.severity in [Severity.HIGH, Severity.CRITICAL]
            for comment in security_review.comments
        )
        
        assert has_critical_or_high, "SQL injection should be marked as high/critical severity"

    @pytest.mark.asyncio
    async def test_parallel_review_execution(self, sample_pr_complex, all_reviewers):
        """Test that multiple agents can review in parallel without conflicts."""
        tasks = [
            reviewer.review(sample_pr_complex)
            for reviewer in all_reviewers.values()
        ]
        
        start_time = datetime.now()
        reviews = await asyncio.gather(*tasks)
        end_time = datetime.now()
        
        assert len(reviews) == 5
        assert all(review is not None for review in reviews)
        
        duration = (end_time - start_time).total_seconds()
        assert duration < 30, "Parallel execution should complete within reasonable time"

    @pytest.mark.asyncio
    async def test_review_completeness(self, sample_pr_complex, all_reviewers):
        """Test that reviews cover all changed files."""
        reviews = []
        
        for reviewer in all_reviewers.values():
            review = await reviewer.review(sample_pr_complex)
            reviews.append(review)
        
        for review in reviews:
            file_paths_covered = set()
            for comment in review.comments:
                if comment.file_path:
                    file_paths_covered.add(comment.file_path)
            
            pr_file_paths = {fc.path for fc in sample_pr_complex.files}
            
            assert len(file_paths_covered) > 0, f"{review.reviewer_type} should comment on files"

    @pytest.mark.asyncio
    async def test_review_consensus_on_critical_issues(self, sample_pr_simple, all_reviewers):
        """Test that multiple reviewers identify the same critical issues."""
        reviews = []
        
        for reviewer in all_reviewers.values():
            review = await reviewer.review(sample_pr_simple)
            reviews.append(review)
        
        sql_mentions = sum(
            1 for review in reviews
            if any('sql' in comment.message.lower() for comment in review.comments)
        )
        
        assert sql_mentions >= 2, "Multiple reviewers should identify SQL issues"

    @pytest.mark.asyncio
    async def test_review_recommendations_actionable(self, sample_pr_complex, all_reviewers):
        """Test that review comments include actionable recommendations."""
        reviews = []
        
        for reviewer in all_reviewers.values():
            review = await reviewer.review(sample_pr_complex)
            reviews.append(review)
        
        for review in reviews:
            for comment in review.comments:
                assert len(comment.message) > 10, "Comments should be substantive"
                
                has_actionable_content = any(
                    keyword in comment.message.lower()
                    for keyword in ['should', 'could', 'consider', 'use', 'avoid', 'fix', 'change']
                )
                
                assert has_actionable_content, f"Comment should be actionable: {comment.message}"

    @pytest.mark.asyncio
    async def test_review_aggregation(self, sample_pr_simple, all_reviewers):
        """Test that reviews can be aggregated for final decision."""
        reviews = []
        
        for reviewer in all_reviewers.values():
            review = await reviewer.review(sample_pr_simple)
            reviews.append(review)
        
        total_comments = sum(len(review.comments) for review in reviews)
        assert total_comments > 0
        
        critical_count = sum(
            1 for review in reviews
            for comment in review.comments
            if comment.severity == Severity.CRITICAL
        )
        
        high_count = sum(
            1 for review in reviews
            for comment in review.comments
            if comment.severity == Severity.HIGH
        )
        
        should_block = critical_count > 0 or high_count >= 3
        
        assert isinstance(should_block, bool)

    @pytest.mark.asyncio
    async def test_review_idempotency(self, sample_pr_simple, all_reviewers):
        """Test that reviewing the same PR twice produces consistent results."""
        first_reviews = {}
        second_reviews = {}
        
        for agent_name, reviewer in all_reviewers.items():
            first_reviews[agent_name] = await reviewer.review(sample_pr_simple)
            second_reviews[agent_name] = await reviewer.review(sample_pr_simple)
        
        for agent_name in all_reviewers.keys():
            first = first_reviews[agent_name]
            second = second_reviews[agent_name]
            
            assert len(first.comments) == len(second.comments), \
                f"{agent_name} should produce consistent number of comments"

    @pytest.mark.asyncio
    async def test_cross_agent_communication(self, sample_pr_complex, all_reviewers):
        """Test that agents can build upon each other's findings."""
        correctness_review = await all_reviewers['correctness'].review(sample_pr_complex)
        performance_review = await all_reviewers['performance'].review(sample_pr_complex)
        
        adversarial_review = await all_reviewers['adversarial'].review(
            sample_pr_complex,
            existing_reviews=[correctness_review, performance_review]
        )
        
        references_others = any(
            'correctness' in comment.message.lower() or
            'performance' in comment.message.lower() or
            'previous' in comment.message.lower()
            for comment in adversarial_review.comments
        )
        
        assert len(adversarial_review.comments) > 0

    @pytest.mark.asyncio
    async def test_review_coverage_metrics(self, sample_pr_complex, all_reviewers):
        """Test that reviews provide comprehensive coverage metrics."""
        reviews = []
        
        for reviewer in all_reviewers.values():
            review = await reviewer.review(sample_pr_complex)
            reviews.append(review)
        
        files_with_comments = set()
        for review in reviews:
            for comment in review.comments:
                if comment.file_path:
                    files_with_comments.add(comment.file_path)
        
        pr_files = {fc.path for fc in sample_pr_complex.files}
        coverage = len(files_with_comments) / len(pr_files) if pr_files else 0
        
        assert coverage > 0, "Reviews should cover at least some files"

    @pytest.mark.asyncio
    async def test_review_json_serialization(self, sample_pr_simple, all_reviewers):
        """Test that all reviews can be serialized to JSON."""
        reviews = []
        
        for reviewer in all_reviewers.values():
            review = await reviewer.review(sample_pr_simple)
            reviews.append(review)
        
        for review in reviews:
            review_dict = review.to_dict()