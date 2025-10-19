# Outils Consultant SCOUT

Guide complet pour les 3 outils consultant inspirés de Zen MCP (Beehive Innovations).

## Vue d'ensemble

SCOUT fournit 3 outils puissants pour le travail de conseil:

1. **Deep Analyst** - Investigation approfondie avec hypothèses
2. **Strategic Planner** - Planification stratégique itérative
3. **Consensus Builder** - Synthèse multi-provider

Ces outils sont conçus pour **multiplier vos capacités d'analyse, de rédaction et de conception par 100**.

---

## 1. Deep Analyst Tool 🔍

Investigation multi-étapes avec tracking de confiance progressive.

### Utilisation

```json
{
  "problem": "Pourquoi notre taux de conversion a chuté de 40% ce mois-ci?",
  "context": "E-commerce B2B, 50K visiteurs/mois, produit SaaS",
  "max_steps": 5,
  "require_high_confidence": true
}
```

### Paramètres

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `problem` | string | **requis** | Problème ou question à investiguer |
| `context` | string | optionnel | Contexte additionnel |
| `max_steps` | int | 5 | Nombre maximum d'étapes (1-10) |
| `require_high_confidence` | bool | true | Continuer jusqu'à haute confiance |
| `use_cross_validation` | bool | false | Valider avec plusieurs providers |

### Résultat

```json
{
  "final_conclusion": "...",
  "confidence_level": "very_high",
  "steps": [
    {
      "step_number": 1,
      "hypothesis": "...",
      "findings": "...",
      "confidence": "exploring"
    }
  ],
  "key_insights": ["...", "..."],
  "recommendations": ["...", "..."],
  "total_steps": 3,
  "duration_seconds": 21.91,
  "total_tokens": 3522
}
```

### Niveaux de Confiance

- `exploring` - Exploration initiale
- `low` - Confiance faible
- `medium` - Confiance moyenne
- `high` - Confiance élevée
- `very_high` - Très haute confiance
- `certain` - Certitude

### Cas d'usage

✅ Diagnostic de problèmes complexes
✅ Analyse de cause racine
✅ Investigation technique approfondie
✅ Recherche structurée

---

## 2. Strategic Planner Tool 📋

Planification stratégique avec raffinement itératif.

### Utilisation

```json
{
  "objective": "Migrer notre infrastructure vers AWS",
  "context": "50 VMs, PostgreSQL, budget $200K, 9 mois",
  "max_iterations": 3,
  "include_alternatives": true,
  "focus_areas": ["timeline", "budget", "risks", "migration-strategy"]
}
```

### Paramètres

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `objective` | string | **requis** | Objectif stratégique |
| `context` | string | optionnel | Contexte et contraintes |
| `max_iterations` | int | 3 | Itérations de raffinement (1-10) |
| `include_alternatives` | bool | false | Générer plans alternatifs |
| `focus_areas` | list | optionnel | Domaines prioritaires |

### Résultat

```json
{
  "plan_steps": [
    {
      "step_number": 1,
      "title": "Infrastructure Assessment",
      "description": "...",
      "dependencies": [],
      "estimated_duration": "2 weeks",
      "estimated_cost": "$15,000",
      "resources_required": ["DevOps Engineer", "Cloud Architect"],
      "risks": ["Data migration complexity"],
      "success_criteria": ["Inventory complete"]
    }
  ],
  "iterations": [
    {
      "iteration_number": 1,
      "changes_made": ["Added risk mitigation"],
      "refinement_focus": ["timeline optimization"]
    }
  ],
  "timeline_overview": "9 months total, 10 major phases",
  "budget_overview": "$180,000 estimated",
  "critical_path": [1, 3, 5, 8],
  "key_risks": ["...", "..."],
  "recommendations": ["...", "..."],
  "alternative_plans": [
    {
      "name": "Fast Track",
      "description": "...",
      "timeline": "6 months",
      "budget": "$250,000"
    }
  ]
}
```

### Focus Areas Disponibles

- `timeline` - Optimisation temporelle
- `budget` - Gestion budgétaire
- `risks` - Mitigation des risques
- `resources` - Allocation ressources
- `quality` - Assurance qualité
- `stakeholders` - Gestion parties prenantes

### Cas d'usage

✅ Migration infrastructure
✅ Lancement produit
✅ Transformation digitale
✅ Projets complexes multi-phases

---

## 3. Consensus Builder Tool 🤝

Synthèse multi-provider pour décisions robustes.

### Utilisation

```json
{
  "question": "Devrions-nous migrer vers microservices?",
  "context": "Monolithe 100K LOC, 20 développeurs, croissance rapide",
  "providers_to_query": ["gemini", "openai", "anthropic"],
  "require_unanimity": false,
  "tie_breaking": true,
  "min_confidence": "medium"
}
```

### Paramètres

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `question` | string | **requis** | Question ou décision |
| `context` | string | optionnel | Contexte de la décision |
| `providers_to_query` | list | tous | Providers à interroger |
| `require_unanimity` | bool | false | Exiger unanimité |
| `tie_breaking` | bool | true | Utiliser tie-breaker si égalité |
| `min_confidence` | string | "medium" | Confiance minimale requise |

### Providers Disponibles

