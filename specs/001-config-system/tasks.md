# Implementation Tasks: Configuration System

**Branch**: `001-config-system` | **Date**: 2025-10-18 | **Plan**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md)

## Task Status Legend
- `[ ]` Not started
- `[x]` Completed
- `P1/P2/P3` Priority (from user stories)
- `US1/US2/US3/US4` User Story mapping

---

## Phase 1: Setup & Project Structure

**Purpose**: Initialize project structure and verify environment

- [ ] [T001] [P1] Create `src/scout/config/` package directory
- [ ] [T002] [P1] Create `src/scout/config/__init__.py` with module docstring
- [ ] [T003] [P1] Create `tests/unit/` directory structure
- [ ] [T004] [P1] Create `tests/integration/` directory structure
- [ ] [T005] [P1] Create `tests/integration/fixtures/` for test YAML files
- [ ] [T006] [P1] Verify dependencies installed: `pydantic>=2.5.0`, `pyyaml>=6.0`, `python-dotenv>=1.0`

**Completion Criteria**: All directories exist, dependencies verified

---

## Phase 2: Foundational - Exception Hierarchy & Base Models

**Purpose**: Establish error handling contracts before implementation

### Exception Hierarchy

- [ ] [T007] [P1] Create `src/scout/config/exceptions.py`
- [ ] [T008] [P1] Define `ScoutError(Exception)` base exception class
- [ ] [T009] [P1] Define `ConfigurationError(ScoutError)` base configuration exception
- [ ] [T010] [P1] Define `ConfigFileNotFoundError(ConfigurationError)` with file path attribute
- [ ] [T011] [P1] Define `ConfigValidationError(ConfigurationError)` with validation details
- [ ] [T012] [P1] Define `EnvironmentVariableError(ConfigurationError)` with variable name attribute
- [ ] [T013] [P1] Add docstrings to all exception classes explaining when they're raised
- [ ] [T014] [P1] Write unit tests for exception initialization in `tests/unit/test_config_exceptions.py`

**Completion Criteria**: All exceptions defined with tests, clear error messages

### Core Pydantic Models

- [ ] [T015] [P1] Create `src/scout/config/models.py` with file docstring
- [ ] [T016] [P1] [US1] Define `ModelConfig` Pydantic model (id, max_tokens, temperature, costs)
- [ ] [T017] [P1] [US1] Add validation to `ModelConfig`: positive costs/tokens, temperature 0-2
- [ ] [T018] [P1] [US1] Define `ProviderConfig` Pydantic model (api_key, models dict)
- [ ] [T019] [P1] [US1] Add validation to `ProviderConfig`: at least one model required
- [ ] [T020] [P1] [US1] Implement API key redaction in `ProviderConfig` using `@field_serializer`
- [ ] [T021] [P1] [US3] Define `TeamMember` Pydantic model (provider, model)
- [ ] [T022] [P1] [US3] Define `ValidatorConfig` Pydantic model (inherits TeamMember, adds trigger)
- [ ] [T023] [P1] [US3] Define `TeamConfig` Pydantic model (description, primary, validators, use_cases)
- [ ] [T024] [P1] [US1] Define `SystemSettings` Pydantic model (defaults, timeouts, redis_url, etc.)
- [ ] [T025] [P1] [US1] Define `IntegrationConfig` Pydantic model (notion, tavily optional)
- [ ] [T026] [P1] [US1] Define `ScoutConfig` root Pydantic model (providers, teams, tool_team_mapping, system, integrations)
- [ ] [T027] [P1] Set `model_config = ConfigDict(frozen=True)` on all models for immutability
- [ ] [T028] [P1] Add comprehensive docstrings to all model fields with examples
- [ ] [T029] [P1] Write unit tests for `ModelConfig` validation in `tests/unit/test_config_models.py`
- [ ] [T030] [P1] Write unit tests for `ProviderConfig` validation including redaction
- [ ] [T031] [P1] Write unit tests for `TeamConfig` validation
- [ ] [T032] [P1] Write unit tests for `ScoutConfig` validation

**Completion Criteria**: All 8 Pydantic models defined, frozen, tested, ≥80% coverage on models.py

---

## Phase 3: User Story 1 - Initial System Setup (P1)

