"""
CodeForge Review - Reviewer Implementations.

Base class and four built-in reviewer types. Each reviewer takes a PRContext
and returns a ReviewResult by calling an LLM with role-specific prompts.
"""

import json
import os
import re
import time
from abc import ABC, abstractmethod

from .models import Finding, PRContext, ReviewResult


class BaseReviewer(ABC):
    """Base class for all code reviewers."""

    def __init__(self, name: str, reviewer_type: str, system_prompt: str):
        """
        Initialize a reviewer.

        Args:
            name: Human-readable name of the reviewer
            reviewer_type: Category (security, correctness, performance, style)
            system_prompt: System prompt to guide the LLM
        """
        self.name = name
        self.reviewer_type = reviewer_type
        self.system_prompt = system_prompt

    def review(self, ctx: PRContext, config) -> ReviewResult:
        """
        Review a pull request and return findings.

        Args:
            ctx: PR context with diff and metadata
            config: CodeForge configuration

        Returns:
            ReviewResult with findings and decision
        """
        start_time = time.time()

        # Build user prompt with PR context
        user_prompt = self._build_user_prompt(ctx)

        # Call LLM
        llm_response = self._call_llm(user_prompt, config)

        # Parse findings from response
        findings = self._parse_findings(llm_response, ctx)

        # Cap findings if configured
        max_findings = getattr(config, "max_findings", 20)
        if len(findings) > max_findings:
            findings = findings[:max_findings]

        # Compute decision based on findings
        decision = self._compute_decision(findings)

        # Generate summary
        summary = self._generate_summary(findings)

        execution_time = time.time() - start_time

        return ReviewResult(
            reviewer_name=self.name,
            reviewer_type=self.reviewer_type,
            decision=decision,
            findings=findings,
            summary=summary,
            execution_time=execution_time,
        )

    def _build_user_prompt(self, ctx: PRContext) -> str:
        """Build the user prompt with PR context."""
        return f"""Review the following pull request:

Repository: {ctx.repo}
PR #{ctx.pr_number}: {ctx.title}
Base: {ctx.base_branch} <- Head: {ctx.head_branch}

Description:
{ctx.description}

Files changed: {', '.join(ctx.files_changed)}

Diff:
```
{ctx.diff}
```

Analyze this code change and identify issues in your area of expertise.
Return your findings as a JSON array of objects with this structure:
{{
  "file": "path/to/file.py",
  "line": 42,
  "severity": "critical|high|medium|low|info",
  "category": "{self.reviewer_type}",
  "title": "Brief issue title",
  "description": "Detailed explanation of the issue",
  "suggested_fix": "Optional code suggestion",
  "confidence": 0.95
}}

Return ONLY the JSON array, no other text.
"""

    def _call_llm(self, user_prompt: str, config) -> str:
        """
        Call the configured LLM provider.

        Args:
            user_prompt: The user prompt
            config: CodeForge configuration

        Returns:
            LLM response text
        """
        provider = getattr(config, "llm_provider", "openai")
        model = getattr(config, "llm_model", "gpt-4")
        api_key = getattr(config, "llm_api_key", os.environ.get("OPENAI_API_KEY"))

        if provider == "openai":
            return self._call_openai(user_prompt, model, api_key)
        elif provider == "anthropic":
            return self._call_anthropic(user_prompt, model, api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    def _call_openai(self, user_prompt: str, model: str, api_key: str) -> str:
        """Call OpenAI API."""
        try:
            import openai
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

        client = openai.OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=4000,
        )

        return response.choices[0].message.content

    def _call_anthropic(self, user_prompt: str, model: str, api_key: str) -> str:
        """Call Anthropic API."""
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            )

        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model=model,
            max_tokens=4000,
            temperature=0.3,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        return message.content[0].text

    def _parse_findings(self, llm_response: str, ctx: PRContext) -> list[Finding]:
        """
        Parse findings from LLM response.

        Args:
            llm_response: Raw LLM response text
            ctx: PR context for validation

        Returns:
            List of Finding objects
        """
        findings = []

        # Extract JSON from response (handle markdown code blocks)
        json_text = llm_response.strip()

        # Remove markdown code fences if present
        if json_text.startswith("```"):
            json_text = re.sub(r"^```(?:json)?\s*", "", json_text)
            json_text = re.sub(r"```\s*$", "", json_text)

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            # Try to extract JSON array from text
            match = re.search(r"\[.*\]", json_text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                except json.JSONDecodeError:
                    return findings
            else:
                return findings

        if not isinstance(data, list):
            return findings

        for item in data:
            try:
                finding = Finding(
                    file=item.get("file", "unknown"),
                    line=int(item.get("line", 0)),
                    severity=item.get("severity", "info"),
                    category=item.get("category", self.reviewer_type),
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    suggested_fix=item.get("suggested_fix", ""),
                    reviewer=self.name,
                    confidence=float(item.get("confidence", 1.0)),
                )
                findings.append(finding)
            except (ValueError, KeyError, TypeError):
                # Skip malformed findings
                continue

        return findings

    def _compute_decision(self, findings: list[Finding]) -> str:
        """
        Compute review decision based on findings.

        Args:
            findings: List of findings

        Returns:
            Decision string: "approve", "request_changes", or "comment"
        """
        if not findings:
            return "approve"

        # Count critical and high severity issues
        critical_count = sum(1 for f in findings if f.severity == "critical")
        high_count = sum(1 for f in findings if f.severity == "high")

        if critical_count > 0:
            return "request_changes"
        elif high_count > 0:
            return "request_changes"
        elif len(findings) > 0:
            return "comment"
        else:
            return "approve"

    def _generate_summary(self, findings: list[Finding]) -> str:
        """
        Generate a summary of findings.

        Args:
            findings: List of findings

        Returns:
            Summary text
        """
        if not findings:
            return f"{self.name} found no issues."

        severity_counts = {}
        for finding in findings:
            severity_counts[finding.severity] = (
                severity_counts.get(finding.severity, 0) + 1
            )

        parts = [f"{self.name} found {len(findings)} issue(s):"]
        for severity in ["critical", "high", "medium", "low", "info"]:
            count = severity_counts.get(severity, 0)
            if count > 0:
                parts.append(f"{count} {severity}")

        return " ".join(parts)


class SecurityReviewer(BaseReviewer):
    """Reviewer focused on security vulnerabilities."""

    def __init__(self):
        system_prompt = """You are a security-focused code reviewer. Your job is to identify security vulnerabilities in code changes.

Focus on:
- SQL injection, command injection, code injection
- Authentication and authorization issues
- Cryptographic weaknesses
- Sensitive data exposure
- Cross-site scripting (XSS)
- Cross-site request forgery (CSRF)
- Insecure deserialization
- Path traversal vulnerabilities
- Use of vulnerable dependencies
- Hardcoded secrets or credentials
- Insufficient input validation
- Improper error handling that leaks information

Be thorough but avoid false positives. Only flag real security issues.
Provide specific, actionable recommendations."""

        super().__init__(
            name="SecurityReviewer",
            reviewer_type="security",
            system_prompt=system_prompt,
        )


class CorrectnessReviewer(BaseReviewer):
    """Reviewer focused on bugs and logic errors."""

    def __init__(self):
        system_prompt = """You are a correctness-focused code reviewer. Your job is to identify bugs, logic errors, and edge cases in code changes.

Focus on:
- Logic errors and incorrect algorithms
- Off-by-one errors
- Null pointer/None reference issues
- Race conditions and concurrency bugs
- Incorrect error handling
- Resource leaks (file handles, connections, etc.)
- Unhandled edge cases
- Type mismatches
- Incorrect API usage
- Missing validation
- Infinite loops or recursion
- Incorrect assumptions about data

Be thorough but avoid false positives. Only flag real correctness issues.
Provide specific, actionable recommendations."""

        super().__init__(
            name="CorrectnessReviewer",
            reviewer_type="correctness",
            system_prompt=system_prompt,
        )


class PerformanceReviewer(BaseReviewer):
    """Reviewer focused on performance issues."""

    def __init__(self):
        system_prompt = """You are a performance-focused code reviewer. Your job is to identify performance issues and inefficiencies in code changes.

Focus on:
- Algorithmic complexity (O(n²) where O(n) is possible)
- Unnecessary loops or iterations
- Memory leaks
- Excessive memory allocation
- Blocking I/O in async code
- N+1 query problems
- Missing database indexes
- Inefficient data structures
- Repeated expensive operations
- Unnecessary copying of large objects
- Missing caching opportunities
- Inefficient string concatenation
- Premature optimization is not a concern - focus on real bottlenecks

Be thorough but avoid false positives. Only flag real performance issues.
Provide specific, actionable recommendations."""

        super().__init__(
            name="PerformanceReviewer",
            reviewer_type="performance",
            system_prompt=system_prompt,
        )


class StyleReviewer(BaseReviewer):
    """Reviewer focused on code style and readability."""

    def __init__(self):
        system_prompt = """You are a style-focused code reviewer. Your job is to identify code style issues and readability problems in code changes.

Focus on:
- Poor naming (unclear variable/function names)
- Overly complex functions (too long, too many parameters)
- Lack of documentation for complex logic
- Inconsistent formatting
- Magic numbers without explanation
- Deeply nested code
- Duplicate code
- Unclear control flow
- Missing type hints (in Python)
- Inconsistent error handling patterns
- Poor module organization
- Violations of language idioms

Be reasonable - only flag significant style issues that hurt readability.
Provide specific, actionable recommendations."""

        super().__init__(
            name="StyleReviewer",
            reviewer_type="style",
            system_prompt=system_prompt,
        )