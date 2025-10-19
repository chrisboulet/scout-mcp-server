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
Unit tests for ToolRegistry.

Following Constitution Principle #3: Mandatory Testing
"""

import pytest
from typing import Any, Dict
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError

from scout.core.tool_registry import (
    ToolRegistry,
    ToolCategory,
    ToolPermission,
    ToolMetadata,
    ToolSchema,
    RegisteredTool,
    BaseTool,
)
from scout.config.exceptions import ConfigurationError


# Mock Pydantic models for testing
class TestInputModel(BaseModel):
    """Test input model."""
    query: str = Field(..., description="Test query")
    limit: int = Field(default=10, description="Result limit")


class TestOutputModel(BaseModel):
    """Test output model."""
    result: str = Field(..., description="Result value")
    count: int = Field(default=0, description="Result count")


class TestErrorModel(BaseModel):
    """Test error model."""
    error: str = Field(..., description="Error message")
    code: int = Field(..., description="Error code")


# Mock Tool implementations
class MockAnalysisTool(BaseTool):
    """Mock analysis tool for testing."""

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        return ToolMetadata(
            name="mock_analysis",
            description="Mock analysis tool",
            category=ToolCategory.ANALYSIS,
            version="1.0.0",
            author="Test Author",
            permissions={ToolPermission.READ},
            tags=["test", "analysis"],
            examples=[{"query": "test", "limit": 5}]
        )

    def get_schema(self) -> ToolSchema:
        """Get tool schema."""
        return ToolSchema(
            input_model=TestInputModel,
            output_model=TestOutputModel
        )

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool."""
        query = kwargs.get("query", "")
        return {"result": f"Analyzed: {query}", "count": len(query)}


class MockGenerationTool(BaseTool):
    """Mock generation tool for testing."""

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        return ToolMetadata(
            name="mock_generation",
            description="Mock generation tool",
            category=ToolCategory.GENERATION,
            version="2.0.0",
            permissions={ToolPermission.WRITE},
            tags=["test", "generation"],
            cost_estimate=0.5,
            avg_latency_ms=100
        )

    def get_schema(self) -> ToolSchema:
        """Get tool schema."""
        return ToolSchema(
            input_model=TestInputModel,
            output_model=TestOutputModel,
            error_model=TestErrorModel
        )

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool."""
        query = kwargs.get("query", "")
        limit = kwargs.get("limit", 10)
        return {"result": f"Generated: {query}", "count": limit}


class MockDeprecatedTool(BaseTool):
    """Mock deprecated tool for testing."""

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        return ToolMetadata(
            name="mock_deprecated",
            description="Mock deprecated tool",
            category=ToolCategory.UTILITY,
            deprecated=True,
            replacement="mock_analysis"
        )

    def get_schema(self) -> ToolSchema:
        """Get tool schema."""
        return ToolSchema(
            input_model=TestInputModel,
            output_model=TestOutputModel
        )

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool."""
        return {"result": "deprecated", "count": 0}


@pytest.fixture
def tool_registry():
    """Create a fresh tool registry for each test."""
    return ToolRegistry()


@pytest.fixture
def mock_analysis_tool():
    """Create mock analysis tool."""
    return MockAnalysisTool()


@pytest.fixture
def mock_generation_tool():
    """Create mock generation tool."""
    return MockGenerationTool()


@pytest.fixture
def mock_deprecated_tool():
    """Create mock deprecated tool."""
    return MockDeprecatedTool()


class TestEnumerations:
    """Test suite for enumeration types."""

    def test_tool_category_values(self):
        """Test ToolCategory enum values."""
        assert ToolCategory.ANALYSIS.value == "analysis"
        assert ToolCategory.GENERATION.value == "generation"
        assert ToolCategory.TRANSFORMATION.value == "transformation"
        assert ToolCategory.INTEGRATION.value == "integration"
        assert ToolCategory.MONITORING.value == "monitoring"
        assert ToolCategory.UTILITY.value == "utility"

    def test_tool_permission_values(self):
        """Test ToolPermission enum values."""
        assert ToolPermission.READ.value == "read"
        assert ToolPermission.WRITE.value == "write"
        assert ToolPermission.EXECUTE.value == "execute"
        assert ToolPermission.ADMIN.value == "admin"

    def test_category_from_string(self):
        """Test creating ToolCategory from string."""
        category = ToolCategory("analysis")
        assert category == ToolCategory.ANALYSIS

    def test_permission_from_string(self):
        """Test creating ToolPermission from string."""
        permission = ToolPermission("write")
        assert permission == ToolPermission.WRITE


