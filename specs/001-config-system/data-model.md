# Configuration System - Data Model

This document describes all Pydantic models used in the SCOUT configuration system.

## Overview

The configuration system consists of 8 immutable Pydantic models that form a hierarchical structure:

```
ScoutConfig (root)
├── providers: Dict[str, ProviderConfig]
│   └── models: Dict[str, ModelConfig]
├── teams: Dict[str, TeamConfig]
│   ├── primary: TeamMember
│   └── validators: List[ValidatorConfig]
├── tool_team_mapping: Dict[str, str]
├── system: SystemSettings
└── integrations: IntegrationConfig
```

All models are:
- **Immutable** (`frozen=True`) - Cannot be modified after creation
- **Type-safe** - Full Pydantic validation with clear error messages
- **Self-documenting** - Rich docstrings and field descriptions
- **Serializable** - Automatic API key redaction for security

---

## 1. ModelConfig

Represents a single AI model configuration within a provider.

### Fields

| Field | Type | Required | Default | Validation | Description |
|-------|------|----------|---------|------------|-------------|
| `id` | `str` | Yes | - | Non-empty | Provider-specific model identifier (e.g., "gpt-4o", "claude-3-5-sonnet") |
| `max_tokens` | `int` | Yes | - | > 0 | Maximum tokens the model can generate in a single response |
| `temperature` | `float` | No | `0.7` | 0.0 - 2.0 | Sampling temperature (0=deterministic, 2=very creative) |
| `cost_per_1k_input` | `float` | No | `0.0` | ≥ 0 | Cost per 1,000 input tokens in USD |
| `cost_per_1k_output` | `float` | No | `0.0` | ≥ 0 | Cost per 1,000 output tokens in USD |

### Example

```yaml
flash:
  id: "gemini-2.0-flash-exp"
  max_tokens: 8192
  temperature: 0.7
  cost_per_1k_input: 0.0001
  cost_per_1k_output: 0.0002
```

```python
from scout.config.models import ModelConfig

model = ModelConfig(
    id="gpt-4o",
    max_tokens=16384,
    temperature=0.7,
    cost_per_1k_input=0.005,
    cost_per_1k_output=0.015
)
```

### Validation Rules

- `max_tokens` must be positive (> 0)
- `temperature` must be between 0.0 and 2.0 inclusive
- `cost_per_1k_input` and `cost_per_1k_output` must be non-negative (≥ 0)

---

## 2. ProviderConfig

Represents an AI provider with its API key and available models.

### Fields

| Field | Type | Required | Default | Validation | Description |
|-------|------|----------|---------|------------|-------------|
| `api_key` | `str` | Yes | - | Non-empty | API key for the provider (automatically redacted) |
| `models` | `Dict[str, ModelConfig]` | Yes | - | Non-empty | Dictionary of model name → ModelConfig |

### Example

```yaml
gemini:
  api_key: "${GEMINI_API_KEY}"
  models:
    flash:
      id: "gemini-2.0-flash-exp"
      max_tokens: 8192
    pro:
      id: "gemini-2.0-pro-exp"
      max_tokens: 32768
```

```python
from scout.config.models import ProviderConfig, ModelConfig

provider = ProviderConfig(
    api_key="sk-secret-key-123",
    models={
        "flash": ModelConfig(
            id="gemini-2.0-flash-exp",
            max_tokens=8192
        )
    }
)

# API key is redacted when serialized
print(provider.model_dump()["api_key"])  # Output: "sk-***"
```

### Validation Rules

- `api_key` must be non-empty string
- `models` must contain at least one model
- Model names (dict keys) must be unique

### Security Features

- API keys are automatically redacted to first 3 characters + "***" when serialized
- Prevents accidental exposure in logs, error messages, or serialization
- Short keys (≤ 3 chars) are fully redacted to "***"

---

## 3. TeamMember

Represents a reference to a provider's model (used for team primary model).

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `provider` | `str` | Yes | - | Name of the provider (must exist in `providers`) |
| `model` | `str` | Yes | - | Name of the model within the provider (must exist in `provider.models`) |

### Example

```yaml
primary:
  provider: "gemini"
  model: "flash"
```

```python
from scout.config.models import TeamMember

member = TeamMember(
    provider="gemini",
    model="flash"
)
```

### Cross-Reference Validation

TeamMember references are validated at the `ScoutConfig` level to ensure:
- Referenced `provider` exists in configuration
- Referenced `model` exists within the provider's models

---

## 4. ValidatorConfig

Extends `TeamMember` with a trigger condition for validation behavior.

### Fields

Inherits all fields from `TeamMember`, plus:

| Field | Type | Required | Default | Validation | Description |
|-------|------|----------|---------|------------|-------------|
| `trigger` | `Literal["always", "on_error", "random"]` | No | `"always"` | One of 3 values | When to invoke this validator |

### Trigger Behaviors

- **`always`**: Validate every response from primary model (highest quality, highest cost)
- **`on_error`**: Only validate if primary model fails or returns error (cost-effective)
- **`random`**: Randomly validate responses for quality assurance (balanced approach)