**User Story**: "A developer sets up SCOUT for the first time, providing their API keys and basic configuration. The system must validate all settings before allowing the server to start."

### Configuration Loader Implementation

- [ ] [T033] [P1] [US1] Create `src/scout/config/loader.py` with file docstring
- [ ] [T034] [P1] [US1] Implement `_load_yaml_file(path: str) -> dict` function using `yaml.safe_load()`
- [ ] [T035] [P1] [US1] Add error handling for missing file → raise `ConfigFileNotFoundError`
- [ ] [T036] [P1] [US1] Add error handling for YAML syntax errors → raise `ConfigValidationError` with line number
- [ ] [T037] [P1] [US1] Implement `_substitute_env_vars(data: dict) -> dict` using regex `r'\$\{([^}]+)\}'`
- [ ] [T038] [P1] [US1] Add error handling for missing env vars → raise `EnvironmentVariableError` with variable name
- [ ] [T039] [P1] [US1] Add support for default values in env var syntax: `${VAR:-default}`
- [ ] [T040] [P1] [US1] Implement `load_config(config_path: str) -> ScoutConfig` function
- [ ] [T041] [P1] [US1] Integrate YAML loading → env var substitution → Pydantic validation
- [ ] [T042] [P1] [US1] Add logging at INFO level: "Configuration loaded successfully from {path}"
- [ ] [T043] [P1] [US1] Add logging at ERROR level for all failure scenarios (with redaction)
- [ ] [T044] [P1] [US1] Export `load_config` in `src/scout/config/__init__.py`

**Completion Criteria**: FR-001, FR-002, FR-003, FR-004 implemented

### Tests for User Story 1

- [ ] [T045] [P1] [US1] Create `tests/integration/fixtures/valid_config.yaml` with minimal valid config
- [ ] [T046] [P1] [US1] **Acceptance Scenario 1**: Test valid config loads successfully
- [ ] [T047] [P1] [US1] Create `tests/integration/fixtures/invalid_missing_key.yaml` missing api_key
- [ ] [T048] [P1] [US1] **Acceptance Scenario 2**: Test missing required field raises `ConfigValidationError` with clear message
- [ ] [T049] [P1] [US1] Create `tests/integration/fixtures/valid_config_with_env_vars.yaml` using `${GEMINI_API_KEY}`
- [ ] [T050] [P1] [US1] **Acceptance Scenario 3**: Test env var substitution works correctly with `monkeypatch` fixture
- [ ] [T051] [P1] [US1] Create `tests/integration/fixtures/invalid_provider_config.yaml` with unknown model type
- [ ] [T052] [P1] [US1] **Acceptance Scenario 4**: Test invalid provider config raises validation error before startup
- [ ] [T053] [P1] [US1] Test malformed YAML (syntax error) raises `ConfigValidationError`
- [ ] [T054] [P1] [US1] Test missing config file raises `ConfigFileNotFoundError`
- [ ] [T055] [P1] [US1] Write unit tests for `_load_yaml_file()` in `tests/unit/test_config_loader.py`
- [ ] [T056] [P1] [US1] Write unit tests for `_substitute_env_vars()` with various scenarios

**Completion Criteria**: All 4 acceptance scenarios pass, FR-001 through FR-004 verified

---

## Phase 4: User Story 2 - Adding New AI Provider (P2)

**User Story**: "A developer wants to add support for a new AI provider. They update the configuration file with the new provider details, and the system validates the new configuration."

### Provider Extensibility Implementation

- [ ] [T057] [P2] [US2] Add validation to `ScoutConfig`: ensure provider names are unique
- [ ] [T058] [P2] [US2] Add validation to `ProviderConfig`: validate model names are unique within provider
- [ ] [T059] [P2] [US2] Document provider schema in `data-model.md` with examples
- [ ] [T060] [P2] [US2] Create example provider config in `config/scout.yaml.example` for all 5 providers (Gemini, OpenAI, Anthropic, OpenRouter, Grok)

**Completion Criteria**: FR-005 implemented, provider extensibility validated

### Tests for User Story 2

