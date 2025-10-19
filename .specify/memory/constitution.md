<!--
Sync Impact Report - 2025-10-19

VERSION CHANGE: 1.0.0 → 1.1.0 (MINOR - Added licensing principle)

MODIFIED PRINCIPLES:
- None modified, all existing principles retained

ADDED SECTIONS:
- VIII. Open Source Licensing Compliance (Apache 2.0)

TEMPLATES STATUS:
✅ plan-template.md - Reviewed, compatible with constitution checks
✅ spec-template.md - Reviewed, user story approach aligns
✅ tasks-template.md - Reviewed, task categorization compatible
✅ All command templates - No updates required

FOLLOW-UP TODOS:
- None - All placeholders filled

RATIONALE FOR VERSION 1.1.0:
Added new principle VIII for Apache 2.0 licensing compliance as requested by user.
This is a MINOR bump because it adds material new guidance about licensing
requirements that affect how the project must be distributed and attributed.
-->

# SCOUT Constitution

## Core Principles

### I. Contract-First Development (MCP Protocol)

**Every feature MUST be specified as an MCP contract before implementation.**

- All tools expose functionality via MCP (Model Context Protocol) standard
- JSON schemas define strict input/output contracts
- Schemas validated using Pydantic models before execution
- Documentation auto-generated from contract definitions
- Breaking changes require explicit versioning (see Section VI)

**Rationale**: Contract-first ensures compatibility with Claude Desktop/Web and enables
seamless integration. MCP protocol provides standardized communication layer that
future-proofs the architecture as new AI models emerge.

### II. Modular Architecture

**Strict separation between tools, resources, prompts, providers, and core orchestration.**

Project structure MUST follow:
- `src/scout/tools/` - MCP-exposed tools (one file per tool)
- `src/scout/resources/` - Structured data and templates
- `src/scout/prompts/` - Reusable prompt templates
- `src/scout/providers/` - AI provider abstractions (Gemini, OpenAI, Anthropic, OpenRouter, Grok)
- `src/scout/core/` - Orchestration, team selection, state management
- `src/scout/config/` - Configuration loader and validators
- `src/scout/utils/` - Utilities (rate limiting, caching, retry logic)

**Prohibited**:
- Mixing tool logic with provider implementation
- Direct API calls to AI providers from tools (MUST use provider abstraction)
- Business logic in MCP handlers (delegate to services)

**Rationale**: Modularity enables zero-downtime updates when adding providers or tools.
Clear boundaries reduce coupling and improve testability.

### III. Mandatory Testing (NON-NEGOTIABLE)

**No tool may be merged without achieving ≥80% test coverage.**

Required test types for every tool:
1. **Unit tests**: Handler logic with mocked dependencies
2. **Schema validation tests**: Valid and invalid input scenarios
3. **Integration tests**: End-to-end flow with mocked providers
4. **Error handling tests**: API failures, timeouts, malformed responses
5. **Performance tests**: P95 latency targets

Test structure:
```python
# tests/test_{tool_name}.py
@pytest.mark.asyncio
async def test_{tool}_valid_input(): ...
async def test_{tool}_invalid_input(): ...
async def test_{tool}_provider_failure(): ...
async def test_{tool}_timeout(): ...
async def test_{tool}_team_override(): ...
@pytest.mark.benchmark
def test_{tool}_performance(): ...
```

**Rationale**: High test coverage prevents regressions when evolving multi-provider
AI orchestration. Mocked providers enable fast, reliable CI/CD pipeline.

### IV. Auto-Generated Documentation

**Documentation is a build artifact, not a manual task.**

All documentation MUST be generated from:
- JSON schemas → API reference (via Pydantic schema export)
- Docstrings → User guides (extracted and formatted)
- Configuration schemas → Reference docs (from YAML validators)

Required docstring format:
```python
async def tool_handler(...):
    """
    Brief description (one line).

    Detailed multi-line description explaining behavior,
    use cases, and considerations.

    Args:
        param1: Description with type info
        param2: Description with constraints

    Returns:
        Description with example structure

    Raises:
        ExceptionType: When and why it occurs

    Example:
        >>> await tool_handler(param1="...", param2="...")
        {"result": "..."}
    """
```

Generated docs stored in `docs/api/` and versioned in Git.

**Rationale**: Auto-generated docs stay synchronized with code changes. Eliminates
documentation drift and reduces maintenance burden.

### V. Robust Error Handling

**Every error MUST be structured, logged, and actionable.**

Exception hierarchy:
```python
class ScoutError(Exception):
    def __init__(self, message: str, code: str, details: dict = None)

class ProviderError(ScoutError): ...
class ConfigurationError(ScoutError): ...
class ToolError(ScoutError): ...
class ValidationError(ScoutError): ...
```

Error messages MUST include:
- Human-readable description
- Unique error code (for programmatic handling)
- Contextual details (provider, model, request_id, etc.)

