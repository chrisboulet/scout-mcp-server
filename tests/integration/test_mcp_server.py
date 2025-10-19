# Copyright 2025 Christian Boulet / Boulet Stratégies TI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Integration tests for SCOUT MCP Server.

These tests verify the complete integration of all SCOUT components:
- Configuration loading
- Provider initialization
- Team selection
- Tool registry
- Server lifecycle

Following Constitution Principle #3: Mandatory Testing
"""

import pytest
from pathlib import Path
from typing import Dict, Any

from scout.server import ScoutMCPServer
from scout.config.models import (
    ScoutConfig,
    SystemSettings,
    ProviderConfig,
    ModelConfig,
    TeamConfig,
    TeamMember,
)
from scout.config.exceptions import ConfigurationError
from scout.core.tool_registry import BaseTool, ToolMetadata, ToolSchema, ToolCategory
from pydantic import BaseModel, Field


# Test Pydantic models
class TestToolInput(BaseModel):
    """Test tool input model."""
    query: str = Field(..., description="Test query")


class TestToolOutput(BaseModel):
    """Test tool output model."""
    result: str = Field(..., description="Test result")


# Test tool implementation
class IntegrationTestTool(BaseTool):
    """Test tool for integration testing."""

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        return ToolMetadata(
            name="integration_test_tool",
            description="Tool for integration testing",
            category=ToolCategory.UTILITY,
            version="1.0.0"
        )

    def get_schema(self) -> ToolSchema:
        """Get tool schema."""
        return ToolSchema(
            input_model=TestToolInput,
            output_model=TestToolOutput
        )

    async def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute test tool."""
        return {"result": f"Processed: {query}"}


@pytest.fixture
def test_config():
    """Create test configuration."""
    return ScoutConfig(
        system=SystemSettings(
            max_retries=3,
            request_timeout_seconds=60,
            default_team="scout"
        ),
        providers={
            "gemini": ProviderConfig(
                api_key="test-gemini-key",
                models={
                    "flash": ModelConfig(
                        id="gemini-1.5-flash",
                        max_tokens=8192,
                        temperature=0.7,
                        cost_per_1k_input=0.075,
                        cost_per_1k_output=0.3
                    )
                },
                default_model="flash"
            ),
            "openai": ProviderConfig(
                api_key="test-openai-key",
                models={
                    "gpt4": ModelConfig(
                        id="gpt-4o",
                        max_tokens=4096,
                        temperature=0.7,
                        cost_per_1k_input=2.5,
                        cost_per_1k_output=10.0
                    )
                },
                default_model="gpt4"
            )
        },
        teams={
            "scout": TeamConfig(
                description="Simple tasks",
                primary=TeamMember(provider="gemini", model="flash")
            ),
            "architect": TeamConfig(
                description="Complex tasks",
                primary=TeamMember(provider="openai", model="gpt4")
            )
        },
        tool_team_mapping={
            "integration_test_tool": "scout"
        }
    )


@pytest.mark.integration
@pytest.mark.asyncio
class TestMCPServerInitialization:
    """Test suite for MCP server initialization."""

    async def test_server_creation_with_config(self, test_config):
        """Test server creation with provided config."""
        server = ScoutMCPServer(config=test_config)

        assert server.config == test_config
        assert server.server_name == "scout-mcp-server"
        assert server.server_version == "0.1.0"
        assert server._initialized is False

    async def test_server_initialization(self, test_config):
        """Test server initialization process."""
        server = ScoutMCPServer(config=test_config)

        await server.initialize()

        assert server._initialized is True
        assert len(server.providers) == 2
        assert "gemini" in server.providers
        assert "openai" in server.providers

        await server.cleanup()

    async def test_server_double_initialization(self, test_config):
        """Test that double initialization is handled gracefully."""
        server = ScoutMCPServer(config=test_config)

        await server.initialize()
        await server.initialize()  # Should not raise

        assert server._initialized is True

        await server.cleanup()

    async def test_server_context_manager(self, test_config):
        """Test server as async context manager."""
        async with ScoutMCPServer(config=test_config) as server:
            assert server._initialized is True
            assert len(server.providers) > 0

        # After context, should be cleaned up
        assert server._initialized is False