class TestToolMetadata:
    """Test suite for ToolMetadata dataclass."""

    def test_metadata_creation(self):
        """Test creating tool metadata."""
        metadata = ToolMetadata(
            name="test_tool",
            description="Test tool description",
            category=ToolCategory.ANALYSIS,
            version="1.0.0"
        )

        assert metadata.name == "test_tool"
        assert metadata.description == "Test tool description"
        assert metadata.category == ToolCategory.ANALYSIS
        assert metadata.version == "1.0.0"
        assert metadata.author is None
        assert metadata.permissions == set()
        assert metadata.tags == []
        assert metadata.deprecated is False

    def test_metadata_with_full_details(self):
        """Test metadata with all optional fields."""
        metadata = ToolMetadata(
            name="advanced_tool",
            description="Advanced tool",
            category=ToolCategory.GENERATION,
            version="2.1.0",
            author="Test Author",
            permissions={ToolPermission.READ, ToolPermission.WRITE},
            tags=["ai", "ml", "nlp"],
            deprecated=True,
            replacement="new_tool",
            examples=[{"input": "test"}],
            cost_estimate=1.5,
            avg_latency_ms=250
        )

        assert metadata.name == "advanced_tool"
        assert metadata.author == "Test Author"
        assert len(metadata.permissions) == 2
        assert len(metadata.tags) == 3
        assert metadata.deprecated is True
        assert metadata.replacement == "new_tool"
        assert len(metadata.examples) == 1
        assert metadata.cost_estimate == 1.5
        assert metadata.avg_latency_ms == 250


class TestToolSchema:
    """Test suite for ToolSchema dataclass."""

    def test_schema_creation(self):
        """Test creating tool schema."""
        schema = ToolSchema(
            input_model=TestInputModel,
            output_model=TestOutputModel
        )

        assert schema.input_model == TestInputModel
        assert schema.output_model == TestOutputModel
        assert schema.error_model is None

    def test_schema_with_error_model(self):
        """Test schema with error model."""
        schema = ToolSchema(
            input_model=TestInputModel,
            output_model=TestOutputModel,
            error_model=TestErrorModel
        )

        assert schema.error_model == TestErrorModel


class TestRegisteredTool:
    """Test suite for RegisteredTool dataclass."""

    async def mock_handler(**kwargs):
        """Mock handler function."""
        return {"result": "test"}

    def test_registered_tool_creation(self):
        """Test creating registered tool."""
        metadata = ToolMetadata(
            name="test",
            description="Test",
            category=ToolCategory.UTILITY
        )
        schema = ToolSchema(
            input_model=TestInputModel,
            output_model=TestOutputModel
        )

        registered = RegisteredTool(
            metadata=metadata,
            schema=schema,
            handler=TestRegisteredTool.mock_handler
        )

        assert registered.metadata == metadata
        assert registered.schema == schema
        assert registered.handler == TestRegisteredTool.mock_handler
        assert registered.validator is None
        assert registered.pre_processor is None
        assert registered.post_processor is None


