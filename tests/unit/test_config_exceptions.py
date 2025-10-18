"""Unit tests for configuration exception hierarchy.

Tests all custom exceptions in scout.config.exceptions to ensure:
- Proper initialization with expected attributes
- Correct inheritance hierarchy
- Human-readable error messages
- Exception-specific attributes (file_path, variable_name, etc.)

Author: SCOUT Development Team
License: MIT
"""

import pytest

from scout.config.exceptions import (
    ConfigFileNotFoundError,
    ConfigurationError,
    ConfigValidationError,
    EnvironmentVariableError,
    ScoutError,
)


class TestScoutError:
    """Test cases for the base ScoutError exception."""

    def test_scouterror_is_exception(self):
        """ScoutError should inherit from built-in Exception."""
        assert issubclass(ScoutError, Exception)

    def test_scouterror_can_be_raised(self):
        """ScoutError should be raisable with a message."""
        with pytest.raises(ScoutError, match="test error"):
            raise ScoutError("test error")


class TestConfigurationError:
    """Test cases for ConfigurationError base exception."""

    def test_configurationerror_inherits_from_scouterror(self):
        """ConfigurationError should inherit from ScoutError."""
        assert issubclass(ConfigurationError, ScoutError)

    def test_configurationerror_stores_message(self):
        """ConfigurationError should store the error message as an attribute."""
        error = ConfigurationError("test configuration error")
        assert error.message == "test configuration error"

    def test_configurationerror_string_representation(self):
        """ConfigurationError should have readable string representation."""
        error = ConfigurationError("test configuration error")
        assert str(error) == "test configuration error"


class TestConfigFileNotFoundError:
    """Test cases for ConfigFileNotFoundError."""

    def test_inherits_from_configurationerror(self):
        """ConfigFileNotFoundError should inherit from ConfigurationError."""
        assert issubclass(ConfigFileNotFoundError, ConfigurationError)

    def test_stores_file_path(self):
        """ConfigFileNotFoundError should store the file path attribute."""
        error = ConfigFileNotFoundError("/path/to/config.yaml")
        assert error.file_path == "/path/to/config.yaml"

    def test_generates_descriptive_message(self):
        """ConfigFileNotFoundError should generate a descriptive error message."""
        error = ConfigFileNotFoundError("/path/to/config.yaml")
        assert "Configuration file not found" in str(error)
        assert "/path/to/config.yaml" in str(error)

    def test_can_be_raised_and_caught(self):
        """ConfigFileNotFoundError should be raisable and catchable."""
        with pytest.raises(ConfigFileNotFoundError) as exc_info:
            raise ConfigFileNotFoundError("missing.yaml")

        assert exc_info.value.file_path == "missing.yaml"


class TestConfigValidationError:
    """Test cases for ConfigValidationError."""

    def test_inherits_from_configurationerror(self):
        """ConfigValidationError should inherit from ConfigurationError."""
        assert issubclass(ConfigValidationError, ConfigurationError)

    def test_basic_validation_error_without_details(self):
        """ConfigValidationError should work with just a message."""
        error = ConfigValidationError("Missing required field: api_key")
        assert "Configuration validation failed" in str(error)
        assert "Missing required field: api_key" in str(error)

    def test_validation_error_with_pydantic_errors(self):
        """ConfigValidationError should accept optional validation_errors parameter."""
        validation_errors = {"field": "value"}  # Simulated Pydantic error
        error = ConfigValidationError("Invalid field", validation_errors=validation_errors)

        assert error.validation_errors == validation_errors
        assert "Configuration validation failed" in str(error)

    def test_validation_error_defaults_to_none(self):
        """ConfigValidationError should default validation_errors to None."""
        error = ConfigValidationError("Some error")
        assert error.validation_errors is None


class TestEnvironmentVariableError:
    """Test cases for EnvironmentVariableError."""

    def test_inherits_from_configurationerror(self):
        """EnvironmentVariableError should inherit from ConfigurationError."""
        assert issubclass(EnvironmentVariableError, ConfigurationError)

    def test_stores_variable_name(self):
        """EnvironmentVariableError should store the variable name attribute."""
        error = EnvironmentVariableError("GEMINI_API_KEY")
        assert error.variable_name == "GEMINI_API_KEY"

    def test_generates_descriptive_message(self):
        """EnvironmentVariableError should generate a descriptive error message."""
        error = EnvironmentVariableError("GEMINI_API_KEY")
        assert "Required environment variable not set" in str(error)
        assert "GEMINI_API_KEY" in str(error)

    def test_can_be_raised_and_caught(self):
        """EnvironmentVariableError should be raisable and catchable."""
        with pytest.raises(EnvironmentVariableError) as exc_info:
            raise EnvironmentVariableError("MISSING_VAR")

        assert exc_info.value.variable_name == "MISSING_VAR"


class TestExceptionHierarchy:
    """Test cases for the overall exception hierarchy structure."""

    def test_all_config_exceptions_are_scouterrors(self):
        """All configuration exceptions should ultimately inherit from ScoutError."""
        assert issubclass(ConfigFileNotFoundError, ScoutError)
        assert issubclass(ConfigValidationError, ScoutError)
        assert issubclass(EnvironmentVariableError, ScoutError)

    def test_can_catch_all_config_errors_with_configurationerror(self):
        """ConfigurationError should catch all specific configuration errors."""
        # Test that all specific config errors can be caught with ConfigurationError
        for error_class in [
            ConfigFileNotFoundError,
            ConfigValidationError,
            EnvironmentVariableError,
        ]:
            with pytest.raises(ConfigurationError):
                if error_class == ConfigFileNotFoundError:
                    raise error_class("test.yaml")
                elif error_class == EnvironmentVariableError:
                    raise error_class("TEST_VAR")
                else:
                    raise error_class("test error")

    def test_can_catch_all_errors_with_scouterror(self):
        """ScoutError should catch all SCOUT-related errors."""
        with pytest.raises(ScoutError):
            raise ConfigFileNotFoundError("test.yaml")

        with pytest.raises(ScoutError):
            raise ConfigValidationError("test error")

        with pytest.raises(ScoutError):
            raise EnvironmentVariableError("TEST_VAR")
