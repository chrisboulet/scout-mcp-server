"""Configuration loader with YAML parsing and environment variable substitution.

This module provides the core configuration loading functionality for SCOUT,
implementing fail-fast validation following Constitution Principle V.

The loading process follows these steps:
    1. Load YAML file from filesystem using yaml.safe_load()
    2. Substitute environment variables with ${VAR} or ${VAR:-default} syntax
    3. Validate configuration structure with Pydantic models
    4. Return immutable, type-safe ScoutConfig object

Environment Variable Substitution:
    - Basic syntax: ${VAR_NAME} - requires variable to exist
    - Default syntax: ${VAR_NAME:-default_value} - uses default if missing
    - Recursive substitution supported (nested values in dicts/lists)
    - Missing required variables raise EnvironmentVariableError

Error Handling:
    - Missing files → ConfigFileNotFoundError
    - YAML syntax errors → ConfigValidationError
    - Missing env vars → EnvironmentVariableError
    - Validation failures → ConfigValidationError with Pydantic details
    - All errors logged at ERROR level with sensitive data redacted

Example Usage:
    >>> from scout.config import load_config
    >>> config = load_config("config/scout.yaml")
    >>> print(config.system.default_team)
    'general'

Constitution Alignment:
    - Principle II: Modular Architecture - Isolated loader module
    - Principle III: Mandatory Testing - Full integration test coverage
    - Principle V: Robust Error Handling - Fail-fast with clear errors
    - Principle VI: Structured Logging - INFO/ERROR logs with redaction

Author: SCOUT Development Team
License: MIT
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Union

import structlog
import yaml
from pydantic import ValidationError

from scout.config.exceptions import (
    ConfigFileNotFoundError,
    ConfigValidationError,
    EnvironmentVariableError,
)
from scout.config.models import ScoutConfig

# Initialize structured logger
logger = structlog.get_logger(__name__)

# Environment variable regex patterns
# Matches ${VAR} or ${VAR:-default}
ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _load_yaml_file(path: str) -> Dict[str, Any]:
    """Load YAML configuration file from filesystem.

    Args:
        path: Absolute or relative path to YAML configuration file

    Returns:
        Parsed YAML content as dictionary

    Raises:
        ConfigFileNotFoundError: If file does not exist at specified path
        ConfigValidationError: If YAML syntax is invalid or file is empty

    Example:
        >>> data = _load_yaml_file("config/scout.yaml")
        >>> print(data["providers"])
    """
    file_path = Path(path)

    # Check if file exists
    if not file_path.exists():
        logger.error("configuration_file_not_found", path=str(file_path))
        raise ConfigFileNotFoundError(str(file_path))

    # Load and parse YAML
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Handle empty YAML files
        if data is None:
            logger.error("configuration_file_empty", path=str(file_path))
            raise ConfigValidationError(f"Configuration file is empty: {file_path}")

        logger.debug("yaml_file_loaded", path=str(file_path), keys=list(data.keys()))
        return data

    except yaml.YAMLError as e:
        error_msg = f"YAML syntax error in {file_path}"
        if hasattr(e, "problem_mark"):
            mark = e.problem_mark
            error_msg += f" at line {mark.line + 1}, column {mark.column + 1}"
        logger.error("yaml_syntax_error", path=str(file_path), error=str(e))
        raise ConfigValidationError(error_msg) from e


def _substitute_env_var(match: re.Match) -> str:
    """Substitute a single environment variable match.

    Handles both ${VAR} and ${VAR:-default} syntax.

    Args:
        match: Regex match object containing env var reference

    Returns:
        Environment variable value or default

    Raises:
        EnvironmentVariableError: If required variable is not set
    """
    var_expr = match.group(1)  # Extract content between ${ and }

    # Check for default value syntax: VAR:-default
    if ":-" in var_expr:
        var_name, default_value = var_expr.split(":-", 1)
        var_name = var_name.strip()
        default_value = default_value.strip()

        value = os.environ.get(var_name)
        if value is None:
            logger.info(
                "env_var_using_default", variable=var_name, default=_redact_value(default_value)
            )
            return default_value
        return value
    else:
        # No default - variable must exist
        var_name = var_expr.strip()
        value = os.environ.get(var_name)
        if value is None:
            logger.error("env_var_not_set", variable=var_name)
            raise EnvironmentVariableError(var_name)
        return value


def _substitute_env_vars(data: Any) -> Any:
    """Recursively substitute environment variables in configuration data.

    Processes strings, dictionaries, and lists recursively to replace all
    ${VAR} and ${VAR:-default} references with actual values.

    Args:
        data: Configuration data (dict, list, str, or primitive)

    Returns:
        Configuration data with all environment variables substituted

    Raises:
        EnvironmentVariableError: If required environment variable is not set

    Example:
        >>> os.environ["API_KEY"] = "sk-test123"
        >>> data = {"key": "${API_KEY}", "timeout": "${TIMEOUT:-60}"}
        >>> result = _substitute_env_vars(data)
        >>> print(result)
        {'key': 'sk-test123', 'timeout': '60'}
    """
    if isinstance(data, dict):
        # Recursively process dictionary values
        return {key: _substitute_env_vars(value) for key, value in data.items()}
    elif isinstance(data, list):
        # Recursively process list items
        return [_substitute_env_vars(item) for item in data]
    elif isinstance(data, str):
        # Substitute environment variables in string
        return ENV_VAR_PATTERN.sub(_substitute_env_var, data)
    else:
        # Return primitives (int, float, bool, None) unchanged
        return data


def _redact_value(value: str) -> str:
    """Redact sensitive values for logging.

    Redacts values that look like API keys, passwords, or secrets to prevent
    leaking sensitive information in logs.

    Args:
        value: String value to potentially redact

    Returns:
        Redacted string (first 3 chars + "***") or original if not sensitive
    """
    # Redact if value looks like a sensitive credential
    sensitive_patterns = ["key", "secret", "token", "sk-", "api", "password", "passwd", "pwd"]
    if any(prefix in value.lower() for prefix in sensitive_patterns):
        if len(value) <= 3:
            return "***"
        return f"{value[:3]}***"
    return value


def load_config(config_path: str) -> ScoutConfig:
    """Load and validate SCOUT configuration from YAML file.

    This is the main entry point for configuration loading. It orchestrates
    YAML parsing, environment variable substitution, and Pydantic validation
    to produce a fully validated, immutable configuration object.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Validated, immutable ScoutConfig object ready for use

    Raises:
        ConfigFileNotFoundError: If configuration file does not exist
        ConfigValidationError: If YAML syntax invalid or validation fails
        EnvironmentVariableError: If required environment variable missing

    Example:
        >>> config = load_config("config/scout.yaml")
        >>> print(config.system.default_team)
        'general'
        >>> print(config.providers["gemini"].api_key)
        'sk-***'  # Redacted in logs
    """
    try:
        # Step 1: Load YAML file
        logger.info("loading_configuration", path=config_path)
        raw_data = _load_yaml_file(config_path)

        # Step 2: Substitute environment variables
        logger.debug("substituting_environment_variables")
        processed_data = _substitute_env_vars(raw_data)

        # Step 3: Validate with Pydantic models
        logger.debug("validating_configuration_schema")
        config = ScoutConfig(**processed_data)

        # Success!
        logger.info(
            "configuration_loaded_successfully",
            path=config_path,
            providers=list(config.providers.keys()),
            teams=list(config.teams.keys()),
        )
        return config

    except (ConfigFileNotFoundError, EnvironmentVariableError):
        # Re-raise our custom exceptions unchanged
        raise

    except ValidationError as e:
        # Convert Pydantic validation errors to our exception type
        error_count = len(e.errors())
        first_error = e.errors()[0] if e.errors() else {}
        field = ".".join(str(x) for x in first_error.get("loc", []))
        message = first_error.get("msg", "Unknown validation error")

        logger.error(
            "configuration_validation_failed",
            path=config_path,
            error_count=error_count,
            first_field=field,
            first_error=message,
        )
        raise ConfigValidationError(
            f"Configuration validation failed: {message} (field: {field})",
            validation_errors=e,
        ) from e

    except Exception as e:
        # Catch-all for unexpected errors
        logger.error("unexpected_configuration_error", path=config_path, error=str(e))
        raise ConfigValidationError(f"Unexpected error loading configuration: {e}") from e
