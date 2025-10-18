# PRD: SCOUT MCP Server
## Product Requirements Document v1.0

**Projet:** SCOUT (Strategic CTO Operations and Unified Tooling)
**Propriétaire:** Christian Boulet, Boulet Stratégies TI
**Date:** 18 octobre 2025
**Statut:** Draft pour implémentation

---

## 1. Vision & Objectifs

### 1.1 Vision Produit
SCOUT est un serveur MCP (Model Context Protocol) personnel qui amplifie la productivité d'un Fractional CTO en orchestrant des équipes d'agents AI spécialisés pour accomplir des tâches complexes d'architecture, d'analyse stratégique, et de reconnaissance d'affaires. SCOUT doit devenir l'outil central de Boulet Stratégies TI, utilisable quotidiennement par Christian et ses futurs associés.

### 1.2 Objectifs Business
- **Réduction 70% du temps** consacré à la recherche environnement client
- **Standardisation** des livrables (avis d'architecture, analyses, audits)
- **Réutilisabilité** de la connaissance accumulée via Notion
- **Scalabilité** pour supporter de futurs associés sans friction
- **Différenciation** marché via vélocité supérieure de livraison

### 1.3 Objectifs Techniques
- Architecture **modulaire et évolutive** anticipant l'arrivée de nouveaux modèles AI
- Configuration **centralisée et versionnée** pour tous les providers AI
- Système de **sélection d'équipe flexible** selon la complexité de la tâche
- **Zero-downtime updates** lors de l'ajout de nouvelles fonctions
- **Compatibilité MCP** totale pour intégration Claude Desktop/Web

### 1.4 Utilisateurs Cibles
- **Primaire:** Christian Boulet (seul utilisateur initial)
- **Secondaires:** Futurs associés de Boulet Stratégies TI (2-3 personnes)
- **Tertiaire:** Potentiellement clients PME (phase 3, non priorisée)

---

## 2. Architecture Système

### 2.1 Vue d'Ensemble Architecturale

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Desktop/Web                        │
│                    (MCP Client)                              │
└─────────────────────┬───────────────────────────────────────┘
                      │ MCP Protocol (STDIO/HTTP+SSE)
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                  SCOUT MCP Server                            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Tool Router & Orchestrator                 │ │
│  │         (FastMCP + Tool Registry Pattern)               │ │
│  └───┬──────────────────────────────────────────────┬─────┘ │
│      │                                               │       │
│  ┌───▼────────┐  ┌──────────────┐  ┌───────────────▼────┐ │
│  │   Tools    │  │   AI Team    │  │   State Manager    │ │
│  │  Registry  │  │   Selector   │  │   (Redis/File)     │ │
│  └───┬────────┘  └──────┬───────┘  └───────────────┬────┘ │
│      │                  │                           │       │
│  ┌───▼──────────────────▼───────────────────────────▼────┐ │
│  │              Provider Abstraction Layer                │ │
│  │    (Unified Interface: Gemini, OpenAI, Claude, etc)   │ │
│  └───┬──────────────────┬───────────────────────┬─────────┘ │
└──────┼──────────────────┼───────────────────────┼───────────┘
       │                  │                       │
   ┌───▼────┐      ┌──────▼─────┐        ┌───────▼──────┐
   │ Gemini │      │   OpenAI   │        │  Anthropic   │
   │  API   │      │    API     │        │     API      │
   └────────┘      └────────────┘        └──────────────┘
```

### 2.2 Composants Principaux

#### 2.2.1 Tool Router & Orchestrator
- **Responsabilité:** Receive MCP tool calls, route vers l'implémentation correcte, orchestrer workflows multi-étapes
- **Tech Stack:** Python 3.11+, FastMCP, asyncio
- **Pattern:** Command pattern avec registry dynamique

#### 2.2.2 AI Team Selector
- **Responsabilité:** Déterminer quelle(s) équipe(s) AI utiliser selon contexte, budget, et complexité
- **Inputs:** Tool demandé, paramètres complexité, préférences utilisateur
- **Output:** Configuration d'équipe (model primaire, model secondaire pour validation, etc.)

#### 2.2.3 Provider Abstraction Layer
- **Responsabilité:** Interface unifiée pour tous les providers AI (Gemini, OpenAI, Claude, etc.)
- **Pattern:** Strategy pattern avec factory
- **Features:** Retry logic, rate limiting, error handling, cost tracking

#### 2.2.4 State Manager
- **Responsabilité:** Persistence contexte conversationnel, cache résultats, tracking projets
- **Storage:** Redis (production) / JSON files (dev)
- **TTL:** Configurable par type de données

#### 2.2.5 Configuration Manager
- **Responsabilité:** Charger et valider configuration models, teams, API keys
- **Format:** YAML pour lisibilité humaine
- **Validation:** Pydantic schemas avec checks au démarrage

---

## 3. Système de Configuration

### 3.1 Structure de Configuration

```yaml
# config/scout.yaml

# ============================================
# PROVIDERS AI - Clés API et Configuration
# ============================================
providers:
  gemini:
    api_key: ${GEMINI_API_KEY}  # Variable d'environnement
    models:
      flash:
        id: "gemini-2.0-flash-exp"
        max_tokens: 8192
        temperature: 0.7
        cost_per_1k_input: 0.00015
        cost_per_1k_output: 0.0006
      pro:
        id: "gemini-2.0-pro-exp"
        max_tokens: 32768
        temperature: 0.7
        cost_per_1k_input: 0.00125
        cost_per_1k_output: 0.005
      thinking:
        id: "gemini-2.0-flash-thinking-exp"
        max_tokens: 8192
        temperature: 1.0
        cost_per_1k_input: 0.00015
        cost_per_1k_output: 0.0006

  openai:
    api_key: ${OPENAI_API_KEY}
    models:
      gpt4o:
        id: "gpt-4o"
        max_tokens: 16384
        temperature: 0.7
        cost_per_1k_input: 0.0025
        cost_per_1k_output: 0.01
      o3mini:
        id: "o3-mini"
        max_tokens: 32768
        temperature: 1.0
        cost_per_1k_input: 0.0015
        cost_per_1k_output: 0.006

  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    models:
      sonnet:
        id: "claude-sonnet-4-20250514"
        max_tokens: 8192
        temperature: 0.7
        cost_per_1k_input: 0.003
        cost_per_1k_output: 0.015
      opus:
        id: "claude-opus-4-20250514"
        max_tokens: 16384
        temperature: 0.7
        cost_per_1k_input: 0.015
        cost_per_1k_output: 0.075

# ============================================
# ÉQUIPES AI - Combinaisons de Modèles
# ============================================
teams:
  # Équipe économique - usage quotidien
  scout:
    description: "Équipe rapide et économique pour reconnaissance initiale"
    primary:
      provider: gemini
      model: flash
    validators: []  # Pas de validation secondaire
    use_cases: ["chat", "quick_analysis", "simple_queries"]

  # Équipe balanced - qualité/coût optimal
  architect:
    description: "Équipe équilibrée pour architecture et design"
    primary:
      provider: gemini
      model: pro
    validators:
      - provider: openai
        model: gpt4o
        trigger: "confidence < 0.8"  # Valide si confiance basse
    use_cases: ["planner", "analyse", "refactor"]

  # Équipe premium - qualité maximale
  expert:
    description: "Équipe premium pour décisions critiques"
    primary:
      provider: anthropic
      model: opus
    validators:
      - provider: gemini
        model: thinking
        trigger: "always"  # Toujours obtenir 2ème opinion
      - provider: openai
        model: o3mini
        trigger: "consensus_required"
    use_cases: ["secaudit", "consensus", "challenge", "critical_decisions"]

  # Équipe raisonnement profond
  thinker:
    description: "Équipe spécialisée raisonnement complexe"
    primary:
      provider: openai
      model: o3mini
    validators:
      - provider: gemini
        model: thinking
    use_cases: ["thinkdeep", "complex_problem_solving"]

# ============================================
# MAPPING OUTILS → ÉQUIPES (Défaut)
# ============================================
tool_team_mapping:
  chat: scout
  clink: scout
  apilookup: scout
  analyse: architect
  planner: architect
  refactor: architect
  thinkdeep: thinker
  consensus: expert
  challenge: expert
  secaudit: expert

# ============================================
# PARAMÈTRES SYSTÈME
# ============================================
system:
  default_team: scout
  allow_team_override: true  # User peut forcer une équipe spécifique
  max_retries: 3
  timeout_seconds: 300
  enable_cost_tracking: true
  state_backend: redis  # redis | file
  redis_url: ${REDIS_URL}
  cache_ttl_seconds: 3600

# ============================================
# INTÉGRATIONS EXTERNES
# ============================================
integrations:
  notion:
    token: ${NOTION_TOKEN}
    research_database_id: ${NOTION_RESEARCH_DB}

  tavily:
    api_key: ${TAVILY_API_KEY}
    max_results: 5
```

### 3.2 Gestion des Variables d'Environnement

**Fichier `.env` (NON versionné):**
```bash
# Providers AI
GEMINI_API_KEY=AIza...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Infrastructure
REDIS_URL=redis://localhost:6379
NOTION_TOKEN=secret_...
NOTION_RESEARCH_DB=1234567890ab...

# Services externes
TAVILY_API_KEY=tvly-...
```

### 3.3 Override et Sélection d'Équipe

L'utilisateur peut spécifier l'équipe AI de trois façons:

**1. Via paramètre direct dans le tool call:**
```json
{
  "tool": "analyse",
  "input": {
    "code": "...",
    "team": "expert"  // Override le default "architect"
  }
}
```

**2. Via configuration contextuelle (session Redis):**
```python
# L'utilisateur peut dire: "Use expert team for this session"
# SCOUT stocke cette préférence en Redis avec TTL
```

**3. Via comportement adaptatif (future phase):**
```python
# SCOUT détecte automatiquement si la tâche nécessite une équipe premium
# basé sur: taille du code, complexité détectée, historique erreurs
```

---

## 4. Spécifications Fonctionnelles

### 4.1 Outils Hérités de ZEN

#### 4.1.1 `chat` - Conversation Multi-Modèle
**Description:** Dialogue interactif avec continuation de contexte, permettant de choisir le modèle conversationnel.

**Paramètres:**
- `message` (string, required): Message de l'utilisateur
- `continuation_id` (string, optional): ID pour reprendre conversation existante
- `team` (string, optional): Override équipe AI (default: "scout")
- `temperature` (float, optional): Override temperature (default: selon team)

**Workflow:**
1. Charger contexte conversationnel si `continuation_id` fourni
2. Sélectionner modèle selon `team` spécifiée
3. Envoyer message avec historique au modèle
4. Sauvegarder réponse dans contexte
5. Retourner réponse + nouveau `continuation_id`

**Output:**
```json
{
  "response": "Réponse du modèle...",
  "continuation_id": "uuid-1234-5678",
  "model_used": "gemini-2.0-flash-exp",
  "tokens_used": {"input": 150, "output": 300},
  "cost_usd": 0.00024
}
```

**Équipe par défaut:** `scout`

---

#### 4.1.2 `planner` - Planification de Projet Technique
**Description:** Décompose un objectif technique en plan actionable multi-étapes avec estimations.

**Paramètres:**
- `objective` (string, required): Objectif ou projet à planifier
- `context` (string, optional): Contexte additionnel (contraintes, environnement)
- `granularity` (enum, optional): "high_level" | "detailed" | "task_level" (default: "detailed")
- `team` (string, optional): Override équipe (default: "architect")

**Workflow:**
1. Modèle primaire génère plan initial avec phases, étapes, dépendances
2. Si `validators` configurés dans team, ils reviewent pour gaps/risques
3. Synthèse finale intégrant feedbacks
4. Génération fichier markdown structuré
5. Optionnel: Sauvegarde dans Notion si intégration active

**Output:**
```json
{
  "plan_markdown": "# Plan: [Objectif]\n\n## Phase 1...",
  "phases": [
    {
      "name": "Phase 1",
      "duration_estimate": "2 semaines",
      "tasks": [...]
    }
  ],
  "dependencies": [],
  "risks_identified": [],
  "notion_url": "https://notion.so/..."  // Si sauvegardé
}
```

**Équipe par défaut:** `architect`

---

#### 4.1.3 `clink` - Analyse de Liens de Contexte
**Description:** Analyse les relations et dépendances entre éléments d'une codebase ou documentation.

**Paramètres:**
- `target` (string, required): Fichier, fonction, ou module à analyser
- `scope` (enum, optional): "file" | "module" | "project" (default: "file")
- `depth` (int, optional): Profondeur d'analyse 1-3 (default: 2)
- `team` (string, optional): Override équipe (default: "scout")

**Workflow:**
1. Extraire contexte du target (via file system ou input)
2. Modèle identifie: imports, dépendances, appels, références
3. Construire graphe de relations
4. Générer visualisation text-based ou Mermaid diagram

**Output:**
```json
{
  "dependencies": {
    "imports": ["module1", "module2"],
    "called_by": ["function_a", "function_b"],
    "calls": ["external_api", "internal_service"]
  },
  "diagram_mermaid": "graph TD\n  A[Target]...",
  "insights": ["Ce module a 15 dépendances...", "..."]
}
```

**Équipe par défaut:** `scout`

---

#### 4.1.4 `thinkdeep` - Raisonnement Profond Multi-Étapes
**Description:** Résolution de problèmes complexes nécessitant raisonnement structuré avec validation étape par étape.

**Paramètres:**
- `problem` (string, required): Problème ou question complexe
- `constraints` (list[string], optional): Contraintes ou considérations
- `target_confidence` (float, optional): Niveau de confiance cible 0-1 (default: 0.95)
- `team` (string, optional): Override équipe (default: "thinker")

**Workflow:**
1. Modèle primaire (o3-mini ou thinking) décompose problème en sous-questions
2. Raisonnement étape par étape avec self-verification
3. Pour chaque étape: hypothèse → test → validation
4. Si confiance < target: modèle validator apporte 2ème perspective
5. Synthèse finale avec niveau de confiance

**Output:**
```json
{
  "solution": "Solution détaillée...",
  "reasoning_steps": [
    {
      "step": 1,
      "hypothesis": "...",
      "validation": "...",
      "confidence": 0.8
    }
  ],
  "final_confidence": 0.96,
  "alternative_approaches": [],
  "models_consulted": ["o3-mini", "gemini-thinking"]
}
```

**Équipe par défaut:** `thinker`

---

#### 4.1.5 `consensus` - Recherche de Consensus Multi-Modèles
**Description:** Obtenir consensus entre plusieurs modèles AI sur une décision critique ou analyse.

**Paramètres:**
- `question` (string, required): Question ou décision nécessitant consensus
- `context` (string, optional): Contexte complet pour la décision
- `min_agreement` (float, optional): % accord minimum 0-1 (default: 0.75)
- `team` (string, optional): Override équipe (default: "expert")

**Workflow:**
1. Soumettre question aux 3 modèles de l'équipe "expert" en parallèle
2. Collecter réponses indépendantes (sans voir réponses des autres)
3. Analyser convergence/divergence des réponses
4. Si divergence significative: 4ème modèle arbitre et explique différences
5. Générer rapport de consensus avec zones d'accord et désaccord

**Output:**
```json
{
  "consensus_reached": true,
  "agreement_level": 0.85,
  "agreed_position": "Les trois modèles convergent sur...",
  "dissenting_views": [
    {
      "model": "gemini-thinking",
      "position": "Perspective alternative...",
      "reasoning": "..."
    }
  ],
  "arbitration": "L'arbitrage final suggère...",
  "confidence": 0.92
}
```

**Équipe par défaut:** `expert`

---

#### 4.1.6 `analyse` - Analyse de Code/Système
**Description:** Analyse approfondie de code, architecture, ou systèmes avec identification de problèmes et recommandations.

**Paramètres:**
- `target` (string, required): Code, fichier, ou description système à analyser
- `analysis_type` (enum, optional): "code_quality" | "architecture" | "performance" | "all" (default: "all")
- `output_format` (enum, optional): "markdown" | "json" | "notion" (default: "markdown")
- `team` (string, optional): Override équipe (default: "architect")

**Workflow:**
1. Modèle primaire effectue analyse selon `analysis_type`
2. Identification: bugs, code smells, anti-patterns, performance issues
3. Si équipe inclut validator: 2ème review pour validation findings
4. Génération rapport structuré avec priorités (critical/high/medium/low)
5. Recommandations concrètes avec exemples de code

**Output:**
```json
{
  "summary": "Analyse identifie 3 issues critiques...",
  "findings": [
    {
      "severity": "critical",
      "category": "security",
      "description": "SQL injection vulnerability...",
      "location": "line 45",
      "recommendation": "Use parameterized queries...",
      "example_fix": "cursor.execute(query, (param,))"
    }
  ],
  "metrics": {
    "complexity_score": 7.2,
    "maintainability_index": 68,
    "test_coverage": 45
  },
  "report_url": "https://notion.so/..."  // Si output_format = "notion"
}
```

**Équipe par défaut:** `architect`

---

#### 4.1.7 `refactor` - Refactoring Assisté
**Description:** Propose et génère des refactorings pour améliorer qualité, lisibilité, ou performance du code.

**Paramètres:**
- `code` (string, required): Code à refactorer
- `objectives` (list[string], optional): Objectifs du refactor (e.g., "reduce_complexity", "improve_readability")
- `preserve_behavior` (bool, optional): Garantir comportement identique (default: true)
- `suggest_tests` (bool, optional): Générer tests de validation (default: true)
- `team` (string, optional): Override équipe (default: "architect")

**Workflow:**
1. Analyse code original: métriques, patterns, problèmes
2. Génération de plusieurs stratégies de refactor
3. Sélection meilleure stratégie selon objectives
4. Génération code refactoré
5. Si `suggest_tests=true`: génération tests unitaires pour validation
6. Diff détaillé old vs new avec explications changements

**Output:**
```json
{
  "original_metrics": {
    "complexity": 12,
    "lines": 150
  },
  "refactored_code": "def optimized_function():\n    ...",
  "improvements": [
    "Reduced cyclomatic complexity from 12 to 5",
    "Extracted 3 helper functions for SRP"
  ],
  "diff": "--- Original\n+++ Refactored\n...",
  "suggested_tests": "def test_refactored_function():\n    ...",
  "refactored_metrics": {
    "complexity": 5,
    "lines": 120
  }
}
```

**Équipe par défaut:** `architect`

---

#### 4.1.8 `secaudit` - Audit de Sécurité
**Description:** Audit de sécurité approfondi avec identification vulnérabilités, conformité, et recommandations hardening.

**Paramètres:**
- `target` (string, required): Code, config, ou système à auditer
- `audit_scope` (list[string], optional): Domaines à couvrir ["owasp_top10", "secrets", "dependencies", "config"]
- `compliance_standards` (list[string], optional): Standards à vérifier (e.g., ["PCI-DSS", "SOC2"])
- `severity_threshold` (enum, optional): Niveau minimum à reporter "low" | "medium" | "high" | "critical" (default: "medium")
- `team` (string, optional): Override équipe (default: "expert")

**Workflow:**
1. Équipe expert (3 modèles) effectue audit en parallèle selon scope
2. Détection: vulnérabilités connues, secrets exposés, config dangereuses
3. Cross-validation findings entre modèles pour éliminer faux positifs
4. Mapping vers frameworks de sécurité (OWASP, CWE, CVE)
5. Génération rapport priorisant par severity + exploitability
6. Recommandations de remédiation avec exemples concrets

**Output:**
```json
{
  "executive_summary": "Audit identifie 2 vulnérabilités critiques...",
  "vulnerabilities": [
    {
      "id": "VULN-001",
      "severity": "critical",
      "category": "authentication",
      "owasp_mapping": "A01:2021 - Broken Access Control",
      "cwe_id": "CWE-287",
      "description": "Missing authentication on admin endpoint",
      "location": "/api/admin",
      "exploitability": "high",
      "impact": "Complete system compromise",
      "remediation": "Implement JWT authentication with role checks",
      "code_example": "..."
    }
  ],
  "secrets_found": [
    {
      "type": "aws_access_key",
      "location": "config.py:15",
      "recommendation": "Move to environment variables"
    }
  ],
  "compliance_gaps": [
    {
      "standard": "SOC2",
      "control": "CC6.1",
      "gap": "Missing encryption at rest"
    }
  ],
  "risk_score": 8.5,
  "validated_by": ["claude-opus", "gemini-thinking", "o3-mini"]
}
```

**Équipe par défaut:** `expert`

---

#### 4.1.9 `apilookup` - Recherche Documentation API
**Description:** Recherche et explique l'utilisation d'APIs, librairies, ou frameworks avec exemples concrets.

**Paramètres:**
- `query` (string, required): API, librairie, ou méthode à rechercher
- `language` (string, optional): Langage de programmation (default: auto-detect)
- `include_examples` (bool, optional): Inclure exemples de code (default: true)
- `version` (string, optional): Version spécifique si pertinent
- `team` (string, optional): Override équipe (default: "scout")

**Workflow:**
1. Web search pour documentation officielle + exemples communautaires
2. Modèle synthétise: signature, paramètres, retour, use cases
3. Génération exemples concrets d'utilisation
4. Ajout best practices et gotchas communs
5. Cache résultat pour requêtes futures similaires

**Output:**
```json
{
  "api_name": "stripe.PaymentIntent.create",
  "description": "Create a PaymentIntent for payment processing",
  "signature": "stripe.PaymentIntent.create(**params)",
  "parameters": [
    {
      "name": "amount",
      "type": "integer",
      "required": true,
      "description": "Amount in cents"
    }
  ],
  "examples": [
    {
      "language": "python",
      "code": "intent = stripe.PaymentIntent.create(\n  amount=2000,\n  currency='usd'\n)"
    }
  ],
  "best_practices": [
    "Always handle exceptions for failed payments",
    "Use idempotency keys for safety"
  ],
  "common_gotchas": [
    "Amount must be in smallest currency unit (cents)"
  ],
  "documentation_url": "https://docs.stripe.com/..."
}
```

**Équipe par défaut:** `scout`

---

#### 4.1.10 `challenge` - Challenge et Validation de Décision
**Description:** Joue l'avocat du diable pour challenger une décision technique ou stratégique.

**Paramètres:**
- `decision` (string, required): Décision ou approche à challenger
- `context` (string, optional): Contexte et rationale de la décision
- `challenge_level` (enum, optional): "constructive" | "aggressive" | "comprehensive" (default: "constructive")
- `team` (string, optional): Override équipe (default: "expert")

**Workflow:**
1. Modèle primaire analyse la décision et identifie assumptions
2. Génération arguments contre avec: risques, alternatives, edge cases
3. Modèle validator joue rôle défenseur de la décision originale
4. Débat structuré entre modèles (3 rounds)
5. Synthèse: forces/faiblesses, recommandations, décision améliorée

**Output:**
```json
{
  "original_decision": "Migrer vers microservices architecture",
  "challenger_arguments": [
    {
      "argument": "Increased operational complexity",
      "evidence": "Team has no experience with container orchestration",
      "severity": "high",
      "mitigation": "Consider modular monolith first"
    }
  ],
  "defender_rebuttals": [
    {
      "to_argument": "Increased operational complexity",
      "rebuttal": "Managed Kubernetes reduces ops burden",
      "strength": "medium"
    }
  ],
  "debate_summary": "After 3 rounds...",
  "risks_identified": [],
  "alternative_approaches": [
    {
      "name": "Modular Monolith",
      "pros": ["Lower complexity", "Easier debugging"],
      "cons": ["Less scalable"],
      "when_to_use": "If team size < 10 and no immediate scale needs"
    }
  ],
  "final_recommendation": "Proceed with microservices but phase implementation...",
  "confidence": 0.78
}
```

**Équipe par défaut:** `expert`

---

## 5. Architecture Technique Détaillée

### 5.1 Structure du Projet

```
scout-mcp-server/
├── .env                          # Variables environnement (gitignored)
├── .env.example                  # Template pour .env
├── pyproject.toml                # Dependencies et metadata
├── README.md
├── config/
│   ├── scout.yaml                # Configuration principale
│   ├── teams.yaml                # Définition équipes (peut override)
│   └── providers.yaml            # Providers AI (peut override)
├── src/
│   ├── scout/
│   │   ├── __init__.py
│   │   ├── main.py               # Point d'entrée serveur MCP
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   ├── loader.py         # Charge et valide config YAML
│   │   │   └── models.py         # Pydantic models pour config
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py   # Tool routing et orchestration
│   │   │   ├── team_selector.py  # Sélection équipe AI
│   │   │   └── state_manager.py  # Gestion état (Redis/File)
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # Abstract base provider
│   │   │   ├── gemini.py         # Google Gemini provider
│   │   │   ├── openai.py         # OpenAI provider
│   │   │   ├── anthropic.py      # Anthropic Claude provider
│   │   │   └── factory.py        # Provider factory
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── registry.py       # Tool registry dynamique
│   │   │   ├── chat.py
│   │   │   ├── planner.py
│   │   │   ├── clink.py
│   │   │   ├── thinkdeep.py
│   │   │   ├── consensus.py
│   │   │   ├── analyse.py
│   │   │   ├── refactor.py
│   │   │   ├── secaudit.py
│   │   │   ├── apilookup.py
│   │   │   └── challenge.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── rate_limiter.py
│   │       ├── retry.py
│   │       ├── cache.py
│   │       └── logger.py
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_providers.py
│   ├── test_tools.py
│   └── fixtures/
└── docs/
    ├── architecture.md
    ├── configuration.md
    └── extending.md
```

### 5.2 Classes Principales

#### 5.2.1 Provider Abstraction

```python
# src/scout/providers/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class AIResponse:
    content: str
    model: str
    tokens_used: Dict[str, int]
    cost_usd: float
    metadata: Dict[str, Any]

class BaseAIProvider(ABC):
    def __init__(self, api_key: str, config: Dict[str, Any]):
        self.api_key = api_key
        self.config = config

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> AIResponse:
        """Génère une réponse synchrone"""
        pass

    @abstractmethod
    async def stream(
        self,
        prompt: str,
        model: str,
        **kwargs
    ):
        """Génère une réponse en streaming"""
        pass

    async def validate_api_key(self) -> bool:
        """Valide que l'API key fonctionne"""
        try:
            await self.generate("test", self.config["models"].keys()[0], max_tokens=10)
            return True
        except:
            return False
```

#### 5.2.2 Team Selector

```python
# src/scout/core/team_selector.py
from typing import Optional, Dict, List
from dataclasses import dataclass

@dataclass
class TeamConfig:
    name: str
    description: str
    primary: Dict[str, str]  # provider, model
    validators: List[Dict[str, Any]]
    use_cases: List[str]

class TeamSelector:
    def __init__(self, config: Dict[str, Any]):
        self.teams = self._load_teams(config)
        self.tool_mapping = config.get("tool_team_mapping", {})
        self.default_team = config["system"]["default_team"]

    def select_team(
        self,
        tool_name: str,
        user_override: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> TeamConfig:
        """
        Sélectionne l'équipe AI appropriée

        Priorité:
        1. user_override si fourni
        2. tool_team_mapping pour le tool
        3. default_team
        """
        if user_override and user_override in self.teams:
            return self.teams[user_override]

        if tool_name in self.tool_mapping:
            team_name = self.tool_mapping[tool_name]
            return self.teams[team_name]

        return self.teams[self.default_team]

    def should_validate(
        self,
        validator_config: Dict,
        context: Dict
    ) -> bool:
        """Détermine si un validator doit être utilisé"""
        trigger = validator_config.get("trigger", "never")

        if trigger == "always":
            return True
        elif trigger == "never":
            return False
        elif trigger.startswith("confidence"):
            # Parse "confidence < 0.8"
            threshold = float(trigger.split("<")[1].strip())
            return context.get("confidence", 1.0) < threshold
        elif trigger == "consensus_required":
            return context.get("consensus_required", False)

        return False
```

#### 5.2.3 Tool Registry Pattern

```python
# src/scout/tools/registry.py
from typing import Callable, Dict, Any
from dataclasses import dataclass
from mcp import types

@dataclass
class ToolDefinition:
    name: str
    description: str
    handler: Callable
    schema: Dict[str, Any]
    default_team: str

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        schema: Dict[str, Any],
        default_team: str = "scout"
    ):
        """Decorator pour enregistrer un tool"""
        def decorator(handler: Callable):
            self._tools[name] = ToolDefinition(
                name=name,
                description=description,
                handler=handler,
                schema=schema,
                default_team=default_team
            )
            return handler
        return decorator

    def get_tool(self, name: str) -> ToolDefinition:
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found")
        return self._tools[name]

    def list_tools(self) -> list[types.Tool]:
        """Retourne liste de tools pour MCP"""
        return [
            types.Tool(
                name=tool.name,
                description=tool.description,
                inputSchema=tool.schema
            )
            for tool in self._tools.values()
        ]

# Global registry instance
registry = ToolRegistry()
```

### 5.3 Exemple d'Implémentation d'un Tool

```python
# src/scout/tools/analyse.py
from scout.tools.registry import registry
from scout.core.team_selector import TeamSelector
from scout.providers.factory import ProviderFactory
import logging

logger = logging.getLogger(__name__)

@registry.register(
    name="analyse",
    description="Analyse approfondie de code, architecture, ou systèmes",
    schema={
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Code ou système à analyser"
            },
            "analysis_type": {
                "type": "string",
                "enum": ["code_quality", "architecture", "performance", "all"],
                "default": "all"
            },
            "output_format": {
                "type": "string",
                "enum": ["markdown", "json", "notion"],
                "default": "markdown"
            },
            "team": {
                "type": "string",
                "description": "Override équipe AI (optional)"
            }
        },
        "required": ["target"]
    },
    default_team="architect"
)
async def analyse_handler(
    target: str,
    analysis_type: str = "all",
    output_format: str = "markdown",
    team: str = None,
    **kwargs
):
    """Handler pour l'outil analyse"""

    # 1. Sélection de l'équipe
    team_selector = kwargs.get("team_selector")
    team_config = team_selector.select_team(
        tool_name="analyse",
        user_override=team
    )

    logger.info(f"Using team '{team_config.name}' for analysis")

    # 2. Obtenir le provider primaire
    provider_factory = kwargs.get("provider_factory")
    primary_provider = provider_factory.get_provider(
        team_config.primary["provider"]
    )

    # 3. Construire le prompt d'analyse
    prompt = f"""Analyse approfondie du code/système suivant.

Type d'analyse demandé: {analysis_type}

Code/Système:
```
{target}
```

Effectue une analyse détaillée couvrant:
- Code quality (si applicable)
- Architecture patterns
- Performance considerations
- Security concerns
- Best practices violations

Format de sortie: {output_format}
"""

    # 4. Exécution analyse primaire
    primary_response = await primary_provider.generate(
        prompt=prompt,
        model=team_config.primary["model"],
        temperature=0.7,
        max_tokens=8192
    )

    findings = primary_response.content
    confidence = 0.85  # TODO: Extract from response

    # 5. Validation secondaire si configurée
    if team_config.validators:
        validator_config = team_config.validators[0]

        if team_selector.should_validate(
            validator_config,
            {"confidence": confidence}
        ):
            logger.info("Running validation review...")

            validator_provider = provider_factory.get_provider(
                validator_config["provider"]
            )

            validation_prompt = f"""Review the following code analysis and validate findings:

Original Analysis:
{findings}

Provide feedback on:
1. Are the findings accurate?
2. Any missing issues?
3. Any false positives?
"""

            validation_response = await validator_provider.generate(
                prompt=validation_prompt,
                model=validator_config["model"],
                temperature=0.5,
                max_tokens=4096
            )

            # Intégrer feedback validation
            findings = _integrate_validation(findings, validation_response.content)

    # 6. Formater output
    if output_format == "json":
        return _format_as_json(findings)
    elif output_format == "notion":
        notion_url = await _save_to_notion(findings)
        return {"report_url": notion_url, "summary": _extract_summary(findings)}
    else:
        return {"report_markdown": findings}

