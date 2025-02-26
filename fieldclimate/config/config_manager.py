"""Configuration management for FieldClimate application."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml


class ConfigError(Exception):
    """Exception raised for configuration errors."""

    pass


class ConfigManager:
    """Manages the application configuration from YAML files and environment variables."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file. If not provided, it will
                       look for the FIELDCLIMATE_CONFIG environment variable or
                       default to 'config.yaml' in the current directory.
        """
        self.config_path = config_path or os.environ.get("FIELDCLIMATE_CONFIG", "config.yaml")
        self.config = self._load_config()
        self._validate_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file.
        
        Returns:
            The configuration dictionary.
            
        Raises:
            ConfigError: If the file is not found or contains invalid YAML.
        """
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)
            return config or {}
        except FileNotFoundError:
            raise ConfigError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in configuration file: {e}")

    def _validate_config(self) -> None:
        """Validate the required configuration sections and values.
        
        Raises:
            ConfigError: If required configuration is missing or invalid.
        """
        # Validate required configuration sections
        required_sections = ["api", "database", "stations"]
        for section in required_sections:
            if section not in self.config:
                raise ConfigError(f"Missing required configuration section: {section}")

        # Validate API configuration
        api_config = self.config["api"]
        required_api_keys = ["public_key_path", "private_key_path", "base_url"]
        for key in required_api_keys:
            if key not in api_config:
                raise ConfigError(f"Missing required API configuration: {key}")

        # Check API key files exist
        for key_path in ["public_key_path", "private_key_path"]:
            path = Path(api_config[key_path])
            if not path.exists():
                raise ConfigError(f"API key file does not exist: {path}")

        # Validate database configuration
        db_config = self.config["database"]
        if "path" not in db_config:
            raise ConfigError("Missing required database path configuration")

    def get(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        """Get configuration value by section and key.
        
        Args:
            section: Configuration section name.
            key: Configuration key within the section. If None, returns the entire section.
            default: Default value to return if the section or key is not found.
            
        Returns:
            The configuration value, the entire section, or the default value.
        """
        if section not in self.config:
            return default

        if key is None:
            return self.config[section]

        return self.config[section].get(key, default)

    def get_stations(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """Get list of configured stations.
        
        Args:
            enabled_only: If True, return only enabled stations.
            
        Returns:
            List of station configurations.
        """
        stations = self.config.get("stations", [])
        if enabled_only:
            return [s for s in stations if s.get("enabled", True)]
        return stations

    def get_api_keys(self) -> Dict[str, str]:
        """Read API keys from files specified in configuration.
        
        Returns:
            Dictionary containing public_key and private_key.
            
        Raises:
            ConfigError: If keys cannot be read from files.
        """
        try:
            public_key_path = self.get("api", "public_key_path")
            private_key_path = self.get("api", "private_key_path")
            
            with open(public_key_path, "r") as f:
                public_key = f.read().strip()
            
            with open(private_key_path, "r") as f:
                private_key = f.read().strip()
            
            return {
                "public_key": public_key,
                "private_key": private_key,
            }
        except (IOError, OSError) as e:
            raise ConfigError(f"Failed to read API keys: {e}")