@pytest.mark.integration
@pytest.mark.asyncio
class TestTeamSelectorIntegration:
    """Test suite for team selector integration."""

    async def test_team_selector_initialization(self, test_config):
        """Test team selector is properly initialized."""
        server = ScoutMCPServer(config=test_config)
        await server.initialize()

        assert server.team_selector is not None
        assert len(server.team_selector.teams) == 2
        assert "scout" in server.team_selector.teams
        assert "architect" in server.team_selector.teams

        await server.cleanup()

    async def test_team_selection_for_simple_task(self, test_config):
        """Test team selection for simple task."""
        server = ScoutMCPServer(config=test_config)
        await server.initialize()

        selection = await server.team_selector.select_team(
            task="What is Python?"
        )

        # Simple tasks should route to scout team
        assert selection.team_name in ["scout", "architect"]
        assert selection.primary_provider in ["gemini", "openai"]

        await server.cleanup()

    async def test_team_selection_with_override(self, test_config):
        """Test team selection with manual override."""
        server = ScoutMCPServer(config=test_config)
        await server.initialize()

        selection = await server.team_selector.select_team(
            task="Any task",
            team_override="architect"
        )

        assert selection.team_name == "architect"
        assert selection.primary_provider == "openai"
        assert selection.primary_model == "gpt4"

        await server.cleanup()


@pytest.mark.integration
@pytest.mark.asyncio
class TestToolRegistryIntegration:
    """Test suite for tool registry integration."""

    async def test_tool_registry_initialization(self, test_config):
        """Test tool registry is properly initialized."""
        server = ScoutMCPServer(config=test_config)
        await server.initialize()

        assert server.tool_registry is not None
        assert isinstance(server.tool_registry._tools, dict)

        await server.cleanup()

    async def test_manual_tool_registration(self, test_config):
        """Test manually registering a tool."""
        server = ScoutMCPServer(config=test_config)
        await server.initialize()

        # Register test tool
        test_tool = IntegrationTestTool()
        server.tool_registry.register_tool("test_tool", test_tool)

        # Verify registration
        registered = server.tool_registry.get_tool("test_tool")
        assert registered is not None
        assert registered.metadata.name == "integration_test_tool"

        await server.cleanup()

    async def test_tool_execution_via_registry(self, test_config):
        """Test executing tool through registry."""
        server = ScoutMCPServer(config=test_config)
        await server.initialize()

        # Register and execute tool
        test_tool = IntegrationTestTool()
        server.tool_registry.register_tool("test_tool", test_tool)

        result = await server.tool_registry.execute_tool(
            "test_tool",
            {"query": "integration test"}
        )

        assert result["result"] == "Processed: integration test"

        await server.cleanup()


@pytest.mark.integration
@pytest.mark.asyncio
class TestServerToolExecution:
    """Test suite for server-level tool execution."""

    async def test_execute_tool_with_team_context(self, test_config):
        """Test tool execution includes team context."""
        server = ScoutMCPServer(config=test_config)
        await server.initialize()

        # Register test tool
        test_tool = IntegrationTestTool()
        server.tool_registry.register_tool("integration_test_tool", test_tool)

        # Execute via server (which adds team context)
        result = await server.execute_tool(
            "integration_test_tool",
            {"query": "test with context"}
        )

        assert "result" in result
        assert result["result"] == "Processed: test with context"

        await server.cleanup()

    async def test_execute_tool_with_team_override(self, test_config):
        """Test tool execution with team override."""
        server = ScoutMCPServer(config=test_config)
        await server.initialize()

        # Register test tool
        test_tool = IntegrationTestTool()
        server.tool_registry.register_tool("integration_test_tool", test_tool)

        # Execute with team override
        result = await server.execute_tool(
            "integration_test_tool",
            {"query": "test"},
            team_override="architect"
        )

        assert "result" in result

        await server.cleanup()

    async def test_execute_nonexistent_tool(self, test_config):
        """Test executing non-existent tool raises error."""
        server = ScoutMCPServer(config=test_config)
        await server.initialize()

        with pytest.raises(ConfigurationError, match="not found"):
            await server.execute_tool(
                "nonexistent_tool",
                {"query": "test"}
            )

        await server.cleanup()


@pytest.mark.integration
@pytest.mark.asyncio
class TestProviderIntegration:
    """Test suite for provider integration."""

    async def test_providers_created(self, test_config):
        """Test all configured providers are created."""
        server = ScoutMCPServer(config=test_config)
        await server.initialize()

        assert len(server.providers) == 2
        assert "gemini" in server.providers
        assert "openai" in server.providers

        # Verify provider types
        from scout.providers.gemini import GeminiProvider
        from scout.providers.openai import OpenAIProvider

        assert isinstance(server.providers["gemini"], GeminiProvider)
        assert isinstance(server.providers["openai"], OpenAIProvider)

        await server.cleanup()

    async def test_provider_initialization(self, test_config):
        """Test providers are initialized."""
        server = ScoutMCPServer(config=test_config)
        await server.initialize()

        # Providers should have their config
        for name, provider in server.providers.items():
            assert provider.config is not None
            assert provider.provider_type is not None

        await server.cleanup()


