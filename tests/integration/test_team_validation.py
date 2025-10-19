"""Integration tests for team validation and cross-references (User Story 3).

Tests that team configurations properly validate references to providers and models,
ensuring referential integrity across the configuration.

Acceptance Scenarios:
  1. Team definition with primary and validators loads successfully
  2. Team referencing non-existent provider raises validation error
  3. Tool mapping referencing non-existent team raises validation error

Author: SCOUT Development Team
License: MIT
"""

from pathlib import Path

import pytest

from scout.config import load_config
from scout.config.exceptions import ConfigValidationError

# Path to fixture directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestTeamConfiguration:
    """Test cases for complex team configurations (Acceptance Scenario 1 / T076)."""

    def test_load_team_config_with_multiple_teams(self):
        """Should successfully load configuration with scout, architect, and expert teams."""
        config_path = str(FIXTURES_DIR / "team_config.yaml")
        config = load_config(config_path)

        # Verify all 3 teams loaded
        assert len(config.teams) == 3
        assert "scout" in config.teams
        assert "architect" in config.teams
        assert "expert" in config.teams

        # Verify scout team structure
        scout = config.teams["scout"]
        assert scout.description == "Scout team for quick exploration and initial analysis"
        assert scout.primary.provider == "gemini"
        assert scout.primary.model == "flash"
        assert len(scout.validators) == 1
        assert scout.validators[0].provider == "openai"
        assert scout.validators[0].trigger == "on_error"

        # Verify architect team with multiple validators
        architect = config.teams["architect"]
        assert architect.primary.provider == "gemini"
        assert architect.primary.model == "pro"
        assert len(architect.validators) == 2
        assert architect.validators[0].provider == "anthropic"
        assert architect.validators[0].trigger == "always"
        assert architect.validators[1].provider == "openai"
        assert architect.validators[1].trigger == "random"

        # Verify expert team
        expert = config.teams["expert"]
        assert expert.primary.provider == "anthropic"
        assert expert.primary.model == "claude"
        assert len(expert.validators) == 1

    def test_tool_team_mapping_references_valid_teams(self):
        """Should validate that tool_team_mapping references existing teams."""
        config_path = str(FIXTURES_DIR / "team_config.yaml")
        config = load_config(config_path)

        # Verify tool mappings
        assert config.tool_team_mapping["quick_research"] == "scout"
        assert config.tool_team_mapping["system_design"] == "architect"
        assert config.tool_team_mapping["deep_analysis"] == "expert"


class TestInvalidTeamReferences:
    """Test cases for invalid team provider/model references (Acceptance Scenario 2 / T078)."""

    def test_team_with_non_existent_provider_rejected(self):
        """Should reject team referencing provider that doesn't exist in providers dict."""
        config_path = str(FIXTURES_DIR / "invalid_team_reference.yaml")

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_path)

        # Verify error message mentions the invalid provider reference
        error_msg = str(exc_info.value)
        assert "non-existent provider" in error_msg or "openai" in error_msg

    def test_team_with_non_existent_model_rejected(self):
        """Should reject team validator referencing model that doesn't exist."""
        config_path = str(FIXTURES_DIR / "invalid_validator_model.yaml")

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_path)

        # Verify error message mentions the invalid model reference
        error_msg = str(exc_info.value)
        assert "non-existent model" in error_msg or "gpt5" in error_msg


class TestInvalidToolTeamMapping:
    """Test cases for invalid tool_team_mapping (T081)."""

    def test_tool_mapping_to_non_existent_team_rejected(self):
        """Should reject tool_team_mapping referencing team that doesn't exist."""
        config_path = str(FIXTURES_DIR / "invalid_tool_mapping.yaml")

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_path)

        # Verify error message mentions the invalid team reference
        error_msg = str(exc_info.value)
        assert "non-existent team" in error_msg or "analyst" in error_msg


class TestValidatorTriggerConditions:
    """Test cases for validator trigger conditions (T071)."""

    def test_validator_trigger_always(self):
        """Should accept 'always' trigger condition."""
        config_path = str(FIXTURES_DIR / "team_config.yaml")
        config = load_config(config_path)

        # Architect team has a validator with 'always' trigger
        architect = config.teams["architect"]
        assert architect.validators[0].trigger == "always"

    def test_validator_trigger_on_error(self):
        """Should accept 'on_error' trigger condition."""
        config_path = str(FIXTURES_DIR / "team_config.yaml")
        config = load_config(config_path)

        # Scout team has a validator with 'on_error' trigger
        scout = config.teams["scout"]
        assert scout.validators[0].trigger == "on_error"

    def test_validator_trigger_random(self):
        """Should accept 'random' trigger condition."""
        config_path = str(FIXTURES_DIR / "team_config.yaml")
        config = load_config(config_path)

        # Architect team has a validator with 'random' trigger
        architect = config.teams["architect"]
        assert architect.validators[1].trigger == "random"

    def test_invalid_trigger_rejected_by_pydantic(self):
        """Should reject invalid trigger values via Pydantic Literal validation."""
        # Invalid trigger values are rejected at Pydantic validation time
        # (before cross-reference validation), so this is tested in unit tests
        pass


class TestCrossReferenceValidation:
    """Test cases for comprehensive cross-reference validation."""

    def test_all_team_primaries_validated(self):
        """Should validate that all team primary models reference existing provider models."""
        # Valid config should pass
        config_path = str(FIXTURES_DIR / "team_config.yaml")
        config = load_config(config_path)

        # Verify all primaries are valid
        for team_name, team in config.teams.items():
            assert team.primary.provider in config.providers
            assert team.primary.model in config.providers[team.primary.provider].models

    def test_all_team_validators_validated(self):
        """Should validate that all team validators reference existing provider models."""
        config_path = str(FIXTURES_DIR / "team_config.yaml")
        config = load_config(config_path)

        # Verify all validators are valid
        for team_name, team in config.teams.items():
            for validator in team.validators:
                assert validator.provider in config.providers
                assert validator.model in config.providers[validator.provider].models
