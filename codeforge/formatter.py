import json
from termcolor import colored
from .models import Finding, ReviewResult
from .consensus import ConsensusResult

def format_github_review(consensus: ConsensusResult) -> str:
    """Format the consensus results into markdown for GitHub review."""
    markdown_lines = []
    for finding in consensus.findings:
        markdown_lines.append(f"### {finding.title}\n")
        markdown_lines.append(f"- **File:** `{finding.file}`\n")
        markdown_lines.append(f"- **Line:** `{finding.line}`\n")
        markdown_lines.append(f"- **Severity:** `{finding.severity}`\n")
        markdown_lines.append(f"- **Category:** `{finding.category}`\n")
        markdown_lines.append(f"- **Description:** {finding.description}\n")
        if finding.suggested_fix:
            markdown_lines.append(f"- **Suggested Fix:** `{finding.suggested_fix}`\n")
        markdown_lines.append("\n")
    return ''.join(markdown_lines)

def format_terminal(consensus: ConsensusResult) -> str:
    """Format the consensus results into colored terminal output."""
    terminal_output = []
    for finding in consensus.findings:
        severity_color = {
            "critical": "red",
            "high": "yellow",
            "medium": "cyan",
            "low": "green",
            "info": "blue"
        }.get(finding.severity, "white")
        
        terminal_output.append(colored(f"{finding.title} (Severity: {finding.severity})", severity_color))
        terminal_output.append(f"File: {finding.file}, Line: {finding.line}\n")
        terminal_output.append(f"Description: {finding.description}\n")
        if finding.suggested_fix:
            terminal_output.append(colored(f"Suggested Fix: {finding.suggested_fix}", "magenta") + "\n")
        terminal_output.append("\n")
    return ''.join(terminal_output)

def format_json(consensus: ConsensusResult) -> str:
    """Format the consensus results into JSON."""
    findings_json = []
    for finding in consensus.findings:
        findings_json.append({
            "file": finding.file,
            "line": finding.line,
            "severity": finding.severity,
            "category": finding.category,
            "title": finding.title,
            "description": finding.description,
            "suggested_fix": finding.suggested_fix,
            "reviewer": finding.reviewer,
            "confidence": finding.confidence
        })
    return json.dumps({"findings": findings_json}, indent=4)