### Example

```yaml
validators:
  - provider: "openai"
    model: "gpt4o"
    trigger: "always"

  - provider: "anthropic"
    model: "sonnet"
    trigger: "on_error"

  - provider: "gemini"
    model: "pro"
    trigger: "random"
```

```python
from scout.config.models import ValidatorConfig

validator = ValidatorConfig(
    provider="openai",
    model="gpt4o",
    trigger="always"
)
```

### Validation Rules

- `trigger` must be one of: `"always"`, `"on_error"`, or `"random"`
- Pydantic Literal validation ensures type safety

---

## 5. TeamConfig

Represents a team of AI models with a primary model and optional validators.

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `description` | `str` | Yes | - | Human-readable description of team's purpose |
| `primary` | `TeamMember` | Yes | - | Primary model that handles requests |
| `validators` | `List[ValidatorConfig]` | No | `[]` | Optional validators for consensus/validation |
| `use_cases` | `List[str]` | No | `[]` | List of use cases this team is optimized for |

### Example

```yaml
architect:
  description: "Architecture team for system design"
  primary:
    provider: "gemini"
    model: "pro"
  validators:
    - provider: "anthropic"
      model: "sonnet"
      trigger: "always"
    - provider: "openai"
      model: "gpt4o"
      trigger: "random"
  use_cases:
    - "system_design"
    - "architecture_review"
```

```python
from scout.config.models import TeamConfig, TeamMember, ValidatorConfig

team = TeamConfig(
    description="Architecture team",
    primary=TeamMember(provider="gemini", model="pro"),
    validators=[
        ValidatorConfig(
            provider="anthropic",
            model="sonnet",
            trigger="always"
        )
    ],
    use_cases=["system_design"]
)
```

### Design Patterns

**Scout Team** (Fast exploration):
- Fast primary model (Gemini Flash, GPT-4o-mini)
- Single `on_error` validator
- Use cases: quick_research, initial_exploration

**Architect Team** (Balanced quality):
- Balanced primary model (Gemini Pro, GPT-4o)
- Multiple validators with mixed triggers
- Use cases: system_design, architecture_review

**Expert Team** (Maximum quality):
- Best primary model (Claude Sonnet, GPT-4o)
- Multiple `always` validators for consensus
- Use cases: deep_analysis, critical_decisions

---

## 6. SystemSettings

Global system configuration affecting all teams and providers.

### Fields

| Field | Type | Required | Default | Validation | Description |
|-------|------|----------|---------|------------|-------------|
| `default_team` | `str` | Yes | - | Non-empty | Name of team to use for unmapped tools |
| `request_timeout_seconds` | `int` | No | `90` | > 0 | Maximum seconds to wait for AI response |
| `max_retries` | `int` | No | `3` | ≥ 0 | Maximum retry attempts for failed requests |
| `cache_ttl_seconds` | `int` | No | `7200` | ≥ 0 | Cache time-to-live in seconds (0 = no cache) |
| `redis_url` | `Optional[str]` | No | `None` | - | Redis URL for distributed caching (null = in-memory) |

### Example

```yaml
system:
  default_team: "scout"
  request_timeout_seconds: 90
  max_retries: 3
  cache_ttl_seconds: 7200
  redis_url: null
```

```python
from scout.config.models import SystemSettings

settings = SystemSettings(
    default_team="scout",
    request_timeout_seconds=120,
    max_retries=5,
    cache_ttl_seconds=3600,
    redis_url="redis://localhost:6379/0"
)
```

### Validation Rules

- `request_timeout_seconds` must be positive (> 0)
- `max_retries` must be non-negative (≥ 0)
- `cache_ttl_seconds` must be non-negative (≥ 0)

### Environment Variable Support

```yaml
system:
  default_team: "scout"
  request_timeout_seconds: ${REQUEST_TIMEOUT:-90}
  cache_ttl_seconds: ${CACHE_TTL:-7200}
  redis_url: ${REDIS_URL:-}
```

---

## 7. IntegrationConfig

Optional third-party integration settings.

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `notion_api_key` | `Optional[str]` | No | `None` | Notion API key for workspace integration (auto-redacted) |
| `tavily_api_key` | `Optional[str]` | No | `None` | Tavily API key for web search integration (auto-redacted) |

### Example

```yaml
integrations:
  notion_api_key: "${NOTION_API_KEY:-}"
  tavily_api_key: "${TAVILY_API_KEY:-}"
```

```python
from scout.config.models import IntegrationConfig

integrations = IntegrationConfig(
    notion_api_key="secret_abc123",
    tavily_api_key="tvly-xyz789"
)

# API keys are redacted when serialized
print(integrations.model_dump())
# Output: {'notion_api_key': 'sec***', 'tavily_api_key': 'tvl***'}
```

### Security Features

- API keys automatically redacted to first 3 characters + "***"
- `None` values remain `None` (not redacted)
- Prevents accidental exposure in logs or error messages

