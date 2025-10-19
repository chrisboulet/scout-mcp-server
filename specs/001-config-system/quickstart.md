# Configuration System - Quick Start Guide

This guide will help you get started with the SCOUT configuration system in under 5 minutes.

## Prerequisites

- Python 3.11+
- API keys for at least one AI provider (Gemini, OpenAI, or Anthropic)

## Installation

```bash
# Install SCOUT
pip install scout-mcp-server

# Or install from source
git clone https://github.com/your-org/scout.git
cd scout
pip install -e .
```

## Quick Start (3 Steps)

### Step 1: Create Configuration File

Copy the example configuration:

```bash
cp config/scout.yaml.example config/scout.yaml
```

### Step 2: Set Environment Variables

Create a `.env` file with your API keys:

```bash
# .env
GEMINI_API_KEY=your-gemini-key-here
OPENAI_API_KEY=your-openai-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here
```

**Security Note**: Never commit your `.env` file or real API keys to version control!

### Step 3: Load Configuration

```python
from scout.config import load_config

# Load configuration
config = load_config("config/scout.yaml")

# Access configuration
print(f"Default team: {config.system.default_team}")
print(f"Available teams: {list(config.teams.keys())}")
print(f"Available providers: {list(config.providers.keys())}")
```

That's it! You're ready to use SCOUT.

## Basic Usage Examples

### Example 1: Access Provider Configuration

```python
from scout.config import load_config

config = load_config("config/scout.yaml")

# Get Gemini provider
gemini = config.providers["gemini"]
print(f"Gemini API key (redacted): {gemini.api_key}")  # Shows: sk-***

# Get model configuration
flash_model = gemini.models["flash"]
print(f"Model ID: {flash_model.id}")
print(f"Max tokens: {flash_model.max_tokens}")
print(f"Temperature: {flash_model.temperature}")
```

### Example 2: Access Team Configuration

```python
# Get scout team configuration
scout_team = config.teams["scout"]
print(f"Description: {scout_team.description}")
print(f"Primary: {scout_team.primary.provider}/{scout_team.primary.model}")

# Check validators
for validator in scout_team.validators:
    print(f"Validator: {validator.provider}/{validator.model} ({validator.trigger})")
```

### Example 3: Use Tool Team Mapping

```python
# Find which team handles a specific tool
team_name = config.tool_team_mapping["quick_research"]
team = config.teams[team_name]
print(f"Tool 'quick_research' → Team '{team_name}'")
print(f"Primary model: {team.primary.provider}/{team.primary.model}")
```

## Environment Variable Substitution

SCOUT supports two types of environment variable substitution:

### Required Variables

```yaml
# Variable MUST be set, or config loading fails
providers:
  gemini:
    api_key: "${GEMINI_API_KEY}"
```

### Optional Variables with Defaults

```yaml
# Uses default if variable not set
system:
  request_timeout_seconds: ${REQUEST_TIMEOUT:-90}
  cache_ttl_seconds: ${CACHE_TTL:-7200}
```

### Best Practices

1. **Use environment variables for all secrets**: API keys, tokens, passwords
2. **Use defaults for optional settings**: Timeouts, cache TTLs, URLs
3. **Set variables in .env file**: Use python-dotenv to load automatically
4. **Never commit real API keys**: Add `.env` to `.gitignore`

## Common Configuration Patterns

### Pattern 1: Single Provider Setup (Minimal)

```yaml
providers:
  gemini:
    api_key: "${GEMINI_API_KEY}"
    models:
      flash:
        id: "gemini-2.0-flash-exp"
        max_tokens: 8192
        temperature: 0.7

teams:
  general:
    description: "General purpose team"
    primary:
      provider: "gemini"
      model: "flash"

tool_team_mapping:
  default: "general"

system:
  default_team: "general"
  request_timeout_seconds: 90
  max_retries: 3
  cache_ttl_seconds: 7200

integrations:
  notion_api_key: null
  tavily_api_key: null
```

### Pattern 2: Multi-Provider with Validation

