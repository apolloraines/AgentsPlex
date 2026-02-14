"""
Configuration Manager

Manages loading, saving, and updating agent configurations.
"""

import json
import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional, Type, Union
from .agent_config import (
    AgentConfig,
    ReviewAgentConfig,
    SecurityReviewConfig,
    CodeQualityReviewConfig,
    PerformanceReviewConfig,
    DocumentationReviewConfig,
)
from .validators import ConfigValidator


class ConfigManager:
    """Manages review agent configurations."""
    
    CONFIG_TYPES = {
        'base': AgentConfig,
        'review': ReviewAgentConfig,
        'security': SecurityReviewConfig,
        'code_quality': CodeQualityReviewConfig,
        'performance': PerformanceReviewConfig,
        'documentation': DocumentationReviewConfig,
    }
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory to store configuration files.
                       Defaults to ~/.review_agents/config
        """
        if config_dir is None:
            config_dir = os.path.join(
                os.path.expanduser("~"),
                ".review_agents",
                "config"
            )
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.configs: Dict[str, AgentConfig] = {}
        self.validator = ConfigValidator()
    
    def load_config(
        self,
        config_type: str,
        config_name: str = "default",
        file_path: Optional[str] = None
    ) -> AgentConfig:
        """
        Load a configuration from file.
        
        Args:
            config_type: Type of configuration to load
            config_name: Name of the configuration
            file_path: Optional custom file path
        
        Returns:
            Loaded configuration object
        """
        if config_type not in self.CONFIG_TYPES:
            raise ValueError(f"Unknown config type: {config_type}")
        
        if file_path is None:
            file_path = self.config_dir / f"{config_type}_{config_name}.yaml"
        else:
            file_path = Path(file_path)
        
        if not file_path.exists():
            # Return default configuration
            config_class = self.CONFIG_TYPES[config_type]
            config = config_class()
        else:
            with open(file_path, 'r') as f:
                if file_path.suffix == '.json':
                    data = json.load(f)
                else:
                    data = yaml.safe_load(f)
            
            config_class = self.CONFIG_TYPES[config_type]
            config = config_class.from_dict(data)
        
        # Validate configuration
        self.validator.validate(config)
        
        # Cache configuration
        cache_key = f"{config_type}:{config_name}"
        self.configs[cache_key] = config
        
        return config
    
    def save_config(
        self,
        config: AgentConfig,
        config_type: str,
        config_name: str = "default",
        file_path: Optional[str] = None,
        format: str = "yaml"
    ) -> Path:
        """
        Save a configuration to file.
        
        Args:
            config: Configuration object to save
            config_type: Type of configuration
            config_name: Name of the configuration
            file_path: Optional custom file path
            format: File format ('yaml' or 'json')
        
        Returns:
            Path to saved configuration file
        """
        # Validate before saving
        self.validator.validate(config)
        
        if file_path is None:
            ext = 'yaml' if format == 'yaml' else 'json'
            file_path = self.config_dir / f"{config_type}_{config_name}.{ext}"
        else:
            file_path = Path(file_path)
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = config.to_dict()
        
        with open(file_path, 'w') as f:
            if format == 'json':
                json.dump(data, f, indent=2)
            else:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        
        # Update cache
        cache_key = f"{config_type}:{config_name}"
        self.configs[cache_key] = config
        
        return file_path
    
    def update_config(
        self,
        config_type: str,
        config_name: str,
        updates: Dict[str, Any]
    ) -> AgentConfig:
        """
        Update an existing configuration.
        
        Args:
            config_type: Type of configuration
            config_name: Name of the configuration
            updates: Dictionary of updates to apply
        
        Returns:
            Updated configuration object
        """
        config = self.load_config(config_type, config_name)
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                raise ValueError(f"Unknown configuration key: {key}")
        
        # Validate updated configuration
        self.validator.validate(config)
        
        # Save updated configuration
        self.save_config(config, config_type, config_name)
        
        return config
    
    def list_configs(self, config_type: Optional[str] = None) -> Dict[str, list]:
        """
        List all available configurations.
        
        Args:
            config_type: Optional filter by config type
        
        Returns:
            Dictionary mapping config types to list of config names
        """
        configs = {}
        
        for file_path in self.config_dir.glob("*"):
            if file_path.is_file() and file_path.suffix in ['.yaml', '.yml', '.json']:
                parts = file_path.stem.split('_', 1)
                if len(parts) == 2:
                    cfg_type, cfg_name = parts
                    
                    if config_type is None or cfg_type == config_type:
                        if cfg_type not in configs:
                            configs[cfg_type] = []
                        configs[cfg_type].append(cfg_name)
        
        return configs
    
    def delete_config(self, config_type: str, config_name: str) -> bool:
        """
        Delete a configuration file.
        
        Args:
            config_type: Type of configuration
            config_name: Name of the configuration
        
        Returns:
            True if deleted successfully, False otherwise
        """
        file_path = self.config_dir / f"{config_type}_{config_name}.yaml"
        
        if file_path.exists():
            file_path.unlink()
            
            # Remove from cache
            cache_key = f"{config_type}:{config_name}"
            if cache_key in self.configs:
                del self.configs