def _integrate_validation(original: str, validation: str) -> str:
    """Intègre les feedbacks de validation"""
    # TODO: Implement smart integration
    return f"{original}\n\n## Validation Review\n{validation}"

def _format_as_json(markdown: str) -> dict:
    """Parse markdown en structure JSON"""
    # TODO: Implement markdown parsing
    return {"findings": [], "summary": ""}

async def _save_to_notion(content: str) -> str:
    """Sauvegarde dans Notion et retourne URL"""
    # TODO: Implement Notion integration
    return "https://notion.so/analysis-123"

def _extract_summary(content: str) -> str:
    """Extrait summary du rapport"""
    # TODO: Implement summary extraction
    return "Analysis completed"
```

---

## 6. Plan d'Extensibilité

### 6.1 Ajout d'un Nouveau Provider AI

**Étapes pour ajouter, par exemple, "Mistral AI":**

1. **Créer provider class:**
```python
# src/scout/providers/mistral.py
from scout.providers.base import BaseAIProvider, AIResponse
import httpx

class MistralProvider(BaseAIProvider):
    async def generate(self, prompt, model, **kwargs):
        # Implementation using Mistral API
        pass
```

2. **Ajouter dans config YAML:**
```yaml
providers:
  mistral:
    api_key: ${MISTRAL_API_KEY}
    models:
      medium:
        id: "mistral-medium-latest"
        max_tokens: 32000
        temperature: 0.7
        cost_per_1k_input: 0.0025
        cost_per_1k_output: 0.0075
