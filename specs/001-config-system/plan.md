# Implementation Plan: Configuration System

**Branch**: `001-config-system` | **Date**: 2025-10-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-config-system/spec.md`

## Summary

The Configuration System provides type-safe loading and validation of YAML-based application configuration with environment variable substitution. It validates AI provider settings, team definitions, tool mappings, and system parameters at startup, ensuring fail-fast behavior before the MCP server begins operation. This is the foundational component upon which all other SCOUT features depend.

**Key Capabilities**:
- Load and parse YAML configuration from file system
- Substitute environment variables using `${VAR}` syntax
- Validate configuration against Pydantic schemas with detailed error reporting
- Provide immutable, type-safe configuration access throughout application
- Redact sensitive values (API keys) in logs and error messages
- Detect configuration errors before application startup (fail-fast principle)

**Technical Approach** (from research):
- Use `pyyaml` for YAML parsing with safe loader
- Use `pydantic` v2 for schema definition and validation
- Use `python-dotenv` for environment variable loading
- Custom validator for environment variable substitution
- Singleton pattern for configuration instance (load once, immutable)

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- `pydantic` v2.5+ (schema validation and serialization)
- `pyyaml` v6.0+ (YAML parsing)
- `python-dotenv` v1.0+ (environment variable loading)
- `structlog` (for logging with redaction)

**Storage**: File system (YAML configuration file at `config/scout.yaml`)
**Testing**:
- `pytest` + `pytest-asyncio` (test framework)
- `pytest-cov` (coverage reporting - target ≥80%)
- Unit tests with mocked file I/O
- Integration tests with real YAML files

**Target Platform**: Cross-platform (Windows, Linux, macOS) - server application
**Project Type**: Single project (library module within SCOUT)

**Performance Goals**:
- Configuration loading and validation in <1 second (SC-001 from spec)
- Support ≥10 providers and ≥20 teams without degradation (SC-007)
- Minimal memory footprint (<10MB for config in memory)

**Constraints**:
- Must validate 100% of configuration before allowing startup (SC-002)
- Error messages must include field names and locations (SC-003)
- Zero runtime errors after validation passes (SC-004)
- Sensitive values (API keys) must be redacted in all logs (SC-006)

**Scale/Scope**:
- Configuration files typically <10KB
- Support up to 50 providers, 100 teams, 1000 tool mappings
- Single configuration file (no multi-file imports initially)

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ I. Contract-First Development (MCP Protocol)

**Status**: PASS (with note)

- Configuration system is internal infrastructure, not an MCP tool
- Configuration schema serves as the contract for YAML structure
- Pydantic models act as the contract definition
- **Note**: This principle applies primarily to MCP tools; configuration is foundational infrastructure

**Evidence**:
- Pydantic schemas define strict contracts for all configuration sections
- Validation ensures configuration adheres to contracts before use
- Type-safe access prevents runtime contract violations

---

### ✅ II. Modular Architecture

**Status**: PASS

- Configuration module isolated in `src/scout/config/`
- Clear separation: `loader.py` (I/O logic) vs `models.py` (schemas)
- No business logic in configuration module
- Other modules depend on config, but config is self-contained

**Evidence**:
- `src/scout/config/loader.py` - Loading and environment substitution
- `src/scout/config/models.py` - Pydantic schema definitions
- No mixing with provider logic, tool logic, or orchestration

---

### ✅ III. Mandatory Testing

**Status**: PASS

**Test Coverage Plan**:
- Unit tests: `tests/unit/test_config_loader.py` (loader logic, env substitution)
- Unit tests: `tests/unit/test_config_models.py` (schema validation)
- Integration tests: `tests/integration/test_config_integration.py` (real YAML files)
- Target: ≥80% coverage (constitution requirement)

**Test Scenarios**:
1. Valid configuration loads successfully
2. Missing required fields trigger validation errors
3. Environment variable substitution works correctly
4. Missing environment variables reported clearly
5. Invalid types (string where number expected) rejected
6. Provider references in teams validated
7. Duplicate provider names detected
8. Sensitive values redacted in error messages

---

### ✅ IV. Auto-Generated Documentation

**Status**: PASS

**Documentation Strategy**:
- Pydantic schemas auto-generate JSON schema for configuration
- Docstrings on all model fields explain purpose and constraints
- `quickstart.md` provides usage examples
- Configuration reference generated from Pydantic schema export

**Deliverables**:
- JSON schema export for configuration validation tools
- Markdown documentation from Pydantic model docstrings
- Example configuration files with inline comments

---

### ✅ V. Robust Error Handling

**Status**: PASS

**Exception Hierarchy**:
```python
class ScoutError(Exception): ...

