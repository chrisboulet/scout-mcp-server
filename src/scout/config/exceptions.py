"""Exception hierarchy for SCOUT configuration system.

This module defines a structured exception hierarchy for configuration-related errors,
following Constitution Principle V (Robust Error Handling). All exceptions inherit from
a base ScoutError to enable consistent error handling throughout the application.

Exception Hierarchy:
    ScoutError (base for all SCOUT exceptions)
    └── ConfigurationError (base for all configuration errors)
        ├── ConfigFileNotFoundError (configuration file missing)
        ├── ConfigValidationError (validation failed)
        └── EnvironmentVariableError (env var missing or invalid)

Usage Example:
    >>> from scout.config.exceptions import ConfigFileNotFoundError
    >>> raise ConfigFileNotFoundError("/path/to/missing.yaml")
    ConfigFileNotFoundError: Configuration file not found: /path/to/missing.yaml

Author: SCOUT Development Team
License: MIT
"""

from typing import Any, Optional


class ScoutError(Exception):
    """Base exception for all SCOUT-related errors.

    All custom exceptions in the SCOUT application should inherit from this class
    to enable consistent error handling and filtering.

    This follows Constitution Principle V: Robust Error Handling with structured
    exception hierarchy.
    """

    pass


class ConfigurationError(ScoutError):
    """Base exception for all configuration-related errors.

    Raised when there are problems loading, parsing, or validating the application
    configuration. This serves as a base class for more specific configuration errors.

    Attributes:
        message: Human-readable error message
    """

    def __init__(self, message: str):
        """Initialize ConfigurationError with a descriptive message.

        Args:
            message: Human-readable description of the configuration error
        """
        self.message = message
        super().__init__(message)


class ConfigFileNotFoundError(ConfigurationError):
    """Raised when the configuration file cannot be found at the specified path.

    This error is raised during the configuration loading phase when the YAML
    configuration file does not exist at the expected location.

    Attributes:
        file_path: Absolute or relative path to the missing configuration file
        message: Human-readable error message including the file path

    Example:
        >>> raise ConfigFileNotFoundError("/app/config/scout.yaml")
        ConfigFileNotFoundError: Configuration file not found: /app/config/scout.yaml
    """

    def __init__(self, file_path: str):
        """Initialize ConfigFileNotFoundError with the missing file path.

        Args:
            file_path: Path to the configuration file that was not found
        """
        self.file_path = file_path
        message = f"Configuration file not found: {file_path}"
        super().__init__(message)


class ConfigValidationError(ConfigurationError):
    """Raised when configuration validation fails.

    This error is raised when the configuration file exists and can be parsed,
    but the values fail Pydantic validation (e.g., missing required fields,
    invalid types, constraint violations).

    Attributes:
        validation_errors: Original validation errors from Pydantic (optional)
        message: Human-readable error message with validation details

    Example:
        >>> raise ConfigValidationError("Missing required field: providers.gemini.api_key")
        ConfigValidationError: Configuration validation failed: Missing required field: providers.gemini.api_key
    """

    def __init__(self, message: str, validation_errors: Optional[Any] = None):
        """Initialize ConfigValidationError with validation details.

        Args:
            message: Human-readable description of the validation error
            validation_errors: Optional Pydantic ValidationError object for detailed error information
        """
        self.validation_errors = validation_errors
        full_message = f"Configuration validation failed: {message}"
        super().__init__(full_message)


class EnvironmentVariableError(ConfigurationError):
    """Raised when a required environment variable is missing or invalid.

    This error is raised during environment variable substitution when a variable
    referenced in the configuration (using ${VAR} syntax) is not set in the environment.

    Attributes:
        variable_name: Name of the missing or invalid environment variable
        message: Human-readable error message including the variable name

    Example:
        >>> raise EnvironmentVariableError("GEMINI_API_KEY")
        EnvironmentVariableError: Required environment variable not set: GEMINI_API_KEY
    """

    def __init__(self, variable_name: str):
        """Initialize EnvironmentVariableError with the variable name.

        Args:
            variable_name: Name of the environment variable that is missing or invalid
        """
        self.variable_name = variable_name
        message = f"Required environment variable not set: {variable_name}"
        super().__init__(message)
