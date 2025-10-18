"""Integration tests for configuration loading.

Tests the complete configuration loading workflow including:
- YAML file loading
- Environment variable substitution
- Pydantic validation
- Error handling for all failure scenarios

These tests use fixture YAML files to validate all acceptance scenarios
from User Story 1.

Author: SCOUT Development Team
License: MIT
"""

import os
from pathlib import Path

import pytest

from scout.config import load_config
from scout.config.exceptions import (
    ConfigFileNotFoundError,
    ConfigValidationError,
    EnvironmentVariableError,
)

# Path to fixture directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestValidConfigurationLoading:
    """Test cases for loading valid configurations (Acceptance Scenario 1)."""

    def test_load_valid_config_file(self):
        """Should successfully load minimal valid configuration file."""
        config_path = str(FIXTURES_DIR / "valid_config.yaml")
        config = load_config(config_path)

        # Verify providers loaded
        assert "gemini" in config.providers
        assert config.providers["gemini"].models["flash"].id == "gemini-2.0-flash-exp"

        # Verify teams loaded
        assert "general" in config.teams
        assert config.teams["general"].primary.provider == "gemini"

        # Verify system defaults applied
        assert config.system.default_team == "general"
        assert config.system.request_timeout_seconds == 60

    def test_loaded_config_is_immutable(self):
        """Loaded configuration should be frozen (immutable)."""
        config_path = str(FIXTURES_DIR / "valid_config.yaml")
        config = load_config(config_path)

        # Attempt to modify should raise error
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            config.system.default_team = "new_team"


class TestMissingRequiredField:
    """Test cases for missing required fields (Acceptance Scenario 2)."""

    def test_missing_api_key_raises_validation_error(self):
        """Should raise ConfigValidationError when required field missing."""
        config_path = str(FIXTURES_DIR / "invalid_missing_key.yaml")

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_path)

        # Verify error message is clear
        error_msg = str(exc_info.value)
        assert "validation failed" in error_msg.lower()
        # Should mention the missing field
        assert "api_key" in error_msg.lower() or "field required" in error_msg.lower()


class TestEnvironmentVariableSubstitution:
    """Test cases for environment variable substitution (Acceptance Scenario 3)."""

    def test_env_var_substitution_with_set_vars(self, monkeypatch):
        """Should substitute environment variables when they are set."""
        # Set required environment variable
        monkeypatch.setenv("GEMINI_API_KEY", "sk-test-from-env-12345")

        config_path = str(FIXTURES_DIR / "valid_config_with_env_vars.yaml")
        config = load_config(config_path)

        # Verify environment variable was substituted
        # Note: API key will be the actual value internally, but redacted when serialized
        assert config.providers["gemini"].api_key == "sk-test-from-env-12345"

    def test_env_var_with_default_uses_default_when_unset(self, monkeypatch):
        """Should use default value when env var with default syntax is unset."""
        # Set required env var but NOT the optional ones
        monkeypatch.setenv("GEMINI_API_KEY", "sk-test-key")
        # DEFAULT_TEAM and REDIS_URL not set - should use defaults

        config_path = str(FIXTURES_DIR / "valid_config_with_env_vars.yaml")
        config = load_config(config_path)

        # Verify defaults were used
        assert config.system.default_team == "general"  # Default from ${DEFAULT_TEAM:-general}

    def test_missing_required_env_var_raises_error(self, monkeypatch):
        """Should raise EnvironmentVariableError when required env var missing."""
        # Do NOT set GEMINI_API_KEY (required, no default)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        config_path = str(FIXTURES_DIR / "valid_config_with_env_vars.yaml")

        with pytest.raises(EnvironmentVariableError) as exc_info:
            load_config(config_path)

        # Verify error indicates which variable is missing
        assert exc_info.value.variable_name == "GEMINI_API_KEY"
        assert "GEMINI_API_KEY" in str(exc_info.value)


class TestInvalidProviderConfiguration:
    """Test cases for invalid provider config (Acceptance Scenario 4)."""

    def test_invalid_model_config_raises_validation_error(self):
        """Should raise validation error for invalid model configuration before startup."""
        config_path = str(FIXTURES_DIR / "invalid_provider_config.yaml")

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_path)

        # Verify error is about validation failure
        error_msg = str(exc_info.value)
        assert "validation failed" in error_msg.lower()


class TestMalformedYAML:
    """Test cases for malformed YAML syntax errors."""

    def test_malformed_yaml_raises_config_validation_error(self, tmp_path):
        """Should raise ConfigValidationError for YAML syntax errors."""
        # Create temporary file with invalid YAML
        invalid_yaml = tmp_path / "malformed.yaml"
        invalid_yaml.write_text(
            """
providers:
  gemini:
    api_key: "test
      # Missing closing quote - syntax error
"""
        )

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(str(invalid_yaml))

        # Verify error mentions YAML syntax
        error_msg = str(exc_info.value)
        assert "syntax error" in error_msg.lower() or "yaml" in error_msg.lower()


class TestMissingConfigFile:
    """Test cases for missing configuration file."""

    def test_missing_config_file_raises_not_found_error(self):
        """Should raise ConfigFileNotFoundError when file does not exist."""
        nonexistent_path = "/path/to/nonexistent/config.yaml"

        with pytest.raises(ConfigFileNotFoundError) as exc_info:
            load_config(nonexistent_path)

        # Verify error includes the file path (path may be normalized on Windows)
        assert "config.yaml" in exc_info.value.file_path
        assert "nonexistent" in exc_info.value.file_path
        assert "config.yaml" in str(exc_info.value)