---

## 8. ScoutConfig

Root configuration model containing all configuration entities.

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `providers` | `Dict[str, ProviderConfig]` | Yes | - | Dictionary of provider name → ProviderConfig |
| `teams` | `Dict[str, TeamConfig]` | Yes | - | Dictionary of team name → TeamConfig |
| `tool_team_mapping` | `Dict[str, str]` | Yes | `{}` | Maps tool names → team names |
| `system` | `SystemSettings` | No | Default values | Global system settings |
| `integrations` | `IntegrationConfig` | No | All `None` | Optional integration settings |

### Example

```yaml
providers:
  gemini:
    api_key: "${GEMINI_API_KEY}"
    models:
      flash:
        id: "gemini-2.0-flash-exp"
        max_tokens: 8192

teams:
  scout:
    description: "Scout team"
    primary:
      provider: "gemini"
      model: "flash"

tool_team_mapping:
  quick_research: "scout"

system:
  default_team: "scout"

integrations:
  notion_api_key: null
  tavily_api_key: null
```

```python
from scout.config import load_config

# Load from file
config = load_config("config/scout.yaml")

# Access configuration
print(f"Providers: {list(config.providers.keys())}")
print(f"Teams: {list(config.teams.keys())}")
print(f"Default team: {config.system.default_team}")
```

### Cross-Reference Validation

ScoutConfig performs comprehensive validation at the model level:

1. **Provider Validation**:
   - At least one provider must be configured
   - Each provider must have at least one model

2. **Team Validation**:
   - At least one team must be configured
   - Team `primary.provider` must exist in `providers`
   - Team `primary.model` must exist in provider's models
   - All team validators must reference existing providers and models

3. **Tool Mapping Validation**:
   - All mapped team names must exist in `teams`
   - Unmapped tools use `system.default_team`

4. **System Validation**:
   - `system.default_team` must exist in `teams`

### Validation Error Examples

```python
# Invalid: Team references non-existent provider
{
    "providers": {"gemini": {...}},
    "teams": {
        "scout": {
            "primary": {"provider": "openai", "model": "gpt4o"}  # Error!
        }
    }
}
# Raises: ValueError: Team 'scout' primary references non-existent provider 'openai'

# Invalid: Tool maps to non-existent team
{
    "teams": {"scout": {...}},
    "tool_team_mapping": {"analyze": "expert"}  # Error!
}
# Raises: ValueError: Tool 'analyze' mapped to non-existent team 'expert'
```

---

## Immutability & Thread Safety

All models use `ConfigDict(frozen=True)`, making them:

- **Immutable**: Cannot be modified after creation
- **Thread-safe**: Safe for concurrent access
- **Hashable**: Can be used as dict keys or in sets (where applicable)

```python
config = load_config("config/scout.yaml")

# This will raise FrozenInstanceError
config.system.default_team = "expert"  # ❌ Error!

# Instead, load a new configuration
new_config = load_config("config/scout-prod.yaml")  # ✅ Correct
```

---

## Type Safety

All models provide full type safety:

```python
from scout.config.models import ModelConfig

# Type-safe construction
model = ModelConfig(
    id="gpt-4o",
    max_tokens=16384,
    temperature=0.7
)

# IDE autocomplete works
print(model.max_tokens)  # ✅ IDE knows this is int

# Type validation
model = ModelConfig(
    id="gpt-4o",
    max_tokens="16384"  # ✅ Pydantic converts to int
)

model = ModelConfig(
    id="gpt-4o",
    max_tokens="invalid"  # ❌ ValidationError
)
```

---

## Serialization & Redaction

All models can be serialized with automatic API key redaction:

```python
config = load_config("config/scout.yaml")

# Serialize to dict (API keys redacted)
data = config.model_dump()

# Serialize to JSON (API keys redacted)
import json
json_str = json.dumps(data, indent=2)

# Redaction format: first 3 chars + "***"
# "sk-secret-key-123" → "sk-***"
# "secret_abc123" → "sec***"
# "xyz" → "***" (short keys fully redacted)
```

---

## Constitution Alignment

The data model implements several Constitution principles:

**Principle II (Modular Architecture)**:
- Clear separation of concerns (Provider, Team, System, Integrations)
- Hierarchical structure with well-defined relationships

**Principle III (Mandatory Testing)**:
- Comprehensive unit tests for all models (94.86% coverage)
- Integration tests for cross-reference validation

**Principle V (Robust Error Handling)**:
- Fail-fast validation at configuration load time
- Clear error messages with field names and locations
- Type safety prevents runtime errors

**Principle VI (Structured Logging)**:
- Automatic API key redaction in all serialization
- Prevents accidental exposure of sensitive data

---

## Further Reading

- **Quick Start**: `quickstart.md` - Getting started guide
- **Example Config**: `../../config/scout.yaml.example` - Comprehensive example
- **JSON Schema**: `contracts/config-schema.json` - Auto-generated schema
- **Source Code**: `../../src/scout/config/models.py` - Pydantic model definitions