```

3. **Enregistrer dans factory:**
```python
# src/scout/providers/factory.py
from scout.providers.mistral import MistralProvider

PROVIDER_CLASSES = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "mistral": MistralProvider,  # Nouveau
}
```

4. **Utiliser dans équipes:**
```yaml
teams:
  european:  # Nouvelle équipe utilisant Mistral
    description: "Équipe utilisant providers européens"
    primary:
      provider: mistral
      model: medium
```

**AUCUN code des tools existants ne change.**

### 6.2 Ajout d'un Nouveau Tool

**Étapes pour ajouter un tool "docgen" (génération documentation):**

1. **Créer fichier tool:**
```python
# src/scout/tools/docgen.py
from scout.tools.registry import registry

@registry.register(
    name="docgen",
    description="Génère documentation à partir de code",
    schema={
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "format": {"type": "string", "enum": ["markdown", "html"]}
        },
        "required": ["code"]
    },
    default_team="scout"
)
async def docgen_handler(code: str, format: str = "markdown", **kwargs):
    # Implementation
    return {"documentation": "..."}
```

2. **Importer dans main.py:**
```python
# src/scout/main.py
from scout.tools import chat, planner, analyse, docgen  # Ajout
```

3. **Optionnel - mapper à une équipe spécifique:**
```yaml
tool_team_mapping:
  docgen: scout  # Utilise équipe économique
