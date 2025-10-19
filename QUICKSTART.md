# Démarrage Rapide - SCOUT MCP Server

Configurez SCOUT en 5 minutes ! 🚀

## 📋 Prérequis

- Python 3.11+
- Claude Desktop
- Au moins une clé API (Gemini, OpenAI ou Anthropic)

## 🚀 Installation Express (3 minutes)

### 1. Clone & Install

```bash
# Cloner le projet
git clone https://github.com/your-org/scout.git
cd scout

# Installer (choisir une option)
pip install -e .        # Mode dev
pip install .          # Mode normal
```

### 2. Configuration Minimale

Créer `.env` avec vos clés :

```bash
# .env
GEMINI_API_KEY=your-gemini-key-here
```

Créer `config/scout.yaml` :

```yaml
providers:
  gemini:
    api_key: "${GEMINI_API_KEY}"
    models:
      flash:
        id: "gemini-2.0-flash-exp"
        max_tokens: 8192

teams:
  general:
    description: "Équipe générale"
    primary:
      provider: "gemini"
      model: "flash"

tool_team_mapping: {}

system:
  default_team: "general"
```

### 3. Intégrer à Claude Desktop

Ajouter dans `claude_desktop_config.json` :

```json
{
  "mcpServers": {
    "scout": {
      "command": "python",
      "args": ["-m", "scout.server"],
      "env": {
        "GEMINI_API_KEY": "your-key-here"
      }
    }
  }
}
```

### 4. Redémarrer Claude

C'est tout ! SCOUT est prêt ! ✅

---

## ⚡ Test Rapide

```python
# Vérifier l'installation
from scout.config import load_config

config = load_config("config/scout.yaml")
print("✅ SCOUT configuré avec:", list(config.providers.keys()))
```

---

## 🎯 3 Configurations Types

### 1️⃣ Solo Provider (Le plus simple)

```yaml
# Un seul provider, une équipe
providers:
  gemini:
    api_key: "${GEMINI_API_KEY}"
    models:
      flash:
        id: "gemini-2.0-flash-exp"
        max_tokens: 8192

teams:
  solo:
    description: "Équipe unique"
    primary:
      provider: "gemini"
      model: "flash"

system:
  default_team: "solo"
```

### 2️⃣ Dual Provider (Équilibré)

```yaml
# Deux providers : rapide + puissant
providers:
  gemini:
    api_key: "${GEMINI_API_KEY}"
    models:
      flash:
        id: "gemini-2.0-flash-exp"
        max_tokens: 8192
      pro:
        id: "gemini-2.0-pro-exp"
        max_tokens: 32768

  openai:
    api_key: "${OPENAI_API_KEY}"
    models:
      gpt4o:
        id: "gpt-4o"
        max_tokens: 16384

teams:
  scout:
    description: "Exploration rapide"
    primary:
      provider: "gemini"
      model: "flash"

  expert:
    description: "Analyse approfondie"
    primary:
      provider: "openai"
      model: "gpt4o"
    validators:
      - provider: "gemini"
        model: "pro"
        trigger: "always"

tool_team_mapping:
  quick_search: "scout"
  deep_analysis: "expert"

system:
  default_team: "scout"
```

### 3️⃣ Full Stack (Production)