- `gemini` - Google Gemini (modèle: flash)
- `openai` - OpenAI GPT (modèle: gpt-4o)
- `anthropic` - Anthropic Claude (modèle: claude-3-5-sonnet)

### Résultat

```json
{
  "consensus_statement": "CONSENSUS SYNTHESIS:\n\nPoints of Agreement:\n1. Focus on web...",
  "confidence_level": "high",
  "agreements": [
    {
      "statement": "Prioritize web application for first year",
      "supporting_providers": ["gemini", "openai", "anthropic"],
      "confidence": "high",
      "evidence": ["Supported by 3/3 providers"]
    }
  ],
  "disagreements": [
    {
      "topic": "confidence_level",
      "positions": {
        "gemini": "very_high confidence",
        "openai": "high confidence"
      },
      "significance": "moderate",
      "resolution_suggestion": "Review evidence..."
    }
  ],
  "recommendations": [
    "Strong consensus achieved across 3 providers - proceed with high confidence",
    "All providers show high confidence - strong recommendation to proceed"
  ],
  "diversity_score": 0.5,
  "providers_consulted": ["gemini", "openai", "anthropic"],
  "total_tokens_used": 2033,
  "duration_seconds": 8.16
}
```

### Diversity Score

Le score de diversité (0-1) mesure la variance des opinions:
- **0.0-0.3** - Consensus très fort
- **0.3-0.5** - Consensus modéré
- **0.5-0.7** - Opinions divergentes
- **0.7-1.0** - Forte diversité d'opinions

### Cas d'usage

✅ Décisions architecturales
✅ Choix technologiques
✅ Décisions business critiques
✅ Validation stratégies
✅ Résolution controverses

---

## Workflow Recommandé

### 1. Investigation (Deep Analyst)

Utilisez Deep Analyst pour comprendre en profondeur un problème:

```json
{
  "problem": "Comment optimiser notre pipeline CI/CD?",
  "max_steps": 5,
  "require_high_confidence": true
}
```

### 2. Planification (Strategic Planner)

Créez un plan stratégique basé sur vos insights:

```json
{
  "objective": "Optimiser pipeline CI/CD",
  "context": "Insights from Deep Analyst: ...",
  "max_iterations": 3,
  "focus_areas": ["timeline", "risks", "resources"]
}
```

### 3. Validation (Consensus Builder)

Validez vos décisions clés avec consensus multi-provider:

```json
{
  "question": "Le plan CI/CD proposé est-il optimal?",
  "context": "Plan from Strategic Planner: ...",
  "providers_to_query": ["gemini", "openai", "anthropic"]
}
```

---

## Comparaison avec Zen MCP

| Aspect | Zen MCP | SCOUT |
|--------|---------|-------|
| **thinkdeep** | ✅ | ✅ Deep Analyst |
| **planner** | ✅ | ✅ Strategic Planner |
| **consensus** | ✅ | ✅ Consensus Builder |
| **Multi-provider** | ✅ | ✅ 3 providers |
| **Iterative refinement** | ✅ | ✅ |
| **Confidence tracking** | ✅ | ✅ |
| **MCP protocol** | ✅ | ✅ FastMCP |

---

## Performance

### Deep Analyst
- ⏱️ **Durée moyenne**: 20-45s
- 🔢 **Tokens**: 3,000-10,000
- 📊 **Steps**: 2-5 typiquement

### Strategic Planner
- ⏱️ **Durée moyenne**: 30-60s
- 🔢 **Tokens**: 3,000-5,000
- 📊 **Iterations**: 3 recommandé

### Consensus Builder
- ⏱️ **Durée moyenne**: 5-15s (parallèle)
- 🔢 **Tokens**: 1,500-3,000
- 📊 **Providers**: 2-3 recommandé

---

## Bonnes Pratiques

### 💡 Deep Analyst

✅ Fournir contexte détaillé
✅ Utiliser `require_high_confidence: true` pour analyses critiques
✅ Limiter à 5-7 steps pour éviter over-analysis
❌ Ne pas utiliser pour questions simples

### 💡 Strategic Planner

✅ Spécifier focus_areas clairs
✅ Utiliser 3-5 iterations pour équilibre qualité/temps
✅ Activer `include_alternatives` pour décisions majeures
❌ Ne pas surcharger avec trop de contraintes

### 💡 Consensus Builder

✅ Interroger 3 providers pour vraie diversité
✅ Utiliser `tie_breaking: true` pour éviter blocages
✅ Analyser diversity_score pour comprendre accord
❌ Ne pas exiger unanimité sauf nécessité absolue

---

## Dépannage

### Erreur "Insufficient responses"

**Cause**: Moins de 2 providers ont répondu
**Solution**: Vérifier configuration providers dans `.env`

### Confiance reste "exploring"

**Cause**: Problème trop vague ou manque de contexte
**Solution**: Augmenter contexte, reformuler question

### Timeout

**Cause**: Trop d'itérations/steps
**Solution**: Réduire `max_steps` ou `max_iterations`

---

## Support

Pour questions ou bugs:
- 📧 GitHub Issues: https://github.com/cboulanger/scout/issues
- 📚 Documentation: https://docs.scout-mcp.com

---

*Inspiré par Zen MCP (Beehive Innovations) - Optimisé pour consultants autonomes*
