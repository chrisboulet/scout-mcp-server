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
Tool Registry Module.

This module provides dynamic tool registration and discovery for MCP tools.
It manages tool metadata, schemas, and execution handlers.

Following Constitution Principle #1: Contract-First Development (MCP Protocol)
Following Constitution Principle #2: Modular Architecture
"""

from typing import Dict, List, Optional, Any, Callable, Type, Set
from dataclasses import dataclass, field
from pathlib import Path
import inspect
import importlib
import importlib.util
from enum import Enum
import json
import structlog
from pydantic import BaseModel, Field, ValidationError
from abc import ABC, abstractmethod

from scout.config.exceptions import ConfigurationError

# Configure structured logging
logger = structlog.get_logger(__name__)


class ToolCategory(Enum):
    """Categories for tool classification."""

    ANALYSIS = "analysis"
    GENERATION = "generation"
    TRANSFORMATION = "transformation"
    INTEGRATION = "integration"
    MONITORING = "monitoring"
    UTILITY = "utility"


class ToolPermission(Enum):
    """Permission levels for tools."""

    READ = "read"       # Can read data
    WRITE = "write"     # Can modify data
    EXECUTE = "execute" # Can execute operations
    ADMIN = "admin"     # Administrative operations


@dataclass
class ToolMetadata:
    """Metadata for a registered tool."""

    name: str
    description: str
    category: ToolCategory
    version: str = "1.0.0"
    author: Optional[str] = None
    permissions: Set[ToolPermission] = field(default_factory=set)
    tags: List[str] = field(default_factory=list)
    deprecated: bool = False
    replacement: Optional[str] = None  # Name of replacement tool if deprecated
    examples: List[Dict[str, Any]] = field(default_factory=list)
    cost_estimate: Optional[float] = None  # Estimated cost per execution
    avg_latency_ms: Optional[int] = None  # Average execution time


@dataclass
class ToolSchema:
    """Schema definition for a tool."""

    input_model: Type[BaseModel]
    output_model: Type[BaseModel]
    error_model: Optional[Type[BaseModel]] = None


@dataclass
class RegisteredTool:
    """Complete registered tool with all information."""

    metadata: ToolMetadata
    schema: ToolSchema
    handler: Callable
    validator: Optional[Callable] = None  # Custom validation function
    pre_processor: Optional[Callable] = None  # Pre-processing function
    post_processor: Optional[Callable] = None  # Post-processing function
    rate_limit: Optional[int] = None  # Requests per minute
    cache_ttl: Optional[int] = None  # Cache time-to-live in seconds


class BaseTool(ABC):
    """
    Abstract base class for all MCP tools.

    All tools must inherit from this class and implement required methods.
    """

    @abstractmethod
    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        pass

    @abstractmethod
    def get_schema(self) -> ToolSchema:
        """Get tool schema."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool."""
        pass

    def validate_input(self, data: Dict[str, Any]) -> bool:
        """
        Validate input data.

        Args:
            data: Input data to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If validation fails
        """
        schema = self.get_schema()
        try:
            schema.input_model(**data)
            return True
        except ValidationError as e:
            logger.error(
                "Tool input validation failed",
                tool=self.get_metadata().name,
                errors=e.errors()
            )
            raise

    def validate_output(self, data: Any) -> bool:
        """
        Validate output data.

        Args:
            data: Output data to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If validation fails
        """
        schema = self.get_schema()
        try:
            if isinstance(data, dict):
                schema.output_model(**data)
            else:
                schema.output_model(result=data)
            return True
        except ValidationError as e:
            logger.error(
                "Tool output validation failed",
                tool=self.get_metadata().name,
                errors=e.errors()
            )
            raise


