#!/usr/bin/env python3
"""Test Deep Analyst Tool."""

import asyncio
from pathlib import Path
from dotenv import load_dotenv
from scout.server import ScoutMCPServer
from scout.providers.factory import ProviderFactory

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)
print(f"📁 Variables chargées depuis: {env_path}\n")


async def test_deep_analyst():
    """Test deep investigation capabilities."""
    print("=" * 70)
    print("🔍 SCOUT Deep Analyst - Test")
    print("=" * 70)

    # Initialize server
    print("\n📦 Initializing server...")
    server = ScoutMCPServer(config_path="config.yaml")
    server._initialized = False

    # Create providers
    server.providers = ProviderFactory.create_all_providers(server.config)
    for name, provider in server.providers.items():
        await provider.initialize()

    # Discover tools
    tools_dir = Path(__file__).parent / "src" / "scout" / "tools"
    if tools_dir.exists():
        discovered = server.tool_registry.discover_tools(tools_dir)
        print(f"   📦 {len(discovered)} tools discovered")

    # Initialize State Manager (optional)
    try:
        import os
        from scout.core.state_manager import StateManager
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        server.state_manager = StateManager(
            redis_url=redis_url,
            default_ttl_seconds=server.config.system.cache_ttl_seconds
        )
        print("   ✅ State Manager connected")
    except:
        server.state_manager = None
        print("   ⚠️  State Manager not available")

    server._initialized = True
    print("✅ Server initialized!\n")

    # Test 1: Technical problem investigation
    print("=" * 70)
    print("📊 Test 1: Technical Problem Investigation")
    print("=" * 70)

    result1 = await server.execute_tool(
        "deep_analyst",
        {
            "problem": "Our API response time degraded from 100ms to 2000ms",
            "context": "Monolithic application, PostgreSQL database, 10K daily users. Degradation started 2 weeks ago.",
            "max_steps": 4,
            "require_high_confidence": True
        }
    )

    print(f"\n✨ Summary: {result1['summary']}")
    print(f"\n📊 Investigation Details:")
    print(f"   Steps Taken: {result1['metadata']['steps_taken']}")
    print(f"   Final Confidence: {result1['confidence'].value}")
    print(f"   Duration: {result1['metadata']['duration_seconds']:.2f}s")
    print(f"   Total Tokens: {result1['metadata']['total_tokens']}")

    print(f"\n🎯 Final Conclusion:")
    print(f"   {result1['final_conclusion'][:500]}...")

    if result1['key_insights']:
        print(f"\n💡 Key Insights ({len(result1['key_insights'])}):")
        for i, insight in enumerate(result1['key_insights'][:3], 1):
            print(f"   {i}. {insight}")

    if result1['recommendations']:
        print(f"\n📋 Recommendations ({len(result1['recommendations'])}):")
        for i, rec in enumerate(result1['recommendations'][:3], 1):
            print(f"   {i}. {rec}")

    # Show investigation steps
    print(f"\n🔬 Investigation Steps:")
    for step in result1['steps']:
        print(f"\n   Step {step.step_number} [{step.confidence.value}]:")
        print(f"   Hypothesis: {step.hypothesis}")
        print(f"   Findings: {step.findings[:200]}...")
        if step.evidence:
            print(f"   Evidence: {len(step.evidence)} points collected")

    # Test 2: Business decision investigation
    print("\n" + "=" * 70)
    print("📊 Test 2: Business Decision Investigation")
    print("=" * 70)

    result2 = await server.execute_tool(
        "deep_analyst",
        {
            "problem": "Should we migrate from monolith to microservices?",
            "context": "500K LOC monolith, 20 developers, PostgreSQL, growing quickly",
            "max_steps": 5,
            "require_high_confidence": False
        }
    )

    print(f"\n✨ Summary: {result2['summary']}")
    print(f"\n📊 Investigation Details:")
    print(f"   Steps Taken: {result2['metadata']['steps_taken']}")
    print(f"   Final Confidence: {result2['confidence'].value}")

    print(f"\n🎯 Final Conclusion:")
    print(f"   {result2['final_conclusion'][:500]}...")

    if result2['recommendations']:
        print(f"\n📋 Recommendations:")
        for i, rec in enumerate(result2['recommendations'][:5], 1):
            print(f"   {i}. {rec}")

    await server.cleanup()

    print("\n" + "=" * 70)
    print("✅ All tests completed!")
    print("=" * 70)

    # Summary
    print("\n📊 Test Summary:")
    print(f"   Test 1: {result1['metadata']['steps_taken']} steps, {result1['confidence'].value} confidence")
    print(f"   Test 2: {result2['metadata']['steps_taken']} steps, {result2['confidence'].value} confidence")


if __name__ == "__main__":
    asyncio.run(test_deep_analyst())