```yaml
# Tous les providers avec équipes spécialisées
providers:
  gemini:
    api_key: "${GEMINI_API_KEY}"
    models:
      flash:
        id: "gemini-2.0-flash-exp"
        max_tokens: 8192
      pro:
        id: "gemini-2.0-pro-exp"
        max_tokens: 32768

  openai:
    api_key: "${OPENAI_API_KEY}"
    models:
      gpt4o:
        id: "gpt-4o"
        max_tokens: 16384
      gpt4o-mini:
        id: "gpt-4o-mini"
        max_tokens: 16384

  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    models:
      sonnet:
        id: "claude-3-5-sonnet-20241022"
        max_tokens: 8192

teams:
  # Équipe rapide pour exploration
  scout:
    description: "Exploration et recherche rapide"
    primary:
      provider: "gemini"
      model: "flash"
    validators:
      - provider: "openai"
        model: "gpt4o-mini"
        trigger: "on_error"

  # Équipe équilibrée pour architecture
  architect:
    description: "Conception et architecture"
    primary:
      provider: "gemini"
      model: "pro"
    validators:
      - provider: "anthropic"
        model: "sonnet"
        trigger: "always"

  # Équipe expert avec consensus
  expert:
    description: "Analyse critique avec consensus"
    primary:
      provider: "anthropic"
      model: "sonnet"
    validators:
      - provider: "openai"
        model: "gpt4o"
        trigger: "always"
      - provider: "gemini"
        model: "pro"
        trigger: "always"

tool_team_mapping:
  # Scout pour exploration
  quick_research: "scout"
  file_search: "scout"
  web_search: "scout"

  # Architect pour conception
  system_design: "architect"
  api_design: "architect"
  database_schema: "architect"

  # Expert pour critique
  security_audit: "expert"
  code_review: "expert"
  production_deploy: "expert"

system:
  default_team: "scout"
  request_timeout_seconds: 90
  max_retries: 3
  cache_ttl_seconds: 7200
```

---

## 📊 Comprendre les Équipes

| Équipe | Utilisation | Coût | Vitesse | Qualité |
|--------|-------------|------|---------|---------|
| **Scout** | Exploration, recherche | 💰 | ⚡⚡⚡ | ⭐⭐ |
| **Architect** | Design, planification | 💰💰 | ⚡⚡ | ⭐⭐⭐ |
| **Expert** | Critique, consensus | 💰💰💰 | ⚡ | ⭐⭐⭐⭐⭐ |

### Triggers de Validation

- **`always`** : Valide chaque réponse (haute qualité, coût élevé)
- **`on_error`** : Valide seulement si erreur (économique)
- **`random`** : Validation aléatoire (équilibré)

---

## 🔧 Variables d'Environnement

### Obligatoires (au moins une)

```bash
GEMINI_API_KEY=xxx
OPENAI_API_KEY=xxx
ANTHROPIC_API_KEY=xxx
```

### Optionnelles

```bash
# Timeouts et cache
REQUEST_TIMEOUT=90      # Défaut: 90 secondes
MAX_RETRIES=3          # Défaut: 3 essais
CACHE_TTL=7200         # Défaut: 2 heures

# Providers additionnels
OPENROUTER_API_KEY=xxx
GROK_API_KEY=xxx

# Intégrations
NOTION_API_KEY=xxx
TAVILY_API_KEY=xxx
REDIS_URL=redis://localhost:6379
```

---

## ❓ Problèmes Fréquents

### "Configuration file not found"

```bash
# Vérifier le chemin
ls config/scout.yaml

# Créer depuis l'exemple
cp config/scout.yaml.example config/scout.yaml
```

### "Environment variable not set: GEMINI_API_KEY"

```bash
# Vérifier la variable
echo $GEMINI_API_KEY

# Charger le .env
source .env  # Linux/Mac
# ou utiliser python-dotenv
```

### "Team 'x' references non-existent provider 'y'"

Vérifier que :
1. Le provider existe dans `providers:`
2. Le modèle existe dans `provider.models:`
3. Les noms correspondent exactement

---

## 📚 Pour Aller Plus Loin

- **Guide Complet** : [GUIDE.md](GUIDE.md)
- **Documentation Technique** : [specs/001-config-system/](specs/001-config-system/)
- **Exemples** : [config/scout.yaml.example](config/scout.yaml.example)

---

## 💡 Tips Pro

1. **Commencez simple** : Un provider, une équipe
2. **Ajoutez progressivement** : Providers puis validators
3. **Optimisez les coûts** :
   - Scout pour 80% des requêtes
   - Expert pour 20% critique
4. **Utilisez le cache** : `cache_ttl_seconds: 7200`
5. **Logs en dev** : `scout-server --verbose`

---

**Prêt en 5 minutes !** 🎉

Pour toute question : [Issues](https://github.com/your-org/scout/issues)