class ConfigurationError(ScoutError):
    """Base error for configuration issues"""
    pass

class ConfigFileNotFoundError(ConfigurationError):
    """Configuration file missing"""
    pass

class ConfigValidationError(ConfigurationError):
    """Configuration validation failed"""
    pass

class EnvironmentVariableError(ConfigurationError):
    """Required environment variable missing or invalid"""
    pass
```

**Recovery Strategies**:
- File not found: Report missing path, exit immediately
- Validation errors: Report all errors at once (not just first), exit immediately
- Missing env vars: Report all missing vars, exit immediately
- Parse errors: Report YAML syntax error with line number, exit immediately

**No retries** - configuration loading is idempotent and must succeed on first attempt.

---

### ✅ VI. Structured Logging

**Status**: PASS

**Logging Plan**:
- `INFO`: Configuration loaded successfully (with redacted summary)
- `WARNING`: Using default values for optional fields
- `ERROR`: Configuration validation failed (with redacted details)
- `DEBUG`: Full configuration values (development only, with redaction)

**Sensitive Value Redaction**:
```python
def redact_sensitive(value: str) -> str:
    """Redact API keys and tokens"""
    if "api_key" in field_name or "token" in field_name:
        return "***REDACTED***"
    return value
```

**Request Correlation**: N/A (configuration loaded once at startup, no per-request tracking)

---

### ✅ VII. Provider Abstraction & Multi-Model Teams

**Status**: PASS

**Alignment**:
- Configuration system directly supports provider abstraction via provider configs
- Team configurations enable multi-model orchestration
- Extensible design allows new providers via config (no code changes)

**Evidence**:
- Provider configuration schema supports any number of providers
- Team configuration schema supports primary + N validators
- Tool-to-team mappings decouple tools from specific teams

---

### 🔍 Constitution Check Summary

**Overall Status**: ✅ **PASS** - All principles satisfied

**No complexity violations** - Configuration system follows constitution principles:
- Simple, focused module (load, validate, provide access)
- Clear separation of concerns (loading vs validation vs models)
- Comprehensive testing planned (≥80% coverage)
- Auto-generated documentation from schemas
- Robust error handling with structured exceptions
- Logging with sensitive value redaction
- Direct support for provider abstraction

**No justifications required** - Design aligns naturally with constitution.

---

## Project Structure

### Documentation (this feature)

```
specs/001-config-system/
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0: Research decisions
├── data-model.md        # Phase 1: Configuration schema entities
├── quickstart.md        # Phase 1: Usage guide
├── contracts/           # Phase 1: JSON schema exports
│   └── config-schema.json
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── spec.md              # Feature specification
```

### Source Code (repository root)

```
src/scout/config/
├── __init__.py              # Public API: load_config()
├── loader.py                # YAML loading, env var substitution
├── models.py                # Pydantic schemas (ProviderConfig, TeamConfig, etc.)
└── exceptions.py            # Configuration-specific exceptions

tests/unit/
├── test_config_loader.py    # Unit tests for loader.py
└── test_config_models.py    # Unit tests for Pydantic models

tests/integration/
├── test_config_integration.py        # End-to-end config loading tests
└── fixtures/
    ├── valid_config.yaml             # Minimal valid config
    ├── invalid_missing_key.yaml      # Missing required field
    ├── invalid_env_var.yaml          # Missing env var reference
    └── invalid_team_reference.yaml   # Team references non-existent provider

