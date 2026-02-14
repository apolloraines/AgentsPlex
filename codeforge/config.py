import os
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from .models import Finding, ReviewResult, PRContext

@dataclass
class CodeForgeConfig:
    reviewers: list[str]         # which reviewer types to run
    llm_provider: str            # "openai" or "anthropic"
    llm_model: str               # model name
    max_findings: int            # cap per reviewer (default 20)
    severity_threshold: str      # minimum severity to report (default "low")
    github_token: str            # from env GITHUB_TOKEN
    llm_api_key: str             # from env

def load_config(config_path=None) -> CodeForgeConfig:
    # Set sensible defaults
    config = {
        "reviewers": ["security", "correctness", "performance", "style"],
        "llm_provider": "openai",
        "llm_model": "gpt-3.5-turbo",
        "max_findings": 20,
        "severity_threshold": "low",
        "github_token": os.getenv("GITHUB_TOKEN", ""),
        "llm_api_key": os.getenv("LLM_API_KEY", "")
    }

    if config_path is None:
        # Check for .codeforge.yaml in the current directory
        config_path = Path(".codeforge.yaml")
        if not config_path.is_file():
            # Fall back to pyproject.toml
            config_path = Path("pyproject.toml")

    if config_path.is_file():
        if config_path.suffix == '.yaml':
            with open(config_path, 'r') as file:
                yaml_config = yaml.safe_load(file) or {}
                config.update(yaml_config)
        elif config_path.suffix == '.toml':
            import toml
            toml_config = toml.load(config_path)
            config.update(toml_config.get("tool", {}).get("codeforge", {}))

    return CodeForgeConfig(
        reviewers=config["reviewers"],
        llm_provider=config["llm_provider"],
        llm_model=config["llm_model"],
        max_findings=config["max_findings"],
        severity_threshold=config["severity_threshold"],
        github_token=config["github_token"],
        llm_api_key=config["llm_api_key"]
    )