Recovery strategies:
- Validation errors: Fail fast, return immediately
- Provider rate limits (429): Exponential backoff retry (max 3 attempts)
- Provider server errors (500): Retry twice, then fail
- Timeouts: No retry, log and return partial result if available

**Rationale**: Structured errors enable debugging distributed AI provider interactions.
Error codes allow clients to implement intelligent retry logic.

### VI. Structured Logging

**All client-server interactions MUST be traceable for debugging.**

Logging levels:
- `DEBUG`: API payloads, full request/response (development only)
- `INFO`: Tool lifecycle (started, completed, team selected, duration, cost)
- `WARNING`: Fallbacks, retries, quota warnings
- `ERROR`: Tool failures, API errors, exceptions (with stack traces)

Required logging format (structlog JSON):
```python
logger.info(
    "tool_execution_started",
    request_id=uuid,
    tool_name="analyse",
    team="architect",
    input_size_bytes=len(input)
)

logger.info(
    "tool_execution_completed",
    request_id=uuid,
    tool_name="analyse",
    duration_ms=3421,
    tokens={"input": 1200, "output": 800},
    cost_usd=0.023,
    cache_hit=False
)
```

Every MCP request receives a unique `request_id` propagated through all logs.

**Rationale**: Structured JSON logs enable aggregation in observability platforms
(DataDog, Grafana Loki). Request correlation simplifies debugging multi-step workflows.

### VII. Provider Abstraction & Multi-Model Teams

**AI providers are interchangeable via unified interface.**

All providers MUST implement:
```python
class BaseAIProvider(ABC):
    @abstractmethod
    async def generate(
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> AIResponse: ...

    @abstractmethod
    async def stream(
        prompt: str,
        model: str,
        **kwargs
    ): ...
```

Supported providers (extensible via configuration):
- **Gemini** (Google): flash, pro, thinking models
- **OpenAI**: gpt-4o, o3-mini
- **Anthropic**: claude-sonnet-4, claude-opus-4
- **OpenRouter**: Multi-model aggregator
- **Grok** (X.AI): grok-2, grok-2-mini

Teams combine primary + validator models:
```yaml
teams:
  scout:
    primary: {provider: gemini, model: flash}
    validators: []
  architect:
    primary: {provider: gemini, model: pro}
    validators:
      - {provider: openai, model: gpt4o, trigger: "confidence < 0.8"}
  expert:
    primary: {provider: anthropic, model: opus}
    validators:
      - {provider: gemini, model: thinking, trigger: "always"}
```

**Rationale**: Provider abstraction decouples tools from specific AI vendors. Team
configuration enables cost/quality tradeoffs without code changes. Validators provide
consensus on critical decisions.

### VIII. Open Source Licensing Compliance (Apache 2.0)

**SCOUT is licensed under Apache 2.0 and MUST maintain full compliance.**

All source files, documentation, and distributions MUST:
1. **Include license headers**: Every source file contains Apache 2.0 header with copyright
2. **Maintain attribution**: Properly credit Zen MCP Server and other derived works
3. **Document modifications**: Track all changes from original sources
4. **Provide legal notices**: Include LICENSE, NOTICE, and THIRD_PARTY_LICENSES files

Required file header format:
```python
# Copyright 2025 Christian Boulet / Boulet Stratégies TI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
```

Attribution requirements:
- **NOTICE file**: Lists all third-party components and their licenses
- **THIRD_PARTY_LICENSES**: Full text of all dependency licenses
- **docs/legal/ATTRIBUTION.md**: Detailed attribution for derived works
- **docs/legal/MODIFICATIONS.md**: Document all modifications from originals

Apache 2.0 benefits:
- Commercial use permitted (monetization allowed)
- Patent grant protection for users and contributors
- Clear modification tracking requirements
- Compatible with proprietary extensions

**Prohibited**:
- Removing attribution from derived works
- Misrepresenting origin or authorship
- Using project trademarks without permission
- Claiming endorsement without authorization

**Rationale**: Apache 2.0 licensing ensures legal clarity for commercial use while
respecting the open source origins of the project. Proper attribution maintains
trust and enables collaboration. The patent grant protects all parties from
intellectual property disputes.

## Technology Stack

**Language**: Python 3.11+ (asyncio for concurrent AI calls)

**Core Dependencies**:
- `fastmcp` - MCP protocol server implementation
- `pydantic` v2 - Schema validation and serialization
- `structlog` - Structured JSON logging
- `redis` - State management and caching
- `httpx` - Async HTTP client for provider APIs
- `opentelemetry` - Metrics and tracing

**AI Provider SDKs**:
- `google-generativeai` (Gemini)
- `openai` (OpenAI)
- `anthropic` (Claude)
- Custom clients for OpenRouter and Grok