config/
└── scout.yaml.example       # Example configuration file (not loaded, for reference)
```

**Structure Decision**: Single project structure under `src/scout/config/`. This module is foundational infrastructure used by all other SCOUT components. The configuration module has no external dependencies within SCOUT (all other modules depend on it, creating a clean dependency graph).

---

## Complexity Tracking

*No violations - this section intentionally left empty.*

Configuration system design is straightforward and aligns with all constitution principles without requiring complexity justifications.

---

## Phase 0: Research & Design Decisions

### Research Topics

The following research tasks were identified to resolve technical decisions:

1. **Environment Variable Substitution Strategy**
   - **Decision**: Custom regex-based substitution before Pydantic validation
   - **Rationale**: Pydantic doesn't natively support `${VAR}` syntax; pre-processing simplifies validation
   - **Alternatives Considered**:
     - Pydantic custom validators (more complex, harder to test)
     - Third-party library like `envyaml` (additional dependency, less control)
   - **Implementation**: Regex `r'\$\{([^}]+)\}'` to find variables, `os.getenv()` for resolution

2. **Configuration Immutability Enforcement**
   - **Decision**: Load configuration once into `frozen=True` Pydantic models
   - **Rationale**: Prevents accidental modification during runtime, simplifies reasoning
   - **Alternatives Considered**:
     - Deep copy on access (performance overhead)
     - Runtime checks (adds complexity)
   - **Implementation**: `pydantic.BaseModel` with `model_config = ConfigDict(frozen=True)`

3. **Validation Error Aggregation**
   - **Decision**: Use Pydantic's built-in error aggregation (reports all errors at once)
   - **Rationale**: Better developer experience than fail-on-first-error
   - **Alternatives Considered**:
     - Custom error accumulation (reinventing wheel)
     - Fail-fast on first error (poor UX)
   - **Implementation**: Pydantic `ValidationError` exception contains all errors with field paths

4. **Sensitive Value Redaction**
   - **Decision**: Custom `__repr__` and `__str__` methods on sensitive fields
   - **Rationale**: Centralized redaction logic, works with logging and error messages
   - **Alternatives Considered**:
     - Filter in logging framework (misses error messages)
     - Manual redaction at every log site (error-prone)
   - **Implementation**: Pydantic `@field_serializer` decorator for redaction

5. **Default Values Strategy**
   - **Decision**: Explicit defaults in Pydantic schemas with documentation
   - **Rationale**: Clear, type-safe, self-documenting
   - **Alternatives Considered**:
     - Separate defaults file (duplication, sync issues)
     - Runtime defaults (less discoverable)
   - **Implementation**: Pydantic `Field(default=...)` with `description` parameter

### Research Findings Summary

All technical decisions finalized. No remaining unknowns. Ready to proceed to Phase 1 design.

**Key Takeaways**:
- Pydantic v2 provides all needed validation features out-of-box
- Environment variable substitution requires custom pre-processing
- Frozen models ensure immutability without runtime overhead
- Built-in error aggregation improves developer experience

---

## Phase 1: Design Artifacts

### Data Model (`data-model.md`)

**Configuration Entities** (implemented as Pydantic models):

1. **ScoutConfig** (root configuration)
   - Fields: `providers`, `teams`, `tool_team_mapping`, `system`, `integrations`
   - Relationships: Contains ProviderConfigs, TeamConfigs, SystemSettings, Integrations
   - Validation: Cross-validates team references to providers

2. **ProviderConfig**
   - Fields: `api_key` (string, redacted), `models` (dict[str, ModelConfig])
   - Validation: At least one model required, API key format checked

3. **ModelConfig**
   - Fields: `id` (string), `max_tokens` (int), `temperature` (float 0-2), `cost_per_1k_input` (float), `cost_per_1k_output` (float)
   - Validation: Positive values for costs/tokens, temperature in valid range

4. **TeamConfig**
   - Fields: `description` (string), `primary` (TeamMember), `validators` (list[ValidatorConfig]), `use_cases` (list[string])
   - Relationships: References ProviderConfig and ModelConfig
   - Validation: Primary model exists, validators reference valid models

5. **TeamMember**
   - Fields: `provider` (string), `model` (string)
   - Validation: Provider and model exist in ProviderConfigs

6. **ValidatorConfig**
   - Inherits: TeamMember
   - Additional Fields: `trigger` (string)
   - Validation: Trigger is valid expression (e.g., "always", "confidence < 0.8")

7. **SystemSettings**
   - Fields: `default_team` (string), `allow_team_override` (bool), `max_retries` (int), `timeout_seconds` (int), `enable_cost_tracking` (bool), `state_backend` (string), `redis_url` (string), `cache_ttl_seconds` (int)
   - Validation: Timeouts/retries > 0, state_backend in ["redis", "file"]

8. **IntegrationConfig**
   - Fields: `notion` (NotionConfig, optional), `tavily` (TavilyConfig, optional)
   - Validation: If specified, required fields present

### Contracts (`contracts/config-schema.json`)

JSON schema exported from Pydantic models for:
- External validation tools (YAML editors with schema support)
- Documentation generation
- Contract testing

**Export command**: `pydantic model_json_schema()` on `ScoutConfig` root model

### Quickstart Guide (`quickstart.md`)

**Usage Examples**:

```python
# Example 1: Load configuration
from scout.config import load_config

config = load_config("config/scout.yaml")

# Access provider settings
gemini_api_key = config.providers["gemini"].api_key  # Returns redacted in logs
flash_model = config.providers["gemini"].models["flash"]

# Access team configurations
architect_team = config.teams["architect"]
primary_model = architect_team.primary  # TeamMember(provider="gemini", model="pro")