```

**Le tool est automatiquement disponible via MCP.**

### 6.3 Modification d'une Équipe

Pour adapter une équipe aux besoins changeants, éditer simplement `config/scout.yaml`:

**Avant:**
```yaml
teams:
  architect:
    primary:
      provider: gemini
      model: pro
    validators:
      - provider: openai
        model: gpt4o
```

**Après (utilise nouveau modèle Gemini 3.0):**
```yaml
teams:
  architect:
    primary:
      provider: gemini
      model: ultra  # Nouveau modèle
    validators:
      - provider: openai
        model: gpt4o
      - provider: anthropic  # Ajout 2ème validator
        model: sonnet
        trigger: "confidence < 0.7"
```

Restart du serveur SCOUT → changements actifs.

---

## 7. Implémentation et Timeline

### 7.1 Phases d'Implémentation

#### Phase 1: Infrastructure Core (Semaine 1-2)
**Objectif:** Serveur MCP fonctionnel avec 1-2 tools de base

**Livrables:**
- [ ] Setup projet Python avec poetry/uv
- [ ] Configuration loader (YAML → Pydantic)
- [ ] Provider abstraction layer (Gemini + OpenAI)
- [ ] Tool registry pattern
- [ ] Team selector basique
- [ ] Implémentation `chat` tool
- [ ] Implémentation `apilookup` tool
- [ ] Tests unitaires core components
- [ ] Documentation setup et configuration

**Validation:** Lancer serveur MCP localement, connecter à Claude Desktop, tester `chat` avec différentes équipes.

#### Phase 2: Tools Essentiels (Semaine 3-4)
**Objectif:** Implémenter tools à haute valeur pour CTO quotidien

**Livrables:**
- [ ] Implémentation `planner`
- [ ] Implémentation `analyse`
- [ ] Implémentation `thinkdeep`
- [ ] State manager avec Redis
- [ ] Rate limiting et retry logic
- [ ] Cost tracking basique
- [ ] Tests d'intégration tools
- [ ] Documentation usage tools

**Validation:** Utiliser SCOUT pour planifier un vrai projet client, analyser une codebase existante.

#### Phase 3: Tools Avancés (Semaine 5-6)
**Objectif:** Compléter suite d'outils avec consensus et validation

**Livrables:**
- [ ] Implémentation `consensus`
- [ ] Implémentation `challenge`
- [ ] Implémentation `secaudit`
- [ ] Implémentation `refactor`
- [ ] Implémentation `clink`
- [ ] Validation multi-modèles fonctionnelle
- [ ] Amélioration team selector (adaptive)
- [ ] Dashboard coûts et usage

**Validation:** Tester `consensus` sur décision technique réelle, `secaudit` sur projet existant.

#### Phase 4: Intégration Notion (Semaine 7)
**Objectif:** Sauvegarde automatique recherches et rapports dans Notion

**Livrables:**
- [ ] Notion provider integration
- [ ] Auto-save analyse/secaudit vers Notion
- [ ] Templates Notion par type de livrable
- [ ] Linking entre recherches
- [ ] Documentation workflow Notion

**Validation:** Exécuter analyse complète qui auto-save dans Notion avec structure correcte.

#### Phase 5: Polish et Production (Semaine 8)
**Objectif:** Prêt pour usage quotidien production

**Livrables:**
- [ ] Error handling robuste partout
- [ ] Logging structured pour debugging
- [ ] Config validation complète au démarrage
- [ ] Health check endpoint
- [ ] Docker container
- [ ] CI/CD pipeline
- [ ] Documentation complète (architecture + usage)
- [ ] Vidéo demo

**Validation:** Déployer en production, utiliser pendant 1 semaine sans issues bloquants.

### 7.2 Critères de Succès

**Mesures Quantitatives:**
- Temps moyen recherche environnement client: < 30 min (vs 2h actuellement)
- Temps génération plan directeur: < 15 min (vs 1h actuellement)
- Uptime serveur MCP: > 99%
- Coût moyen par requête: < $0.50 USD
- Latence réponse P95: < 60 secondes

**Mesures Qualitatives:**
- Christian utilise SCOUT quotidiennement (5+ fois/jour)
- Zéro frustration majeure lors de l'usage
- Confiance dans les recommandations: "je révise mais ne refais pas"
- Facilité d'ajout d'un nouveau provider AI: < 2h de dev
- Facilité d'ajout d'un nouveau tool: < 4h de dev

### 7.3 Risques et Mitigation

| Risque | Impact | Probabilité | Mitigation |
|--------|---------|-------------|-----------|
| API costs explosent | High | Medium | Implement strict rate limits, budgets alerts, coût tracking par requête |
| Nouveau modèle AI incompatible avec abstraction | Medium | Low | Design provider interface suffisamment flexible, prévoir adapter pattern |
| MCP protocol change breaking | High | Low | Pin version MCP SDK, watch changelog, tests automated |
| Redis unavailable casse tout | High | Medium | Fallback gracieux vers file-based state, health checks |
| Qualité réponses AI insuffisante | High | Medium | Validation multi-modèles pour décisions critiques, tune prompts |
| Notion API rate limits | Medium | Medium | Implement local queue, batch writes, respect 3 req/sec |

---

## 8. Documentation et Maintenance

### 8.1 Documentation Requise

**Pour Utilisateurs (Christian + futurs associés):**
- README: Installation, configuration, premiers pas
- Guide usage par tool avec exemples concrets
- Best practices: quand utiliser quelle équipe
- Troubleshooting commun
- FAQ

**Pour Développeurs (extending SCOUT):**
- Architecture overview avec diagrammes
- Guide ajout provider AI (avec exemple complet)
- Guide ajout tool (avec template)
- Guide modification équipes
- API reference des classes core
- Testing strategy

### 8.2 Plan de Maintenance

**Mensuel:**
- Review costs et optimiser si nécessaire
- Update providers AI vers derniers modèles
- Review et améliorer prompts selon feedback
- Backup configuration et state

**Trimestriel:**
- Évaluation nouveaux providers AI (Mistral, Cohere, etc.)
- Refactoring code si patterns émergent
- Update dependencies
- Review sécurité (secrets rotation)

**Ad-hoc:**
- Hot fixes pour bugs bloquants
- Ajout outils selon nouveaux besoins clients
- Intégration nouvelles sources données

---

## 9. Annexes

### 9.1 Exemple de Configuration Complète

Voir fichier `config/scout.yaml` en section 3.1

### 9.2 Exemple d'Usage End-to-End

**Scénario:** Christian prépare une intervention chez un client manufacturier

**1. Reconnaissance environnement:**
```
User: "SCOUT, recherche l'environnement d'affaires du secteur manufacturier aérospatial au Québec - focus sur stack techno et défis ERP"

