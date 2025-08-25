"""
Application settings and configuration.
Load environment variables and define app-wide settings.
"""

from typing import List, Optional
from dotenv import load_dotenv, dotenv_values

load_dotenv(".env")
config = dotenv_values(".env")

# Application Constants
APP_NAME = "Runable"
VERSION = "1.0.0"
API_V1_PREFIX: str = "/api/v1"
ALLOWED_HOSTS: List[str] = ["*"]

# Environment Configuration
NODE_ENV: str = config.get("NODE_ENV", "development")
ENV: str = config.get("ENV", "development")
DEBUG: bool = config.get("DEBUG", "True").lower() == "true"
PORT: int = int(config.get("PORT", "8081"))

# Logging Configuration
LOG_LEVEL: str = config.get("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
LOG_TO_FILE: bool = config.get("LOG_TO_FILE", "True").lower() == "true"
LOG_TO_CONSOLE: bool = config.get("LOG_TO_CONSOLE", "True").lower() == "true"
LOG_FORMAT: str = config.get("LOG_FORMAT", "detailed")  # simple, detailed, json

GOOGLE_API_KEY: str = config.get("GOOGLE_API_KEY", "shashank")