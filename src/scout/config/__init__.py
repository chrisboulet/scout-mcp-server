"""Configuration System for SCOUT MCP Server.

This module provides type-safe loading and validation of YAML-based application
configuration with environment variable substitution. It validates AI provider
settings, team definitions, tool mappings, and system parameters at startup,
ensuring fail-fast behavior before the MCP server begins operation.

Key Features:
    - Load and parse YAML configuration from file system
    - Substitute environment variables using ${VAR} syntax
    - Validate configuration against Pydantic schemas with detailed error reporting
    - Provide immutable, type-safe configuration access throughout application
    - Redact sensitive values (API keys) in logs and error messages
    - Detect configuration errors before application startup (fail-fast principle)

Example Usage:
    >>> from scout.config import load_config
    >>> config = load_config("config/scout.yaml")
    >>> gemini_key = config.providers["gemini"].api_key
    >>> default_team = config.system.default_team

Constitution Alignment:
    - Principle II: Modular Architecture - Isolated configuration module
    - Principle III: Mandatory Testing - ≥80% coverage requirement
    - Principle V: Robust Error Handling - Structured exception hierarchy
    - Principle VI: Structured Logging - INFO/ERROR logs with redaction
    - Principle VII: Provider Abstraction - Multi-provider configuration support

Version: 0.1.0
Author: SCOUT Development Team
License: MIT
"""

from scout.config.loader import load_config

__all__ = ["load_config"]
__version__ = "0.1.0"