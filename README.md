# SCOUT - Strategic CTO Operations and Unified Tooling

**Personal MCP server for amplifying Fractional CTO productivity through orchestrated AI teams.**

SCOUT orchestrates specialized AI agents (Gemini, OpenAI, Claude, OpenRouter, Grok) to accomplish complex architecture, analysis, and strategic tasks following the [Model Context Protocol (MCP)](https://modelcontextprotocol.io).

---

## 📋 Features

- **Multi-Provider AI Orchestration**: Seamlessly use 5 AI providers with unified interface
- **Team-Based Execution**: Configure primary + validator models for consensus
- **MCP Protocol Native**: Full compatibility with Claude Desktop and Web
- **Contract-First Development**: JSON schemas define strict tool contracts
- **80%+ Test Coverage**: Mandatory testing ensures reliability
- **Structured Logging**: Full traceability with request correlation
- **Cost Tracking**: Real-time monitoring of API usage and costs
- **Smart Caching**: Redis-based caching reduces redundant API calls

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Redis** (local or cloud)
- **API Keys** for at least one AI provider (Gemini, OpenAI, Anthropic, OpenRouter, or Grok)

### 1. Clone and Setup

```bash
# Clone repository
git clone <repository-url>
cd SCOUT

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
# Required: At least one AI provider API key
# Required: REDIS_URL (default: redis://localhost:6379)
```

**Minimum required variables:**
```bash
# Choose at least one provider
GEMINI_API_KEY=AIza...          # OR
OPENAI_API_KEY=sk-proj-...      # OR
ANTHROPIC_API_KEY=sk-ant-...    # OR
OPENROUTER_API_KEY=sk-or-v1-... # OR
GROK_API_KEY=xai-...

# Infrastructure
REDIS_URL=redis://localhost:6379
```

### 3. Setup Redis

**Option A: Docker (Recommended)**

```bash
# Run Redis container
docker run -d \
  --name scout-redis \
  -p 6379:6379 \
  redis:7-alpine

# Verify connection
docker exec scout-redis redis-cli ping
# Expected output: PONG
```

**Option B: Local Installation**

**Windows:**
```powershell
# Install via Chocolatey
choco install redis-64

# Start Redis
redis-server
```

**macOS:**
```bash
# Install via Homebrew
brew install redis

# Start Redis service
brew services start redis
```

**Linux (Ubuntu/Debian):**
```bash
# Install Redis
sudo apt update
sudo apt install redis-server

# Start Redis service
sudo systemctl start redis
sudo systemctl enable redis
```

**Option C: Cloud Redis (Upstash)**

1. Create free account at [Upstash](https://upstash.com/)
2. Create Redis database
3. Copy connection URL to `.env`:
   ```bash
   REDIS_URL=redis://default:<password>@<host>:<port>
   ```

### 4. Test Installation

```bash
# Run tests
pytest

# Check coverage
pytest --cov=src/scout --cov-report=html

# Start MCP server (when implemented)
python -m scout
```

---

## 📁 Project Structure

```
SCOUT/
├── .specify/                   # SpecKit framework
│   ├── memory/
│   │   └── constitution.md     # Project governance (7 principles)
│   └── templates/              # Feature spec/plan/tasks templates
├── src/scout/
│   ├── tools/                  # MCP-exposed tools (chat, planner, analyse, etc.)
│   ├── providers/              # AI provider abstractions
│   │   ├── base.py             # BaseAIProvider interface
│   │   ├── gemini.py           # Google Gemini
│   │   ├── openai.py           # OpenAI (GPT-4o, o3-mini)
│   │   ├── anthropic.py        # Anthropic Claude
│   │   ├── openrouter.py       # OpenRouter aggregator
│   │   ├── grok.py             # X.AI Grok
│   │   └── factory.py          # Provider factory
│   ├── core/
│   │   ├── orchestrator.py     # Tool routing and execution
│   │   ├── team_selector.py    # AI team selection logic
│   │   └── state_manager.py    # Redis state management
│   ├── config/
│   │   ├── loader.py           # YAML configuration loader
│   │   └── models.py           # Pydantic configuration schemas
│   └── utils/
│       ├── cache.py            # Redis caching
│       ├── rate_limiter.py     # Request rate limiting
│       ├── retry.py            # Retry logic with backoff
│       └── logger.py           # Structured logging setup
├── config/
│   └── scout.yaml              # Main configuration (providers, teams, mappings)
├── tests/
│   ├── unit/                   # Unit tests (mocked dependencies)
│   └── integration/            # Integration tests (mocked providers)
├── docs/
│   ├── api/                    # Auto-generated API docs
│   ├── architecture.md         # System architecture
│   └── quickstart.md           # This file
├── pyproject.toml              # Python project metadata & dependencies
├── .env.example                # Environment variables template
└── README.md                   # This file
```

---

## 🏗️ Architecture

SCOUT follows a **contract-first**, **modular architecture** as defined in the [Constitution](.specify/memory/constitution.md).

```
┌─────────────────────────────────────────────────────────────┐
│                  Claude Desktop/Web (MCP Client)             │
└─────────────────────┬───────────────────────────────────────┘
                      │ MCP Protocol (STDIO/HTTP+SSE)
┌─────────────────────▼───────────────────────────────────────┐
│                  SCOUT MCP Server                            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         Tool Router & Orchestrator                      │ │
│  │         (FastMCP + Tool Registry)                       │ │
│  └───┬──────────────────────────────────────────────┬─────┘ │
│      │                                               │       │
│  ┌───▼────────┐  ┌──────────────┐  ┌───────────────▼────┐ │
│  │   Tools    │  │   AI Team    │  │   State Manager    │ │
│  │  Registry  │  │   Selector   │  │   (Redis)          │ │
│  └───┬────────┘  └──────┬───────┘  └───────────────┬────┘ │
│      │                  │                           │       │
│  ┌───▼──────────────────▼───────────────────────────▼────┐ │
│  │            Provider Abstraction Layer                  │ │
│  │   (Unified Interface: Gemini, OpenAI, Claude, etc.)   │ │
│  └───┬──────┬──────┬─────────┬──────────┬───────────────┘ │
└──────┼──────┼──────┼─────────┼──────────┼─────────────────┘
       │      │      │         │          │
   ┌───▼──┐ ┌▼───┐ ┌▼──────┐ ┌▼────────┐ ┌▼────┐
   │Gemini│ │OAI │ │Claude │ │OpenRoute│ │Grok │
   └──────┘ └────┘ └───────┘ └─────────┘ └─────┘
```

### Core Principles (from Constitution)

1. **Contract-First Development** - Every tool defined via MCP schema
2. **Modular Architecture** - Strict separation of concerns
3. **Mandatory Testing** - ≥80% coverage (non-negotiable)
4. **Auto-Generated Documentation** - Docs from schemas
5. **Robust Error Handling** - Structured exceptions + recovery
6. **Structured Logging** - Request correlation + observability
7. **Provider Abstraction** - Unified multi-model interface

---

## 🛠️ Configuration

SCOUT uses a type-safe YAML configuration system with environment variable substitution and automatic validation.

### Quick Configuration

Create `config/scout.yaml` from the example:

```bash
cp config/scout.yaml.example config/scout.yaml
```

**Minimal configuration (single provider)**:

```yaml
providers:
  gemini:
    api_key: ${GEMINI_API_KEY}
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

**Multi-provider with validation**:

```yaml
providers:
  gemini:
    api_key: ${GEMINI_API_KEY}
    models:
      flash: { id: "gemini-2.0-flash-exp", max_tokens: 8192 }

  openai:
    api_key: ${OPENAI_API_KEY}
    models:
      gpt4o: { id: "gpt-4o", max_tokens: 16384 }

teams:
  architect:
    description: "Architecture team with validation"
    primary:
      provider: "gemini"
      model: "flash"
    validators:
      - provider: "openai"
        model: "gpt4o"
        trigger: "always"  # Validate all responses

tool_team_mapping:
  system_design: "architect"
```

### Environment Variable Substitution

- **Required**: `${VAR}` - Variable must be set
- **Optional**: `${VAR:-default}` - Uses default if not set

```yaml
system:
  request_timeout_seconds: ${REQUEST_TIMEOUT:-90}  # Default: 90
  cache_ttl_seconds: ${CACHE_TTL:-7200}            # Default: 7200
```

### Configuration Features

✅ **Type-safe** - Pydantic validation catches errors at startup
✅ **Immutable** - Frozen models prevent runtime modification
✅ **Secure** - Automatic API key redaction in logs/errors
✅ **Fast** - Loads in ~5ms (tested with 50 providers, 100 teams)
✅ **Cross-reference validation** - Teams reference existing providers/models
✅ **Environment-aware** - Different configs per environment

### Documentation

- **📖 Quick Start**: [`specs/001-config-system/quickstart.md`](specs/001-config-system/quickstart.md)
- **📋 Data Model**: [`specs/001-config-system/data-model.md`](specs/001-config-system/data-model.md)
- **📝 Example**: [`config/scout.yaml.example`](config/scout.yaml.example) - 5 providers, 3 teams
- **🔧 JSON Schema**: [`specs/001-config-system/contracts/config-schema.json`](specs/001-config-system/contracts/config-schema.json)

### Adding a New Provider (< 5 minutes)

1. Add to `config/scout.yaml`:
```yaml
providers:
  new_provider:
    api_key: "${NEW_PROVIDER_API_KEY}"
    models:
      model_name:
        id: "model-id"
        max_tokens: 8192
```

2. Set environment variable:
```bash
export NEW_PROVIDER_API_KEY=your-key-here
```

3. Reference in team:
```yaml
teams:
  new_team:
    primary:
      provider: "new_provider"
      model: "model_name"
```

That's it! Cross-reference validation ensures everything is correctly configured.

---

## 🧪 Development Workflow

SCOUT follows the **SpecKit** development process:

### 1. Specify Feature

```bash
/speckit.specify <feature-description>
```

Creates detailed specification with:
- User scenarios (prioritized)
- Requirements (functional + non-functional)
- MCP contract (JSON schema)
- Acceptance criteria

### 2. Clarify Ambiguities

```bash
/speckit.clarify
```

Identifies underspecified areas and asks targeted questions.

### 3. Generate Implementation Plan

```bash
/speckit.plan
```

Creates phased implementation plan with:
- Technical design
- Dependency analysis
- Risk mitigation
- Testing strategy

### 4. Generate Tasks

```bash
/speckit.tasks
```

Generates dependency-ordered checklist organized by user story.

### 5. Implement

```bash
/speckit.implement
```

Executes implementation following TDD (Test-Driven Development).

### 6. Analyze Consistency

```bash
/speckit.analyze
```

Cross-validates spec, plan, tasks, and code for consistency.

---

## ✅ Testing

### Run All Tests

```bash
# Run full test suite
pytest

# Run with coverage report
pytest --cov=src/scout --cov-report=term-missing

# Run only unit tests
pytest tests/unit -m unit

# Run only integration tests
pytest tests/integration -m integration

# Run performance benchmarks
pytest -m benchmark
```

### Write Tests (Mandatory)

Every tool MUST have:

```python
# tests/unit/test_chat.py
import pytest
from scout.tools.chat import chat_handler

@pytest.mark.asyncio
async def test_chat_valid_input(mock_dependencies):
    """Test nominal case with valid input."""
    result = await chat_handler(
        message="Hello",
        **mock_dependencies
    )
    assert "response" in result
    assert result["metadata"]["cost_usd"] > 0

@pytest.mark.asyncio
async def test_chat_invalid_input():
    """Test schema validation with invalid input."""
    with pytest.raises(ValidationError):
        await chat_handler(message="")  # Empty message

@pytest.mark.asyncio
async def test_chat_provider_failure(mock_failing_provider):
    """Test error handling when provider fails."""
    with pytest.raises(ProviderError):
        await chat_handler(
            message="Test",
            provider_factory=mock_failing_provider
        )
```

---

## 📊 Monitoring & Observability

### Structured Logging

All logs use JSON format with request correlation:

```json
{
  "event": "tool_execution_started",
  "request_id": "uuid-1234-5678",
  "tool_name": "analyse",
  "team": "architect",
  "timestamp": "2025-10-18T10:30:00Z"
}
```

### Metrics (OpenTelemetry)

- `scout.tool.duration_ms` - P50/P95/P99 latency
- `scout.tool.errors` - Error count by type
- `scout.tool.cost_usd` - Cost per tool execution
- `scout.provider.requests` - Requests per provider

### Cost Tracking

Track costs in real-time:

```python
# Automatic tracking per tool execution
logger.info(
    "tool_execution_completed",
    cost_usd=0.023,
    tokens={"input": 1200, "output": 800}
)
```

Budget alerts trigger at $50/day threshold (configurable).

---

## 🔒 Security

### Secrets Management

- **NEVER** commit `.env` (in `.gitignore`)
- **ALWAYS** use environment variables for API keys
- **Rotate** API keys every 90 days
- **Use** pre-commit hook to detect secrets:

```bash
# Install pre-commit hook
pip install pre-commit
pre-commit install

# Manually scan for secrets
detect-secrets scan
```

### Input Validation

All inputs validated via Pydantic:

```python
class AnalyseInput(BaseModel):
    target: constr(max_length=100000)
    analysis_type: Literal["code_quality", "architecture", "performance"]

    @validator('target')
    def sanitize_target(cls, v):
        return v.strip()
```

### Rate Limiting

Automatic rate limiting prevents abuse:
- 100 requests/hour per user
- 1000 requests/day globally
- Provider-specific limits (Gemini: 60 RPM, etc.)

---

## 📚 Documentation

- **Constitution**: [.specify/memory/constitution.md](.specify/memory/constitution.md)
- **PRD**: [PRD.md](PRD.md)
- **Architecture**: `docs/architecture.md` (coming soon)
- **API Reference**: `docs/api/` (auto-generated)

---

## 🤝 Contributing

SCOUT follows strict governance via the [Constitution](.specify/memory/constitution.md).

### Pull Request Checklist

- [ ] All tests pass (`pytest`)
- [ ] Coverage ≥ 80% (`pytest --cov`)
- [ ] No secrets exposed (`detect-secrets scan`)
- [ ] Code formatted (`black src/ tests/`)
- [ ] Linting clean (`ruff check src/ tests/`)
- [ ] Type checking passes (`mypy src/`)
- [ ] Documentation updated
- [ ] MCP schema validated (no breaking changes)
- [ ] Constitution principles referenced in PR

### Before Committing

```bash
# Format code
black src/ tests/

# Lint
ruff check --fix src/ tests/

# Type check
mypy src/

# Test
pytest --cov=src/scout --cov-fail-under=80

# Security scan
bandit -r src/
detect-secrets scan
```

---

## 📈 Roadmap

### Phase 1: Infrastructure Core (Weeks 1-2)
- [x] Project structure
- [x] Constitution
- [x] **Configuration system** ✅ (116 tests, 94.86% coverage)
- [ ] Provider abstraction layer
- [ ] Team selector
- [ ] Tool registry

### Phase 2: First Tool "chat" (Weeks 3-4)
- [ ] Chat tool implementation
- [ ] State manager (Redis)
- [ ] MCP server entrypoint
- [ ] Integration with Claude Desktop

### Phase 3: Essential Tools (Weeks 5-6)
- [ ] apilookup
- [ ] planner
- [ ] analyse
- [ ] thinkdeep

### Phase 4: Advanced Tools (Weeks 7-8)
- [ ] consensus
- [ ] challenge
- [ ] secaudit
- [ ] refactor

---

## 🆘 Troubleshooting

### Redis Connection Failed

**Error**: `redis.exceptions.ConnectionError`

**Solutions**:
```bash
# Check Redis is running
docker ps | grep redis

# Test connection
redis-cli ping

# Verify REDIS_URL in .env
echo $REDIS_URL
```

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'scout'`

**Solution**:
```bash
# Install in editable mode
pip install -e .
```

### API Key Errors

**Error**: `ConfigurationError: Missing API key`

**Solution**:
```bash
# Verify .env exists and has keys
cat .env | grep API_KEY

# Load environment variables
source .env  # macOS/Linux
# or reload terminal on Windows
```

---

## 📜 License & Attribution

SCOUT is licensed under the [Apache License 2.0](LICENSE).

### Third-Party Components

This project includes components derived from:
- **[Zen MCP Server](https://github.com/BeehiveInnovations/zen-mcp-server)** by BeehiveInnovations (Apache 2.0)

Zen MCP Server provides the foundational architecture for multi-model AI orchestration, tool registry patterns, and provider abstraction. SCOUT extends this foundation with YAML-based configuration, Redis state management, and specialized tools for Fractional CTO workflows.

For complete attribution and licensing information, see [NOTICE](NOTICE).

### Why Apache 2.0?

Apache 2.0 provides:
- ✅ **Commercial use freedom** - Boulet Stratégies TI can monetize SCOUT services
- ✅ **Patent protection** - Built-in patent grant protects users and contributors
- ✅ **Clear attribution** - Transparent acknowledgment of original work
- ✅ **Modification transparency** - Changes must be documented
- ✅ **Compatible with proprietary extensions** - Clients can build private modules

This license allows Boulet Stratégies TI clients to use, modify, and integrate SCOUT while maintaining legal clarity and flexibility.

### Copyright Notice

```
SCOUT - Strategic CTO Operations and Unified Tooling
Copyright 2025 Christian Boulet / Boulet Stratégies TI

Portions derived from Zen MCP Server
Copyright BeehiveInnovations
```

For questions about licensing or commercial use:
- Email: christian@bouletstrategies.com
- Website: https://bouletstrategies.com

---



## 📧 Contact

**Christian Boulet**
- Email: christian@bouletstrategies.com
- Company: Boulet Stratégies TI

---

**Version**: 0.1.0
**Last Updated**: 2025-10-18
