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
SCOUT MCP Server - Main server implementation.

This module implements the Model Context Protocol (MCP) server that provides
AI-powered tools for software development and analysis.

Following Constitution Principles:
- #1: Contract-First Development (MCP Protocol)
- #2: Modular Architecture
- #4: AI Provider Abstraction
- #5: Robust Error Handling
- #6: Structured Logging
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import asyncio
import structlog
from fastmcp import FastMCP

from scout.config.loader import load_config
from scout.config.models import ScoutConfig
from scout.config.exceptions import ConfigurationError
from scout.core.team_selector import TeamSelector
from scout.core.tool_registry import ToolRegistry, BaseTool
from scout.core.state_manager import StateManager
from scout.providers.factory import ProviderFactory
from scout.providers.base import BaseAIProvider, Message, Role

# Configure structured logging
logger = structlog.get_logger(__name__)


class ScoutMCPServer:
    """
    SCOUT MCP Server implementation.

    This class integrates all SCOUT components into a cohesive MCP server:
    - Configuration management
    - AI provider abstraction
    - Team-based model selection
    - Dynamic tool registry
    - MCP protocol compliance

    Constitution Compliance:
    - Principle #1: MCP Protocol implementation
    - Principle #2: Modular component integration
    - Principle #4: Multi-provider AI support
    - Principle #5: Comprehensive error handling
    - Principle #6: Structured logging throughout
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        config: Optional[ScoutConfig] = None,
        server_name: str = "scout-mcp-server",
        server_version: str = "0.1.0"
    ):
        """
        Initialize SCOUT MCP Server.

        Args:
            config_path: Path to configuration file (YAML/JSON)
            config: Pre-loaded ScoutConfig instance
            server_name: MCP server name
            server_version: MCP server version

        Raises:
            ConfigurationError: If configuration is invalid
        """
        self.server_name = server_name
        self.server_version = server_version
        self.logger = logger.bind(server=server_name)

        # Load configuration
        if config:
            self.config = config
            self.logger.info("Using provided configuration")
        elif config_path:
            self.config = load_config(str(config_path))
            self.logger.info("Loaded configuration from file", path=str(config_path))
        else:
            # Try to load from environment variable or default location
            import os
            default_path = os.getenv("SCOUT_CONFIG", "config.yaml")
            try:
                self.config = load_config(default_path)
                self.logger.info("Loaded configuration from default", path=default_path)
            except Exception as e:
                raise ConfigurationError(
                    f"No configuration provided and default config not found: {e}"
                )

        # Initialize FastMCP server
        self.mcp = FastMCP(
            name=server_name,
            version=server_version
        )

        # Initialize core components
        self.tool_registry = ToolRegistry()
        self.team_selector = TeamSelector(scout_config=self.config)
        self.providers: Dict[str, BaseAIProvider] = {}
        self.state_manager: Optional[StateManager] = None

        # Server state
        self._initialized = False
        self._running = False

        self.logger.info(
            "SCOUT MCP Server created",
            version=server_version,
            teams_configured=len(self.config.teams),
            providers_configured=len(self.config.providers)
        )

    async def initialize(self) -> None:
        """
        Initialize server components.

        This method:
        1. Creates all configured AI providers
        2. Initializes provider connections
        3. Discovers and registers tools
        4. Sets up MCP tool handlers

        Raises:
            ConfigurationError: If initialization fails
        """
        if self._initialized:
            self.logger.warning("Server already initialized")
            return

        self.logger.info("Initializing SCOUT MCP Server")

        try:
            # Initialize providers
            self.logger.info("Creating AI providers")
            self.providers = ProviderFactory.create_all_providers(self.config)

            # Initialize each provider
            for name, provider in self.providers.items():
                await provider.initialize()
                self.logger.debug("Provider initialized", provider=name)

            # Initialize State Manager (optional - fails gracefully if Redis unavailable)
            try:
                import os
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
                self.state_manager = StateManager(
                    redis_url=redis_url,
                    default_ttl_seconds=self.config.system.cache_ttl_seconds
                )
                self.logger.info("State manager initialized", redis_url=redis_url)
            except Exception as e:
                self.logger.warning(
                    "State manager initialization failed - conversations won't persist",
                    error=str(e)
                )
                self.state_manager = None

            # Discover and register tools from tools directory
            tools_dir = Path(__file__).parent / "tools"
            if tools_dir.exists():
                discovered = self.tool_registry.discover_tools(tools_dir)
                self.logger.info(
                    "Tools discovered",
                    count=len(discovered),
                    tools=discovered
                )

            # Register MCP tool handlers
            self._register_mcp_handlers()

            self._initialized = True
            self.logger.info("SCOUT MCP Server initialized successfully")

        except Exception as e:
            self.logger.error(
                "Server initialization failed",
                error=str(e),
                exc_info=True
            )
            raise ConfigurationError(f"Failed to initialize server: {e}") from e

    def _register_mcp_handlers(self) -> None:
        """
        Register MCP protocol handlers for all tools.

        This method creates FastMCP tool wrappers for each registered tool,
        enabling them to be called via the MCP protocol.
        """
        # Get all registered tools
        tool_names = self.tool_registry.list_tools(include_deprecated=False)

        for tool_name in tool_names:
            tool = self.tool_registry.get_tool(tool_name)
            if not tool:
                continue

            # Create MCP tool handler
            @self.mcp.tool(name=tool_name)
            async def tool_handler(**kwargs) -> Dict[str, Any]:
                """Dynamic tool handler for MCP."""
                return await self.execute_tool(tool_name, kwargs)

            self.logger.debug(
                "MCP handler registered",
                tool=tool_name,
                category=tool.metadata.category.value
            )

    async def execute_tool(
        self,
        tool_name: str,
        input_data: Dict[str, Any],
        team_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool with AI provider integration.

        This method:
        1. Selects appropriate AI team based on task
        2. Executes the tool with selected provider
        3. Handles errors and logging

        Args:
            tool_name: Name of tool to execute
            input_data: Tool input parameters
            team_override: Optional team name override

        Returns:
            Tool execution result

        Raises:
            ConfigurationError: If tool not found
            Exception: On execution errors
        """
        self.logger.info(
            "Executing tool",
            tool=tool_name,
            team_override=team_override
        )

        try:
            # Get tool metadata to determine task characteristics
            metadata = self.tool_registry.get_tool_metadata(tool_name)
            if not metadata:
                raise ConfigurationError(f"Tool '{tool_name}' not found")

            # Extract task description from input if available
            task_description = input_data.get("query", metadata.description)

            # Select appropriate team
            team_selection = await self.team_selector.select_team(
                task=task_description,
                team_override=team_override
            )

            self.logger.debug(
                "Team selected",
                tool=tool_name,
                team=team_selection.team_name,
                provider=team_selection.primary_provider,
                model=team_selection.primary_model,
                confidence=team_selection.confidence
            )

            # Get provider instance for the selected team
            provider_name = team_selection.primary_provider
            provider = self.providers.get(provider_name)

            if not provider:
                self.logger.warning(
                    "Provider not available, tool will run without AI integration",
                    provider=provider_name
                )

            # Add team selection context to input
            input_data["team_context"] = {
                "team": team_selection.team_name,
                "provider": team_selection.primary_provider,
                "model": team_selection.primary_model,
                "complexity": team_selection.complexity.value,
                "domain": team_selection.domain.value
            }

            # Add runtime dependencies (provider and state manager)
            # These are injected by the server and not part of the tool's input schema
            input_data["provider"] = provider
            input_data["state_manager"] = self.state_manager

            # Execute tool
            result = await self.tool_registry.execute_tool(
                tool_name,
                input_data,
                validate=True
            )

            self.logger.info(
                "Tool executed successfully",
                tool=tool_name,
                team=team_selection.team_name
            )

            return result

        except Exception as e:
            self.logger.error(
                "Tool execution failed",
                tool=tool_name,
                error=str(e),
                exc_info=True
            )
            raise

    async def chat(
        self,
        messages: List[Message],
        team_override: Optional[str] = None,
        model_override: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Send chat messages with intelligent team selection.

        Args:
            messages: List of conversation messages
            team_override: Force specific team
            model_override: Force specific model
            **kwargs: Additional provider parameters

        Returns:
            AI response content

        Raises:
            ConfigurationError: If team/provider not available
        """
        # Extract last message as task description
        last_message = messages[-1].content if messages else ""

        # Select team
        team_selection = await self.team_selector.select_team(
            task=last_message,
            team_override=team_override
        )

        # Get provider
        provider_name = team_selection.primary_provider
        if provider_name not in self.providers:
            raise ConfigurationError(f"Provider '{provider_name}' not available")

        provider = self.providers[provider_name]

        # Use model override if provided
        model = model_override or team_selection.primary_model

        # Send chat request
        response = await provider.chat(
            messages=messages,
            model=model,
            **kwargs
        )

        self.logger.info(
            "Chat completed",
            team=team_selection.team_name,
            provider=provider_name,
            model=model,
            tokens_used=response.total_tokens
        )

        return response.content

    async def cleanup(self) -> None:
        """
        Clean up server resources.

        This method:
        1. Closes all provider connections
        2. Cleans up tool registry
        3. Releases resources
        """
        if not self._initialized:
            return

        self.logger.info("Cleaning up SCOUT MCP Server")

        try:
            # Cleanup providers
            await ProviderFactory.cleanup_all()

            # Clear provider cache
            ProviderFactory.clear_cache()

            self._initialized = False
            self._running = False

            self.logger.info("SCOUT MCP Server cleanup complete")

        except Exception as e:
            self.logger.error(
                "Cleanup failed",
                error=str(e),
                exc_info=True
            )

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all components.

        Returns:
            Health status for server and all providers
        """
        health = {
            "server": "healthy" if self._initialized else "not_initialized",
            "version": self.server_version,
            "providers": {},
            "tools": {
                "total": len(self.tool_registry.list_tools()),
                "available": len(self.tool_registry.list_tools(include_deprecated=False))
            }
        }

        # Check each provider
        for name, provider in self.providers.items():
            try:
                is_healthy = await provider.health_check()
                health["providers"][name] = "healthy" if is_healthy else "unhealthy"
            except Exception as e:
                health["providers"][name] = f"error: {str(e)}"

        return health

    def get_server_info(self) -> Dict[str, Any]:
        """
        Get server information.

        Returns:
            Server metadata and statistics
        """
        return {
            "name": self.server_name,
            "version": self.server_version,
            "initialized": self._initialized,
            "running": self._running,
            "teams": list(self.config.teams.keys()),
            "providers": list(self.providers.keys()),
            "tools": self.tool_registry.get_statistics()
        }

    async def run(self) -> None:
        """
        Run the MCP server.

        This starts the FastMCP server and keeps it running.
        """
        if not self._initialized:
            await self.initialize()

        self._running = True
        self.logger.info("SCOUT MCP Server starting")

        try:
            # Run FastMCP server
            await self.mcp.run()

        except KeyboardInterrupt:
            self.logger.info("Server interrupted by user")
        except Exception as e:
            self.logger.error(
                "Server error",
                error=str(e),
                exc_info=True
            )
            raise
        finally:
            await self.cleanup()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
