"""Logging configuration for FieldClimate application."""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional


def setup_logging(config: Dict[str, Any]) -> logging.Logger:
    """Set up logging configuration based on application settings.
    
    Args:
        config: The logging configuration dictionary with optional keys:
            - level: The log level (INFO, DEBUG, WARNING, ERROR, CRITICAL)
            - file: Path to the log file
            - max_size: Maximum size in bytes before rotation (default: 10MB)
            - backup_count: Number of backup files to keep (default: 5)
    
    Returns:
        The configured root logger.
    """
    # Extract configuration values with defaults
    log_level_name = config.get("level", "INFO").upper()
    log_file = config.get("file")
    max_size = config.get("max_size", 10 * 1024 * 1024)  # 10 MB
    backup_count = config.get("backup_count", 5)
    
    # Get the log level from the name
    log_level = getattr(logging, log_level_name, logging.INFO)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Remove existing handlers if any
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation (if log file is specified)
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            Path(log_dir).mkdir(parents=True, exist_ok=True)
            
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a named logger.
    
    Args:
        name: The name for the logger, typically the module name.
        
    Returns:
        A configured logger instance.
    """
    return logging.getLogger(name)