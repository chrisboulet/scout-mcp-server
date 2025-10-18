# Plan d'Implémentation : {{FEATURE_NAME}}

> Plan généré conformément à la constitution SCOUT
> Date : {{DATE}}
> Version : {{VERSION}}

## 1. Vue d'Ensemble

### Objectif
{{FEATURE_OBJECTIVE}}

### Alignement Constitution
Principes constitutionnels appliqués :
- [ ] Architecture Contract-First (schéma MCP défini)
- [ ] Architecture Modulaire (séparation tools/resources/prompts)
- [ ] Tests Obligatoires (couverture ≥80%)
- [ ] Documentation Auto-Générée
- [ ] Gestion d'Erreur Robuste
- [ ] Logging Structuré

### Scope
**In scope :**
- {{IN_SCOPE_ITEM_1}}
- {{IN_SCOPE_ITEM_2}}

**Out of scope :**
- {{OUT_OF_SCOPE_ITEM_1}}
- {{OUT_OF_SCOPE_ITEM_2}}

---

## 2. Analyse d'Impact

### Composants Affectés
| Composant | Type de Changement | Impact | Risque |
|-----------|-------------------|---------|---------|
| {{COMPONENT_1}} | {{NEW/MODIFY/DELETE}} | {{HIGH/MEDIUM/LOW}} | {{HIGH/MEDIUM/LOW}} |
| {{COMPONENT_2}} | {{NEW/MODIFY/DELETE}} | {{HIGH/MEDIUM/LOW}} | {{HIGH/MEDIUM/LOW}} |

### Dépendances
**Nouveaux packages requis :**
- `{{PACKAGE_NAME}}` v{{VERSION}} - {{REASON}}

**Dépendances internes :**
- Dépend de : `{{MODULE_NAME}}`
- Requis par : `{{MODULE_NAME}}`

### Breaking Changes
{{DESCRIBE_BREAKING_CHANGES_OR_NONE}}

---

## 3. Design Technique

### 3.1 Architecture

#### Diagramme de Composants
```mermaid
graph TD
    A[{{COMPONENT_A}}] --> B[{{COMPONENT_B}}]
    B --> C[{{COMPONENT_C}}]
    C --> D[{{EXTERNAL_SERVICE}}]
```

#### Contrat MCP (Contract-First)

**Schéma JSON du Tool :**
```json
{
  "name": "{{TOOL_NAME}}",
  "description": "{{TOOL_DESCRIPTION}}",
  "inputSchema": {
    "type": "object",
    "properties": {
      "{{PARAM_1}}": {
        "type": "{{TYPE}}",
        "description": "{{DESCRIPTION}}",
        "{{CONSTRAINT_KEY}}": "{{CONSTRAINT_VALUE}}"
      }
    },
    "required": ["{{REQUIRED_PARAMS}}"]
  }
}
```

**Validation Pydantic :**
```python
from pydantic import BaseModel, validator

class {{ToolName}}Input(BaseModel):
    {{param_1}}: {{Type}}
    {{param_2}}: {{Type}} = {{DEFAULT_VALUE}}

    @validator('{{param_1}}')
    def validate_{{param_1}}(cls, v):
        # Validation logic
        return v
```

### 3.2 Flux de Données

**Séquence d'exécution :**
1. **Réception requête MCP** : Claude Desktop → SCOUT Server
2. **Validation input** : Schéma JSON → Pydantic validation
3. **Sélection équipe AI** : Team Selector → Configuration équipe
4. **Exécution primaire** : Provider → Modèle AI primaire
5. **Validation secondaire** (si configured) : Validator → Consensus
6. **Post-traitement** : Formatage résultat
7. **Réponse MCP** : SCOUT Server → Claude Desktop

### 3.3 Gestion d'Erreur

**Hiérarchie d'exceptions :**
```python
class {{FeatureName}}Error(ScoutError):
    """Erreur spécifique à {{FEATURE_NAME}}"""
    pass

class {{SpecificError}}({{FeatureName}}Error):
    """Cas d'erreur spécifique"""
    pass
```