- [ ] [T061] [P2] [US2] Create `tests/integration/fixtures/multi_provider_config.yaml` with 3 providers
- [ ] [T062] [P2] [US2] **Acceptance Scenario 1**: Test adding new provider section loads successfully
- [ ] [T063] [P2] [US2] **Acceptance Scenario 2**: Test all required provider fields validated (api_key, models)
- [ ] [T064] [P2] [US2] Create `tests/integration/fixtures/duplicate_provider_names.yaml`
- [ ] [T065] [P2] [US2] **Acceptance Scenario 3**: Test duplicate provider names rejected with clear error
- [ ] [T066] [P2] [US2] Test provider with empty models dict raises validation error
- [ ] [T067] [P2] [US2] Test provider with invalid model cost (negative) raises validation error

**Completion Criteria**: All 3 acceptance scenarios pass, FR-005 verified

---

## Phase 5: User Story 3 - Configuring AI Teams (P2)

**User Story**: "A developer configures different AI teams (scout, architect, expert) that combine multiple models for consensus-based decision making."

### Team Validation Implementation

- [ ] [T068] [P2] [US3] Implement cross-field validation in `ScoutConfig`: validate team references to providers
- [ ] [T069] [P2] [US3] Implement `@model_validator` in `TeamConfig`: validate primary model exists in providers
- [ ] [T070] [P2] [US3] Implement `@model_validator` in `TeamConfig`: validate all validator models exist in providers
- [ ] [T071] [P2] [US3] Validate trigger conditions are exactly one of: "always", "on_error", or "random" (no expressions allowed per Constitution Principle V)
- [ ] [T072] [P2] [US3] Add validation: team names are unique
- [ ] [T073] [P2] [US3] Add validation: tool_team_mapping references existing teams
- [ ] [T074] [P2] [US3] Document team schema in `data-model.md` with examples

**Completion Criteria**: FR-006, FR-007, FR-010 implemented

### Tests for User Story 3

- [ ] [T075] [P2] [US3] Create `tests/integration/fixtures/team_config.yaml` with scout, architect, expert teams
- [ ] [T076] [P2] [US3] **Acceptance Scenario 1**: Test team definition with primary and validators loads successfully
- [ ] [T077] [P2] [US3] Create `tests/integration/fixtures/invalid_team_reference.yaml` referencing non-existent provider
- [ ] [T078] [P2] [US3] **Acceptance Scenario 2**: Test team referencing non-existent provider raises validation error
- [ ] [T079] [P2] [US3] Create `tests/integration/fixtures/invalid_trigger.yaml` with malformed trigger expression
- [ ] [T080] [P2] [US3] **Acceptance Scenario 3**: Test invalid trigger condition raises validation error
- [ ] [T081] [P2] [US3] Test tool_team_mapping referencing non-existent team raises error
- [ ] [T082] [P2] [US3] Test team with non-existent model in validators raises error

**Completion Criteria**: All 3 acceptance scenarios pass, FR-006, FR-007, FR-010 verified

---

## Phase 6: User Story 4 - Environment-Specific Configuration (P3)

**User Story**: "A developer needs different configurations for development, staging, and production environments using environment variables to override defaults."

### Environment Variable Enhancement

- [ ] [T083] [P3] [US4] Enhance `_substitute_env_vars()` to support default value syntax `${VAR:-default}`
- [ ] [T084] [P3] [US4] Add validation: warn if optional env vars use defaults (INFO log level)
- [ ] [T085] [P3] [US4] Implement comprehensive redaction for all sensitive fields (api_key, token, password)
- [ ] [T086] [P3] [US4] Test redaction in error messages (ConfigValidationError should redact API keys)
- [ ] [T087] [P3] [US4] Test redaction in log messages (INFO/ERROR logs should redact sensitive values)
- [ ] [T088] [P3] [US4] Document environment variable best practices in `quickstart.md`

**Completion Criteria**: FR-003, FR-009, FR-012, FR-013, FR-014 implemented

### Tests for User Story 4

