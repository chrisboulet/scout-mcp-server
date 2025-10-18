"""Unit tests for configuration loader functions.

Tests individual loader functions in isolation:
- _load_yaml_file() - YAML file loading
- _substitute_env_vars() - Environment variable substitution

Author: SCOUT Development Team
License: MIT
"""

import os
from pathlib import Path

import pytest

from scout.config.exceptions import (
    ConfigFileNotFoundError,
    ConfigValidationError,
    EnvironmentVariableError,
)
from scout.config.loader import _load_yaml_file, _substitute_env_vars


class TestLoadYamlFile:
    """Test cases for _load_yaml_file() function."""

    def test_load_valid_yaml_file(self, tmp_path):
        """Should successfully load valid YAML file and return dict."""
        # Create temporary YAML file
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
providers:
  gemini:
    api_key: "sk-test"
teams:
  general:
    description: "Test team"
"""
        )

        result = _load_yaml_file(str(yaml_file))

        assert isinstance(result, dict)
        assert "providers" in result
        assert "teams" in result
        assert result["providers"]["gemini"]["api_key"] == "sk-test"

    def test_load_nonexistent_file_raises_error(self):
        """Should raise ConfigFileNotFoundError for missing file."""
        nonexistent_path = "/nonexistent/path/config.yaml"

        with pytest.raises(ConfigFileNotFoundError) as exc_info:
            _load_yaml_file(nonexistent_path)

        # Path may be normalized on Windows (/ to \), check path is present in error
        assert "config.yaml" in exc_info.value.file_path
        assert "nonexistent" in exc_info.value.file_path

    def test_load_empty_yaml_file_raises_error(self, tmp_path):
        """Should raise ConfigValidationError for empty YAML file."""
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")

        with pytest.raises(ConfigValidationError) as exc_info:
            _load_yaml_file(str(empty_file))

        assert "empty" in str(exc_info.value).lower()

    def test_load_malformed_yaml_raises_error(self, tmp_path):
        """Should raise ConfigValidationError for invalid YAML syntax."""
        malformed_file = tmp_path / "malformed.yaml"
        malformed_file.write_text(
            """
providers:
  gemini:
    api_key: "unclosed string
      # Syntax error - missing quote
"""
        )

        with pytest.raises(ConfigValidationError) as exc_info:
            _load_yaml_file(str(malformed_file))

        error_msg = str(exc_info.value)
        assert "syntax error" in error_msg.lower() or "yaml" in error_msg.lower()


class TestSubstituteEnvVars:
    """Test cases for _substitute_env_vars() function."""

    def test_substitute_single_env_var_in_string(self, monkeypatch):
        """Should substitute single environment variable in string."""
        monkeypatch.setenv("TEST_VAR", "test_value")

        data = "Value is ${TEST_VAR}"
        result = _substitute_env_vars(data)

        assert result == "Value is test_value"

    def test_substitute_multiple_env_vars_in_string(self, monkeypatch):
        """Should substitute multiple environment variables in one string."""
        monkeypatch.setenv("VAR1", "value1")
        monkeypatch.setenv("VAR2", "value2")

        data = "${VAR1} and ${VAR2}"
        result = _substitute_env_vars(data)

        assert result == "value1 and value2"

    def test_substitute_env_vars_in_dict(self, monkeypatch):
        """Should recursively substitute env vars in dictionary values."""
        monkeypatch.setenv("API_KEY", "sk-12345")
        monkeypatch.setenv("TIMEOUT", "120")

        data = {"key": "${API_KEY}", "timeout": "${TIMEOUT}", "nested": {"value": "${API_KEY}"}}

        result = _substitute_env_vars(data)

        assert result["key"] == "sk-12345"
        assert result["timeout"] == "120"
        assert result["nested"]["value"] == "sk-12345"

    def test_substitute_env_vars_in_list(self, monkeypatch):
        """Should recursively substitute env vars in list items."""
        monkeypatch.setenv("ITEM1", "value1")
        monkeypatch.setenv("ITEM2", "value2")

        data = ["${ITEM1}", "${ITEM2}", "static"]

        result = _substitute_env_vars(data)

        assert result == ["value1", "value2", "static"]

    def test_substitute_with_default_value_when_var_set(self, monkeypatch):
        """Should use actual value when env var with default is set."""
        monkeypatch.setenv("VAR_WITH_DEFAULT", "actual_value")

        data = "${VAR_WITH_DEFAULT:-default_value}"
        result = _substitute_env_vars(data)

        assert result == "actual_value"

    def test_substitute_with_default_value_when_var_not_set(self, monkeypatch):
        """Should use default value when env var with default is not set."""
        monkeypatch.delenv("VAR_NOT_SET", raising=False)

        data = "${VAR_NOT_SET:-default_value}"
        result = _substitute_env_vars(data)

        assert result == "default_value"

    def test_substitute_with_default_containing_special_chars(self, monkeypatch):
        """Should handle defaults with special characters correctly."""
        monkeypatch.delenv("REDIS_URL", raising=False)

        data = "${REDIS_URL:-redis://localhost:6379/0}"
        result = _substitute_env_vars(data)

        assert result == "redis://localhost:6379/0"

    def test_missing_required_env_var_raises_error(self, monkeypatch):
        """Should raise EnvironmentVariableError for missing required var."""
        monkeypatch.delenv("MISSING_VAR", raising=False)

        data = "${MISSING_VAR}"

        with pytest.raises(EnvironmentVariableError) as exc_info:
            _substitute_env_vars(data)

        assert exc_info.value.variable_name == "MISSING_VAR"

    def test_preserve_non_string_primitives(self):
        """Should preserve non-string primitives unchanged."""
        data = {
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list_of_ints": [1, 2, 3],
        }

        result = _substitute_env_vars(data)

        assert result["integer"] == 42
        assert result["float"] == 3.14
        assert result["boolean"] is True
        assert result["null"] is None
        assert result["list_of_ints"] == [1, 2, 3]

    def test_handle_string_without_env_vars(self):
        """Should return strings without env vars unchanged."""
        data = "This is a plain string"
        result = _substitute_env_vars(data)

        assert result == "This is a plain string"

    def test_handle_empty_dict(self):
        """Should handle empty dictionary."""
        data = {}
        result = _substitute_env_vars(data)

        assert result == {}

    def test_handle_empty_list(self):
        """Should handle empty list."""
        data = []
        result = _substitute_env_vars(data)

        assert result == []

    def test_complex_nested_structure(self, monkeypatch):
        """Should handle complex nested data structures."""
        monkeypatch.setenv("PROVIDER", "gemini")
        monkeypatch.setenv("MODEL_ID", "gemini-2.0-flash")
        monkeypatch.setenv("TIMEOUT", "60")

        data = {
            "providers": {
                "${PROVIDER}": {
                    "models": ["${MODEL_ID}"],
                    "settings": {"timeout": "${TIMEOUT:-30}"},
                }
            },
            "defaults": [1, "${PROVIDER}", {"nested": "${MODEL_ID}"}],
        }

        result = _substitute_env_vars(data)

        # Note: dict keys are not substituted in this implementation
        # Only values are substituted
        assert result["providers"]["${PROVIDER}"]["models"][0] == "gemini-2.0-flash"
        assert result["providers"]["${PROVIDER}"]["settings"]["timeout"] == "60"
        assert result["defaults"][1] == "gemini"
        assert result["defaults"][2]["nested"] == "gemini-2.0-flash"