**Development Tools**:
- `pytest` + `pytest-asyncio` - Testing framework
- `pytest-cov` - Coverage reporting
- `black` - Code formatting
- `mypy` - Static type checking
- `ruff` - Fast linting

**Infrastructure**:
- Redis (local or Upstash cloud) - Required for state management
- Docker - Containerization for deployment
- GitHub Actions - CI/CD pipeline

## Security Requirements

**I. Secrets Management**

- ALL API keys stored in environment variables (`.env` file, gitignored)
- Use `python-dotenv` for secure loading
- API key rotation every 90 days (calendar reminder required)
- Different secrets per environment (dev/staging/prod)
- Pre-commit hook MUST detect secrets before commit (`detect-secrets`)

**II. Input Validation**

- ALL user inputs validated via Pydantic schemas
- Maximum input size: 100KB per field
- Sanitization applied before sending to AI providers
- No arbitrary code execution from user inputs
- Regular expression constraints for string fields

**III. Rate Limiting**

Per-user limits:
- 100 requests/hour per user
- 1000 requests/day global limit
- Budget alerts at $50/day threshold

Per-provider limits (respect API quotas):
- Gemini: 60 RPM (requests per minute)
- OpenAI: Tier-based (monitor quota)
- Anthropic: Account-based limits

**IV. Logging Security**

- NEVER log API keys (not even partial)
- Sanitize personally identifiable information (PII)
- Log access controls for production environments

## Performance Standards

**Latency Targets**:
- P50: < 5 seconds
- P95: < 60 seconds
- P99: < 120 seconds

**Availability**:
- Uptime: > 99% (measured monthly)
- Mean Time Between Failures (MTBF): > 168 hours
- Mean Time To Recovery (MTTR): < 15 minutes

**Cost Management**:
- Track cost per tool per execution
- Alert if daily cost exceeds $50 USD
- Aggressive caching (Redis TTL: 1 hour for identical requests)
- Automatic team downgrade (architect → scout) for simple queries

**Scalability**:
- Support 100 concurrent tool executions
- Redis connection pooling (max 50 connections)
- Provider request queuing with backpressure

## Development Workflow

**I. Feature Development**

Every feature follows SpecKit workflow:
1. `/speckit.specify` - Create feature specification
2. `/speckit.clarify` - Resolve ambiguities
3. `/speckit.plan` - Generate implementation plan
4. `/speckit.tasks` - Generate dependency-ordered tasks
5. `/speckit.implement` - Execute implementation
6. `/speckit.analyze` - Verify cross-artifact consistency

**II. Code Review Requirements**

Pull request checklist:
- [ ] All tests pass (100% of test suite)
- [ ] Coverage ≥ 80% on new code
- [ ] Documentation updated (auto-generated + manual guides)
- [ ] No secrets exposed (pre-commit hook passed)
- [ ] Structured logging added for new operations
- [ ] Error handling includes recovery strategies
- [ ] MCP schema validated (no breaking changes without version bump)
- [ ] Performance acceptable (no regressions in benchmarks)
- [ ] Apache 2.0 license headers present on all new files
- [ ] Attribution maintained for any derived code

**III. Quality Gates**

Before merging to `main`:
- CI pipeline green (tests, linting, type checking)
- Code review approved by maintainer
- Integration tests pass with mocked providers
- Documentation generated successfully
- Security scan clean (Bandit, Safety)
- License compliance verified (headers, attribution)

## Governance

**Constitution Authority**: This constitution supersedes all other development practices,
coding standards, and architectural decisions. In case of conflict, constitution principles
take precedence.

**Amendment Process**:
1. Propose amendment via pull request to `.specify/memory/constitution.md`
2. Document rationale and impact analysis
3. Update version according to semantic versioning:
   - MAJOR: Breaking governance changes (remove/redefine principles)
   - MINOR: New principles or material expansions
   - PATCH: Clarifications, typos, non-semantic fixes
4. Update all dependent templates (plan, spec, tasks)
5. Require approval from project owner (Christian Boulet)
6. Include migration plan if changes affect existing code

**Compliance Verification**:
- All pull requests MUST reference constitution principles
- Code reviews MUST verify adherence to testing requirements (Principle III)
- Complexity MUST be justified against simplicity principle
- Use `.specify/templates/` for all feature specifications
- License headers MUST be present on all source files (Principle VIII)

**Versioning Policy**:
- Constitution version increments independently of code version
- Each amendment updates `LAST_AMENDED_DATE`
- `RATIFICATION_DATE` remains constant (original adoption date)

**Exception Handling**:
- Exceptions to constitution require explicit documentation in PR
- Temporary exceptions MUST include sunset date and migration plan
- No exceptions allowed for Principle III (Mandatory Testing)
- No exceptions allowed for Principle VIII (Licensing Compliance)

---

**Version**: 1.1.0 | **Ratified**: 2025-10-18 | **Last Amended**: 2025-10-19