class ToolRegistry:
    """
    Central registry for all MCP tools.

    This registry manages:
    - Tool registration and discovery
    - Schema validation
    - Tool lifecycle
    - Access control
    """

    def __init__(self):
        """Initialize tool registry."""
        self._tools: Dict[str, RegisteredTool] = {}
        self._categories: Dict[ToolCategory, List[str]] = {
            category: [] for category in ToolCategory
        }
        self._tags: Dict[str, List[str]] = {}
        self._aliases: Dict[str, str] = {}  # Alias -> actual tool name

        logger.info("Tool registry initialized")

    def register_tool(
        self,
        name: str,
        tool: BaseTool,
        alias: Optional[str] = None,
        override: bool = False
    ) -> None:
        """
        Register a tool in the registry.

        Args:
            name: Unique tool name
            tool: Tool instance
            alias: Optional alias for the tool
            override: Whether to override existing tool

        Raises:
            ConfigurationError: If tool already exists and override is False
        """
        if name in self._tools and not override:
            raise ConfigurationError(
                f"Tool '{name}' already registered. Use override=True to replace."
            )

        # Get tool information
        metadata = tool.get_metadata()
        schema = tool.get_schema()

        # Validate tool name matches
        if metadata.name != name:
            logger.warning(
                "Tool name mismatch",
                registered_name=name,
                metadata_name=metadata.name
            )

        # Create registered tool
        registered = RegisteredTool(
            metadata=metadata,
            schema=schema,
            handler=tool.execute,
            validator=getattr(tool, "validate", None),
            pre_processor=getattr(tool, "pre_process", None),
            post_processor=getattr(tool, "post_process", None),
            rate_limit=getattr(tool, "rate_limit", None),
            cache_ttl=getattr(tool, "cache_ttl", None)
        )

        # Store in registry
        self._tools[name] = registered

        # Update category index
        self._categories[metadata.category].append(name)

        # Update tag index
        for tag in metadata.tags:
            if tag not in self._tags:
                self._tags[tag] = []
            self._tags[tag].append(name)

        # Register alias if provided
        if alias:
            self._aliases[alias] = name

        logger.info(
            "Tool registered",
            name=name,
            category=metadata.category.value,
            version=metadata.version,
            tags=metadata.tags
        )

    def register_from_function(
        self,
        name: str,
        handler: Callable,
        metadata: ToolMetadata,
        input_model: Type[BaseModel],
        output_model: Type[BaseModel],
        **kwargs
    ) -> None:
        """
        Register a tool from a function.

        Args:
            name: Tool name
            handler: Handler function
            metadata: Tool metadata
            input_model: Input schema model
            output_model: Output schema model
            **kwargs: Additional RegisteredTool fields
        """
        schema = ToolSchema(
            input_model=input_model,
            output_model=output_model,
            error_model=kwargs.pop("error_model", None)
        )

        registered = RegisteredTool(
            metadata=metadata,
            schema=schema,
            handler=handler,
            **kwargs
        )

        self._tools[name] = registered
        self._categories[metadata.category].append(name)

        for tag in metadata.tags:
            if tag not in self._tags:
                self._tags[tag] = []
            self._tags[tag].append(name)

        logger.info(
            "Tool registered from function",
            name=name,
            function=handler.__name__
        )

    def discover_tools(self, directory: Path) -> List[str]:
        """
        Discover and register tools from a directory.

        Args:
            directory: Directory to scan for tools

        Returns:
            List of discovered tool names
        """
        discovered = []

        if not directory.exists():
            logger.warning(
                "Tool directory does not exist",
                directory=str(directory)
            )
            return discovered

        # Scan for Python files
        for file_path in directory.glob("*.py"):
            if file_path.name.startswith("_"):
                continue

            module_name = file_path.stem

            try:
                # Import module
                spec = importlib.util.spec_from_file_location(
                    f"scout.tools.{module_name}",
                    file_path
                )

                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Look for tool classes
                    for name, obj in inspect.getmembers(module):
                        if (
                            inspect.isclass(obj) and
                            issubclass(obj, BaseTool) and
                            obj != BaseTool
                        ):
                            try:
                                tool_instance = obj()
                                tool_name = tool_instance.get_metadata().name
                                self.register_tool(tool_name, tool_instance)
                                discovered.append(tool_name)

                                logger.debug(
                                    "Tool discovered",
                                    name=tool_name,
                                    module=module_name
                                )

                            except Exception as e:
                                logger.error(
                                    "Failed to register discovered tool",
                                    class_name=name,
                                    module=module_name,
                                    error=str(e)
                                )

            except Exception as e:
                logger.error(
                    "Failed to import tool module",
                    module=module_name,
                    error=str(e)
                )

        logger.info(
            "Tool discovery complete",
            directory=str(directory),
            discovered=len(discovered)
        )

        return discovered

    def get_tool(self, name: str) -> Optional[RegisteredTool]:
        """
        Get a registered tool.

        Args:
            name: Tool name or alias

        Returns:
            RegisteredTool or None if not found
        """
        # Check if it's an alias
        if name in self._aliases:
            name = self._aliases[name]

        return self._tools.get(name)

    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        tag: Optional[str] = None,
        include_deprecated: bool = False
    ) -> List[str]:
        """
        List registered tools.

        Args:
            category: Filter by category
            tag: Filter by tag
            include_deprecated: Include deprecated tools

        Returns:
            List of tool names
        """
        tools = set(self._tools.keys())

        # Filter by category
        if category:
            tools &= set(self._categories.get(category, []))

        # Filter by tag
        if tag:
            tools &= set(self._tags.get(tag, []))

        # Filter out deprecated
        if not include_deprecated:
            tools = {
                name for name in tools
                if not self._tools[name].metadata.deprecated
            }

        return sorted(list(tools))

    def get_tool_metadata(self, name: str) -> Optional[ToolMetadata]:
        """
        Get metadata for a tool.

        Args:
            name: Tool name

        Returns:
            ToolMetadata or None if not found
        """
        tool = self.get_tool(name)
        return tool.metadata if tool else None

    def get_tool_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get JSON schema for a tool.

        Args:
            name: Tool name

        Returns:
            JSON schema dictionary or None
        """
        tool = self.get_tool(name)
        if not tool:
            return None

        return {
            "input": tool.schema.input_model.model_json_schema(),
            "output": tool.schema.output_model.model_json_schema(),
            "error": (
                tool.schema.error_model.model_json_schema()
                if tool.schema.error_model else None
            )
        }

    def validate_tool_input(self, name: str, data: Dict[str, Any]) -> bool:
        """
        Validate input for a tool.

        Args:
            name: Tool name
            data: Input data

        Returns:
            True if valid

        Raises:
            ConfigurationError: If tool not found
            ValidationError: If validation fails
        """
        tool = self.get_tool(name)
        if not tool:
            raise ConfigurationError(f"Tool '{name}' not found")

        try:
            tool.schema.input_model(**data)
            return True
        except ValidationError:
            raise

    async def execute_tool(
        self,
        name: str,
        input_data: Dict[str, Any],
        validate: bool = True,
        **kwargs
    ) -> Any:
        """
        Execute a registered tool.

        Args:
            name: Tool name
            input_data: Input data
            validate: Whether to validate input
            **kwargs: Additional execution parameters

        Returns:
            Tool execution result

        Raises:
            ConfigurationError: If tool not found
            ValidationError: If validation fails
        """
        tool = self.get_tool(name)
        if not tool:
            raise ConfigurationError(f"Tool '{name}' not found")

        # Check if deprecated
        if tool.metadata.deprecated:
            logger.warning(
                "Executing deprecated tool",
                name=name,
                replacement=tool.metadata.replacement
            )

        # Validate input
        if validate:
            self.validate_tool_input(name, input_data)

        # Pre-process if available
        if tool.pre_processor:
            input_data = await tool.pre_processor(input_data)

        # Execute tool
        try:
            result = await tool.handler(**input_data, **kwargs)
        except Exception as e:
            logger.error(
                "Tool execution failed",
                name=name,
                error=str(e)
            )
            raise

        # Post-process if available
        if tool.post_processor:
            result = await tool.post_processor(result)

        # Validate output
        if validate and tool.schema.output_model:
            try:
                if isinstance(result, dict):
                    tool.schema.output_model(**result)
                else:
                    tool.schema.output_model(result=result)
            except ValidationError as e:
                logger.error(
                    "Tool output validation failed",
                    name=name,
                    errors=e.errors()
                )
                raise

        return result

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Statistics dictionary
        """
        deprecated_count = sum(
            1 for tool in self._tools.values()
            if tool.metadata.deprecated
        )

        category_counts = {
            category.value: len(tools)
            for category, tools in self._categories.items()
        }

        return {
            "total_tools": len(self._tools),
            "deprecated_tools": deprecated_count,
            "total_aliases": len(self._aliases),
            "categories": category_counts,
            "total_tags": len(self._tags),
            "tools_with_validators": sum(
                1 for tool in self._tools.values()
                if tool.validator is not None
            ),
            "tools_with_cache": sum(
                1 for tool in self._tools.values()
                if tool.cache_ttl is not None
            ),
            "tools_with_rate_limits": sum(
                1 for tool in self._tools.values()
                if tool.rate_limit is not None
            )
        }

    def export_manifest(self) -> Dict[str, Any]:
        """
        Export tool manifest for MCP protocol.

        Returns:
            MCP-compliant tool manifest
        """
        tools = {}

        for name, tool in self._tools.items():
            if tool.metadata.deprecated:
                continue

            tools[name] = {
                "description": tool.metadata.description,
                "inputSchema": tool.schema.input_model.model_json_schema(),
                "outputSchema": tool.schema.output_model.model_json_schema(),
                "metadata": {
                    "category": tool.metadata.category.value,
                    "version": tool.metadata.version,
                    "tags": tool.metadata.tags,
                    "permissions": [p.value for p in tool.metadata.permissions],
                    "examples": tool.metadata.examples,
                    "costEstimate": tool.metadata.cost_estimate,
                    "avgLatencyMs": tool.metadata.avg_latency_ms
                }
            }

        return {
            "tools": tools,
            "version": "1.0.0",
            "capabilities": {
                "validation": True,
                "caching": True,
                "rateLimiting": True,
                "preprocessing": True,
                "postprocessing": True
            }
        }


