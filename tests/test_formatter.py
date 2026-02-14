import pytest
import json
from codeforge.models import Finding, ReviewResult, PRContext
from codeforge.consensus import ConsensusResult
from codeforge.formatter import format_github_review, format_terminal, format_json

@pytest.fixture
def consensus_with_no_findings():
    return ConsensusResult(findings=[])

@pytest.fixture
def consensus_with_single_finding():
    finding = Finding(
        file="src/auth.py",
        line=42,
        severity="high",
        category="security",
        title="Potential SQL Injection",
        description="The query might be vulnerable to SQL injection.",
        suggested_fix="Use parameterized queries."
    )
    return ConsensusResult(findings=[finding])

@pytest.fixture
def consensus_with_multiple_findings():
    finding1 = Finding(
        file="src/auth.py",
        line=42,
        severity="high",
        category="security",
        title="Potential SQL Injection",
        description="The query might be vulnerable to SQL injection.",
        suggested_fix="Use parameterized queries."
    )
    finding2 = Finding(
        file="src/utils.py",
        line=10,
        severity="critical",
        category="bug",
        title="Null Pointer Exception",
        description="Dereferencing a null object.",
        suggested_fix="Add a null check."
    )
    return ConsensusResult(findings=[finding1, finding2])

def test_format_github_review_no_findings(consensus_with_no_findings):
    result = format_github_review(consensus_with_no_findings)
    assert result == ""

def test_format_github_review_single_finding(consensus_with_single_finding):
    expected = (
        "### Potential SQL Injection\n"
        "- **File:** `src/auth.py`\n"
        "- **Line:** `42`\n"
        "- **Severity:** `high`\n"
        "- **Category:** `security`\n"
        "- **Description:** The query might be vulnerable to SQL injection.\n"
        "- **Suggested Fix:** `Use parameterized queries.`\n\n"
    )
    result = format_github_review(consensus_with_single_finding)
    assert result == expected

def test_format_github_review_multiple_findings(consensus_with_multiple_findings):
    expected = (
        "### Potential SQL Injection\n"
        "- **File:** `src/auth.py`\n"
        "- **Line:** `42`\n"
        "- **Severity:** `high`\n"
        "- **Category:** `security`\n"
        "- **Description:** The query might be vulnerable to SQL injection.\n"
        "- **Suggested Fix:** `Use parameterized queries.`\n\n"
        "### Null Pointer Exception\n"
        "- **File:** `src/utils.py`\n"
        "- **Line:** `10`\n"
        "- **Severity:** `critical`\n"
        "- **Category:** `bug`\n"
        "- **Description:** Dereferencing a null object.\n"
        "- **Suggested Fix:** `Add a null check.`\n\n"
    )
    result = format_github_review(consensus_with_multiple_findings)
    assert result == expected

def test_format_terminal_no_findings(consensus_with_no_findings):
    result = format_terminal(consensus_with_no_findings)
    assert result == ""

def test_format_terminal_single_finding(consensus_with_single_finding):
    expected = (
        "\x1b[33mPotential SQL Injection (Severity: high)\x1b[0m\n"
        "File: src/auth.py, Line: 42\n"
        "Description: The query might be vulnerable to SQL injection.\n"
        "\x1b[35mSuggested Fix: Use parameterized queries\x1b[0m\n\n"
    )
    result = format_terminal(consensus_with_single_finding)
    assert result == expected

def test_format_terminal_multiple_findings(consensus_with_multiple_findings):
    expected = (
        "\x1b[33mPotential SQL Injection (Severity: high)\x1b[0m\n"
        "File: src/auth.py, Line: 42\n"
        "Description: The query might be vulnerable to SQL injection.\n"
        "\x1b[35mSuggested Fix: Use parameterized queries\x1b[0m\n\n"
        "\x1b[31mNull Pointer Exception (Severity: critical)\x1b[0m\n"
        "File: src/utils.py, Line: 10\n"
        "Description: Dereferencing a null object.\n"
        "\x1b[35mSuggested Fix: Add a null check\x1b[0m\n\n"
    )
    result = format_terminal(consensus_with_multiple_findings)
    assert result == expected

def test_format_json_no_findings(consensus_with_no_findings):
    expected = json.dumps({"findings": []}, indent=4)
    result = format_json(consensus_with_no_findings)
    assert result == expected

def test_format_json_single_finding(consensus_with_single_finding):
    expected = json.dumps({
        "findings": [{
            "file": "src/auth.py",
            "line": 42,
            "severity": "high",
            "category": "security",
            "title": "Potential SQL Injection",
            "description": "The query might be vulnerable to SQL injection.",
            "suggested_fix": "Use parameterized queries.",
            "reviewer": "",
            "confidence": 1.0
        }]
    }, indent=4)
    result = format_json(consensus_with_single_finding)
    assert result == expected

def test_format_json_multiple_findings(consensus_with_multiple_findings):
    expected = json.dumps({
        "findings": [{
            "file": "src/auth.py",
            "line": 42,
            "severity": "high",
            "category": "security",
            "title": "Potential SQL Injection",
            "description": "The query might be vulnerable to SQL injection.",
            "suggested_fix": "Use parameterized queries.",
            "reviewer": "",
            "confidence": 1.0
        }, {
            "file": "src/utils.py",
            "line": 10,
            "severity": "critical",
            "category": "bug",
            "title": "Null Pointer Exception",
            "description": "Dereferencing a null object.",
            "suggested_fix": "Add a null check.",
            "reviewer": "",
            "confidence": 1.0
        }]
    }, indent=4)
    result = format_json(consensus_with_multiple_findings)
    assert result == expected