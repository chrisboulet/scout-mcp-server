"""Pydantic data models for SCOUT configuration.

This module defines immutable, validated configuration models using Pydantic v2.
All models are frozen (immutable after creation) to prevent accidental modification
of configuration values at runtime.

The configuration model hierarchy:
    - ModelConfig: AI model definition with cost tracking
    - ProviderConfig: AI provider settings with API key redaction
    - TeamMember: Single AI model assignment for a team role
    - ValidatorConfig: Validator with trigger conditions (extends TeamMember)
    - TeamConfig: Multi-model team configuration with validators
    - SystemSettings: Global system parameters and defaults
    - IntegrationConfig: Optional third-party integrations (Notion, Tavily)
    - ScoutConfig: Root configuration combining all settings

Constitution Alignment:
    - Principle II: Modular Architecture - Clear separation of concerns
    - Principle III: Mandatory Testing - All models fully testable
    - Principle V: Robust Error Handling - Pydantic validation errors
    - Principle VI: Structured Logging - API key redaction via field_serializer
    - Principle VII: Provider Abstraction - Generic provider/model structure

Example:
    >>> from scout.config.models import ScoutConfig
    >>> config = ScoutConfig(
    ...     providers={"gemini": ProviderConfig(api_key="sk-...")},
    ...     teams={"analyst": TeamConfig(...)},
    ...     tool_team_mapping={"analyze_code": "analyst"},
    ...     system=SystemSettings(),
    ...     integrations=IntegrationConfig()
    ... )
    >>> config.providers["gemini"].api_key  # Returns: "sk-***"

Author: SCOUT Development Team
License: MIT
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class ModelConfig(BaseModel):
    """Configuration for a single AI model.

    Defines model parameters and cost tracking information for usage monitoring
    and budget management.

    Attributes:
        id: Unique model identifier (e.g., "gemini-2.0-flash-exp", "gpt-4o")
        max_tokens: Maximum tokens allowed in model response
        temperature: Sampling temperature (0.0-2.0) for response randomness
        cost_per_1k_input: USD cost per 1000 input tokens
        cost_per_1k_output: USD cost per 1000 output tokens

    Example:
        >>> model = ModelConfig(
        ...     id="gemini-2.0-flash-exp",
        ...     max_tokens=8192,
        ...     temperature=0.7,
        ...     cost_per_1k_input=0.0001,
        ...     cost_per_1k_output=0.0003
        ... )
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        ...,
        description="Model identifier from provider (e.g., 'gpt-4o', 'claude-3-5-sonnet-20241022')",
        examples=["gemini-2.0-flash-exp", "gpt-4o"],
    )
    max_tokens: int = Field(
        ...,
        ge=1,
        le=2000000,
        description="Maximum tokens in model response (validated 1-2M range)",
        examples=[8192, 16384, 100000],
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0=deterministic, 2.0=very random)",
        examples=[0.0, 0.7, 1.0],
    )
    cost_per_1k_input: float = Field(
        default=0.0,
        ge=0.0,
        description="USD cost per 1000 input tokens for budget tracking",
        examples=[0.0001, 0.001, 0.01],
    )
    cost_per_1k_output: float = Field(
        default=0.0,
        ge=0.0,
        description="USD cost per 1000 output tokens for budget tracking",
        examples=[0.0003, 0.003, 0.03],
    )


class ProviderConfig(BaseModel):
    """Configuration for an AI provider.

    Stores provider-specific settings including API credentials and available models.
    API keys are automatically redacted in logs and serialization for security.

    Attributes:
        api_key: API authentication key (redacted to first 3 + "***" when serialized)
        models: Dictionary of available models keyed by model name

    Example:
        >>> provider = ProviderConfig(
        ...     api_key="sk-1234567890abcdef",
        ...     models={
        ...         "flash": ModelConfig(id="gemini-2.0-flash-exp", max_tokens=8192),
        ...         "pro": ModelConfig(id="gemini-2.0-pro-exp", max_tokens=32768)
        ...     }
        ... )
        >>> provider.model_dump()["api_key"]  # Returns: "sk-***"
    """

    model_config = ConfigDict(frozen=True)

    api_key: str = Field(
        ...,
        description="API authentication key for provider (auto-redacted in logs)",
        examples=["sk-1234567890abcdef", "AIzaSyC-1234567890"],
    )
    models: Dict[str, ModelConfig] = Field(
        ...,
        description="Available models keyed by friendly name (e.g., 'flash', 'pro')",
        examples=[{"flash": {}, "pro": {}}],
    )

    @field_validator("models")
    @classmethod
    def validate_models_not_empty(cls, models: Dict[str, ModelConfig]) -> Dict[str, ModelConfig]:
        """Validate that provider has at least one model configured.

        Args:
            models: Dictionary of models for this provider

        Returns:
            Validated models dictionary

        Raises:
            ValueError: If models dictionary is empty
        """
        if not models:
            raise ValueError("Provider must have at least one model configured")
        return models

    @field_serializer("api_key")
    def redact_api_key(self, api_key: str) -> str:
        """Redact API key to first 3 characters + '***' for security.

        Args:
            api_key: Original API key value

        Returns:
            Redacted key in format "abc***"
        """
        if len(api_key) <= 3:
            return "***"
        return f"{api_key[:3]}***"


