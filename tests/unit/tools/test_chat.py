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
Unit tests for Chat Tool.

Tests cover:
- Input/output schema validation
- Basic chat execution
- Session management
- System prompts
- Parameter customization
- Error handling

Following Constitution Principle #3: Mandatory Testing
"""

import pytest
from pydantic import ValidationError

from scout.tools.chat import ChatTool, ChatInput, ChatOutput


@pytest.mark.unit
@pytest.mark.asyncio
class TestChatToolMetadata:
    """Test suite for chat tool metadata."""

    def test_tool_metadata(self):
        """Test tool metadata is correct."""
        tool = ChatTool()
        metadata = tool.get_metadata()

        assert metadata.name == "chat"
        assert "conversation" in metadata.description.lower()
        assert metadata.category.value == "utility"
        assert metadata.version == "1.0.0"
        assert len(metadata.examples) >= 3

    def test_tool_schema(self):
        """Test tool schema is correct."""
        tool = ChatTool()
        schema = tool.get_schema()

        assert schema.input_model == ChatInput
        assert schema.output_model == ChatOutput


@pytest.mark.unit
class TestChatInputValidation:
    """Test suite for chat input validation."""

    def test_valid_minimal_input(self):
        """Test valid minimal input."""
        input_data = ChatInput(message="Hello")

        assert input_data.message == "Hello"
        assert input_data.session_id is None
        assert input_data.system_prompt is None

    def test_valid_full_input(self):
        """Test valid input with all fields."""
        input_data = ChatInput(
            message="Explain Python",
            session_id="session-123",
            system_prompt="You are a Python expert",
            max_tokens=2000,
            temperature=0.7,
            team_override="expert"
        )

        assert input_data.message == "Explain Python"
        assert input_data.session_id == "session-123"
        assert input_data.system_prompt == "You are a Python expert"
        assert input_data.max_tokens == 2000
        assert input_data.temperature == 0.7
        assert input_data.team_override == "expert"

    def test_empty_message_rejected(self):
        """Test empty message is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChatInput(message="")

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("message",) for error in errors)

    def test_message_too_long_rejected(self):
        """Test message exceeding max length is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChatInput(message="a" * 100001)  # Max is 100000

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("message",) for error in errors)

    def test_system_prompt_too_long_rejected(self):
        """Test system prompt exceeding max length is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChatInput(
                message="Hello",
                system_prompt="a" * 10001  # Max is 10000
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("system_prompt",) for error in errors)

    def test_invalid_max_tokens_rejected(self):
        """Test invalid max_tokens is rejected."""
        with pytest.raises(ValidationError):
            ChatInput(message="Hello", max_tokens=0)

        with pytest.raises(ValidationError):
            ChatInput(message="Hello", max_tokens=-100)

        with pytest.raises(ValidationError):
            ChatInput(message="Hello", max_tokens=100001)

    def test_invalid_temperature_rejected(self):
        """Test invalid temperature is rejected."""
        with pytest.raises(ValidationError):
            ChatInput(message="Hello", temperature=-0.1)

        with pytest.raises(ValidationError):
            ChatInput(message="Hello", temperature=2.1)


@pytest.mark.unit
class TestChatOutputValidation:
    """Test suite for chat output validation."""

    def test_valid_output(self):
        """Test valid output structure."""
        output = ChatOutput(
            response="This is the AI response",
            session_id="session-123",
            team_used="scout",
            provider_used="gemini",
            model_used="flash",
            metadata={
                "input_tokens": 10,
                "output_tokens": 20,
                "cost_usd": 0.001
            }
        )

        assert output.response == "This is the AI response"
        assert output.session_id == "session-123"
        assert output.team_used == "scout"
        assert output.provider_used == "gemini"
        assert output.model_used == "flash"
        assert output.metadata["input_tokens"] == 10

    def test_minimal_output(self):
        """Test minimal valid output."""
        output = ChatOutput(
            response="Response",
            session_id="session-1",
            team_used="scout",
            provider_used="gemini",
            model_used="flash"
        )

        assert output.response == "Response"
        assert output.metadata == {}