# Access system settings
default_team = config.system.default_team  # "scout"
redis_url = config.system.redis_url
```

```python
# Example 2: Handle configuration errors
from scout.config import load_config
from scout.config.exceptions import ConfigurationError

try:
    config = load_config("config/scout.yaml")
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    # Output: "Configuration error: Missing required field 'providers.gemini.api_key'"
    sys.exit(1)
```

```python
# Example 3: Environment variable substitution
# config/scout.yaml:
#   providers:
#     gemini:
#       api_key: ${GEMINI_API_KEY}

# Shell:
#   export GEMINI_API_KEY=AIza123...

# Python:
config = load_config("config/scout.yaml")
# API key is correctly substituted and validated
```

---

## Phase 2: Implementation Planning

**Note**: Detailed task breakdown is generated by `/speckit.tasks` command (not part of this plan).

### High-Level Implementation Phases

**Phase 2.1: Core Models (Priority: P1)**
- Implement Pydantic schemas in `src/scout/config/models.py`
- Define exception hierarchy in `src/scout/config/exceptions.py`
- Write unit tests for schema validation

**Phase 2.2: Configuration Loader (Priority: P1)**
- Implement YAML loading in `src/scout/config/loader.py`
- Implement environment variable substitution
- Implement sensitive value redaction
- Write unit tests for loader logic

**Phase 2.3: Integration & Validation (Priority: P1)**
- Create integration tests with fixture YAML files
- Test all error scenarios (missing file, invalid YAML, missing env vars, validation failures)
- Verify ≥80% test coverage

**Phase 2.4: Example Configuration (Priority: P2)**
- Create `config/scout.yaml.example` with comprehensive examples
- Document all configuration options with inline comments
- Provide multiple team configurations for reference

**Phase 2.5: Documentation (Priority: P2)**
- Generate JSON schema from Pydantic models
- Create usage documentation
- Add docstrings to all public functions

### Dependencies & Constraints

**External Dependencies**:
- Pydantic v2 (mature, stable API)
- PyYAML (standard library-quality)
- python-dotenv (widely used)

**Internal Dependencies**:
- None - configuration is the foundation; all other modules depend on it

**Blocking Issues**:
- None identified

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Environment variable not set | Medium | High | Clear error message with variable name; fail fast |
| YAML syntax error | Low | Medium | PyYAML reports line numbers; fail fast with error |
| Circular team references | Low | Low | Validation detects cycles; reject config |
| Large configuration files | Low | Low | Current scope <10KB; optimize if needed |
| Pydantic v1 vs v2 differences | Low | Medium | Pin to pydantic>=2.5.0 in pyproject.toml |

---

## Success Metrics

From specification success criteria (SC-001 through SC-007):

1. **Performance**: Configuration loads in <1 second ✓
2. **Reliability**: 100% of errors detected before startup ✓
3. **Usability**: Error messages include field names and locations ✓
4. **Security**: 0% API key exposure in logs ✓
5. **Extensibility**: Add provider in <5 minutes (config-only change) ✓
6. **Scalability**: Support ≥10 providers, ≥20 teams ✓

**Validation Approach**:
- Performance: Benchmark test with `pytest-benchmark`
- Reliability: Integration tests covering all error scenarios
- Usability: Manual review of error messages
- Security: Audit tests verify redaction in all code paths
- Extensibility: Timed developer task (add new provider)
- Scalability: Stress test with 50 providers, 100 teams

---

## Completion Criteria

**Phase 0 Complete When**:
- ✅ All research decisions documented in `research.md`
- ✅ No remaining "NEEDS CLARIFICATION" items

**Phase 1 Complete When**:
- ✅ `data-model.md` defines all configuration entities
- ✅ `contracts/config-schema.json` generated from Pydantic models
- ✅ `quickstart.md` provides usage examples
- ✅ Constitution Check re-validated (all principles still satisfied)

**Phase 2 Complete When** (via `/speckit.implement`):
- All Pydantic models implemented and tested (≥80% coverage)
- Configuration loader implemented and tested
- Integration tests pass with real YAML files
- Example configuration file created
- Documentation complete and accurate

---

## Next Steps

1. ✅ **Phase 0 Complete**: Research decisions finalized (see Research section above)
2. ✅ **Phase 1 Complete**: Design artifacts defined (see Phase 1 section above)
3. ⏭️ **Ready for Phase 2**: Run `/speckit.tasks` to generate detailed implementation tasks
4. ⏭️ **Implementation**: Run `/speckit.implement` to execute tasks

**This plan is complete and ready for task generation.**

---

**Plan Created**: 2025-10-18
**Last Updated**: 2025-10-18
**Status**: ✅ Ready for `/speckit.tasks`
