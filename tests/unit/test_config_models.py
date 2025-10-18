"""Unit tests for Pydantic configuration models.

Tests all configuration models in scout.config.models to ensure:
- Proper validation with Pydantic v2
- Immutability via frozen=True
- Field constraints (ranges, types)
- API key redaction in ProviderConfig
- Model serialization/deserialization
- Default values and optional fields

Author: SCOUT Development Team
License: MIT
"""

import pytest
from pydantic import ValidationError

from scout.config.models import (
    IntegrationConfig,
    ModelConfig,
    ProviderConfig,
    ScoutConfig,
    SystemSettings,
    TeamConfig,
    TeamMember,
    ValidatorConfig,
)


class TestModelConfig:
    """Test cases for ModelConfig Pydantic model."""

    def test_modelconfig_valid_creation(self):
        """ModelConfig should accept all valid required fields."""
        model = ModelConfig(
            id="gemini-2.0-flash-exp",
            max_tokens=8192,
            temperature=0.7,
            cost_per_1k_input=0.0001,
            cost_per_1k_output=0.0003,
        )
        assert model.id == "gemini-2.0-flash-exp"
        assert model.max_tokens == 8192
        assert model.temperature == 0.7
        assert model.cost_per_1k_input == 0.0001
        assert model.cost_per_1k_output == 0.0003

    def test_modelconfig_defaults(self):
        """ModelConfig should apply default values for optional fields."""
        model = ModelConfig(id="gpt-4o", max_tokens=16384)
        assert model.temperature == 0.7  # Default
        assert model.cost_per_1k_input == 0.0  # Default
        assert model.cost_per_1k_output == 0.0  # Default

    def test_modelconfig_max_tokens_validation(self):
        """ModelConfig should validate max_tokens range (1 to 2M)."""
        # Valid boundary
        ModelConfig(id="test", max_tokens=1)
        ModelConfig(id="test", max_tokens=2000000)

        # Invalid: below minimum
        with pytest.raises(ValidationError):
            ModelConfig(id="test", max_tokens=0)

        # Invalid: above maximum
        with pytest.raises(ValidationError):
            ModelConfig(id="test", max_tokens=2000001)

    def test_modelconfig_temperature_validation(self):
        """ModelConfig should validate temperature range (0.0 to 2.0)."""
        # Valid boundaries
        ModelConfig(id="test", max_tokens=100, temperature=0.0)
        ModelConfig(id="test", max_tokens=100, temperature=2.0)

        # Invalid: below minimum
        with pytest.raises(ValidationError):
            ModelConfig(id="test", max_tokens=100, temperature=-0.1)

        # Invalid: above maximum
        with pytest.raises(ValidationError):
            ModelConfig(id="test", max_tokens=100, temperature=2.1)

    def test_modelconfig_cost_validation(self):
        """ModelConfig should validate costs are non-negative."""
        # Valid: zero and positive
        ModelConfig(id="test", max_tokens=100, cost_per_1k_input=0.0)
        ModelConfig(id="test", max_tokens=100, cost_per_1k_output=0.01)

        # Invalid: negative costs
        with pytest.raises(ValidationError):
            ModelConfig(id="test", max_tokens=100, cost_per_1k_input=-0.001)
        with pytest.raises(ValidationError):
            ModelConfig(id="test", max_tokens=100, cost_per_1k_output=-0.001)

    def test_modelconfig_frozen(self):
        """ModelConfig should be immutable after creation."""
        model = ModelConfig(id="test", max_tokens=100)
        with pytest.raises(ValidationError):
            model.id = "new_id"


class TestProviderConfig:
    """Test cases for ProviderConfig Pydantic model."""

    def test_providerconfig_valid_creation(self):
        """ProviderConfig should accept valid api_key and models."""
        provider = ProviderConfig(
            api_key="sk-1234567890abcdef",
            models={"flash": ModelConfig(id="gemini-2.0-flash-exp", max_tokens=8192)},
        )
        assert provider.api_key == "sk-1234567890abcdef"
        assert "flash" in provider.models
        assert provider.models["flash"].id == "gemini-2.0-flash-exp"

    def test_providerconfig_api_key_redaction(self):
        """ProviderConfig should redact API key when serialized."""
        provider = ProviderConfig(
            api_key="sk-1234567890abcdef",
            models={"flash": ModelConfig(id="test", max_tokens=100)},
        )
        serialized = provider.model_dump()
        assert serialized["api_key"] == "sk-***"

    def test_providerconfig_short_api_key_redaction(self):
        """ProviderConfig should handle short API keys (≤3 chars) gracefully."""
        provider = ProviderConfig(
            api_key="abc", models={"flash": ModelConfig(id="test", max_tokens=100)}
        )
        serialized = provider.model_dump()
        assert serialized["api_key"] == "***"

        provider = ProviderConfig(
            api_key="ab", models={"flash": ModelConfig(id="test", max_tokens=100)}
        )
        serialized = provider.model_dump()
        assert serialized["api_key"] == "***"

    def test_providerconfig_frozen(self):
        """ProviderConfig should be immutable after creation."""
        provider = ProviderConfig(
            api_key="sk-test", models={"flash": ModelConfig(id="test", max_tokens=100)}
        )
        with pytest.raises(ValidationError):
            provider.api_key = "new_key"


