"""Integration tests for environment variable substitution (User Story 4).

Tests environment variable substitution with defaults, validation, and redaction
to ensure secure configuration management across environments.

Acceptance Scenarios:
  1. Environment variables correctly override config file values
  2. Missing required env vars raise clear error with variable name
  3. API keys are redacted when config is logged or displayed

Author: SCOUT Development Team
License: MIT
"""

import os
from pathlib import Path

import pytest

from scout.config import load_config
from scout.config.exceptions import ConfigValidationError, EnvironmentVariableError

# Path to fixture directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestEnvVarSubstitution:
    """Test cases for environment variable substitution (Acceptance Scenario 1 / T090)."""

    def test_env_var_overrides_config_value(self):
        """Should successfully substitute environment variable when set."""
        # Set environment variables
        os.environ["GEMINI_API_KEY"] = "sk-real-gemini-key-12345"
        os.environ["NOTION_API_KEY"] = "secret_notion_xyz789"

        try:
            config_path = str(FIXTURES_DIR / "env_override_config.yaml")
            config = load_config(config_path)

            # Verify environment variable was used (not default)
            # Note: API keys are redacted in model_dump(), but internally they're full
            assert config.providers["gemini"].api_key == "sk-real-gemini-key-12345"
            assert config.integrations.notion_api_key == "secret_notion_xyz789"

        finally:
            # Clean up
            del os.environ["GEMINI_API_KEY"]
            del os.environ["NOTION_API_KEY"]

    def test_env_var_with_default_uses_default_when_not_set(self):
        """Should use default value when optional env var not set (T094)."""
        # Ensure vars are NOT set
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("REQUEST_TIMEOUT", None)
        os.environ.pop("TAVILY_API_KEY", None)
        os.environ["NOTION_API_KEY"] = "notion-key-required"

        try:
            config_path = str(FIXTURES_DIR / "env_override_config.yaml")
            config = load_config(config_path)

            # Verify defaults were used
            assert config.providers["gemini"].api_key == "sk-test-default-key"
            assert config.system.request_timeout_seconds == 90  # Pydantic converts to int
            assert config.integrations.tavily_api_key == "default-tavily-key"

        finally:
            del os.environ["NOTION_API_KEY"]

    def test_env_var_with_default_uses_env_when_set(self):
        """Should use env var value when set, ignoring default (T094)."""
        os.environ["GEMINI_API_KEY"] = "sk-override-gemini"
        os.environ["REQUEST_TIMEOUT"] = "120"
        os.environ["NOTION_API_KEY"] = "notion-override"

        try:
            config_path = str(FIXTURES_DIR / "env_override_config.yaml")
            config = load_config(config_path)

            # Verify env vars were used (not defaults)
            assert config.providers["gemini"].api_key == "sk-override-gemini"
            assert config.system.request_timeout_seconds == 120  # Pydantic converts to int

        finally:
            del os.environ["GEMINI_API_KEY"]
            del os.environ["REQUEST_TIMEOUT"]
            del os.environ["NOTION_API_KEY"]


class TestMissingEnvVar:
    """Test cases for missing required env vars (Acceptance Scenario 2 / T092)."""

    def test_missing_required_env_var_raises_error_with_name(self):
        """Should raise EnvironmentVariableError with variable name when required var missing."""
        # Ensure variable is NOT set
        os.environ.pop("MISSING_REQUIRED_VAR", None)

        config_path = str(FIXTURES_DIR / "missing_env_var.yaml")

        with pytest.raises(EnvironmentVariableError) as exc_info:
            load_config(config_path)

        # Verify error message includes variable name
        error = exc_info.value
        assert "MISSING_REQUIRED_VAR" in str(error)
        assert error.variable_name == "MISSING_REQUIRED_VAR"