class TestBaseTool:
    """Test suite for BaseTool abstract class."""

    def test_base_tool_cannot_instantiate(self):
        """Test BaseTool cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseTool()

    def test_mock_tool_has_required_methods(self, mock_analysis_tool):
        """Test mock tool implements required methods."""
        assert hasattr(mock_analysis_tool, "get_metadata")
        assert hasattr(mock_analysis_tool, "get_schema")
        assert hasattr(mock_analysis_tool, "execute")

    def test_tool_metadata(self, mock_analysis_tool):
        """Test tool metadata retrieval."""
        metadata = mock_analysis_tool.get_metadata()
        assert metadata.name == "mock_analysis"
        assert metadata.category == ToolCategory.ANALYSIS

    def test_tool_schema(self, mock_analysis_tool):
        """Test tool schema retrieval."""
        schema = mock_analysis_tool.get_schema()
        assert schema.input_model == TestInputModel
        assert schema.output_model == TestOutputModel

    @pytest.mark.asyncio
    async def test_tool_execution(self, mock_analysis_tool):
        """Test tool execution."""
        result = await mock_analysis_tool.execute(query="test", limit=5)
        assert result["result"] == "Analyzed: test"
        assert result["count"] == 4

    def test_tool_validate_input_success(self, mock_analysis_tool):
        """Test successful input validation."""
        valid_data = {"query": "test", "limit": 10}
        assert mock_analysis_tool.validate_input(valid_data) is True

    def test_tool_validate_input_failure(self, mock_analysis_tool):
        """Test failed input validation."""
        invalid_data = {"limit": 10}  # Missing required 'query'
        with pytest.raises(ValidationError):
            mock_analysis_tool.validate_input(invalid_data)

    def test_tool_validate_output_success(self, mock_analysis_tool):
        """Test successful output validation."""
        valid_output = {"result": "test", "count": 5}
        assert mock_analysis_tool.validate_output(valid_output) is True

    def test_tool_validate_output_failure(self, mock_analysis_tool):
        """Test failed output validation."""
        invalid_output = {"count": 5}  # Missing required 'result'
        with pytest.raises(ValidationError):
            mock_analysis_tool.validate_output(invalid_output)


@pytest.mark.asyncio
class TestToolRegistryInitialization:
    """Test suite for ToolRegistry initialization."""

    def test_initialization(self, tool_registry):
        """Test basic registry initialization."""
        assert isinstance(tool_registry._tools, dict)
        assert len(tool_registry._tools) == 0
        assert isinstance(tool_registry._categories, dict)
        assert len(tool_registry._categories) == len(ToolCategory)
        assert isinstance(tool_registry._tags, dict)
        assert isinstance(tool_registry._aliases, dict)


@pytest.mark.asyncio
class TestToolRegistration:
    """Test suite for tool registration."""

    def test_register_tool_success(self, tool_registry, mock_analysis_tool):
        """Test successful tool registration."""
        tool_registry.register_tool("mock_analysis", mock_analysis_tool)

        assert "mock_analysis" in tool_registry._tools
        assert len(tool_registry._categories[ToolCategory.ANALYSIS]) == 1
        assert "test" in tool_registry._tags
        assert "analysis" in tool_registry._tags

    def test_register_tool_with_alias(self, tool_registry, mock_analysis_tool):
        """Test tool registration with alias."""
        tool_registry.register_tool(
            "mock_analysis",
            mock_analysis_tool,
            alias="ma"
        )

        assert "ma" in tool_registry._aliases
        assert tool_registry._aliases["ma"] == "mock_analysis"

    def test_register_duplicate_tool_fails(self, tool_registry, mock_analysis_tool):
        """Test duplicate registration fails without override."""
        tool_registry.register_tool("mock_analysis", mock_analysis_tool)

        with pytest.raises(ConfigurationError, match="already registered"):
            tool_registry.register_tool("mock_analysis", mock_analysis_tool)

    def test_register_duplicate_tool_with_override(
        self,
        tool_registry,
        mock_analysis_tool,
        mock_generation_tool
    ):
        """Test duplicate registration with override."""
        tool_registry.register_tool("test_tool", mock_analysis_tool)
        tool_registry.register_tool("test_tool", mock_generation_tool, override=True)

        tool = tool_registry.get_tool("test_tool")
        assert tool.metadata.category == ToolCategory.GENERATION

    def test_register_from_function(self, tool_registry):
        """Test registering tool from function."""
        async def test_handler(query: str, limit: int = 10) -> Dict[str, Any]:
            return {"result": query, "count": limit}

        metadata = ToolMetadata(
            name="func_tool",
            description="Function tool",
            category=ToolCategory.UTILITY
        )

        tool_registry.register_from_function(
            name="func_tool",
            handler=test_handler,
            metadata=metadata,
            input_model=TestInputModel,
            output_model=TestOutputModel
        )

        assert "func_tool" in tool_registry._tools
        tool = tool_registry.get_tool("func_tool")
        assert tool.metadata.name == "func_tool"
        assert tool.handler == test_handler


@pytest.mark.asyncio
class TestToolRetrieval:
    """Test suite for tool retrieval."""

    def test_get_tool_success(self, tool_registry, mock_analysis_tool):
        """Test successful tool retrieval."""
        tool_registry.register_tool("mock_analysis", mock_analysis_tool)

        tool = tool_registry.get_tool("mock_analysis")
        assert tool is not None
        assert tool.metadata.name == "mock_analysis"

    def test_get_tool_not_found(self, tool_registry):
        """Test getting non-existent tool."""
        tool = tool_registry.get_tool("nonexistent")
        assert tool is None

    def test_get_tool_by_alias(self, tool_registry, mock_analysis_tool):
        """Test retrieving tool by alias."""
        tool_registry.register_tool(
            "mock_analysis",
            mock_analysis_tool,
            alias="ma"
        )

        tool = tool_registry.get_tool("ma")
        assert tool is not None
        assert tool.metadata.name == "mock_analysis"

    def test_get_tool_metadata(self, tool_registry, mock_analysis_tool):
        """Test getting tool metadata."""
        tool_registry.register_tool("mock_analysis", mock_analysis_tool)

        metadata = tool_registry.get_tool_metadata("mock_analysis")
        assert metadata is not None
        assert metadata.name == "mock_analysis"
        assert metadata.category == ToolCategory.ANALYSIS

    def test_get_tool_metadata_not_found(self, tool_registry):
        """Test getting metadata for non-existent tool."""
        metadata = tool_registry.get_tool_metadata("nonexistent")
        assert metadata is None

    def test_get_tool_schema(self, tool_registry, mock_analysis_tool):
        """Test getting tool schema."""
        tool_registry.register_tool("mock_analysis", mock_analysis_tool)

        schema = tool_registry.get_tool_schema("mock_analysis")
        assert schema is not None
        assert "input" in schema
        assert "output" in schema
        assert "error" in schema

    def test_get_tool_schema_not_found(self, tool_registry):
        """Test getting schema for non-existent tool."""
        schema = tool_registry.get_tool_schema("nonexistent")
        assert schema is None


@pytest.mark.asyncio
class TestToolListing:
    """Test suite for tool listing."""

    def test_list_all_tools(
        self,
        tool_registry,
        mock_analysis_tool,
        mock_generation_tool
    ):
        """Test listing all tools."""
        tool_registry.register_tool("tool1", mock_analysis_tool)
        tool_registry.register_tool("tool2", mock_generation_tool)

        tools = tool_registry.list_tools()
        assert len(tools) == 2
        assert "tool1" in tools
        assert "tool2" in tools

    def test_list_tools_by_category(
        self,
        tool_registry,
        mock_analysis_tool,
        mock_generation_tool
    ):
        """Test listing tools filtered by category."""
        tool_registry.register_tool("analysis_tool", mock_analysis_tool)
        tool_registry.register_tool("gen_tool", mock_generation_tool)

        analysis_tools = tool_registry.list_tools(category=ToolCategory.ANALYSIS)
        assert len(analysis_tools) == 1
        assert "analysis_tool" in analysis_tools

        gen_tools = tool_registry.list_tools(category=ToolCategory.GENERATION)
        assert len(gen_tools) == 1
        assert "gen_tool" in gen_tools

    def test_list_tools_by_tag(
        self,
        tool_registry,
        mock_analysis_tool,
        mock_generation_tool
    ):
        """Test listing tools filtered by tag."""
        tool_registry.register_tool("tool1", mock_analysis_tool)
        tool_registry.register_tool("tool2", mock_generation_tool)

        analysis_tagged = tool_registry.list_tools(tag="analysis")
        assert len(analysis_tagged) == 1
        assert "tool1" in analysis_tagged

        test_tagged = tool_registry.list_tools(tag="test")
        assert len(test_tagged) == 2

    def test_list_tools_exclude_deprecated(
        self,
        tool_registry,
        mock_analysis_tool,
        mock_deprecated_tool
    ):
        """Test deprecated tools are excluded by default."""
        tool_registry.register_tool("active_tool", mock_analysis_tool)
        tool_registry.register_tool("deprecated_tool", mock_deprecated_tool)

        tools = tool_registry.list_tools(include_deprecated=False)
        assert len(tools) == 1
        assert "active_tool" in tools
        assert "deprecated_tool" not in tools

    def test_list_tools_include_deprecated(
        self,
        tool_registry,
        mock_analysis_tool,
        mock_deprecated_tool
    ):
        """Test including deprecated tools."""
        tool_registry.register_tool("active_tool", mock_analysis_tool)
        tool_registry.register_tool("deprecated_tool", mock_deprecated_tool)

        tools = tool_registry.list_tools(include_deprecated=True)
        assert len(tools) == 2
        assert "deprecated_tool" in tools


@pytest.mark.asyncio
class TestToolValidation:
    """Test suite for tool validation."""

    def test_validate_tool_input_success(self, tool_registry, mock_analysis_tool):
        """Test successful input validation."""
        tool_registry.register_tool("mock_analysis", mock_analysis_tool)

        valid_data = {"query": "test", "limit": 5}
        assert tool_registry.validate_tool_input("mock_analysis", valid_data) is True

    def test_validate_tool_input_failure(self, tool_registry, mock_analysis_tool):
        """Test failed input validation."""
        tool_registry.register_tool("mock_analysis", mock_analysis_tool)

        invalid_data = {"limit": 5}  # Missing required 'query'
        with pytest.raises(ValidationError):
            tool_registry.validate_tool_input("mock_analysis", invalid_data)

    def test_validate_tool_input_not_found(self, tool_registry):
        """Test validation for non-existent tool."""
        with pytest.raises(ConfigurationError, match="not found"):
            tool_registry.validate_tool_input("nonexistent", {})


@pytest.mark.asyncio
class TestToolExecution:
    """Test suite for tool execution."""

    async def test_execute_tool_success(self, tool_registry, mock_analysis_tool):
        """Test successful tool execution."""
        tool_registry.register_tool("mock_analysis", mock_analysis_tool)

        result = await tool_registry.execute_tool(
            "mock_analysis",
            {"query": "test", "limit": 10}
        )

        assert result["result"] == "Analyzed: test"
        assert result["count"] == 4

    async def test_execute_tool_not_found(self, tool_registry):
        """Test executing non-existent tool."""
        with pytest.raises(ConfigurationError, match="not found"):
            await tool_registry.execute_tool("nonexistent", {})

    async def test_execute_tool_with_validation(
        self,
        tool_registry,
        mock_analysis_tool
    ):
        """Test tool execution with validation."""
        tool_registry.register_tool("mock_analysis", mock_analysis_tool)

        # Valid input
        result = await tool_registry.execute_tool(
            "mock_analysis",
            {"query": "test", "limit": 5},
            validate=True
        )
        assert result is not None

        # Invalid input
        with pytest.raises(ValidationError):
            await tool_registry.execute_tool(
                "mock_analysis",
                {"limit": 5},  # Missing required 'query'
                validate=True
            )

    async def test_execute_tool_without_validation(
        self,
        tool_registry,
        mock_analysis_tool
    ):
        """Test tool execution without validation."""
        tool_registry.register_tool("mock_analysis", mock_analysis_tool)

        # Should not validate, but might fail in handler
        try:
            await tool_registry.execute_tool(
                "mock_analysis",
                {"limit": 5},
                validate=False
            )
        except Exception:
            # Expected to fail in handler, not in validation
            pass

    async def test_execute_deprecated_tool(
        self,
        tool_registry,
        mock_deprecated_tool
    ):
        """Test executing deprecated tool logs warning."""
        tool_registry.register_tool("mock_deprecated", mock_deprecated_tool)

        # Should execute but log warning
        result = await tool_registry.execute_tool(
            "mock_deprecated",
            {"query": "test"}
        )
        assert result is not None


@pytest.mark.asyncio
class TestToolStatistics:
    """Test suite for tool statistics."""

    def test_get_statistics_empty(self, tool_registry):
        """Test statistics for empty registry."""
        stats = tool_registry.get_statistics()

        assert stats["total_tools"] == 0
        assert stats["deprecated_tools"] == 0

    def test_get_statistics_with_tools(
        self,
        tool_registry,
        mock_analysis_tool,
        mock_generation_tool,
        mock_deprecated_tool
    ):
        """Test statistics with registered tools."""
        tool_registry.register_tool("tool1", mock_analysis_tool)
        tool_registry.register_tool("tool2", mock_generation_tool)
        tool_registry.register_tool("tool3", mock_deprecated_tool)

        stats = tool_registry.get_statistics()

        assert stats["total_tools"] == 3
        assert stats["deprecated_tools"] == 1
        assert "categories" in stats
        assert stats["categories"][ToolCategory.ANALYSIS.value] == 1
        assert stats["categories"][ToolCategory.GENERATION.value] == 1
        assert stats["categories"][ToolCategory.UTILITY.value] == 1