**Stratégies de récupération :**
| Erreur | Action | Retry | Fallback |
|--------|--------|-------|----------|
| {{ERROR_TYPE_1}} | {{ACTION}} | {{YES/NO}} | {{FALLBACK_STRATEGY}} |
| {{ERROR_TYPE_2}} | {{ACTION}} | {{YES/NO}} | {{FALLBACK_STRATEGY}} |

### 3.4 Logging et Observabilité

**Points de logging obligatoires :**
```python
# Start
logger.info(
    "{{tool_name}}_execution_started",
    tool_name="{{TOOL_NAME}}",
    team="{{TEAM_NAME}}",
    input_size={{SIZE}}
)

# Success
logger.info(
    "{{tool_name}}_execution_completed",
    tool_name="{{TOOL_NAME}}",
    duration_ms={{DURATION}},
    tokens_used={"input": {{IN}}, "output": {{OUT}}},
    cost_usd={{COST}}
)

# Error
logger.error(
    "{{tool_name}}_execution_failed",
    tool_name="{{TOOL_NAME}}",
    error_code="{{CODE}}",
    error_message="{{MESSAGE}}",
    exc_info=True
)
```

**Métriques OpenTelemetry :**
- `scout.{{tool_name}}.duration_ms` (histogram)
- `scout.{{tool_name}}.errors` (counter)
- `scout.{{tool_name}}.cost_usd` (histogram)

---

## 4. Implémentation par Étapes

### Phase 1 : Foundation ({{DURATION}})

**Objectif :** Mise en place structure et contrats

**Tâches :**
- [ ] Créer schéma JSON MCP dans `{{FILE_PATH}}`
- [ ] Implémenter modèle Pydantic validation
- [ ] Définir exceptions spécifiques
- [ ] Créer structure de logging
- [ ] Documenter contrat dans `docs/api/`

**Critères de validation :**
- ✅ Schéma JSON valide selon MCP spec
- ✅ Validation Pydantic passe avec inputs valides/invalides
- ✅ Documentation générée automatiquement

**Estimation :** {{HOURS}} heures

---

### Phase 2 : Core Logic ({{DURATION}})

**Objectif :** Implémentation logique métier

**Tâches :**
- [ ] Implémenter handler tool dans `src/scout/tools/{{tool_name}}.py`
- [ ] Intégrer Team Selector
- [ ] Implémenter appel provider(s) AI
- [ ] Ajouter gestion d'erreur avec retry logic
- [ ] Implémenter caching (si applicable)
- [ ] Enregistrer dans Tool Registry

**Critères de validation :**
- ✅ Tool exécute correctement avec mocks
- ✅ Sélection équipe fonctionne (default + override)
- ✅ Gestion d'erreur complète (try/except/logging)
- ✅ Rate limiting respecté

**Estimation :** {{HOURS}} heures

---

### Phase 3 : Tests ({{DURATION}})

**Objectif :** Couverture tests ≥80%

**Tâches :**
- [ ] Tests unitaires handler (avec mocks providers)
- [ ] Tests validation schéma (valid/invalid inputs)
- [ ] Tests intégration avec providers mockés
- [ ] Tests gestion d'erreur (API failure, timeout, invalid response)
- [ ] Tests performance (latence P95 < 60s)
- [ ] Tests coûts (estimation $ USD)

**Structure tests :**
```python
# tests/test_{{tool_name}}.py
import pytest
from scout.tools.{{tool_name}} import {{tool_name}}_handler

@pytest.mark.asyncio
async def test_{{tool_name}}_valid_input():
    """Test cas nominal"""
    pass

@pytest.mark.asyncio
async def test_{{tool_name}}_invalid_input():
    """Test validation entrée"""
    pass

@pytest.mark.asyncio
async def test_{{tool_name}}_provider_failure():
    """Test gestion erreur provider"""
    pass

@pytest.mark.asyncio
async def test_{{tool_name}}_with_team_override():
    """Test sélection équipe custom"""
    pass
```