```yaml
providers:
  gemini:
    api_key: "${GEMINI_API_KEY}"
    models:
      flash:
        id: "gemini-2.0-flash-exp"
        max_tokens: 8192

  openai:
    api_key: "${OPENAI_API_KEY}"
    models:
      gpt4o:
        id: "gpt-4o"
        max_tokens: 16384

teams:
  production:
    description: "Production team with validation"
    primary:
      provider: "gemini"
      model: "flash"
    validators:
      - provider: "openai"
        model: "gpt4o"
        trigger: "always"  # Validate all responses

tool_team_mapping:
  production_query: "production"

system:
  default_team: "production"
```

### Pattern 3: Environment-Specific Configuration

```yaml
# Development environment
providers:
  gemini:
    api_key: "${GEMINI_API_KEY}"
    models:
      flash:
        id: "gemini-2.0-flash-exp"
        max_tokens: 8192

system:
  default_team: "dev"
  request_timeout_seconds: ${DEV_TIMEOUT:-30}  # Shorter timeout for dev
  cache_ttl_seconds: ${DEV_CACHE_TTL:-600}      # 10 min cache for dev
```

```bash
# .env.development
GEMINI_API_KEY=dev-key-here
DEV_TIMEOUT=30
DEV_CACHE_TTL=600

# .env.production
GEMINI_API_KEY=prod-key-here
# Uses defaults: timeout=90, cache=7200
```

## Error Handling

SCOUT provides clear, actionable error messages:

### Missing Configuration File

```python
try:
    config = load_config("nonexistent.yaml")
except ConfigFileNotFoundError as e:
    print(f"Error: {e}")
    # Error: Configuration file not found: nonexistent.yaml
```

### Missing Environment Variable

```python
# If GEMINI_API_KEY not set:
try:
    config = load_config("config/scout.yaml")
except EnvironmentVariableError as e:
    print(f"Missing env var: {e.variable_name}")
    # Missing env var: GEMINI_API_KEY
```

### Invalid Configuration

```python
try:
    config = load_config("config/invalid.yaml")
except ConfigValidationError as e:
    print(f"Validation error: {e}")
    # Validation error: Provider must have at least one model (field: providers.gemini.models)
```

## Adding a New Provider

Adding a new provider takes less than 5 minutes:

1. **Add provider to configuration**:
```yaml
providers:
  new_provider:
    api_key: "${NEW_PROVIDER_API_KEY}"
    models:
      model_name:
        id: "model-id"
        max_tokens: 8192
        temperature: 0.7
```

2. **Add to team or create new team**:
```yaml
teams:
  new_team:
    description: "Team using new provider"
    primary:
      provider: "new_provider"
      model: "model_name"
```

3. **Map tools to team**:
```yaml
tool_team_mapping:
  specialized_task: "new_team"
```

4. **Set environment variable**:
```bash
export NEW_PROVIDER_API_KEY=your-key-here
```

That's it! The system automatically validates cross-references and ensures the provider is correctly configured.

## Next Steps

- **Advanced Configuration**: See `config/scout.yaml.example` for comprehensive examples
- **Data Model Documentation**: Read `data-model.md` for entity details
- **API Reference**: Check module docstrings for programmatic usage
- **Constitution**: Review project principles in `.claude/constitution.md`

## Troubleshooting

### Problem: Config loads slowly

**Solution**: Check if you're validating large team configurations. Consider:
- Reducing number of validators
- Using "on_error" trigger instead of "always"
- Caching configuration object

### Problem: API keys visible in logs

**Solution**: API keys are automatically redacted in:
- Model serialization (`model_dump()`)
- Log output (structlog)
- Error messages

If you see unredacted keys, file a bug report.

### Problem: Cross-reference validation fails

**Solution**: Ensure:
- Team primary/validators reference existing providers
- Tool mappings reference existing teams
- Provider models reference existing model IDs

Error messages include field names and locations to help debug.

## Support

- **Issues**: https://github.com/your-org/scout/issues
- **Documentation**: `specs/001-config-system/`
- **Examples**: `config/scout.yaml.example`

---

**Constitution Principle V**: Fail-fast validation catches configuration errors at startup, not runtime.
