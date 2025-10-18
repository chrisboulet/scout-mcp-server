# Constitution du Projet SCOUT

> Constitution établie le 18 octobre 2025 pour le projet SCOUT MCP Server

## Principes Architecturaux

### 1. Architecture Contract-First

**Principe fondamental :** Toute fonctionnalité doit être spécifiée dans son contrat avant implémentation.

- **MCP comme standard** : Le protocole MCP (Model Context Protocol) définit le contrat de communication
- **Schémas JSON stricts** : Chaque outil expose un schéma JSON validé avant exécution
- **Documentation auto-générée** : Les capacités du serveur sont documentées automatiquement depuis les schémas
- **Versioning explicite** : Chaque modification de contrat implique une version

**Application pratique :**
```python
# ✅ CORRECT - Contrat défini d'abord
@registry.register(
    name="analyse",
    description="Analyse approfondie de code, architecture, ou systèmes",
    schema={
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "..."},
            "analysis_type": {"type": "string", "enum": [...]},
        },
        "required": ["target"]
    }
)
async def analyse_handler(...): ...

# ❌ INCORRECT - Implémentation sans contrat
async def analyse_handler(...):
    # Code sans schéma défini
```

### 2. Architecture Modulaire

**Principe fondamental :** Séparation stricte entre outils, ressources et prompts.

- **Tools** : Fonctions exposées via MCP (`chat`, `planner`, `analyse`, etc.)
- **Resources** : Données structurées accessibles (configurations, templates)
- **Prompts** : Templates réutilisables pour interactions avec les modèles AI
- **Providers** : Abstractions des services AI (Gemini, OpenAI, Anthropic)
- **Core** : Orchestration, sélection d'équipe, gestion d'état

**Structure imposée :**
```
src/scout/
├── tools/         # Outils MCP (un fichier par outil)
├── resources/     # Ressources MCP (configurations, templates)
├── prompts/       # Templates de prompts réutilisables
├── providers/     # Abstractions des services AI
├── core/          # Orchestration, team selector, state manager
└── utils/         # Utilitaires (rate limiting, cache, logging)
```

**Interdictions :**
- ❌ Mélanger logique de tool avec logique de provider
- ❌ Accès direct aux APIs AI depuis les tools (toujours via provider)
- ❌ Logique métier dans les handlers MCP (déléguer aux services)

### 3. Tests Obligatoires pour Chaque Outil

**Principe fondamental :** Aucun outil ne peut être mergé sans tests complets.

**Couverture minimale requise :**
- ✅ Test unitaire du handler (sans appels AI réels - mocks)
- ✅ Test de validation du schéma JSON
- ✅ Test d'intégration avec provider mocké
- ✅ Test de gestion d'erreur (API failure, timeout, invalid input)

**Exemple obligatoire :**
```python
# tests/test_analyse.py
import pytest
from scout.tools.analyse import analyse_handler

@pytest.mark.asyncio
async def test_analyse_handler_valid_input():
    """Test analyse avec input valide"""
    result = await analyse_handler(
        target="def foo(): pass",
        analysis_type="code_quality",
        # Mock dependencies
        team_selector=mock_team_selector,
        provider_factory=mock_provider_factory
    )
    assert "findings" in result

@pytest.mark.asyncio
async def test_analyse_handler_invalid_analysis_type():
    """Test validation du schéma"""
    with pytest.raises(ValidationError):
        await analyse_handler(target="code", analysis_type="invalid")
```

**Couverture cible :** Minimum 80% sur les tools, 90% sur le core.

### 4. Documentation Auto-Générée

**Principe fondamental :** La documentation est une sortie, pas une entrée.

- **Schémas MCP → Docs API** : Génération automatique depuis les schémas JSON
- **Docstrings → Guide utilisateur** : Extraction des docstrings pour documentation
- **Configuration → Référence** : Documentation des paramètres depuis YAML schemas

**Outils requis :**
- `pydantic` pour validation et génération de schémas JSON
- Script de génération `scripts/generate_docs.py` exécuté en pre-commit
- Markdown généré dans `docs/api/` (versionné en Git)

