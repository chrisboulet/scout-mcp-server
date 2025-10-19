"""
Test script for Consensus Builder Tool.

Tests multi-provider consensus building with real AI providers.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from scout.server import ScoutMCPServer


async def test_consensus_builder():
    """Test consensus building across multiple providers."""
    print("=" * 70)
    print("🤝 SCOUT Consensus Builder - Test")
    print("=" * 70)
    print()

    # Load environment variables
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"📁 Variables chargées depuis: {env_path}\n")
    else:
        print("⚠️  Fichier .env non trouvé\n")

    # Initialize server
    print("📦 Initializing server...")
    server = ScoutMCPServer()
    await server.initialize()

    # Check if consensus_builder tool is registered
    tool_names = server.tool_registry.list_tools(include_deprecated=False)
    print(f"   📦 {len(tool_names)} tools discovered: {', '.join(tool_names)}")

    if "consensus_builder" not in tool_names:
        print("❌ Consensus Builder tool not found!")
        await server.cleanup()
        return

    print("✅ Server initialized!")
    print()

    # Test 1: Business Decision
    print("=" * 70)
    print("📊 Test 1: Business Decision Consensus")
    print("=" * 70)

    question1 = "Should our SaaS startup prioritize building mobile apps or focus exclusively on web for the first year?"
    context1 = """
Company: Early-stage B2B SaaS startup
Team: 5 developers, 2 designers
Budget: $500K runway
Current: Web MVP with 50 beta customers
Market: 70% of target users access via desktop, 30% mobile
Competitors: Most have both web and mobile apps
"""

    result1 = await server.execute_tool(
        "consensus_builder",
        {
            "question": question1,
            "context": context1,
            "require_unanimity": False,
            "tie_breaking": True,
            "min_confidence": "medium"
        }
    )

    print()
    print(f"✨ Consensus Statement:")
    print(f"{result1['consensus_statement'][:500]}...")
    print()
    print(f"📊 Consensus Details:")
    print(f"   Confidence: {result1['confidence_level']}")
    print(f"   Providers: {', '.join(result1['providers_consulted'])}")
    print(f"   Agreements: {len(result1['agreements'])}")
    print(f"   Disagreements: {len(result1['disagreements'])}")
    print(f"   Diversity: {result1['diversity_score']}")
    print(f"   Duration: {result1['duration_seconds']:.2f}s")
    print(f"   Tokens: {result1['total_tokens_used']:,}")
    print()

    if result1['agreements']:
        print(f"✅ Key Agreements ({len(result1['agreements'])}):")
        for i, agreement in enumerate(result1['agreements'][:3], 1):
            supporters = ', '.join(agreement['supporting_providers'])
            print(f"   {i}. {agreement['statement'][:80]}...")
            print(f"      └─ Supported by: {supporters}")
        print()

    if result1['disagreements']:
        print(f"⚠️  Disagreements ({len(result1['disagreements'])}):")
        for i, disagreement in enumerate(result1['disagreements'][:3], 1):
            print(f"   {i}. {disagreement['topic']} ({disagreement['significance']})")
            if disagreement['resolution_suggestion']:
                print(f"      └─ Resolution: {disagreement['resolution_suggestion']}")
        print()

    if result1['recommendations']:
        print(f"💡 Recommendations ({len(result1['recommendations'])}):")
        for i, rec in enumerate(result1['recommendations'], 1):
            print(f"   {i}. {rec}")
        print()

    # Test 2: Technical Decision
    print("=" * 70)
    print("📊 Test 2: Technical Architecture Consensus")
    print("=" * 70)

    question2 = "For a real-time collaboration app, should we use WebSockets or Server-Sent Events (SSE)?"
    context2 = """
App: Real-time document collaboration (like Google Docs)
Scale: 100K concurrent users expected
Features: Cursor tracking, live edits, presence indicators
Team expertise: Strong in Node.js, moderate in WebSocket libraries
Infrastructure: AWS with load balancers
Latency requirement: <100ms for updates
Browser support: Modern browsers only (Chrome, Firefox, Safari)
"""

    result2 = await server.execute_tool(
        "consensus_builder",
        {
            "question": question2,
            "context": context2,
            "providers_to_query": ["gemini", "openai"],  # Test with subset
            "require_unanimity": False,
            "tie_breaking": False,
            "min_confidence": "high"
        }
    )

    print()
    print(f"✨ Consensus Statement:")
    print(f"{result2['consensus_statement'][:500]}...")
    print()
    print(f"📊 Consensus Details:")
    print(f"   Confidence: {result2['confidence_level']}")
    print(f"   Providers: {', '.join(result2['providers_consulted'])}")
    print(f"   Agreements: {len(result2['agreements'])}")
    print(f"   Disagreements: {len(result2['disagreements'])}")
    print(f"   Diversity: {result2['diversity_score']}")
    print(f"   Duration: {result2['duration_seconds']:.2f}s")
    print(f"   Tokens: {result2['total_tokens_used']:,}")
    print()

    # Cleanup
    await server.cleanup()

    print("=" * 70)
    print("✅ Test completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_consensus_builder())