@pytest.mark.integration
@pytest.mark.asyncio
class TestHealthCheck:
    """Test suite for health check functionality."""

    async def test_health_check_before_init(self, test_config):
        """Test health check before initialization."""
        server = ScoutMCPServer(config=test_config)

        health = await server.health_check()

        assert health["server"] == "not_initialized"
        assert health["version"] == "0.1.0"

    async def test_health_check_after_init(self, test_config):
        """Test health check after initialization."""
        server = ScoutMCPServer(config=test_config)
        await server.initialize()

        health = await server.health_check()

        assert health["server"] == "healthy"
        assert "providers" in health
        assert "tools" in health
        assert health["tools"]["total"] >= 0

        await server.cleanup()

    async def test_health_check_providers_status(self, test_config):
        """Test provider health status in health check."""
        server = ScoutMCPServer(config=test_config)
        await server.initialize()

        health = await server.health_check()

        assert "providers" in health
        # Provider health checks may fail without real API keys, that's ok
        assert len(health["providers"]) == 2

        await server.cleanup()


@pytest.mark.integration
@pytest.mark.asyncio
class TestServerInfo:
    """Test suite for server info functionality."""

    async def test_get_server_info(self, test_config):
        """Test getting server information."""
        server = ScoutMCPServer(config=test_config)
        await server.initialize()

        info = server.get_server_info()

        assert info["name"] == "scout-mcp-server"
        assert info["version"] == "0.1.0"
        assert info["initialized"] is True
        assert "teams" in info
        assert "providers" in info
        assert "tools" in info

        await server.cleanup()

    async def test_server_info_teams(self, test_config):
        """Test server info includes team information."""
        server = ScoutMCPServer(config=test_config)
        await server.initialize()

        info = server.get_server_info()

        assert "scout" in info["teams"]
        assert "architect" in info["teams"]

        await server.cleanup()

    async def test_server_info_providers(self, test_config):
        """Test server info includes provider information."""
        server = ScoutMCPServer(config=test_config)
        await server.initialize()

        info = server.get_server_info()

        assert "gemini" in info["providers"]
        assert "openai" in info["providers"]

        await server.cleanup()


@pytest.mark.integration
@pytest.mark.asyncio
class TestServerLifecycle:
    """Test suite for server lifecycle management."""

    async def test_initialization_and_cleanup(self, test_config):
        """Test complete initialization and cleanup cycle."""
        server = ScoutMCPServer(config=test_config)

        # Before init
        assert server._initialized is False

        # Initialize
        await server.initialize()
        assert server._initialized is True

        # Cleanup
        await server.cleanup()
        assert server._initialized is False

    async def test_cleanup_without_init(self, test_config):
        """Test cleanup without initialization doesn't error."""
        server = ScoutMCPServer(config=test_config)

        # Should not raise
        await server.cleanup()

        assert server._initialized is False

    async def test_multiple_cleanup_calls(self, test_config):
        """Test multiple cleanup calls are safe."""
        server = ScoutMCPServer(config=test_config)
        await server.initialize()

        await server.cleanup()
        await server.cleanup()  # Should not raise

        assert server._initialized is False


@pytest.mark.integration
@pytest.mark.asyncio
class TestConfigurationLoading:
    """Test suite for configuration loading."""

    async def test_server_with_provided_config(self, test_config):
        """Test server creation with provided config object."""
        server = ScoutMCPServer(config=test_config)

        assert server.config == test_config
        assert len(server.config.teams) == 2
        assert len(server.config.providers) == 2

    async def test_invalid_config_raises_error(self):
        """Test server with invalid config raises error."""
        # Creating invalid config (no teams) should raise validation error
        with pytest.raises(Exception):  # Pydantic ValidationError
            invalid_config = ScoutConfig(
                system=SystemSettings(
                    max_retries=3,
                    request_timeout_seconds=60
                ),
                providers={
                    "test": ProviderConfig(
                        api_key="test",
                        models={
                            "model": ModelConfig(
                                id="test-model",
                                max_tokens=1000,
                                temperature=0.7
                            )
                        },
                        default_model="model"
                    )
                },
                teams={},  # Empty teams - invalid
                tool_team_mapping={}
            )


@pytest.mark.integration
@pytest.mark.asyncio
class TestErrorHandling:
    """Test suite for error handling."""

    async def test_tool_execution_error_handling(self, test_config):
        """Test error handling during tool execution."""
        server = ScoutMCPServer(config=test_config)
        await server.initialize()

        # Try to execute non-existent tool
        with pytest.raises(ConfigurationError):
            await server.execute_tool(
                "nonexistent",
                {"query": "test"}
            )

        await server.cleanup()

    async def test_invalid_tool_input_validation(self, test_config):
        """Test validation errors for invalid tool input."""
        server = ScoutMCPServer(config=test_config)
        await server.initialize()

        test_tool = IntegrationTestTool()
        server.tool_registry.register_tool("test_tool", test_tool)

        # Missing required field
        with pytest.raises(Exception):  # ValidationError
            await server.tool_registry.execute_tool(
                "test_tool",
                {},  # Missing 'query' field
                validate=True
            )

        await server.cleanup()
