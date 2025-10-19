# Guide d'Utilisation SCOUT MCP Server

## Table des Matières

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Configuration Initiale](#configuration-initiale)
4. [Utilisation de Base](#utilisation-de-base)
5. [Configuration Avancée](#configuration-avancée)
6. [Cas d'Usage](#cas-dusage)
7. [Dépannage](#dépannage)
8. [Référence API](#référence-api)

---

## Introduction

SCOUT est un serveur MCP (Model Context Protocol) qui orchestre plusieurs providers IA (Gemini, OpenAI, Anthropic) dans des équipes spécialisées pour optimiser la qualité et le coût des réponses.

### Concepts Clés

- **Providers** : Services IA configurés (Gemini, OpenAI, Anthropic)
- **Teams** : Groupes de modèles travaillant ensemble
- **Tool Mapping** : Association d'outils MCP à des équipes spécialisées
- **Validators** : Modèles de validation pour consensus et qualité

### Architecture

```
┌─────────────────────────────────────────┐
│           Client MCP (Claude)           │
└────────────────┬───────────────────────┘
                 │ MCP Protocol
┌────────────────┴───────────────────────┐
│            SCOUT MCP Server            │
├────────────────────────────────────────┤
│         Team Selector (Router)         │
├──────────┬──────────┬─────────────────┤
│  Scout   │ Architect │   Expert       │
│  Team    │   Team    │   Team         │
├──────────┴──────────┴─────────────────┤
│        Provider Abstraction            │
├──────────┬──────────┬─────────────────┤
│  Gemini  │  OpenAI  │  Anthropic      │
└──────────┴──────────┴─────────────────┘
```

---

## Installation

### Prérequis

- Python 3.11 ou supérieur
- Claude Desktop App
- Clés API pour au moins un provider

### Installation Étape par Étape

#### 1. Cloner le Repository

```bash
git clone https://github.com/your-org/scout.git
cd scout
```

#### 2. Créer l'Environnement Virtuel

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

#### 3. Installer SCOUT

```bash
# Installation en mode développement
pip install -e .

# OU installation normale
pip install .
```

#### 4. Vérifier l'Installation

```bash
# Vérifier que SCOUT est installé
python -c "from scout.config import load_config; print('SCOUT installé avec succès!')"

# Vérifier la version
scout-server --version
```

---

## Configuration Initiale

### 1. Créer le Fichier de Configuration

```bash
# Copier l'exemple de configuration
cp config/scout.yaml.example config/scout.yaml
```

### 2. Configurer les Variables d'Environnement

Créer un fichier `.env` à la racine :

```bash
# .env
# Providers IA (au moins un requis)
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# Optionnel
OPENROUTER_API_KEY=your-openrouter-key
GROK_API_KEY=your-grok-key

# Configuration système
REQUEST_TIMEOUT=90
CACHE_TTL=7200

# Intégrations (optionnel)
NOTION_API_KEY=your-notion-key
TAVILY_API_KEY=your-tavily-key
```

### 3. Configuration Minimale

Pour démarrer rapidement avec un seul provider :

```yaml
# config/scout.yaml (minimal)
providers:
  gemini:
    api_key: "${GEMINI_API_KEY}"
    models:
      flash:
        id: "gemini-2.0-flash-exp"
        max_tokens: 8192

teams:
  general:
    description: "Équipe polyvalente"
    primary:
      provider: "gemini"
      model: "flash"

tool_team_mapping:
  default: "general"

system:
  default_team: "general"
```

### 4. Intégration avec Claude Desktop

Ajouter dans `claude_desktop_config.json` :

```json
{
  "mcpServers": {
    "scout": {
      "command": "python",
      "args": ["-m", "scout.server"],
      "env": {
        "GEMINI_API_KEY": "your-key",
        "OPENAI_API_KEY": "your-key",
        "ANTHROPIC_API_KEY": "your-key"
      }
    }
  }
}
```

---

## Utilisation de Base

### Tester la Configuration

```python
from scout.config import load_config

# Charger la configuration
config = load_config("config/scout.yaml")

# Vérifier les providers
print("Providers disponibles:", list(config.providers.keys()))
print("Équipes disponibles:", list(config.teams.keys()))
print("Équipe par défaut:", config.system.default_team)

# Accéder à un provider (clé API redactée)
gemini = config.providers["gemini"]
print(f"Gemini API Key: {gemini.api_key}")  # Affiche: sk-***
```

### Démarrer le Serveur MCP

```bash
# Démarrer en mode normal
scout-server

# Démarrer avec logs détaillés
scout-server --verbose

# Démarrer avec configuration spécifique
scout-server --config config/production.yaml
```

### Utilisation dans Claude

Une fois configuré, SCOUT est automatiquement disponible dans Claude :

1. Les outils MCP sont routés vers les équipes appropriées
2. Les validateurs s'activent selon leurs triggers
3. Les réponses sont optimisées pour qualité/coût

---

## Configuration Avancée

### Configuration Multi-Provider

```yaml
providers:
  gemini:
    api_key: "${GEMINI_API_KEY}"
    models:
      flash:
        id: "gemini-2.0-flash-exp"
        max_tokens: 8192
        temperature: 0.7
        cost_per_1k_input: 0.0001
        cost_per_1k_output: 0.0002

      pro:
        id: "gemini-2.0-pro-exp"
        max_tokens: 32768
        temperature: 0.5
        cost_per_1k_input: 0.001
        cost_per_1k_output: 0.002

  openai:
    api_key: "${OPENAI_API_KEY}"
    models:
      gpt4o:
        id: "gpt-4o"
        max_tokens: 16384
        temperature: 0.7
        cost_per_1k_input: 0.005
        cost_per_1k_output: 0.015

  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    models:
      sonnet:
        id: "claude-3-5-sonnet-20241022"
        max_tokens: 8192
        temperature: 0.7
        cost_per_1k_input: 0.003
        cost_per_1k_output: 0.015
```

### Configuration des Équipes

#### Équipe Scout (Exploration Rapide)

```yaml
teams:
  scout:
    description: "Exploration rapide et recherche initiale"
    primary:
      provider: "gemini"
      model: "flash"
    validators:
      - provider: "openai"
        model: "gpt4o-mini"
        trigger: "on_error"  # Valide seulement si erreur
    use_cases:
      - "quick_research"
      - "initial_exploration"
      - "simple_queries"
```

#### Équipe Architect (Équilibrée)

```yaml
teams:
  architect:
    description: "Conception et décisions architecturales"
    primary:
      provider: "gemini"
      model: "pro"
    validators:
      - provider: "anthropic"
        model: "sonnet"
        trigger: "always"  # Validation systématique
      - provider: "openai"
        model: "gpt4o"
        trigger: "random"  # Validation aléatoire
    use_cases:
      - "system_design"
      - "architecture_review"
      - "technical_decisions"
```

#### Équipe Expert (Haute Qualité)

```yaml
teams:
  expert:
    description: "Analyse approfondie avec consensus"
    primary:
      provider: "anthropic"
      model: "sonnet"
    validators:
      - provider: "gemini"
        model: "pro"
        trigger: "always"
      - provider: "openai"
        model: "gpt4o"
        trigger: "always"
    use_cases:
      - "deep_analysis"
      - "critical_review"
      - "consensus_decision"
```

### Mapping des Outils

```yaml
tool_team_mapping:
  # Outils de recherche → Scout
  quick_research: "scout"
  web_search: "scout"
  file_search: "scout"

  # Outils de conception → Architect
  system_design: "architect"
  database_design: "architect"
  api_design: "architect"

  # Outils critiques → Expert
  security_audit: "expert"
  code_review: "expert"
  production_deploy: "expert"
```

### Configuration Système

```yaml
system:
  default_team: "scout"
  request_timeout_seconds: ${REQUEST_TIMEOUT:-90}
  max_retries: ${MAX_RETRIES:-3}
  cache_ttl_seconds: ${CACHE_TTL:-7200}
  redis_url: ${REDIS_URL:-}  # null = cache en mémoire
```

---

## Cas d'Usage

### 1. Optimisation Coût/Performance

```yaml
# Stratégie : Modèles rapides pour exploration, chers pour critique

teams:
  fast_explorer:
    primary:
      provider: "gemini"
      model: "flash"  # $0.0001/1K tokens
    validators: []     # Pas de validation

  quality_reviewer:
    primary:
      provider: "anthropic"
      model: "sonnet"  # $0.003/1K tokens
    validators:
      - provider: "openai"
        model: "gpt4o"  # $0.005/1K tokens
        trigger: "always"
```

### 2. Validation de Sécurité

```yaml
teams:
  security:
    description: "Équipe sécurité avec double validation"
    primary:
      provider: "anthropic"
      model: "sonnet"
    validators:
      - provider: "openai"
        model: "gpt4o"
        trigger: "always"  # Toujours valider
      - provider: "gemini"
        model: "pro"
        trigger: "always"  # Double validation
    use_cases:
      - "security_audit"
      - "vulnerability_scan"
      - "penetration_test"
```

### 3. Mode Développement vs Production

```yaml
# config/scout-dev.yaml
system:
  default_team: "scout"  # Équipe rapide par défaut
  request_timeout_seconds: 30
  cache_ttl_seconds: 600  # Cache court

# config/scout-prod.yaml
system:
  default_team: "architect"  # Équipe équilibrée
  request_timeout_seconds: 120
  cache_ttl_seconds: 7200  # Cache long
```

### 4. Gestion Multi-Environnement

```bash
# .env.development
GEMINI_API_KEY=dev-key
REQUEST_TIMEOUT=30
CACHE_TTL=600

# .env.production
GEMINI_API_KEY=prod-key
REQUEST_TIMEOUT=120
CACHE_TTL=7200
```

---

## Dépannage

### Problèmes Courants

#### 1. Erreur : "Configuration file not found"

```python
# Vérifier le chemin
import os
print("Chemin actuel:", os.getcwd())
print("Config existe:", os.path.exists("config/scout.yaml"))
```

#### 2. Erreur : "Required environment variable not set"

```bash
# Vérifier les variables
echo $GEMINI_API_KEY

# Charger le .env
python -m dotenv list
```

#### 3. Erreur : "Team references non-existent provider"

```yaml
# Vérifier que le provider existe
teams:
  myteam:
    primary:
      provider: "gemini"  # Doit exister dans 'providers'
      model: "flash"      # Doit exister dans provider.models
```

#### 4. Configuration lente à charger

Solutions :
- Réduire le nombre de validators
- Utiliser `trigger: "on_error"` au lieu de `"always"`
- Activer le cache Redis

### Logs et Debugging

```python
# Activer les logs détaillés
import structlog
logger = structlog.get_logger()
logger.setLevel("DEBUG")

# Tester la configuration
from scout.config import load_config
config = load_config("config/scout.yaml")
```

### Validation de Configuration

```python
# Script de validation
from scout.config import load_config

try:
    config = load_config("config/scout.yaml")
    print("✅ Configuration valide")
    print(f"Providers: {list(config.providers.keys())}")
    print(f"Teams: {list(config.teams.keys())}")
    print(f"Mappings: {len(config.tool_team_mapping)} tools")
except Exception as e:
    print(f"❌ Erreur: {e}")
```

---

## Référence API

### Module `scout.config`

#### `load_config(config_path: str) -> ScoutConfig`

Charge et valide la configuration depuis un fichier YAML.

```python
from scout.config import load_config

config = load_config("config/scout.yaml")
```

### Modèles Pydantic

#### ScoutConfig

```python
class ScoutConfig:
    providers: Dict[str, ProviderConfig]
    teams: Dict[str, TeamConfig]
    tool_team_mapping: Dict[str, str]
    system: SystemSettings
    integrations: IntegrationConfig
```

#### ProviderConfig

```python
class ProviderConfig:
    api_key: str  # Redacté automatiquement
    models: Dict[str, ModelConfig]
```

#### TeamConfig

```python
class TeamConfig:
    description: str
    primary: TeamMember
    validators: List[ValidatorConfig]
    use_cases: List[str]
```

### Exceptions

```python
from scout.config.exceptions import (
    ConfigFileNotFoundError,
    ConfigValidationError,
    EnvironmentVariableError
)

try:
    config = load_config("config.yaml")
except ConfigFileNotFoundError:
    print("Fichier non trouvé")
except EnvironmentVariableError as e:
    print(f"Variable manquante: {e.variable_name}")
except ConfigValidationError as e:
    print(f"Validation échouée: {e}")
```

---

## Support et Ressources

### Documentation

- [README.md](README.md) - Vue d'ensemble du projet
- [specs/001-config-system/](specs/001-config-system/) - Documentation technique
- [config/scout.yaml.example](config/scout.yaml.example) - Configuration exemple

### Exemples

- Configuration minimale : `config/examples/minimal.yaml`
- Multi-provider : `config/examples/multi-provider.yaml`
- Production : `config/examples/production.yaml`

### Communauté

- Issues : https://github.com/your-org/scout/issues
- Discussions : https://github.com/your-org/scout/discussions

---

## Annexes

### Performance Benchmarks

| Configuration | Temps de Chargement | Mémoire |
|--------------|-------------------|---------|
| Minimal (1 provider) | ~3ms | ~10MB |
| Typique (3 providers) | ~5ms | ~15MB |
| Large (5 providers) | ~8ms | ~20MB |
| Stress (50 providers) | <5s | ~100MB |

### Matrice de Compatibilité

| SCOUT Version | Python | MCP Protocol | Claude Desktop |
|--------------|--------|--------------|----------------|
| 0.1.0 | 3.11+ | 1.0 | 1.85+ |

### Constitution Compliance

| Principe | Implementation | Status |
|----------|---------------|--------|
| I. Contract-First | JSON Schema | ✅ |
| II. Modular Architecture | Modules séparés | ✅ |
| III. Mandatory Testing | 94.86% coverage | ✅ |
| IV. Auto-Generated Docs | Pydantic schemas | ✅ |
| V. Robust Error Handling | Exception hierarchy | ✅ |
| VI. Structured Logging | structlog + redaction | ✅ |
| VII. Provider Abstraction | Multi-provider | ✅ |

---

**Version**: 1.0.0
**Date**: 2025-01-19
**Auteur**: SCOUT Development Team