- [ ] [T089] [P3] [US4] Create `tests/integration/fixtures/env_override_config.yaml` with `${REDIS_URL}`, `${LOG_LEVEL}`
- [ ] [T090] [P3] [US4] **Acceptance Scenario 1**: Test env var correctly overrides config file value
- [ ] [T091] [P3] [US4] Create `tests/integration/fixtures/missing_env_var.yaml` with `${MISSING_VAR}`
- [ ] [T092] [P3] [US4] **Acceptance Scenario 2**: Test missing env var raises error with variable name
- [ ] [T093] [P3] [US4] **Acceptance Scenario 3**: Test API keys redacted when config logged/displayed
- [ ] [T094] [P3] [US4] Test env var substitution with default value `${VAR:-default}` works correctly
- [ ] [T095] [P3] [US4] Test empty env var (`VAR=""`) handled correctly vs missing var
- [ ] [T096] [P3] [US4] Test type mismatch after substitution (string where int expected) raises validation error

**Completion Criteria**: All 3 acceptance scenarios pass, FR-009, FR-014 verified

---

## Phase 7: Cross-Cutting Concerns & Polish

### Performance & Success Criteria Validation

- [ ] [T097] [P2] Add `pytest-benchmark` test: verify config loads in <1 second (SC-001)
- [ ] [T098] [P2] Create stress test: 10 providers, 20 teams load successfully (SC-007)
- [ ] [T099] [P2] Create stress test: 50 providers, 100 teams for scalability verification
- [ ] [T100] [P2] Review all error messages: ensure field names and locations included (SC-003)
- [ ] [T101] [P2] Audit test coverage: verify ≥80% for all modules (SC-002, Constitution III)

**Completion Criteria**: SC-001, SC-007 verified with tests

### Documentation & Examples

- [ ] [T102] [P2] Create comprehensive `config/scout.yaml.example` with:
  - All 5 providers (Gemini, OpenAI, Anthropic, OpenRouter, Grok)
  - 3 team examples (scout, architect, expert)
  - System settings with comments
  - Integration configs (Notion, Tavily)
  - Inline documentation for every field
- [ ] [T103] [P2] Generate JSON schema from Pydantic models using `model_json_schema()`
- [ ] [T104] [P2] Save JSON schema to `specs/001-config-system/contracts/config-schema.json`
- [ ] [T105] [P2] Create `specs/001-config-system/quickstart.md` with usage examples
- [ ] [T106] [P2] Create `specs/001-config-system/data-model.md` documenting all 8 entities
- [ ] [T107] [P2] Add comprehensive docstrings to all public functions in `loader.py`
- [ ] [T108] [P2] Add comprehensive docstrings to all models in `models.py`
- [ ] [T109] [P2] Update `README.md` configuration section with link to scout.yaml.example

**Completion Criteria**: SC-005 (add provider in <5 min) achievable with example config

### Final Validation

- [ ] [T110] [P1] Run full test suite: `pytest tests/`
- [ ] [T110a] [P1] [FR-008] Test type-safe access after config loads (no runtime type errors when accessing config fields)
- [ ] [T110b] [P1] [FR-011] Test deeply nested configuration structures (providers → models → settings → sub-settings)
- [ ] [T111] [P1] Run coverage report: `pytest --cov=src/scout/config --cov-report=term-missing --cov-fail-under=80`
- [ ] [T112] [P1] Verify all 16 functional requirements (FR-001 through FR-016) implemented
- [ ] [T113] [P1] Verify all 7 success criteria (SC-001 through SC-007) validated
- [ ] [T114] [P1] Verify all 13 acceptance scenarios pass (4 US1 + 3 US2 + 3 US3 + 3 US4)
- [ ] [T115] [P2] Run type checking: `mypy src/scout/config/`
- [ ] [T116] [P2] Run linting: `ruff check src/scout/config/`
- [ ] [T117] [P2] Run formatting: `black src/scout/config/ tests/`
- [ ] [T118] [P2] Manual test: Load example config and verify no errors
- [ ] [T119] [P2] Code review: Verify constitution principles I-VII satisfied
- [ ] [T120] [P2] Git commit: "feat: implement configuration system with validation and env var substitution"

**Completion Criteria**: All tests pass, ≥80% coverage, constitution compliant, ready for integration

---

## Task Summary

**Total Tasks**: 122
**By Priority**:
- P1 (Critical): 84 tasks
- P2 (High): 36 tasks
- P3 (Medium): 2 tasks

