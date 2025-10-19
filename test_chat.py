#!/usr/bin/env python3
"""Test simple du Chat Tool SCOUT."""

import asyncio
from pathlib import Path
from dotenv import load_dotenv
from scout.server import ScoutMCPServer

# Charger les variables d'environnement depuis .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)
print(f"📁 Variables chargées depuis: {env_path}")

async def test_chat():
    """Test de chat simple avec conversation multi-tour."""
    print("\n" + "=" * 60)
    print("🚀 SCOUT Chat Tool - Test")
    print("=" * 60)

    # Initialiser le serveur (sans MCP pour éviter le bug **kwargs)
    print("\n📦 Initialisation du serveur...")
    try:
        server = ScoutMCPServer(config_path="config.yaml")
        # Initialisation manuelle pour éviter l'enregistrement MCP
        server._initialized = False

        # Créer les providers
        from scout.providers.factory import ProviderFactory
        server.providers = ProviderFactory.create_all_providers(server.config)

        # Initialiser chaque provider
        for name, provider in server.providers.items():
            await provider.initialize()

        # Découvrir et enregistrer les tools
        from pathlib import Path
        tools_dir = Path(__file__).parent / "src" / "scout" / "tools"
        if tools_dir.exists():
            discovered = server.tool_registry.discover_tools(tools_dir)
            print(f"   📦 {len(discovered)} tools découverts: {', '.join(discovered)}")

        # Initialiser State Manager (optionnel)
        try:
            import os
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            from scout.core.state_manager import StateManager
            server.state_manager = StateManager(
                redis_url=redis_url,
                default_ttl_seconds=server.config.system.cache_ttl_seconds
            )
            print("   ✅ State Manager connecté (Redis actif)")
        except Exception:
            server.state_manager = None
            print("   ⚠️  State Manager non disponible (Redis absent - pas de persistance)")

        server._initialized = True
        print("✅ Serveur initialisé!")
    except Exception as e:
        print(f"❌ Erreur d'initialisation: {e}")
        import traceback
        traceback.print_exc()
        raise

    # Premier message
    print("\n💬 Premier message...")
    result = await server.execute_tool(
        "chat",
        {"message": "Explique-moi les microservices en 3 phrases"}
    )

    print(f"\n🤖 Réponse:")
    print(f"   {result['response']}")
    print(f"\n📊 Métadonnées:")
    print(f"   Session ID: {result['session_id']}")
    print(f"   Team: {result['team_used']}")
    print(f"   Provider: {result['provider_used']}")
    print(f"   Model: {result['model_used']}")
    print(f"   Tokens: {result['metadata']['total_tokens']}")
    print(f"   Coût: ${result['metadata']['cost_usd']:.6f} USD")

    # Continuer la conversation (même session)
    print("\n💬 Suite de la conversation...")
    result2 = await server.execute_tool(
        "chat",
        {
            "message": "Donne-moi un exemple concret d'entreprise",
            "session_id": result["session_id"]  # Même session!
        }
    )

    print(f"\n🤖 Réponse (suite):")
    print(f"   {result2['response']}")
    print(f"\n📊 Métadonnées:")
    print(f"   Tokens: {result2['metadata']['total_tokens']}")
    print(f"   Coût: ${result2['metadata']['cost_usd']:.6f} USD")

    await server.cleanup()
    print("\n✅ Test terminé avec succès!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_chat())
