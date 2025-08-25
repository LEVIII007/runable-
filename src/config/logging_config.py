"""
Logging configuration for the Trench AI project.
Provides structured logging with different levels, formats, and handlers.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
from src.config.settings import DEBUG, NODE_ENV, LOG_TO_CONSOLE, LOG_TO_FILE

# Create logs directory if it doesn't exist
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Log file paths
APP_LOG_FILE = LOGS_DIR / "trench_ai.log"
ERROR_LOG_FILE = LOGS_DIR / "errors.log"
ACCESS_LOG_FILE = LOGS_DIR / "access.log"

# Log formats
DETAILED_FORMAT = logging.Formatter(
    fmt="%(asctime)s | %(name)s | %(levelname)s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

SIMPLE_FORMAT = logging.Formatter(
    fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S"
)

CONSOLE_FORMAT = logging.Formatter(
    fmt="%(levelname)s | %(name)s | %(message)s"
)

JSON_FORMAT = logging.Formatter(
    fmt='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "file": "%(filename)s:%(lineno)d", "function": "%(funcName)s"}',
    datefmt="%Y-%m-%d %H:%M:%S"
)


def setup_logger(
    name: str,
    level: Optional[str] = None,
    log_to_file: bool = None,
    log_to_console: bool = None
) -> logging.Logger:
    """
    Set up a logger with the specified configuration.
    
    Args:
        name: Logger name (usually __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file (defaults to settings)
        log_to_console: Whether to log to console (defaults to settings)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Use settings defaults if not specified
    if log_to_file is None:
        log_to_file = LOG_TO_FILE
    if log_to_console is None:
        log_to_console = LOG_TO_CONSOLE
    
    # Set log level
    if level:
        logger.setLevel(getattr(logging, level.upper()))
    else:
        logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
    
    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False
    
    # Console handler - Make this more prominent
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        # Set console level to DEBUG to see all logs
        console_handler.setLevel(logging.DEBUG)
        # Use simpler format for console
        console_handler.setFormatter(CONSOLE_FORMAT)
        logger.addHandler(console_handler)
    
    # File handler for general logs
    if log_to_file:
        file_handler = logging.handlers.RotatingFileHandler(
            APP_LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(DETAILED_FORMAT)
        logger.addHandler(file_handler)
        
        # Error file handler
        error_handler = logging.handlers.RotatingFileHandler(
            ERROR_LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(DETAILED_FORMAT)
        logger.addHandler(error_handler)
    
    return logger


def setup_root_logger() -> None:
    """Set up the root logger with basic configuration."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)  # Only show warnings and above from third-party libraries
    
    # Add a console handler for root logger
    if not root_logger.handlers:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(SIMPLE_FORMAT)
        root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    This is a convenience function that uses the default configuration.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return setup_logger(name)


def configure_all_loggers():
    """
    Configure all existing loggers to use our custom configuration.
    This is useful for loggers that were created before our config was loaded.
    """
    # Get all existing loggers
    existing_loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
    
    for logger in existing_loggers:
        if logger.name and not logger.handlers:
            # Only configure loggers that don't already have handlers
            setup_logger(logger.name)


# Initialize root logger
setup_root_logger()

# Create default logger for the config module
logger = get_logger(__name__)
logger.info("Logging configuration initialized")

# Configure any existing loggers
configure_all_loggers() 