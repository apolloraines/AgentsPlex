"""
Consensus engine for aggregating and resolving findings from multiple reviewers.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from collections import defaultdict

from .models import Finding, ReviewResult


@dataclass
class ConsensusResult:
    """Result of consensus aggregation across multiple reviewers."""
    decision: str  # "approve", "request_changes", "comment"
    findings: List[Finding]
    summary: str
    reviewers_run: List[str]
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int


class ConsensusEngine:
    """
    Aggregates findings from multiple reviewers, deduplicates, resolves conflicts,
    and computes a final verdict.
    """

    def aggregate(self, results: List[ReviewResult]) -> ConsensusResult:
        """
        Aggregate multiple review results into a single consensus result.
        
        Args:
            results: List of ReviewResult objects from different reviewers
            
        Returns:
            ConsensusResult with deduplicated findings and final verdict
        """
        if not results:
            return ConsensusResult(
                decision="approve",
                findings=[],
                summary="No reviewers were run.",
                reviewers_run=[],
                total_findings=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                info_count=0
            )
        
        # Collect all findings from all reviewers
        all_findings = []
        for result in results:
            all_findings.extend(result.findings)
        
        # Deduplicate findings
        deduplicated = self.deduplicate(all_findings)
        
        # Resolve conflicts between reviewers
        resolved = self.resolve_conflicts(deduplicated)
        
        # Sort by severity (critical first) and then by file/line
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        resolved.sort(key=lambda f: (severity_order.get(f.severity, 5), f.file, f.line))
        
        # Compute final verdict
        decision = self.compute_verdict(results)
        
        # Count findings by severity
        severity_counts = self._count_by_severity(resolved)
        
        # Generate summary
        summary = self._generate_summary(results, resolved, severity_counts)
        
        return ConsensusResult(
            decision=decision,
            findings=resolved,
            summary=summary,
            reviewers_run=[r.reviewer_name for r in results],
            total_findings=len(resolved),
            critical_count=severity_counts["critical"],
            high_count=severity_counts["high"],
            medium_count=severity_counts["medium"],
            low_count=severity_counts["low"],
            info_count=severity_counts["info"]
        )

    def deduplicate(self, findings: List[Finding]) -> List[Finding]:
        """
        Merge findings that refer to the same file and line.
        
        When multiple reviewers flag the same location, we keep the finding with
        the highest severity and merge information from others.
        
        Args:
            findings: List of findings to deduplicate
            
        Returns:
            Deduplicated list of findings
        """
        if not findings:
            return []
        
        # Group findings by (file, line)
        location_groups: Dict[Tuple[str, int], List[Finding]] = defaultdict(list)
        for finding in findings:
            key = (finding.file, finding.line)
            location_groups[key].append(finding)
        
        deduplicated = []
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        
        for (file, line), group in location_groups.items():
            if len(group) == 1:
                # No duplicates, keep as-is
                deduplicated.append(group[0])
            else:
                # Multiple findings at same location - merge them
                # Sort by severity (most severe first)
                group.sort(key=lambda f: severity_order.get(f.severity, 5))
                primary = group[0]
                
                # Collect all reviewers who found this
                reviewers = [f.reviewer for f in group if f.reviewer]
                reviewer_str = ", ".join(sorted(set(reviewers)))
                
                # Collect all categories
                categories = [f.category for f in group]
                category_str = ", ".join(sorted(set(categories)))
                
                # Merge descriptions if they differ significantly
                descriptions = [f.description for f in group]
                unique_descriptions = []
                seen = set()
                for desc in descriptions:
                    # Simple deduplication - consider descriptions unique if different
                    desc_normalized = desc.lower().strip()
                    if desc_normalized not in seen:
                        unique_descriptions.append(desc)
                        seen.add(desc_normalized)
                
                merged_description = primary.description
                if len(unique_descriptions) > 1:
                    # Multiple distinct perspectives
                    merged_description = "\n\n".join([
                        f"**Perspective {i+1}:** {desc}"
                        for i, desc in enumerate(unique_descriptions)
                    ])
                
                # Take the best suggested fix (longest non-empty one)
                suggested_fixes = [f.suggested_fix for f in group if f.suggested_fix]
                best_fix = max(suggested_fixes, key=len) if suggested_fixes else ""
                
                # Average confidence
                avg_confidence = sum(f.confidence for f in group) / len(group)
                
                merged = Finding(
                    file=primary.file,
                    line=primary.line,
                    severity=primary.severity,
                    category=category_str,
                    title=primary.title,
                    description=merged_description,
                    suggested_fix=best_fix,
                    reviewer=reviewer_str,
                    confidence=avg_confidence
                )
                deduplicated.append(merged)
        
        return deduplicated

    def resolve_conflicts(self, findings: List[Finding]) -> List[Finding]:
        """
        Resolve disagreements between reviewers about the same issue.
        
        When reviewers disagree about severity or whether something is an issue,
        we apply conflict resolution rules:
        - If severities differ, use the higher severity (more conservative)
        - If categories differ, combine them
        - Weight by reviewer confidence
        
        Args:
            findings: List of findings (possibly after deduplication)
            
        Returns:
            List of findings with conflicts resolved
        """
        if not findings:
            return []
        
        # Group by approximate location (same file, nearby lines)
        # This catches issues that are about the same problem but flagged at different lines
        location_clusters: Dict[str, List[Finding]] = defaultdict(list)
        
        for finding in findings:
            # Create clusters by file and line ranges (±2 lines)
            base_line = (finding.line // 3) * 3  # Group into buckets of 3 lines
            cluster_key = f"{finding.file}:{base_line}"
            location_clusters[cluster_key].append(finding)
        
        resolved = []
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        
        for cluster_findings in location_clusters.values():
            if len(cluster_findings) == 1:
                # No conflicts in this cluster
                resolved.extend(cluster_findings)
                continue
            
            # Check if findings in this cluster are about similar issues
            # (similar titles or categories)
            similar_groups = self._group_similar_findings(cluster_findings)
            
            for similar_group in similar_groups:
                if len(similar_group) == 1:
                    resolved.append(similar_group[0])
                else:
                    # Multiple similar findings - resolve conflict
                    # Use the most severe finding, weighted by confidence
                    weighted_severities = []
                    for f in similar_group:
                        sev_rank = severity_order.get(f.severity, 5)
                        # Lower rank = more severe, so invert for weighting
                        weight = (5 - sev_rank) * f.confidence
                        weighted_severities.append((weight, f))
                    
                    weighted_severities.sort(reverse=True, key=lambda x: x[0])
                    primary = weighted_severities[0][1]
                    
                    # If multiple findings have similar weight, keep them separate
                    # Otherwise merge into the primary
                    max_weight = weighted_severities[0][0]
                    close_weights = [f for w, f in weighted_severities if w >= max_weight * 0.8]
                    
                    if len(close_weights) > 1:
                        # Too close to call - keep all
                        resolved.extend(close_weights)
                    else:
                        # Clear winner - use primary
                        resolved.append(primary)
        
        return resolved

    def compute_verdict(self, results: List[ReviewResult]) -> str:
        """
        Determine final approve/reject decision based on reviewer results.
        
        Rules:
        - If any reviewer says "request_changes", final is "request_changes"
        - If all say "approve", final is "approve"
        - Otherwise, final is "comment"
        
        Args:
            results: List of ReviewResult objects
            
        Returns:
            One of "approve", "request_changes", or "comment"
        """
        if not results:
            return "approve"
        
        decisions = [r.decision for r in results]
        
        # If any reviewer requests changes, we request changes
        if "request_changes" in decisions:
            return "request_changes"
        
        # If all reviewers approve, we approve
        if all(d == "approve" for d in decisions):
            return "approve"
        
        # Mixed or all comments
        return "comment"

    def _count_by_severity(self, findings: List[Finding]) -> Dict[str, int]:
        """Count findings by severity level."""
        counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0
        }
        for finding in findings:
            severity = finding.severity.lower()
            if severity in counts:
                counts[severity] += 1
        return counts

    def _generate_summary(
        self,
        results: List[ReviewResult],
        findings: List[Finding],
        severity_counts: Dict[str, int]
    ) -> str:
        """Generate a human-readable summary of the consensus."""
        reviewer_names = [r.reviewer_name for r in results]
        
        summary_parts = [
            f"Consensus from {len(results)} reviewer(s): {', '.join(reviewer_names)}",
            f"Total findings: {len(findings)}"
        ]
        
        if findings:
            severity_parts = []
            if severity_counts["critical"] > 0:
                severity_parts.append(f"{severity_counts['critical']} critical")
            if severity_counts["high"] > 0:
                severity_parts.append(f"{severity_counts['high']} high")
            if severity_counts["medium"] > 0:
                severity_parts.append(f"{severity_counts['medium']} medium")
            if severity_counts["low"] > 0:
                severity_parts.append(f"{severity_counts['low']} low")
            if severity_counts["info"] > 0:
                severity_parts.append(f"{severity_counts['info']} info")
            
            if severity_parts:
                summary_parts.append(f"Severity breakdown: {', '.join(severity_parts)}")
        
        return "\n".join(summary_parts)

    def _group_similar_findings(self, findings: List[Finding]) -> List[List[Finding]]:
        """
        Group findings that appear to be about the same issue.
        
        Uses title similarity and category overlap to determine if findings
        are talking about the same problem.
        """
        if len(findings) <= 1:
            return [findings]
        
        groups = []
        used = set()
        
        for i, finding in enumerate(findings):
            if i in used:
                continue
            
            group = [finding]
            used.add(i)
            
            for j, other in enumerate(findings[i+1:], start=i+1):
                if j in used:
                    continue
                
                # Check if similar
                if self._are_similar(finding, other):
                    group.append(other)
                    used.add(j)
            
            groups.append(group)
        
        return groups

    def _are_similar(self, f1: Finding, f2: Finding) -> bool:
        """
        Determine if two findings are similar enough to be considered the same issue.
        """
        # Must be in same file
        if f1.file != f2.file:
            return False
        
        # Must be close in line number (within 5 lines)
        if abs(f1.line - f2.line) > 5:
            return False
        
        # Check category overlap
        cats1 = set(c.strip().lower() for c in f1.category.split(","))
        cats2 = set(c.strip().lower() for c in f2.category.split(","))
        if cats1 & cats2:  # Any overlap
            # Check title similarity (simple word overlap)
            words1 = set(f1.title.lower().split())
            words2 = set(f2.title.lower().split())
            common_words = words1 & words2
            # If more than 30% of words overlap, consider similar
            if len(common_words) >= min(len(words1), len(words2)) * 0.3:
                return True
        
        return False