**Format imposé pour docstrings :**
```python
async def tool_handler(...):
    """
    Brève description (une ligne).

    Description détaillée sur plusieurs lignes expliquant
    le comportement, les cas d'usage, et les considérations.

    Args:
        param1: Description du paramètre
        param2: Description du paramètre

    Returns:
        Description du format de retour avec exemple

    Raises:
        ValueError: Quand...
        ProviderError: Quand...

    Example:
        >>> await tool_handler(param1="...", param2="...")
        {"result": "..."}
    """
```

### 5. Gestion d'Erreur Robuste

**Principe fondamental :** Chaque erreur est structurée, loggée et explicite.

**Hiérarchie d'exceptions :**
```python
# src/scout/exceptions.py
class ScoutError(Exception):
    """Base exception pour SCOUT"""
    def __init__(self, message: str, code: str, details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}

class ProviderError(ScoutError):
    """Erreur liée à un provider AI"""
    pass

class ConfigurationError(ScoutError):
    """Erreur de configuration"""
    pass

class ToolError(ScoutError):
    """Erreur lors de l'exécution d'un tool"""
    pass
```

**Messages d'erreur structurés :**
```python
# ✅ CORRECT
raise ProviderError(
    message="Failed to generate response from Gemini",
    code="PROVIDER_API_FAILURE",
    details={
        "provider": "gemini",
        "model": "gemini-2.0-pro-exp",
        "status_code": 429,
        "retry_after": 60
    }
)

# ❌ INCORRECT
raise Exception("Gemini API failed")
```

**Obligation de logging :**
```python
import logging
logger = logging.getLogger(__name__)

try:
    result = await provider.generate(...)
except ProviderError as e:
    logger.error(
        "Provider generation failed",
        extra={
            "error_code": e.code,
            "provider": e.details.get("provider"),
            "model": e.details.get("model")
        },
        exc_info=True
    )
    raise
```

### 6. Logging Structuré pour Debugging

**Principe fondamental :** Chaque interaction client-serveur est tracée pour debugging.

**Niveaux de logging :**
- `DEBUG` : Détails des appels API, payloads, réponses (dev seulement)
- `INFO` : Lifecycle des tools (start, success, team selected)
- `WARNING` : Fallbacks, retries, dépassements de quotas
- `ERROR` : Échecs de tools, erreurs API, exceptions

**Format structuré imposé :**
```python
# Utiliser structlog pour JSON structuré
import structlog
logger = structlog.get_logger()

logger.info(
    "tool_execution_started",
    tool_name="analyse",
    team="architect",
    user_override=False,
    input_size=1500
)

logger.info(
    "tool_execution_completed",
    tool_name="analyse",
    duration_ms=3421,
    tokens_used={"input": 1200, "output": 800},
    cost_usd=0.023
)
```

**Corrélation des logs :**
Chaque requête MCP reçoit un `request_id` propagé dans tous les logs :
```python
# Middleware MCP
@app.middleware
async def add_request_id(request, call_next):
    request_id = str(uuid4())
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)
    return response
```

## Principes de Configuration

### 7. Configuration Centralisée

**Principe fondamental :** Une source de vérité pour toute la configuration.

**Hiérarchie :**
1. **Variables d'environnement** : Secrets (API keys)
2. **config/scout.yaml** : Configuration applicative
3. **Runtime overrides** : Paramètres utilisateur (team selection)

**Interdictions :**
- ❌ Hardcoder des API keys ou secrets dans le code
- ❌ Configuration dispersée dans plusieurs fichiers sans raison
- ❌ Valeurs par défaut magiques (toujours explicites dans config)

**Validation au démarrage :**
```python
# src/scout/config/loader.py
from pydantic import BaseModel, validator

class ScoutConfig(BaseModel):
    providers: dict
    teams: dict
    system: SystemConfig

    @validator('providers')
    def validate_providers(cls, v):
        for name, config in v.items():
            if not config.get('api_key'):
                raise ValueError(f"Missing API key for provider {name}")
        return v

# main.py
config = load_config("config/scout.yaml")
config.validate()  # Fail fast si config invalide
```

### 8. Gestion de Versions

**Principe fondamental :** Toute évolution de contrat ou configuration est versionnée.