**By User Story**:
- US1 (Initial Setup): 25 tasks
- US2 (Add Provider): 11 tasks
- US3 (Configure Teams): 15 tasks
- US4 (Env Config): 14 tasks
- Foundation/Polish: 55 tasks

**Estimated Effort**: 3-4 days for experienced Python developer
- Day 1: Phase 1-2 (Setup + Foundational models/exceptions)
- Day 2: Phase 3 (User Story 1 - core loader functionality)
- Day 3: Phase 4-5 (User Stories 2-3 - extensibility + teams)
- Day 4: Phase 6-7 (User Story 4 + documentation + polish)

---

## Dependencies Graph

**Critical Path** (must be completed sequentially):
1. T001-T006 (Setup) → T007-T014 (Exceptions) → T015-T032 (Models) → T033-T044 (Loader) → T045-T056 (US1 Tests)

**Parallel Execution Opportunities**:
- After T032 (Models complete): Can work on T057-T074 (US2/US3 validations) in parallel with T033-T044 (Loader implementation)
- After T056 (US1 complete): Can work on T061-T082 (US2/US3 tests) in parallel with T083-T088 (US4 implementation)
- Phase 7 tasks (T097-T120) can be executed in any order after Phase 6 complete

**Blocking Tasks** (must complete before others):
- T015-T032 (Models) blocks all test tasks
- T033-T044 (Loader) blocks all integration tests
- T068-T073 (Team validation) blocks T075-T082 (Team tests)

---

## Testing Strategy

**Unit Tests** (tests/unit/):
- `test_config_exceptions.py` - Exception initialization and attributes
- `test_config_models.py` - Pydantic model validation (all 8 models)
- `test_config_loader.py` - YAML loading, env var substitution functions

**Integration Tests** (tests/integration/):
- `test_config_integration.py` - End-to-end config loading with real YAML files
- 10+ fixture YAML files covering valid, invalid, edge cases

**Coverage Target**: ≥80% (Constitution Principle III)

**Test Execution**:
```bash
# Run all tests
pytest tests/

# Run only unit tests
pytest tests/unit/

# Run with coverage
pytest --cov=src/scout/config --cov-report=term-missing --cov-fail-under=80

# Run integration tests only
pytest tests/integration/
```

---

## Success Validation Checklist

**Functional Requirements** (15 total):
- [ ] FR-001: Load configuration from file at startup
- [ ] FR-002: Validate all values before proceeding
- [ ] FR-003: Support `${VAR}` environment variable substitution
- [ ] FR-004: Fail fast with clear error messages
- [ ] FR-005: Validate AI provider configurations
- [ ] FR-006: Validate team definitions
- [ ] FR-007: Validate tool-to-team mappings
- [ ] FR-008: Provide type-safe access to config
- [ ] FR-009: Redact sensitive values in logs
- [ ] FR-010: Validate provider/model references in teams
- [ ] FR-011: Support nested configuration structures
- [ ] FR-012: Report validation errors with location info
- [ ] FR-013: Support default values for optional fields
- [ ] FR-014: Validate environment variables are set
- [ ] FR-015: Load configuration exactly once (immutable)

**Success Criteria** (7 total):
- [ ] SC-001: Config validation completes in <1 second
- [ ] SC-002: 100% of errors detected before startup
- [ ] SC-003: Error messages include field names and formats
- [ ] SC-004: Zero runtime errors after validation passes
- [ ] SC-005: Add provider in <5 minutes (config-only)
- [ ] SC-006: 0% API key exposure in logs
- [ ] SC-007: Support ≥10 providers and ≥20 teams

**Constitution Principles** (7 total):
- [ ] I. Contract-First: Pydantic schemas define contracts
- [ ] II. Modular Architecture: Isolated config module
- [ ] III. Mandatory Testing: ≥80% coverage achieved
- [ ] IV. Auto-Generated Documentation: JSON schema + docstrings
- [ ] V. Robust Error Handling: Exception hierarchy implemented
- [ ] VI. Structured Logging: INFO/ERROR logs with redaction
- [ ] VII. Provider Abstraction: Configuration supports all providers

---

**Tasks Generated**: 2025-10-18
**Ready for**: `/speckit.implement`
**Status**: ✅ Complete - Ready for implementation