class TeamMember(BaseModel):
    """Single AI model assignment for a team role.

    Represents one model from one provider assigned to a specific role in a team.
    Used for both primary models and validators.

    Attributes:
        provider: Name of AI provider (must match key in providers config)
        model: Name of model from provider (must match key in provider's models)

    Example:
        >>> member = TeamMember(provider="gemini", model="flash")
    """

    model_config = ConfigDict(frozen=True)

    provider: str = Field(
        ...,
        description="AI provider name (must exist in providers config)",
        examples=["gemini", "openai", "anthropic"],
    )
    model: str = Field(
        ...,
        description="Model name within provider (must exist in provider.models)",
        examples=["flash", "gpt-4o", "claude-3-5-sonnet"],
    )


class ValidatorConfig(TeamMember):
    """Validator model with trigger conditions.

    Extends TeamMember to add conditional triggering based on tool results.
    Validators perform quality checks, security reviews, or accuracy validation.

    Attributes:
        provider: Inherited from TeamMember
        model: Inherited from TeamMember
        trigger: Condition for running validator ("always", "on_error", "random")

    Example:
        >>> validator = ValidatorConfig(
        ...     provider="anthropic",
        ...     model="claude-3-5-sonnet",
        ...     trigger="on_error"
        ... )
    """

    model_config = ConfigDict(frozen=True)

    trigger: Literal["always", "on_error", "random"] = Field(
        default="always",
        description="When to run validator: 'always', 'on_error', or 'random'",
        examples=["always", "on_error", "random"],
    )


class TeamConfig(BaseModel):
    """Multi-model team configuration.

    Defines a team of AI models working together with a primary executor and
    optional validators. Each team is optimized for specific tool categories.

    Attributes:
        description: Human-readable team purpose description
        primary: Primary model that executes the tool
        validators: Optional list of validation models with trigger conditions
        use_cases: Example tools or tasks this team handles

    Example:
        >>> team = TeamConfig(
        ...     description="Code analysis and review team",
        ...     primary=TeamMember(provider="gemini", model="flash"),
        ...     validators=[
        ...         ValidatorConfig(
        ...             provider="anthropic",
        ...             model="claude-3-5-sonnet",
        ...             trigger="always"
        ...         )
        ...     ],
        ...     use_cases=["analyze_code", "review_pr", "find_bugs"]
        ... )
    """

    model_config = ConfigDict(frozen=True)

    description: str = Field(
        ...,
        description="Human-readable description of team's purpose and capabilities",
        examples=[
            "Code analysis and review team",
            "Strategic planning and research team",
        ],
    )
    primary: TeamMember = Field(
        ...,
        description="Primary model that executes tool requests",
    )
    validators: List[ValidatorConfig] = Field(
        default_factory=list,
        description="Optional validation models that review primary output",
    )
    use_cases: List[str] = Field(
        default_factory=list,
        description="Example tools or task types this team is optimized for",
        examples=[["analyze_code", "review_pr"], ["plan_strategy", "research_topic"]],
    )


class SystemSettings(BaseModel):
    """Global system configuration parameters.

    Defines system-wide defaults, timeouts, and infrastructure settings that apply
    across all teams and providers.

    Attributes:
        default_team: Team name to use when no specific mapping exists
        request_timeout_seconds: HTTP request timeout for all API calls
        max_retries: Maximum retry attempts for failed API requests
        cache_ttl_seconds: Time-to-live for Redis cache entries
        redis_url: Optional Redis connection URL for caching and state

    Example:
        >>> settings = SystemSettings(
        ...     default_team="general",
        ...     request_timeout_seconds=60,
        ...     max_retries=3,
        ...     cache_ttl_seconds=3600,
        ...     redis_url="redis://localhost:6379/0"
        ... )
    """

    model_config = ConfigDict(frozen=True)

    default_team: str = Field(
        default="general",
        description="Default team name when tool has no specific team mapping",
        examples=["general", "analyst", "planner"],
    )
    request_timeout_seconds: int = Field(
        default=60,
        ge=1,
        le=300,
        description="Timeout for AI provider API requests (1-300 seconds)",
        examples=[30, 60, 120],
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for failed API requests (0-10)",
        examples=[0, 3, 5],
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        ge=0,
        description="Redis cache TTL in seconds (0=no expiration)",
        examples=[0, 3600, 86400],
    )
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis connection URL for caching (None=no caching)",
        examples=["redis://localhost:6379/0", "redis://:password@localhost:6379/1"],
    )