**Semantic versioning appliqué :**
- **MAJOR** : Breaking changes (changement de schéma incompatible)
- **MINOR** : Ajout de fonctionnalités rétrocompatibles
- **PATCH** : Bug fixes

**Exemple évolution :**
```yaml
# v1.0.0 - Initial
tools:
  analyse:
    schema_version: "1.0.0"
    required: ["target"]

# v1.1.0 - Ajout paramètre optionnel (rétrocompatible)
tools:
  analyse:
    schema_version: "1.1.0"
    required: ["target"]
    optional: ["analysis_type"]  # Nouveau

# v2.0.0 - Changement breaking (nouveau required)
tools:
  analyse:
    schema_version: "2.0.0"
    required: ["target", "context"]  # Breaking: context obligatoire
```

## Principes de Qualité

### 9. Code Review Systématique

**Principe fondamental :** Aucun code n'est mergé sans review.

**Checklist obligatoire :**
- [ ] Tests passent (100% des nouveaux tests)
- [ ] Couverture de code maintenue (≥80%)
- [ ] Documentation à jour (docstrings + README si applicable)
- [ ] Pas de secrets exposés (check pre-commit)
- [ ] Logging approprié (info/error selon cas)
- [ ] Gestion d'erreur robuste
- [ ] Schéma JSON validé
- [ ] Performance acceptable (pas de régression)

### 10. Monitoring et Observabilité

**Principe fondamental :** Ce qui n'est pas mesuré ne peut être amélioré.

**Métriques obligatoires :**
- **Latence** : P50, P95, P99 par tool
- **Taux d'erreur** : Ratio succès/échec par tool et provider
- **Coûts** : $ USD par tool, par jour, par provider
- **Usage** : Nombre d'appels par tool, par équipe

**Implémentation :**
```python
# Utiliser OpenTelemetry pour métriques
from opentelemetry import metrics

meter = metrics.get_meter(__name__)
tool_duration = meter.create_histogram("scout.tool.duration_ms")
tool_errors = meter.create_counter("scout.tool.errors")
tool_cost = meter.create_histogram("scout.tool.cost_usd")

@tool_wrapper
async def analyse_handler(...):
    start = time.time()
    try:
        result = await _execute_analyse(...)
        tool_duration.record((time.time() - start) * 1000, {"tool": "analyse"})
        tool_cost.record(result.cost_usd, {"tool": "analyse"})
        return result
    except Exception as e:
        tool_errors.add(1, {"tool": "analyse", "error_type": type(e).__name__})
        raise
```

## Principes de Sécurité

### 11. Secrets et API Keys

**Principe fondamental :** Zéro secret en clair, rotation régulière.

**Règles strictes :**
- ✅ API keys dans variables d'environnement `.env` (gitignored)
- ✅ Utiliser `python-dotenv` pour chargement sécurisé
- ✅ Rotation des secrets tous les 90 jours (calendrier)
- ✅ Secrets différents par environnement (dev/staging/prod)
- ❌ Jamais commiter `.env` ou secrets
- ❌ Jamais logger les API keys (même partiellement)

**Pre-commit hook obligatoire :**
```bash
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

### 12. Validation des Entrées

**Principe fondamental :** Toute entrée utilisateur est suspecte jusqu'à validation.

**Règles :**
- ✅ Validation via schéma JSON (pydantic)
- ✅ Sanitization des inputs avant envoi aux providers
- ✅ Limites de taille (max 100KB par input)
- ❌ Jamais exécuter du code fourni par l'utilisateur
- ❌ Jamais construire des requêtes SQL/NoSQL à partir d'input brut

```python
from pydantic import BaseModel, validator, constr

class AnalyseInput(BaseModel):
    target: constr(max_length=100000)  # Max 100KB
    analysis_type: Literal["code_quality", "architecture", "performance", "all"]

    @validator('target')
    def sanitize_target(cls, v):
        # Supprimer caractères potentiellement dangereux
        return v.strip()