# Global registry instance
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """
    Get the global tool registry instance.

    Returns:
        ToolRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def register_tool(name: str = None, **metadata_kwargs):
    """
    Decorator to register a tool class or function.

    Args:
        name: Optional tool name (defaults to class/function name)
        **metadata_kwargs: Metadata fields

    Returns:
        Decorator function
    """
    def decorator(obj):
        registry = get_registry()

        # Determine tool name
        tool_name = name or obj.__name__.lower().replace("tool", "")

        if inspect.isclass(obj) and issubclass(obj, BaseTool):
            # Register class-based tool
            tool_instance = obj()
            registry.register_tool(tool_name, tool_instance)

        elif inspect.isfunction(obj):
            # Register function-based tool
            # Extract type hints for schema
            sig = inspect.signature(obj)
            params = sig.parameters

            # Create input model from parameters
            input_fields = {}
            for param_name, param in params.items():
                if param_name in ["self", "cls"]:
                    continue

                param_type = param.annotation if param.annotation != inspect.Parameter.empty else Any
                default = param.default if param.default != inspect.Parameter.empty else ...

                input_fields[param_name] = (param_type, Field(default=default))

            InputModel = type(
                f"{tool_name.title()}Input",
                (BaseModel,),
                input_fields
            )

            # Simple output model
            OutputModel = type(
                f"{tool_name.title()}Output",
                (BaseModel,),
                {"result": (Any, Field(...))}
            )

            # Create metadata
            metadata = ToolMetadata(
                name=tool_name,
                description=obj.__doc__ or f"Tool: {tool_name}",
                category=metadata_kwargs.get("category", ToolCategory.UTILITY),
                **{k: v for k, v in metadata_kwargs.items() if k != "category"}
            )

            # Register function
            registry.register_from_function(
                name=tool_name,
                handler=obj,
                metadata=metadata,
                input_model=InputModel,
                output_model=OutputModel
            )

        return obj

    return decorator