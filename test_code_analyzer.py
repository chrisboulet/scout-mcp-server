#!/usr/bin/env python3
"""Test script for Code Analyzer Tool."""

import asyncio
from pathlib import Path
from dotenv import load_dotenv
from scout.server import ScoutMCPServer
from scout.providers.factory import ProviderFactory

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)
print(f"📁 Variables chargées depuis: {env_path}\n")


# Test code samples
GOOD_CODE = '''
def calculate_average(numbers):
    """Calculate the average of a list of numbers.

    Args:
        numbers: List of numeric values

    Returns:
        float: The average value
    """
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)


class DataProcessor:
    """Process and analyze data."""

    def __init__(self, data):
        self.data = data

    def process(self):
        """Process the data."""
        return [self.calculate_average(chunk) for chunk in self.data]

    def calculate_average(self, numbers):
        """Calculate average for a chunk."""
        return sum(numbers) / len(numbers) if numbers else 0.0
'''

BAD_CODE = '''
password = "hardcoded123"
api_key = 'secret-key-12345'

def process(user_input):
    # Security issue: eval
    result = eval(user_input)

    # Performance issue: nested loops
    for i in range(1000):
        for j in range(1000):
            x = i * j

    # SQL injection risk
    query = "SELECT * FROM users WHERE id = %s" % user_input
    cursor.execute(query)

    return result

def function_with_high_complexity(a,b,c,d,e,f,g):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        if f:
                            if g:
                                return "too complex"
    return "ok"
'''

SIMPLE_CODE = '''
def hello_world():
    print("Hello, World!")

hello_world()
'''


async def test_code_analyzer():
    """Test code analyzer with various code samples."""
    print("=" * 70)
    print("🔍 SCOUT Code Analyzer - Test Suite")
    print("=" * 70)

    # Initialize server
    print("\n📦 Initializing server...")
    server = ScoutMCPServer(config_path="config.yaml")

    # Manual initialization (avoid MCP **kwargs bug)
    server.providers = ProviderFactory.create_all_providers(server.config)
    for name, provider in server.providers.items():
        await provider.initialize()

    # Discover tools
    from pathlib import Path
    tools_dir = Path(__file__).parent / "src" / "scout" / "tools"
    if tools_dir.exists():
        discovered = server.tool_registry.discover_tools(tools_dir)
        print(f"   📦 {len(discovered)} tools discovered: {', '.join(discovered)}")

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

    # Test 1: Good code (should have high score)
    print("=" * 70)
    print("📊 Test 1: Well-written code (high quality expected)")
    print("=" * 70)

    result1 = await server.execute_tool(
        "code_analyzer",
        {
            "code": GOOD_CODE,
            "language": "python",
            "analysis_type": "comprehensive",
            "use_ai": True  # Request AI insights
        }
    )

    print(f"\n✨ Summary: {result1['summary']}")
    print(f"\n📈 Metrics:")
    print(f"   LOC: {result1['metrics'].lines_of_code}")
    print(f"   Functions: {result1['metrics'].functions_count}")
    print(f"   Classes: {result1['metrics'].classes_count}")
    print(f"   Complexity: {result1['metrics'].cyclomatic_complexity}")
    print(f"   Maintainability: {result1['metrics'].maintainability_index:.1f}/100")
    print(f"\n🎯 Quality Score: {result1['quality_score']}/100")
    print(f"🐛 Issues Found: {len(result1['issues'])}")

    if result1['issues']:
        print("\n⚠️  Issues:")
        for issue in result1['issues'][:3]:  # Show first 3
            print(f"   [{issue.severity.upper()}] {issue.message}")
            if issue.suggestion:
                print(f"      💡 {issue.suggestion}")

    if result1.get('ai_insights'):
        print(f"\n🤖 AI Insights:")
        insights = result1['ai_insights'][:500]  # First 500 chars
        print(f"   {insights}...")

    # Test 2: Bad code (should have low score and many issues)
    print("\n" + "=" * 70)
    print("📊 Test 2: Problematic code (low quality expected)")
    print("=" * 70)

    result2 = await server.execute_tool(
        "code_analyzer",
        {
            "code": BAD_CODE,
            "language": "python",
            "analysis_type": "comprehensive",
            "use_ai": False  # Skip AI for faster test
        }
    )

    print(f"\n✨ Summary: {result2['summary']}")
    print(f"\n📈 Metrics:")
    print(f"   LOC: {result2['metrics'].lines_of_code}")
    print(f"   Complexity: {result2['metrics'].cyclomatic_complexity}")
    print(f"   Maintainability: {result2['metrics'].maintainability_index:.1f}/100")
    print(f"\n🎯 Quality Score: {result2['quality_score']}/100")
    print(f"🐛 Issues Found: {len(result2['issues'])}")

    if result2['issues']:
        print("\n⚠️  Critical & High Issues:")
        for issue in result2['issues']:
            if issue.severity in ['critical', 'high']:
                line_info = f" (line {issue.line})" if issue.line else ""
                print(f"   [{issue.severity.upper()}] {issue.category}: {issue.message}{line_info}")
                if issue.suggestion:
                    print(f"      💡 {issue.suggestion}")

    # Test 3: Security-focused analysis
    print("\n" + "=" * 70)
    print("📊 Test 3: Security-focused analysis")
    print("=" * 70)

    result3 = await server.execute_tool(
        "code_analyzer",
        {
            "code": BAD_CODE,
            "language": "python",
            "analysis_type": "security",
            "use_ai": False
        }
    )

    print(f"\n✨ Summary: {result3['summary']}")
    print(f"🔒 Security Issues: {len([i for i in result3['issues'] if i.category == 'security'])}")

    security_issues = [i for i in result3['issues'] if i.category == 'security']
    if security_issues:
        print("\n⚠️  Security Vulnerabilities:")
        for issue in security_issues:
            print(f"   [{issue.severity.upper()}] {issue.message}")
            if issue.suggestion:
                print(f"      💡 {issue.suggestion}")

    # Cleanup
    await server.cleanup()

    print("\n" + "=" * 70)
    print("✅ All tests completed!")
    print("=" * 70)

    # Summary
    print("\n📊 Test Summary:")
    print(f"   Good Code Score: {result1['quality_score']}/100 ({'PASS' if result1['quality_score'] > 70 else 'FAIL'})")
    print(f"   Bad Code Score: {result2['quality_score']}/100 ({'PASS' if result2['quality_score'] < 50 else 'FAIL'})")
    print(f"   Security Issues Detected: {len(security_issues)} ({'PASS' if len(security_issues) > 0 else 'FAIL'})")


if __name__ == "__main__":
    asyncio.run(test_code_analyzer())