class IntegrationConfig(BaseModel):
    """Optional third-party integration settings.

    Configures external services like Notion and Tavily that SCOUT can integrate
    with for enhanced functionality.

    Attributes:
        notion_api_key: Optional Notion API key for workspace integration
        tavily_api_key: Optional Tavily API key for web search capabilities

    Example:
        >>> integrations = IntegrationConfig(
        ...     notion_api_key="secret_abc123",
        ...     tavily_api_key="tvly-xyz789"
        ... )
        >>> integrations.model_dump()["notion_api_key"]  # Returns: "sec***" (redacted)
    """

    model_config = ConfigDict(frozen=True)

    notion_api_key: Optional[str] = Field(
        default=None,
        description="Notion API key for workspace integration (optional, auto-redacted)",
        examples=["secret_abc123def456"],
    )
    tavily_api_key: Optional[str] = Field(
        default=None,
        description="Tavily API key for web search integration (optional, auto-redacted)",
        examples=["tvly-abc123def456"],
    )

    @field_serializer("notion_api_key", "tavily_api_key")
    def redact_integration_keys(self, key: Optional[str]) -> Optional[str]:
        """Redact integration API keys to first 3 characters + '***' for security.

        Args:
            key: Original API key value (or None)

        Returns:
            Redacted key in format "abc***" or None if key is None
        """
        if key is None:
            return None
        if len(key) <= 3:
            return "***"
        return f"{key[:3]}***"


class ScoutConfig(BaseModel):
    """Root SCOUT configuration model.

    Top-level configuration combining all provider settings, team definitions,
    tool mappings, system parameters, and integrations. This is the single
    validated configuration object used throughout the application.

    Attributes:
        providers: Dictionary of AI providers keyed by provider name
        teams: Dictionary of team configurations keyed by team name
        tool_team_mapping: Dictionary mapping tool names to team names
        system: Global system settings and defaults
        integrations: Optional third-party integration configurations

    Example:
        >>> config = ScoutConfig(
        ...     providers={
        ...         "gemini": ProviderConfig(
        ...             api_key="sk-abc123",
        ...             models={"flash": ModelConfig(...)}
        ...         )
        ...     },
        ...     teams={
        ...         "analyst": TeamConfig(
        ...             description="Code analysis team",
        ...             primary=TeamMember(provider="gemini", model="flash")
        ...         )
        ...     },
        ...     tool_team_mapping={"analyze_code": "analyst"},
        ...     system=SystemSettings(),
        ...     integrations=IntegrationConfig()
        ... )
    """

    model_config = ConfigDict(frozen=True)

    providers: Dict[str, ProviderConfig] = Field(
        ...,
        description="AI providers keyed by provider name (e.g., 'gemini', 'openai')",
        examples=[{"gemini": {}, "openai": {}}],
    )
    teams: Dict[str, TeamConfig] = Field(
        ...,
        description="Team configurations keyed by team name (e.g., 'analyst', 'planner')",
        examples=[{"analyst": {}, "planner": {}}],
    )
    tool_team_mapping: Dict[str, str] = Field(
        ...,
        description="Tool-to-team mapping (tool_name -> team_name)",
        examples=[{"analyze_code": "analyst", "plan_strategy": "planner"}],
    )
    system: SystemSettings = Field(
        default_factory=SystemSettings,
        description="Global system configuration and defaults",
    )
    integrations: IntegrationConfig = Field(
        default_factory=IntegrationConfig,
        description="Optional third-party service integrations",
    )

    @field_validator("providers")
    @classmethod
    def validate_providers_not_empty(
        cls, providers: Dict[str, ProviderConfig]
    ) -> Dict[str, ProviderConfig]:
        """Validate that at least one AI provider is configured.

        Args:
            providers: Dictionary of provider configurations

        Returns:
            Validated providers dictionary

        Raises:
            ValueError: If providers dictionary is empty
        """
        if not providers:
            raise ValueError("Configuration must have at least one AI provider")
        return providers

    @field_validator("teams")
    @classmethod
    def validate_teams_not_empty(cls, teams: Dict[str, TeamConfig]) -> Dict[str, TeamConfig]:
        """Validate that at least one team is configured.

        Args:
            teams: Dictionary of team configurations

        Returns:
            Validated teams dictionary

        Raises:
            ValueError: If teams dictionary is empty
        """
        if not teams:
            raise ValueError("Configuration must have at least one team")
        return teams
