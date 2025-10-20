# 🐳 SCOUT - Guide de Déploiement Docker

Guide complet pour déployer SCOUT MCP Server avec Docker et Docker Compose.

## 📋 Table des Matières

1. [Prérequis](#prérequis)
2. [Installation Rapide](#installation-rapide)
3. [Configuration](#configuration)
4. [Démarrage](#démarrage)
5. [Vérification](#vérification)
6. [Commandes Utiles](#commandes-utiles)
7. [Troubleshooting](#troubleshooting)
8. [Production](#production)

---

## Prérequis

### Logiciels Requis

- **Docker**: Version 20.10+ ([Installation](https://docs.docker.com/get-docker/))
- **Docker Compose**: Version 2.0+ (inclus avec Docker Desktop)

### Vérification

```bash
docker --version          # Docker version 20.10.x ou supérieur
docker-compose --version  # Docker Compose version 2.x ou supérieur
```

### Clés API Requises

Au minimum, configurez **1 provider AI** parmi:

- **Google Gemini** (recommandé pour démarrer) → https://makersuite.google.com/app/apikey
- **OpenAI GPT** → https://platform.openai.com/api-keys
- **Anthropic Claude** → https://console.anthropic.com/settings/keys
- **OpenRouter** → https://openrouter.ai/keys
- **Grok / X.AI** → https://console.x.ai/

---

## Installation Rapide

### Étape 1: Cloner le Projet

```bash
git clone https://github.com/cboulanger/scout.git
cd scout
```

### Étape 2: Configuration Environnement

```bash
# Copier le template
cp .env.example .env

# Éditer avec vos clés API
nano .env  # ou vim, code, notepad, etc.
```

**Minimum requis dans `.env`:**

```bash
# Au moins UN provider (Gemini recommandé pour commencer)
GEMINI_API_KEY=AIza...

# Redis (déjà configuré pour Docker)
REDIS_HOST=redis
REDIS_PORT=6379

# Environnement
SCOUT_ENV=production
LOG_LEVEL=INFO
```

### Étape 3: Démarrer SCOUT

```bash
# Construire et démarrer tous les services
docker-compose up -d

# Voir les logs en temps réel
docker-compose logs -f scout
```

✅ **SCOUT est maintenant en cours d'exécution!**

---

## Configuration

### Structure des Services

SCOUT utilise 2 services Docker:

| Service | Description | Port |
|---------|-------------|------|
| **scout** | MCP Server principal | 3000 |
| **redis** | Base de données d'état | 6379 |

### Variables d'Environnement Importantes

#### Providers AI

```bash
# Google Gemini (Flash 2.0)
GEMINI_API_KEY=AIza...

# OpenAI (GPT-4)
OPENAI_API_KEY=sk-proj-...

# Anthropic (Claude 3.5)
ANTHROPIC_API_KEY=sk-ant-...

# OpenRouter (multi-modèle)
OPENROUTER_API_KEY=sk-or-v1-...

# X.AI (Grok)
GROK_API_KEY=xai-...
```

#### Infrastructure

```bash
# Redis (automatique avec Docker Compose)
REDIS_HOST=redis       # Nom du service Docker
REDIS_PORT=6379
REDIS_PASSWORD=        # Vide par défaut

# Environnement
SCOUT_ENV=production   # ou development
LOG_LEVEL=INFO         # DEBUG, INFO, WARNING, ERROR
```

#### Limites & Performance

```bash
# Concurrence
MAX_CONCURRENT_TOOLS=100

# Timeouts
REQUEST_TIMEOUT=300

# Rate limiting
MAX_REQUESTS_PER_HOUR_PER_USER=100
```

### Fichier `docker-compose.yml`

Le fichier par défaut est optimisé pour la production. Pour le personnaliser:

```yaml
# Modifier les limites de ressources
services:
  scout:
    deploy:
      resources:
        limits:
          cpus: '4.0'      # Augmenter pour plus de performance
          memory: 4G
```

---

## Démarrage

### Démarrage Standard

```bash
# Démarrer en arrière-plan
docker-compose up -d

# Voir les logs
docker-compose logs -f

# Arrêter
docker-compose down
```

### Démarrage avec Rebuild

Si vous avez modifié le code:

```bash
# Rebuild et redémarrer
docker-compose up -d --build

# Forcer un rebuild complet
docker-compose build --no-cache
docker-compose up -d
```

### Démarrage Sélectif

```bash
# Démarrer uniquement Redis
docker-compose up -d redis

# Démarrer uniquement SCOUT
docker-compose up -d scout
```

---

## Vérification

### Health Check

```bash
# Vérifier le statut des containers
docker-compose ps

# Exécuter le health check SCOUT
docker-compose exec scout python -m scout.main --health-check
```

**Sortie attendue:**

```
=== SCOUT MCP Server Health Check ===

Server Status: healthy
Version: 0.1.0

Tools: 5/5 available

Providers:
  ✓ gemini: healthy
  ✓ openai: healthy
  ✓ anthropic: healthy

✅ All systems operational
```

### Vérifier les Logs

```bash
# Logs SCOUT
docker-compose logs -f scout

# Logs Redis
docker-compose logs -f redis

# Dernières 100 lignes
docker-compose logs --tail=100 scout
```

### Tester une Requête

```bash
# Entrer dans le container
docker-compose exec scout bash

# Tester un outil (exemple: Chat)
python -c "
import asyncio
import sys
sys.path.insert(0, '/app/src')
from scout.server import ScoutMCPServer

async def test():
    server = ScoutMCPServer()
    await server.initialize()
    result = await server.execute_tool('chat', {
        'message': 'Hello SCOUT!',
        'team': 'speed'
    })
    print(result)

asyncio.run(test())
"
```

---

## Commandes Utiles

### Gestion des Containers

```bash
# Démarrer
docker-compose up -d

# Arrêter
docker-compose down

# Redémarrer
docker-compose restart

# Reconstruire
docker-compose up -d --build

# Voir le statut
docker-compose ps

# Voir les ressources utilisées
docker stats scout-mcp scout-redis
```

### Logs & Debug

```bash
# Logs en temps réel
docker-compose logs -f

# Logs spécifique
docker-compose logs -f scout
docker-compose logs -f redis

# Dernières N lignes
docker-compose logs --tail=50 scout

# Logs depuis un timestamp
docker-compose logs --since 2025-01-19T10:00:00 scout
```

### Accès Shell

```bash
# Shell dans SCOUT
docker-compose exec scout bash

# Shell dans Redis
docker-compose exec redis sh

# Exécuter une commande ponctuelle
docker-compose exec scout python -m scout.main --version
```

### Nettoyage

```bash
# Arrêter et supprimer les containers
docker-compose down

# Supprimer aussi les volumes (⚠️ PERTE DE DONNÉES)
docker-compose down -v

# Nettoyer les images inutilisées
docker image prune -f

# Nettoyage complet (⚠️ DANGEREUX)
docker system prune -a --volumes
```

---

## Troubleshooting

### Problème: Container ne démarre pas

**Symptômes:**
```bash
docker-compose ps
# scout-mcp   Exit 1
```

**Solution:**
```bash
# Voir les logs d'erreur
docker-compose logs scout

# Vérifier la configuration
docker-compose config

# Vérifier les variables d'environnement
docker-compose exec scout env | grep -E "(GEMINI|OPENAI|REDIS)"
```

### Problème: Redis inaccessible

**Symptômes:**
```
ConnectionError: Error connecting to Redis
```

**Solutions:**
```bash
# 1. Vérifier que Redis tourne
docker-compose ps redis

# 2. Vérifier les logs Redis
docker-compose logs redis

# 3. Tester la connexion
docker-compose exec redis redis-cli ping
# Doit retourner: PONG

# 4. Redémarrer Redis
docker-compose restart redis
```

### Problème: API Key invalide

**Symptômes:**
```
AuthenticationError: Invalid API key
```

**Solutions:**
```bash
# 1. Vérifier que .env existe et contient les clés
cat .env | grep API_KEY

# 2. Recharger les variables d'environnement
docker-compose down
docker-compose up -d

# 3. Vérifier dans le container
docker-compose exec scout env | grep GEMINI_API_KEY
```

### Problème: Out of Memory

**Symptômes:**
```
Container killed (OOMKilled)
```

**Solutions:**
```bash
# 1. Augmenter les limites dans docker-compose.yml
services:
  scout:
    deploy:
      resources:
        limits:
          memory: 4G  # Augmenter de 2G à 4G

# 2. Vérifier la mémoire utilisée
docker stats scout-mcp

# 3. Redémarrer avec nouvelles limites
docker-compose up -d
```

### Problème: Port déjà utilisé

**Symptômes:**
```
Error: port 3000 is already in use
```

**Solutions:**
```bash
# 1. Trouver le processus utilisant le port
lsof -i :3000  # Linux/Mac
netstat -ano | findstr :3000  # Windows

# 2. Changer le port dans docker-compose.yml
services:
  scout:
    ports:
      - "3001:3000"  # Utiliser 3001 au lieu de 3000

# 3. Redémarrer
docker-compose up -d
```

---

## Production

### Checklist de Sécurité

- [ ] Changer le mot de passe Redis (config/redis.conf)
- [ ] Utiliser des secrets Docker pour les API keys
- [ ] Activer HTTPS/TLS
- [ ] Configurer un firewall
- [ ] Limiter l'exposition des ports
- [ ] Activer les logs d'audit
- [ ] Configurer la rotation des logs

### Configuration Redis Sécurisée

```bash
# Éditer config/redis.conf
requirepass your_super_secure_password_here

# Mettre à jour .env
REDIS_PASSWORD=your_super_secure_password_here
REDIS_URL=redis://default:your_super_secure_password_here@redis:6379

# Redémarrer
docker-compose down
docker-compose up -d
```

### Monitoring

```bash
# Activer les métriques
ENABLE_METRICS=true
ENABLE_TRACING=true

# Configurer OpenTelemetry (optionnel)
OTEL_EXPORTER_OTLP_ENDPOINT=http://your-collector:4318
```

### Backups

```bash
# Backup Redis data
docker-compose exec redis redis-cli BGSAVE
docker cp scout-redis:/data/dump.rdb ./backups/redis-$(date +%Y%m%d).rdb

# Backup automatique (cron)
0 2 * * * docker-compose exec redis redis-cli BGSAVE && \
  docker cp scout-redis:/data/dump.rdb /backups/redis-$(date +\%Y\%m\%d).rdb
```

### Mise à Jour

```bash
# 1. Sauvegarder les données
docker-compose exec redis redis-cli BGSAVE

# 2. Pull la nouvelle version
git pull origin master

# 3. Rebuild
docker-compose up -d --build

# 4. Vérifier
docker-compose exec scout python -m scout.main --health-check
```

### Performance Tuning

```yaml
# docker-compose.yml
services:
  scout:
    deploy:
      resources:
        limits:
          cpus: '4.0'      # Ajuster selon charge
          memory: 4G
    environment:
      - MAX_CONCURRENT_TOOLS=200  # Augmenter pour haute charge
      - REQUEST_TIMEOUT=600       # Augmenter si timeouts fréquents
```

---

## Support

### Ressources

- 📚 **Documentation**: [README.md](README.md)
- 🛠️ **Outils Consultant**: [docs/tools/consultant-tools.md](docs/tools/consultant-tools.md)
- 📊 **Statistiques**: [STATISTICS.md](STATISTICS.md)
- 🐛 **Issues**: https://github.com/cboulanger/scout/issues

### Logs de Debug

```bash
# Activer le mode debug
docker-compose down
echo "LOG_LEVEL=DEBUG" >> .env
docker-compose up -d

# Suivre les logs détaillés
docker-compose logs -f scout
```

---

## Conclusion

SCOUT est maintenant déployé avec Docker! 🚀

**Prochaines étapes:**

1. ✅ Tester les 5 outils via MCP client
2. ✅ Configurer tous vos providers AI
3. ✅ Ajuster les limites de ressources si nécessaire
4. ✅ Configurer les backups Redis
5. ✅ Activer le monitoring (optionnel)

**Questions?** Ouvrez une issue sur GitHub!

---

*Copyright 2025 Christian Boulet / Boulet Stratégies TI*
*Licence: Apache 2.0*
