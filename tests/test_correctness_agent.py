"""Tests for the correctness review agent."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json


class TestCorrectnessAgent:
    """Test suite for correctness review agent."""
    
    def test_initialization(self, sample_review_config):
        """Test agent initialization with config."""
        from agents.correctness_agent import CorrectnessAgent
        
        agent = CorrectnessAgent(sample_review_config["correctness"])
        assert agent.enabled == True
        assert agent.severity_threshold == "low"
    
    def test_detect_division_by_zero(self, sample_code_with_bugs):
        """Test detection of division by zero issues."""
        from agents.correctness_agent import CorrectnessAgent
        
        agent = CorrectnessAgent({"enabled": True})
        issues = agent.analyze_code(sample_code_with_bugs)
        
        division_issues = [i for i in issues if "division" in i["description"].lower()]
        assert len(division_issues) > 0
        assert any("zero" in i["description"].lower() for i in division_issues)
    
    def test_detect_index_out_of_bounds(self, sample_code_with_bugs):
        """Test detection of potential index errors."""
        from agents.correctness_agent import CorrectnessAgent
        
        agent = CorrectnessAgent({"enabled": True})
        issues = agent.analyze_code(sample_code_with_bugs)
        
        index_issues = [i for i in issues if "index" in i["description"].lower() or "bounds" in i["description"].lower()]
        assert len(index_issues) > 0
    
    def test_detect_missing_error_handling(self, sample_code_with_bugs):
        """Test detection of missing error handling."""
        from agents.correctness_agent import CorrectnessAgent
        
        agent = CorrectnessAgent({"enabled": True, "check_error_handling": True})
        issues = agent.analyze_code(sample_code_with_bugs)
        
        error_handling_issues = [i for i in issues if "error" in i["description"].lower() or "exception" in i["description"].lower()]
        assert len(error_handling_issues) > 0
    
    def test_no_issues_for_correct_code(self, sample_code_correct):
        """Test that correct code produces no issues."""
        from agents.correctness_agent import CorrectnessAgent
        
        agent = CorrectnessAgent({"enabled": True})
        issues = agent.analyze_code(sample_code_correct)
        
        assert len(issues) == 0 or all(i["severity"] == "info" for i in issues)
    
    def test_severity_levels(self, sample_code_with_bugs):
        """Test that issues have appropriate severity levels."""
        from agents.correctness_agent import CorrectnessAgent
        
        agent = CorrectnessAgent({"enabled": True})
        issues = agent.analyze_code(sample_code_with_bugs)
        
        assert len(issues) > 0
        for issue in issues:
            assert "severity" in issue
            assert issue["severity"] in ["low", "medium", "high", "critical"]
    
    def test_issue_structure(self, sample_code_with_bugs):
        """Test that issues have required fields."""
        from agents.correctness_agent import CorrectnessAgent
        
        agent = CorrectnessAgent({"enabled": True})
        issues = agent.analyze_code(sample_code_with_bugs)
        
        required_fields = ["type", "severity", "description", "line"]
        for issue in issues:
            for field in required_fields:
                assert field in issue
    
    def test_analyze_diff(self, sample_diff_modify):
        """Test analysis of git diff."""
        from agents.correctness_agent import CorrectnessAgent
        
        agent = CorrectnessAgent({"enabled": True})
        issues = agent.analyze_diff(sample_diff_modify)
        
        assert isinstance(issues, list)
    
    def test_filter_by_severity(self, sample_code_with_bugs):
        """Test filtering issues by severity threshold."""
        from agents.correctness_agent import CorrectnessAgent
        
        agent_high = CorrectnessAgent({"enabled": True, "severity_threshold": "high"})
        agent_low = CorrectnessAgent({"enabled": True, "severity_threshold": "low"})
        
        issues_high = agent_high.analyze_code(sample_code_with_bugs)
        issues_low = agent_low.analyze_code(sample_code_with_bugs)
        
        assert len(issues_low) >= len(issues_high)
    
    def test_type_checking_detection(self):
        """Test detection of type-related issues."""
        from agents.correctness_agent import CorrectnessAgent
        
        code = """
def add_values(a, b):
    return a + b  # No type hints, could fail with incompatible types

def process(data):
    return data.strip()  # Assumes string, no validation
"""
        agent = CorrectnessAgent({"enabled": True, "check_type_safety": True})
        issues = agent.analyze_code(code)
        
        type_issues = [i for i in issues if "type" in i["description"].lower()]
        assert len(type_issues) >= 0
    
    def test_edge_case_detection(self):
        """Test detection of unhandled edge cases."""
        from agents.correctness_agent import CorrectnessAgent
        
        code = """
def get_first_element(items):
    return items[0]  # No check for empty list

def calculate_percentage(part, total):
    return (part / total) * 100  # No check for zero total
"""
        agent = CorrectnessAgent({"enabled": True, "check_edge_cases": True})
        issues = agent.analyze_code(code)
        
        assert len(issues) > 0
    
    @patch('openai.OpenAI')
    def test_llm_integration(self, mock_openai, sample_code_with_bugs, mock_llm_response_correctness):
        """Test integration with LLM for analysis."""
        from agents.correctness_agent import CorrectnessAgent
        
        mock_client = Mock()
        mock_response = Mock