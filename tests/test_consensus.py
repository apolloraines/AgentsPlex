import pytest
from codeforge.models import Finding, ReviewResult, PRContext
from codeforge.consensus import ConsensusEngine, ConsensusResult

@pytest.fixture
def sample_findings():
    return [
        Finding(file="src/auth.py", line=10, severity="high", category="security",
                title="Potential SQL Injection", description="Use parameterized queries.",
                reviewer="Reviewer1"),
        Finding(file="src/auth.py", line=10, severity="critical", category="security",
                title="SQL Injection Vulnerability", description="Directly interpolating user input.",
                reviewer="Reviewer2"),
        Finding(file="src/utils.py", line=20, severity="medium", category="performance",
                title="Inefficient Loop", description="Consider using a set for lookups.",
                reviewer="Reviewer1"),
        Finding(file="src/utils.py", line=25, severity="low", category="style",
                title="Inconsistent Naming", description="Variable names should be more descriptive.",
                reviewer="Reviewer3"),
    ]

@pytest.fixture
def review_results(sample_findings):
    return [
        ReviewResult(reviewer_name="Reviewer1", reviewer_type="security", decision="request_changes",
                     findings=[sample_findings[0], sample_findings[2]], summary="Found issues.", execution_time=1.2),
        ReviewResult(reviewer_name="Reviewer2", reviewer_type="security", decision="approve",
                     findings=[sample_findings[1]], summary="Looks good.", execution_time=1.0),
        ReviewResult(reviewer_name="Reviewer3", reviewer_type="style", decision="request_changes",
                     findings=[sample_findings[3]], summary="Styling issues.", execution_time=1.5),
    ]

def test_aggregate_happy_path(review_results):
    engine = ConsensusEngine()
    consensus = engine.aggregate(review_results)

    assert consensus.decision == "request_changes"
    assert len(consensus.findings) == 3
    assert consensus.total_findings == 3
    assert consensus.critical_count == 1
    assert consensus.high_count == 1
    assert consensus.medium_count == 1
    assert consensus.low_count == 1
    assert "Reviewer1" in consensus.reviewers_run
    assert "Reviewer2" in consensus.reviewers_run
    assert "Reviewer3" in consensus.reviewers_run

def test_deduplicate_findings(sample_findings):
    engine = ConsensusEngine()
    deduplicated = engine.deduplicate(sample_findings)

    assert len(deduplicated) == 3  # Should merge findings from the same file and line
    assert deduplicated[0].severity == "critical"  # The more severe finding should be retained
    assert deduplicated[1].severity == "medium"
    assert deduplicated[2].severity == "low"

def test_resolve_conflicts(review_results):
    engine = ConsensusEngine()
    
    findings = [Finding(file="src/auth.py", line=10, severity="high", category="security",
                        title="Potential SQL Injection", description="Use parameterized queries.",
                        reviewer="Reviewer1"),
                Finding(file="src/auth.py", line=10, severity="critical", category="security",
                        title="SQL Injection Vulnerability", description="Directly interpolating user input.",
                        reviewer="Reviewer2")]

    resolved = engine.resolve_conflicts(findings)

    assert len(resolved) == 1  # Only one finding should exist after resolution
    assert resolved[0].severity == "critical"  # Critical finding should prevail

def test_compute_verdict(review_results):
    engine = ConsensusEngine()
    decision = engine.compute_verdict(review_results)

    assert decision == "request_changes"  # Majority decision should be request_changes

def test_empty_review_results():
    engine = ConsensusEngine()
    consensus = engine.aggregate([])

    assert consensus.decision == "approve"
    assert len(consensus.findings) == 0
    assert consensus.summary == "No reviewers were run."

def test_deduplication_empty():
    engine = ConsensusEngine()
    deduplicated = engine.deduplicate([])

    assert deduplicated == []  # Should return an empty list when input is empty

def test_conflict_resolution_no_conflict():
    engine = ConsensusEngine()
    
    findings = [Finding(file="src/utils.py", line=20, severity="medium", category="performance",
                        title="Inefficient Loop", description="Consider using a set for lookups.",
                        reviewer="Reviewer1")]

    resolved = engine.resolve_conflicts(findings)

    assert len(resolved) == 1  # Should return the single finding without changes

def test_conflict_resolution_with_conflict():
    engine = ConsensusEngine()
    
    findings = [
        Finding(file="src/utils.py", line=20, severity="medium", category="performance",
                title="Inefficient Loop", description="Consider using a set for lookups.",
                reviewer="Reviewer1"),
        Finding(file="src/utils.py", line=20, severity="low", category="style",
                title="Inconsistent Naming", description="Variable names should be more descriptive.",
                reviewer="Reviewer2")
    ]

    resolved = engine.resolve_conflicts(findings)

    assert len(resolved) == 1  # Should resolve to one finding
    assert resolved[0].severity == "medium"  # Higher severity should prevail

def test_multiple_findings_same_line():
    engine = ConsensusEngine()
    
    findings = [
        Finding(file="src/auth.py", line=10, severity="high", category="security",
                title="Potential SQL Injection", description="Use parameterized queries.",
                reviewer="Reviewer1"),
        Finding(file="src/auth.py", line=10, severity="critical", category="security",
                title="SQL Injection Vulnerability", description="Directly interpolating user input.",
                reviewer="Reviewer2"),
        Finding(file="src/auth.py", line=10, severity="medium", category="security",
                title="Potential SQL Injection Alternative", description="Consider escaping input.",
                reviewer="Reviewer3")
    ]

    resolved = engine.deduplicate(findings)

    assert len(resolved) == 1  # Should merge into a single finding
    assert resolved[0].severity == "critical"  # Critical should prevail
    assert resolved[0].reviewer == "Reviewer2"  # Reviewer of the highest severity should prevail