Claude utilise SCOUT tool "market_research" (pas encore implémenté dans Phase 1, mais exemple du futur)
→ SCOUT génère rapport dans Notion
→ Retourne: "Rapport complet: [lien Notion]"
```

**2. Planification intervention:**
```
User: "Planner un mandat d'audit cybersécurité pour une PME manufacturière avec 200 employés, focus ICS/SCADA"

Claude utilise SCOUT tool "planner" avec team "architect"
→ SCOUT génère plan 5 phases avec estimations
→ Retourne: Plan markdown + notion_url
```

**3. Analyse code existant client (partagé en avance):**
```
User: "Analyse cette codebase [upload fichiers]. Focus sécurité et dette technique"

Claude utilise SCOUT tool "secaudit" avec team "expert"
→ 3 modèles auditent en parallèle
→ Consensus sur vulnérabilités critiques
→ Rapport détaillé avec priorités
→ Auto-save Notion
```

**4. Challenge de leur approche actuelle:**
```
User: "Ils veulent migrer vers SAP. Challenge cette décision."

Claude utilise SCOUT tool "challenge" avec team "expert"
→ Débat multi-modèles sur SAP vs alternatives
→ Identification risques et alternatives
→ Recommandation nuancée
```

**Total time:** ~45 minutes vs 4-5h manuellement

### 9.3 Évolutions Futures (Post-v1.0)

**Phase 6 - Intelligence Collective:**
- Learning from feedback: SCOUT apprend des corrections de Christian
- Patterns detection: Identifie patterns récurrents dans mandats
- Auto-suggest: "Ce client ressemble à X, voici ce qui avait fonctionné"

**Phase 7 - Productisation:**
- Multi-tenant support pour associés
- Fine-tuning modèles sur livrables historiques
- API externe pour clients PME (facturation)
- Interface web dédiée (pas que via Claude)

**Phase 8 - Écosystème:**
- Marketplace de tools communautaires
- Intégration CRM (Pipedrive, HubSpot)
- Intégration facturation (FreshBooks)
- Slack bot pour queries rapides

---

## 10. Approbation et Next Steps

**Décision Requise:**
- [ ] Approuver scope Phase 1
- [ ] Confirmer budget API ($200/mois estimé Phase 1)
- [ ] Valider timeline 8 semaines
- [ ] Décider: self-dev ou contracter partie de dev ?

**Actions Immédiates:**
1. Setup repo GitHub "scout-mcp-server"
2. Créer .env.example avec toutes les vars requises
3. Obtenir API keys: Gemini, OpenAI, (Anthropic optionnel Phase 1)
4. Setup Redis local ou cloud (Upstash free tier OK pour démarrage)
5. Créer workspace Notion dédié avec databases research

**Contact:**
Christian Boulet - christian@bouletstrategies.com

---

**Version:** 1.0
**Dernière mise à jour:** 18 octobre 2025
**Prochaine review:** Fin Phase 1 (semaine 2)