@pytest.mark.unit
@pytest.mark.asyncio
class TestChatToolExecution:
    """Test suite for chat tool execution."""

    async def test_basic_execution(self):
        """Test basic chat execution."""
        tool = ChatTool()

        result = await tool.execute(message="Hello, how are you?")

        assert "response" in result
        assert "session_id" in result
        assert "team_used" in result
        assert "provider_used" in result
        assert "model_used" in result
        assert "metadata" in result
        assert result["session_id"].startswith("chat-")

    async def test_execution_with_session_id(self):
        """Test execution with provided session ID."""
        tool = ChatTool()
        session_id = "my-session-123"

        result = await tool.execute(
            message="Continue conversation",
            session_id=session_id
        )

        assert result["session_id"] == session_id

    async def test_execution_with_system_prompt(self):
        """Test execution with system prompt."""
        tool = ChatTool()

        result = await tool.execute(
            message="Explain Python",
            system_prompt="You are a Python expert"
        )

        assert "response" in result
        assert result["metadata"] is not None

    async def test_execution_with_parameters(self):
        """Test execution with temperature and max_tokens."""
        tool = ChatTool()

        result = await tool.execute(
            message="Generate code",
            temperature=0.2,
            max_tokens=1000
        )

        assert result["metadata"]["temperature"] == 0.2
        assert result["metadata"]["max_tokens"] == 1000

    async def test_execution_with_team_context(self):
        """Test execution with team context injection."""
        tool = ChatTool()

        team_context = {
            "team": "architect",
            "provider": "openai",
            "model": "gpt4o",
            "complexity": "moderate",
            "domain": "technical"
        }

        result = await tool.execute(
            message="Design a system",
            team_context=team_context
        )

        assert result["team_used"] == "architect"
        assert result["provider_used"] == "openai"
        assert result["model_used"] == "gpt4o"

    async def test_execution_without_team_context(self):
        """Test execution defaults when no team context."""
        tool = ChatTool()

        result = await tool.execute(message="Simple question")

        assert result["team_used"] == "default"
        assert result["provider_used"] == "unknown"
        assert result["model_used"] == "unknown"

    async def test_metadata_includes_tokens(self):
        """Test metadata includes token counts."""
        tool = ChatTool()

        result = await tool.execute(message="Calculate something complex")

        metadata = result["metadata"]
        assert "input_tokens" in metadata
        assert "output_tokens" in metadata
        assert "total_tokens" in metadata
        assert metadata["total_tokens"] > 0

    async def test_metadata_includes_cost(self):
        """Test metadata includes cost estimation."""
        tool = ChatTool()

        result = await tool.execute(message="Test")

        metadata = result["metadata"]
        assert "cost_usd" in metadata
        assert isinstance(metadata["cost_usd"], float)
        assert metadata["cost_usd"] >= 0

    async def test_long_message_execution(self):
        """Test execution with long message."""
        tool = ChatTool()
        long_message = "This is a test. " * 1000  # Long message

        result = await tool.execute(message=long_message)

        assert "response" in result
        assert result["metadata"]["input_tokens"] > 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestChatToolEdgeCases:
    """Test suite for chat tool edge cases."""

    async def test_unicode_message(self):
        """Test chat with unicode characters."""
        tool = ChatTool()

        result = await tool.execute(
            message="Bonjour! Comment ça va? 你好！¿Cómo estás?"
        )

        assert "response" in result

    async def test_special_characters(self):
        """Test chat with special characters."""
        tool = ChatTool()

        result = await tool.execute(
            message="Test <html> & \"quotes\" and 'apostrophes'"
        )

        assert "response" in result

    async def test_multiline_message(self):
        """Test chat with multiline message."""
        tool = ChatTool()

        message = """
        This is a multiline message.

        It has multiple paragraphs.

        And blank lines.
        """

        result = await tool.execute(message=message)

        assert "response" in result

    async def test_code_in_message(self):
        """Test chat with code snippets."""
        tool = ChatTool()

        message = """
        Explain this code:
        ```python
        def hello():
            print("world")
        ```
        """

        result = await tool.execute(message=message)

        assert "response" in result