**Critères de validation :**
- ✅ Tous les tests passent (100%)
- ✅ Couverture ≥80% sur nouveau code
- ✅ Pas de régression sur tests existants

**Estimation :** {{HOURS}} heures

---

### Phase 4 : Documentation ({{DURATION}})

**Objectif :** Documentation complète pour utilisateurs et développeurs

**Tâches :**
- [ ] Docstrings complètes avec exemples
- [ ] Guide utilisateur dans `docs/usage/{{tool_name}}.md`
- [ ] Exemples d'usage (3-5 cas concrets)
- [ ] Mise à jour `README.md` avec nouveau tool
- [ ] Génération documentation API (script auto)

**Template docstring obligatoire :**
```python
async def {{tool_name}}_handler(...):
    """
    {{BRIEF_DESCRIPTION}}

    {{DETAILED_DESCRIPTION}}

    Args:
        {{param_1}}: {{DESCRIPTION}}
        {{param_2}}: {{DESCRIPTION}}

    Returns:
        {{RETURN_DESCRIPTION}}

    Raises:
        {{Exception}}: {{WHEN}}

    Example:
        >>> await {{tool_name}}_handler({{param_1}}="...", {{param_2}}="...")
        {"result": "..."}
    """
```

**Critères de validation :**
- ✅ Documentation générée sans erreurs
- ✅ Exemples testés et fonctionnels
- ✅ Lisible par utilisateur non-technique

**Estimation :** {{HOURS}} heures

---

### Phase 5 : Review & Deploy ({{DURATION}})

**Objectif :** Review code, déploiement, monitoring

**Tâches :**
- [ ] Code review (checklist constitution)
- [ ] Validation security (no secrets, input validation)
- [ ] Test en environnement staging
- [ ] Configuration monitoring (métriques + alerts)
- [ ] Déploiement production
- [ ] Smoke tests post-déploiement

**Checklist Review (Constitution) :**
- [ ] Tests passent (100%)
- [ ] Couverture ≥80%
- [ ] Documentation à jour
- [ ] Pas de secrets exposés
- [ ] Logging structuré approprié
- [ ] Gestion d'erreur robuste
- [ ] Schéma JSON validé
- [ ] Performance acceptable

**Critères de validation :**
- ✅ Review approuvée par mainteneur
- ✅ Smoke tests passent en production
- ✅ Métriques remontent dans dashboard
- ✅ Pas d'alertes déclenchées 24h post-deploy

**Estimation :** {{HOURS}} heures

---

## 5. Tests et Validation

### 5.1 Stratégie de Test

| Type de Test | Couverture Cible | Outils |
|--------------|------------------|--------|
| Unitaires | ≥80% | pytest, pytest-asyncio |
| Intégration | Cas critiques | pytest avec mocks |
| Performance | P95 < 60s | pytest-benchmark |
| Sécurité | Input validation | pytest + fuzzing |

### 5.2 Cas de Test Critiques

**Test 1 : Cas nominal**
```python
# Input
{
  "{{param_1}}": "{{VALUE}}",
  "{{param_2}}": "{{VALUE}}"
}

# Expected Output
{
  "{{result_key}}": "{{EXPECTED_VALUE}}"
}
```

**Test 2 : Input invalide**
```python
# Input
{
  "{{param_1}}": {{INVALID_VALUE}}
}

# Expected Error
ValidationError: "{{ERROR_MESSAGE}}"
```

**Test 3 : Provider failure + retry**
```python
# Scenario
1. Provider API returns 429 (rate limit)
2. Retry after 1s
3. Success on 2nd attempt

# Expected Behavior
- Log warning "provider_retry_attempted"
- Return success after retry
- Total duration < 5s
```

---

## 6. Risques et Mitigations

| Risque | Impact | Probabilité | Mitigation |
|--------|---------|-------------|-----------|
| {{RISK_1}} | {{HIGH/MEDIUM/LOW}} | {{HIGH/MEDIUM/LOW}} | {{MITIGATION_STRATEGY}} |
| {{RISK_2}} | {{HIGH/MEDIUM/LOW}} | {{HIGH/MEDIUM/LOW}} | {{MITIGATION_STRATEGY}} |