class TestTeamMember:
    """Test cases for TeamMember Pydantic model."""

    def test_teammember_valid_creation(self):
        """TeamMember should accept valid provider and model names."""
        member = TeamMember(provider="gemini", model="flash")
        assert member.provider == "gemini"
        assert member.model == "flash"

    def test_teammember_required_fields(self):
        """TeamMember should require both provider and model fields."""
        with pytest.raises(ValidationError):
            TeamMember(provider="gemini")  # Missing model
        with pytest.raises(ValidationError):
            TeamMember(model="flash")  # Missing provider

    def test_teammember_frozen(self):
        """TeamMember should be immutable after creation."""
        member = TeamMember(provider="gemini", model="flash")
        with pytest.raises(ValidationError):
            member.provider = "openai"


class TestValidatorConfig:
    """Test cases for ValidatorConfig Pydantic model."""

    def test_validatorconfig_valid_creation(self):
        """ValidatorConfig should accept valid provider, model, and trigger."""
        validator = ValidatorConfig(provider="anthropic", model="claude-3-5-sonnet", trigger="always")
        assert validator.provider == "anthropic"
        assert validator.model == "claude-3-5-sonnet"
        assert validator.trigger == "always"

    def test_validatorconfig_default_trigger(self):
        """ValidatorConfig should default trigger to 'always'."""
        validator = ValidatorConfig(provider="openai", model="gpt-4o")
        assert validator.trigger == "always"

    def test_validatorconfig_trigger_validation(self):
        """ValidatorConfig should only accept valid trigger literals."""
        # Valid triggers
        ValidatorConfig(provider="test", model="test", trigger="always")
        ValidatorConfig(provider="test", model="test", trigger="on_error")
        ValidatorConfig(provider="test", model="test", trigger="random")

        # Invalid trigger
        with pytest.raises(ValidationError):
            ValidatorConfig(provider="test", model="test", trigger="invalid")

    def test_validatorconfig_inherits_from_teammember(self):
        """ValidatorConfig should inherit from TeamMember."""
        assert issubclass(ValidatorConfig, TeamMember)


class TestTeamConfig:
    """Test cases for TeamConfig Pydantic model."""

    def test_teamconfig_valid_creation(self):
        """TeamConfig should accept all valid fields."""
        team = TeamConfig(
            description="Code analysis team",
            primary=TeamMember(provider="gemini", model="flash"),
            validators=[
                ValidatorConfig(provider="anthropic", model="claude-3-5-sonnet", trigger="always")
            ],
            use_cases=["analyze_code", "review_pr"],
        )
        assert team.description == "Code analysis team"
        assert team.primary.provider == "gemini"
        assert len(team.validators) == 1
        assert team.validators[0].provider == "anthropic"
        assert team.use_cases == ["analyze_code", "review_pr"]

    def test_teamconfig_defaults(self):
        """TeamConfig should default validators and use_cases to empty lists."""
        team = TeamConfig(
            description="Simple team", primary=TeamMember(provider="gemini", model="flash")
        )
        assert team.validators == []
        assert team.use_cases == []

    def test_teamconfig_frozen(self):
        """TeamConfig should be immutable after creation."""
        team = TeamConfig(
            description="Test team", primary=TeamMember(provider="gemini", model="flash")
        )
        with pytest.raises(ValidationError):
            team.description = "New description"


class TestSystemSettings:
    """Test cases for SystemSettings Pydantic model."""

    def test_systemsettings_defaults(self):
        """SystemSettings should apply all default values."""
        settings = SystemSettings()
        assert settings.default_team == "general"
        assert settings.request_timeout_seconds == 60
        assert settings.max_retries == 3
        assert settings.cache_ttl_seconds == 3600
        assert settings.redis_url is None

    def test_systemsettings_custom_values(self):
        """SystemSettings should accept custom values."""
        settings = SystemSettings(
            default_team="analyst",
            request_timeout_seconds=120,
            max_retries=5,
            cache_ttl_seconds=7200,
            redis_url="redis://localhost:6379/0",
        )
        assert settings.default_team == "analyst"
        assert settings.request_timeout_seconds == 120
        assert settings.max_retries == 5
        assert settings.cache_ttl_seconds == 7200
        assert settings.redis_url == "redis://localhost:6379/0"

    def test_systemsettings_timeout_validation(self):
        """SystemSettings should validate request_timeout_seconds (1-300)."""
        SystemSettings(request_timeout_seconds=1)
        SystemSettings(request_timeout_seconds=300)

        with pytest.raises(ValidationError):
            SystemSettings(request_timeout_seconds=0)
        with pytest.raises(ValidationError):
            SystemSettings(request_timeout_seconds=301)

    def test_systemsettings_max_retries_validation(self):
        """SystemSettings should validate max_retries (0-10)."""
        SystemSettings(max_retries=0)
        SystemSettings(max_retries=10)

        with pytest.raises(ValidationError):
            SystemSettings(max_retries=-1)
        with pytest.raises(ValidationError):
            SystemSettings(max_retries=11)

    def test_systemsettings_cache_ttl_validation(self):
        """SystemSettings should validate cache_ttl_seconds (≥0)."""
        SystemSettings(cache_ttl_seconds=0)
        SystemSettings(cache_ttl_seconds=86400)

        with pytest.raises(ValidationError):
            SystemSettings(cache_ttl_seconds=-1)

    def test_systemsettings_frozen(self):
        """SystemSettings should be immutable after creation."""
        settings = SystemSettings()
        with pytest.raises(ValidationError):
            settings.default_team = "new_team"