```

## Principes d'Évolutivité

### 13. Extensibilité par Configuration

**Principe fondamental :** Ajouter un provider ou un outil sans modifier le core.

**Pattern imposé :**
```python
# Nouveau provider ajouté via config uniquement
# config/scout.yaml
providers:
  mistral:  # Nouveau provider
    api_key: ${MISTRAL_API_KEY}
    models:
      medium:
        id: "mistral-medium-latest"

# src/scout/providers/mistral.py (nouveau fichier)
class MistralProvider(BaseAIProvider):
    async def generate(...): ...

# src/scout/providers/factory.py (enregistrement)
PROVIDER_CLASSES = {
    "mistral": MistralProvider,  # Ajout d'une ligne
}
```

### 14. Backward Compatibility

**Principe fondamental :** Les changements ne cassent jamais les clients existants.

**Règles :**
- ✅ Paramètres optionnels avec valeurs par défaut pour nouvelles features
- ✅ Dépréciation progressive (warning → error sur 2 versions)
- ✅ Support des anciennes versions de schéma pendant 6 mois
- ❌ Jamais supprimer un paramètre sans période de dépréciation
- ❌ Jamais changer le type d'un paramètre existant

**Exemple dépréciation :**
```python
async def tool_handler(
    target: str,
    # Deprecated parameter
    old_param: str = None,  # v1.0.0
    # New parameter
    new_param: str = None   # v2.0.0
):
    if old_param is not None:
        logger.warning(
            "Parameter 'old_param' is deprecated since v2.0.0. "
            "Use 'new_param' instead. Will be removed in v3.0.0"
        )
        new_param = old_param  # Compatibility
```

## Principes de Performance

### 15. Optimisation de Coûts

**Principe fondamental :** Chaque dollar dépensé est justifié.

**Stratégies :**
- ✅ Caching agressif des réponses identiques (Redis, TTL 1h)
- ✅ Sélection automatique de l'équipe la plus économique
- ✅ Rate limiting pour éviter les runaway costs
- ✅ Budget alerts (email si > $50/jour)

**Implémentation obligatoire :**
```python
# src/scout/utils/cache.py
from functools import wraps
import hashlib
import json

def cache_ai_response(ttl_seconds=3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Cache key basé sur (tool, prompt, model)
            cache_key = hashlib.sha256(
                json.dumps({"args": args, "kwargs": kwargs}).encode()
            ).hexdigest()

            cached = await redis.get(f"cache:{cache_key}")
            if cached:
                logger.info("cache_hit", key=cache_key)
                return json.loads(cached)

            result = await func(*args, **kwargs)
            await redis.setex(f"cache:{cache_key}", ttl_seconds, json.dumps(result))
            return result
        return wrapper
    return decorator
```

### 16. Rate Limiting

**Principe fondamental :** Protéger les quotas et les budgets.

**Limites imposées :**
- **Par utilisateur** : 100 requêtes/heure
- **Par provider** : Respecter limites API (ex: Gemini 60 RPM)
- **Global** : 1000 requêtes/jour (budget $50/jour)

```python
from aiolimiter import AsyncLimiter

# src/scout/utils/rate_limiter.py
class RateLimiter:
    def __init__(self):
        self.user_limiter = AsyncLimiter(100, 3600)  # 100/hour
        self.global_limiter = AsyncLimiter(1000, 86400)  # 1000/day

    async def acquire(self, user_id: str):
        await self.user_limiter.acquire()
        await self.global_limiter.acquire()
```

---

## Validation de la Constitution

Cette constitution doit être :
- ✅ Reviewée et approuvée par Christian Boulet
- ✅ Respectée par tout code mergé dans `main`
- ✅ Mise à jour lors de changements architecturaux majeurs
- ✅ Référencée dans tous les PR reviews

**Version :** 1.0.0
**Date :** 18 octobre 2025
**Auteur :** Christian Boulet
**Statut :** Draft → Approuvée

---

## Engagement des Contributeurs

En contribuant à SCOUT, je m'engage à :
1. Lire et comprendre cette constitution
2. Respecter tous les principes lors du développement
3. Faire reviewer mon code selon les critères établis
4. Documenter les déviations nécessaires avec justification
5. Proposer des améliorations à la constitution si nécessaire

**Signature :** _Christian Boulet, 18 octobre 2025_
