"""
Formatters for different report output formats.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime

from .models import ReviewOutcome, AgentResult, Finding, Severity, Status, ReportConfig


class BaseFormatter(ABC):
    """Base class for report formatters."""

    def __init__(self, config: ReportConfig):
        """
        Initialize the formatter.

        Args:
            config: Report configuration
        """
        self.config = config

    @abstractmethod
    def format(self, outcome: ReviewOutcome) -> str:
        """
        Format the review outcome into a report.

        Args:
            outcome: The review outcome to format

        Returns:
            Formatted report string
        """
        pass

    def _filter_findings(self, findings: List[Finding]) -> List[Finding]:
        """Filter findings based on configuration."""
        if self.config.severity_threshold:
            severity_order = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]
            threshold_index = severity_order.index(self.config.severity_threshold)
            findings = [f for f in findings if severity_order.index(f.severity) <= threshold_index]
        return findings

    def _sort_findings(self, findings: List[Finding]) -> List[Finding]:
        """Sort findings based on configuration."""
        if self.config.sort_by == "severity":
            severity_order = {
                Severity.CRITICAL: 0,
                Severity.HIGH: 1,
                Severity.MEDIUM: 2,
                Severity.LOW: 3,
                Severity.INFO: 4
            }
            return sorted(findings, key=lambda f: severity_order[f.severity])
        return findings


class MarkdownFormatter(BaseFormatter):
    """Formats reports as Markdown."""

    def format(self, outcome: ReviewOutcome) -> str:
        """Format the review outcome as Markdown."""
        lines = []
        
        # Header
        lines.append("# Integration Review Report")
        lines.append("")
        lines.append(f"**Review ID:** `{outcome.review_id}`")
        lines.append(f"**Target:** `{outcome.target}`")
        lines.append(f"**Timestamp:** {outcome.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Execution Time:** {outcome.total_execution_time:.2f}s")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        stats = outcome.get_summary_stats()
        lines.append(f"- **Total Findings:** {stats['total_findings']}")
        lines.append(f"- **Critical:** {stats['critical']}")
        lines.append(f"- **High:** {stats['high']}")
        lines.append(f"- **Medium:** {stats['medium']}")
        lines.append(f"- **Low:** {stats['low']}")
        lines.append(f"- **Info:** {stats['info']}")
        lines.append("")
        lines.append(f"- **Agents Run:** {stats['agents_run']}")
        lines.append(f"- **Agents Succeeded:** {stats['agents_succeeded']}")
        lines.append(f"- **Agents Failed:** {stats['agents_failed']}")
        lines.append("")

        # Findings by severity
        if self.config.group_by == "severity":
            lines.extend(self._format_by_severity(outcome))
        elif self.config.group_by == "agent":
            lines.extend(self._format_by_agent(outcome))
        else:
            lines.extend(self._format_by_agent(outcome))

        # Metadata
        if self.config.include_metadata and outcome.metadata:
            lines.append("## Metadata")
            lines.append("")
            for key, value in outcome.metadata.items():
                lines.append(f"- **{key}:** {value}")
            lines.append("")

        return "\n".join(lines)

    def _format_by_severity(self, outcome: ReviewOutcome) -> List[str]:
        """Format findings grouped by severity."""
        lines = []
        
        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
            findings = outcome.get_findings_by_severity(severity)
            findings = self._filter_findings(findings)
            
            if not findings:
                continue

            lines.append(f"## {severity.value.upper()} Severity Findings")
            lines.append("")
            
            for i, finding in enumerate(findings, 1):
                lines.extend(self._format_finding(finding, i))
            
            lines.append("")

        return lines

    def _format_by_agent(self, outcome: ReviewOutcome) -> List[str]:
        """Format findings grouped by agent."""
        lines = []
        
        for result in outcome.agent_results:
            lines.append(f"## Agent: {result.agent_name}")
            lines.append("")
            lines.append(f"**Type:** {result.agent_type}")
            lines.append(f"**Status:** {result.status.value}")
            lines.append(f"**Execution Time:** {result.execution_time:.2f}s")
            lines.append(f"**Findings:** {len(result.findings)}")
            lines.append("")

            if result.error_message:
                lines.append(f"**Error:** {result.error_message}")
                lines.append("")

            findings = self._filter_findings(result.findings)
            findings = self._sort_findings(findings)

            if self.config.max_findings_per_agent:
                findings = findings[:self.config.max_findings_per_agent]

            for i, finding in enumerate(findings, 1):
                lines.extend(self._format_finding(finding, i))

            lines.append("")

        return lines

    def _format_finding(self, finding: Finding, index: int) -> List[str]:
        """Format a single finding."""
        lines = []
        
        lines.append(f"### {index}. {finding.title}")
        lines.append("")
        lines.append(f"**Severity:** {finding.severity.value.upper()}")
        
        if finding.location:
            location_str = finding.location
            if finding.line_number:
                location_str += f":{finding.line_number}"
            lines.append(f"**Location:** `{location_str}`")
        
        lines.append("")
        lines.append(finding.description)
        lines.append("")