class TestIntegrationConfig:
    """Test cases for IntegrationConfig Pydantic model."""

    def test_integrationconfig_defaults(self):
        """IntegrationConfig should default all fields to None."""
        integrations = IntegrationConfig()
        assert integrations.notion_api_key is None
        assert integrations.tavily_api_key is None

    def test_integrationconfig_with_keys(self):
        """IntegrationConfig should accept optional API keys."""
        integrations = IntegrationConfig(
            notion_api_key="secret_abc123", tavily_api_key="tvly-xyz789"
        )
        assert integrations.notion_api_key == "secret_abc123"
        assert integrations.tavily_api_key == "tvly-xyz789"

    def test_integrationconfig_frozen(self):
        """IntegrationConfig should be immutable after creation."""
        integrations = IntegrationConfig()
        with pytest.raises(ValidationError):
            integrations.notion_api_key = "new_key"


class TestScoutConfig:
    """Test cases for ScoutConfig root model."""

    def test_scoutconfig_valid_creation(self):
        """ScoutConfig should accept all valid nested configurations."""
        config = ScoutConfig(
            providers={
                "gemini": ProviderConfig(
                    api_key="sk-abc123",
                    models={"flash": ModelConfig(id="gemini-2.0-flash-exp", max_tokens=8192)},
                )
            },
            teams={
                "analyst": TeamConfig(
                    description="Code analysis team",
                    primary=TeamMember(provider="gemini", model="flash"),
                )
            },
            tool_team_mapping={"analyze_code": "analyst"},
            system=SystemSettings(),
            integrations=IntegrationConfig(),
        )
        assert "gemini" in config.providers
        assert "analyst" in config.teams
        assert config.tool_team_mapping["analyze_code"] == "analyst"
        assert config.system.default_team == "general"

    def test_scoutconfig_defaults(self):
        """ScoutConfig should apply defaults for system and integrations."""
        config = ScoutConfig(
            providers={
                "gemini": ProviderConfig(
                    api_key="sk-test",
                    models={"flash": ModelConfig(id="test", max_tokens=100)},
                )
            },
            teams={
                "analyst": TeamConfig(
                    description="Test", primary=TeamMember(provider="gemini", model="flash")
                )
            },
            tool_team_mapping={},
        )
        assert config.system.default_team == "general"
        assert config.integrations.notion_api_key is None

    def test_scoutconfig_required_fields(self):
        """ScoutConfig should require providers, teams, and tool_team_mapping."""
        with pytest.raises(ValidationError):
            ScoutConfig()  # Missing all required fields

        with pytest.raises(ValidationError):
            ScoutConfig(
                providers={
                    "gemini": ProviderConfig(
                        api_key="sk-test",
                        models={"flash": ModelConfig(id="test", max_tokens=100)},
                    )
                }
            )  # Missing teams and tool_team_mapping

    def test_scoutconfig_frozen(self):
        """ScoutConfig should be immutable after creation."""
        config = ScoutConfig(
            providers={
                "gemini": ProviderConfig(
                    api_key="sk-test",
                    models={"flash": ModelConfig(id="test", max_tokens=100)},
                )
            },
            teams={
                "analyst": TeamConfig(
                    description="Test", primary=TeamMember(provider="gemini", model="flash")
                )
            },
            tool_team_mapping={},
        )
        with pytest.raises(ValidationError):
            config.system = SystemSettings(default_team="new_team")

    def test_scoutconfig_api_key_redaction_in_nested_structure(self):
        """ScoutConfig should redact API keys in nested ProviderConfig."""
        config = ScoutConfig(
            providers={
                "gemini": ProviderConfig(
                    api_key="sk-1234567890abcdef",
                    models={"flash": ModelConfig(id="test", max_tokens=100)},
                )
            },
            teams={
                "analyst": TeamConfig(
                    description="Test", primary=TeamMember(provider="gemini", model="flash")
                )
            },
            tool_team_mapping={},
        )
        serialized = config.model_dump()
        assert serialized["providers"]["gemini"]["api_key"] == "sk-***"
