#!/usr/bin/env python3
"""Test Strategic Planner Tool."""

import asyncio
from pathlib import Path
from dotenv import load_dotenv
from scout.server import ScoutMCPServer
from scout.providers.factory import ProviderFactory

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)
print(f"📁 Variables chargées depuis: {env_path}\n")


async def test_strategic_planner():
    """Test strategic planning capabilities."""
    print("=" * 70)
    print("📋 SCOUT Strategic Planner - Test")
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

    server._initialized = True
    print("✅ Server initialized!\n")

    # Test: Cloud Migration Planning
    print("=" * 70)
    print("📊 Test: Cloud Migration Strategic Plan")
    print("=" * 70)

    result = await server.execute_tool(
        "strategic_planner",
        {
            "objective": "Migrate on-premise infrastructure to AWS cloud",
            "context": "Current: 50 VMs, PostgreSQL databases, file storage. Budget: $200K, Timeline: 9 months, Cannot afford downtime",
            "max_iterations": 3,
            "focus_areas": ["timeline", "budget", "risks", "migration-strategy"]
        }
    )

    print(f"\n✨ Summary:")
    print(f"   {result['summary']}")

    print(f"\n📊 Plan Details:")
    print(f"   Status: {result['status'].value}")
    print(f"   Total Steps: {len(result['plan_steps'])}")
    print(f"   Iterations: {result['metadata']['iterations_performed']}")
    print(f"   Duration: {result['metadata']['duration_seconds']:.2f}s")
    print(f"   Tokens: {result['metadata']['total_tokens']}")

    print(f"\n📅 Timeline: {result['timeline_overview']}")
    print(f"💰 Budget: {result['budget_overview']}")

    print(f"\n🎯 Plan Steps:")
    for step in result['plan_steps'][:5]:  # Show first 5
        print(f"\n   Step {step.step_number}: {step.title}")
        print(f"   └─ {step.description[:150]}...")
        if step.estimated_duration:
            print(f"   └─ Duration: {step.estimated_duration}")
        if step.estimated_cost:
            print(f"   └─ Cost: {step.estimated_cost}")
        if step.risks:
            print(f"   └─ Risks: {len(step.risks)} identified")

    if result['critical_path']:
        print(f"\n🚨 Critical Path: Steps {result['critical_path']}")

    if result['key_risks']:
        print(f"\n⚠️  Key Risks ({len(result['key_risks'])}):")
        for i, risk in enumerate(result['key_risks'][:3], 1):
            print(f"   {i}. {risk}")

    if result['recommendations']:
        print(f"\n💡 Recommendations ({len(result['recommendations'])}):")
        for i, rec in enumerate(result['recommendations'], 1):
            print(f"   {i}. {rec}")

    print(f"\n📝 Planning Iterations:")
    for iteration in result['iterations']:
        print(f"\n   Iteration {iteration.iteration_number}: {iteration.focus}")
        print(f"   └─ Changes: {', '.join(iteration.changes_made[:2])}")
        print(f"   └─ Rationale: {iteration.rationale[:100]}...")

    await server.cleanup()

    print("\n" + "=" * 70)
    print("✅ Test completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_strategic_planner())