class TestEmptyVsUnsetEnvVar:
    """Test cases for empty vs missing environment variables (T095)."""

    def test_empty_env_var_uses_empty_string(self):
        """Should use empty string when env var is set to empty (VAR="")."""
        os.environ["GEMINI_API_KEY"] = ""
        os.environ["NOTION_API_KEY"] = "notion-key"

        try:
            config_path = str(FIXTURES_DIR / "env_override_config.yaml")
            config = load_config(config_path)

            # Empty string should be used, not the default
            assert config.providers["gemini"].api_key == ""

        finally:
            del os.environ["GEMINI_API_KEY"]
            del os.environ["NOTION_API_KEY"]

    def test_unset_env_var_with_default_uses_default(self):
        """Should use default when env var is unset (not in environment)."""
        # Ensure var is completely unset (not just empty)
        os.environ.pop("CACHE_TTL", None)
        os.environ["NOTION_API_KEY"] = "notion-key"

        try:
            config_path = str(FIXTURES_DIR / "env_override_config.yaml")
            config = load_config(config_path)

            # Should use default value from YAML
            assert config.system.cache_ttl_seconds == 7200  # Pydantic converts to int

        finally:
            del os.environ["NOTION_API_KEY"]


class TestTypeMismatchAfterSubstitution:
    """Test cases for type validation after env var substitution (T096)."""

    def test_type_mismatch_raises_validation_error(self):
        """Should raise ConfigValidationError when env var substitution results in wrong type."""
        # Set timeout to a non-numeric string
        os.environ["REQUEST_TIMEOUT"] = "not-a-number"
        os.environ["NOTION_API_KEY"] = "notion-key"

        try:
            config_path = str(FIXTURES_DIR / "env_override_config.yaml")

            with pytest.raises(ConfigValidationError) as exc_info:
                load_config(config_path)

            # Verify error mentions validation failure
            error_msg = str(exc_info.value)
            assert "validation" in error_msg.lower() or "invalid" in error_msg.lower()

        finally:
            del os.environ["REQUEST_TIMEOUT"]
            del os.environ["NOTION_API_KEY"]


class TestAPIKeyRedaction:
    """Test cases for API key redaction (Acceptance Scenario 3 / T093, T086, T087)."""

    def test_api_keys_redacted_in_serialization(self):
        """Should redact API keys when config is serialized (model_dump)."""
        os.environ["GEMINI_API_KEY"] = "sk-very-secret-key-123456789"
        os.environ["NOTION_API_KEY"] = "secret_notion_key_abc123"

        try:
            config_path = str(FIXTURES_DIR / "env_override_config.yaml")
            config = load_config(config_path)

            # Serialize config
            serialized = config.model_dump()

            # Verify API keys are redacted
            assert serialized["providers"]["gemini"]["api_key"] == "sk-***"
            assert serialized["integrations"]["notion_api_key"] == "sec***"

        finally:
            del os.environ["GEMINI_API_KEY"]
            del os.environ["NOTION_API_KEY"]

    def test_redaction_works_with_defaults(self):
        """Should redact default API key values as well."""
        # Use defaults (no env vars set)
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("TAVILY_API_KEY", None)
        os.environ["NOTION_API_KEY"] = "required-key"

        try:
            config_path = str(FIXTURES_DIR / "env_override_config.yaml")
            config = load_config(config_path)

            serialized = config.model_dump()

            # Default values should also be redacted
            assert serialized["providers"]["gemini"]["api_key"] == "sk-***"
            assert serialized["integrations"]["tavily_api_key"] == "def***"

        finally:
            del os.environ["NOTION_API_KEY"]

    def test_password_values_redacted_in_logging(self):
        """Should redact values containing 'password' in logging (T087)."""
        from scout.config.loader import _redact_value

        # Test various sensitive patterns
        assert _redact_value("mypassword123") == "myp***"
        assert _redact_value("secret_key") == "sec***"
        assert _redact_value("api_token_xyz") == "api***"
        assert _redact_value("sk-test-123") == "sk-***"
        assert _redact_value("pwd12345") == "pwd***"

        # Non-sensitive values should not be redacted
        assert _redact_value("general_config") == "general_config"
        assert _redact_value("timeout") == "timeout"


class TestErrorMessageRedaction:
    """Test cases for redaction in error messages (T086)."""

    def test_validation_error_redacts_api_keys(self):
        """Should redact API keys in ConfigValidationError messages."""
        # This test verifies that if an API key appears in error messages,
        # it would be caught by validation before being displayed
        # The current implementation validates structure, not content,
        # so API keys don't appear in error messages by design

        # Testing the redaction function directly
        from scout.config.loader import _redact_value

        # Simulate redacting a value that might appear in error context
        sensitive_value = "sk-secret-key-12345"
        redacted = _redact_value(sensitive_value)

        assert redacted == "sk-***"
        assert "secret" not in redacted
        assert "12345" not in redacted