### Risques Spécifiques

**Risque : {{SPECIFIC_RISK}}**
- **Impact :** {{DESCRIPTION_IMPACT}}
- **Mitigation :** {{DETAILED_MITIGATION}}
- **Contingency :** {{PLAN_B}}

---

## 7. Performance et Coûts

### Estimations Performance

| Métrique | Cible | Mesure Réelle |
|----------|-------|---------------|
| Latence P50 | {{TARGET}} | {{ACTUAL}} |
| Latence P95 | {{TARGET}} | {{ACTUAL}} |
| Latence P99 | {{TARGET}} | {{ACTUAL}} |
| Throughput | {{TARGET}} req/s | {{ACTUAL}} |

### Estimations Coûts

| Équipe AI | Coût/requête (moyen) | Volume attendu | Coût/jour |
|-----------|----------------------|----------------|-----------|
| Scout | ${{COST}} | {{VOLUME}} | ${{TOTAL}} |
| Architect | ${{COST}} | {{VOLUME}} | ${{TOTAL}} |
| Expert | ${{COST}} | {{VOLUME}} | ${{TOTAL}} |

**Budget total estimé :** ${{TOTAL_BUDGET}}/jour

**Optimisations prévues :**
- Caching : Réduction {{PERCENT}}% des appels redondants
- Team selection intelligente : Utiliser Scout quand possible
- Rate limiting : Prévenir runaway costs

---

## 8. Rollout et Monitoring

### Plan de Déploiement

**Phase 1 : Staging ({{DATE}})**
- Déploiement environnement staging
- Tests fonctionnels complets
- Validation métriques baseline

**Phase 2 : Production Limited ({{DATE}})**
- Déploiement production
- Feature flag activé pour 10% utilisateurs
- Monitoring intensif 48h

**Phase 3 : Production Full ({{DATE}})**
- Feature flag 100%
- Communication aux utilisateurs
- Documentation disponible

### Métriques de Succès

**KPIs à suivre (7 jours post-deploy) :**
- Adoption : {{TARGET}}% utilisateurs actifs utilisent le tool
- Performance : P95 latence < {{TARGET}}s
- Fiabilité : Taux succès > {{TARGET}}%
- Coûts : Coût réel < {{TARGET}}% estimé

**Critères de rollback :**
- ❌ Taux d'erreur > 5%
- ❌ P95 latence > 120s
- ❌ Coûts > 150% estimé
- ❌ Issue critique de sécurité

---

## 9. Documentation de Référence

### Liens Utiles
- Constitution SCOUT : `.speckit/constitution.md`
- PRD complet : `PRD.md`
- API Reference : `docs/api/{{tool_name}}.md`
- Architecture : `docs/architecture.md`

### Ressources Externes
- MCP Protocol Spec : https://modelcontextprotocol.io
- Pydantic Documentation : https://docs.pydantic.dev
- {{OTHER_RELEVANT_LINKS}}

---

## 10. Changelog et Versioning

### Version {{VERSION}} ({{DATE}})

**Ajouté :**
- {{ADDED_FEATURE_1}}
- {{ADDED_FEATURE_2}}

**Modifié :**
- {{MODIFIED_FEATURE_1}}

**Déprécié :**
- {{DEPRECATED_FEATURE_1}}

**Supprimé :**
- {{REMOVED_FEATURE_1}}

**Corrigé :**
- {{FIXED_BUG_1}}

**Sécurité :**
- {{SECURITY_FIX_1}}

---

## Approbation

**Plan révisé par :**
- [ ] Christian Boulet (Product Owner)
- [ ] {{TECH_LEAD}} (Tech Lead)
- [ ] {{REVIEWER}} (Code Reviewer)

**Approuvé pour implémentation :** {{DATE}}

**Prochaine revue :** {{REVIEW_DATE}}
