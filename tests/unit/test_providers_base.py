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
Unit tests for BaseAIProvider.

Following Constitution Principle #3: Mandatory Testing
"""

import pytest
from typing import List, AsyncIterator, Optional, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from scout.providers.base import (
    BaseAIProvider,
    Message,
    Role,
    CompletionResponse,
    StreamChunk,
    ProviderType,
    ProviderException,
    RateLimitException,
    AuthenticationException,
    ModelNotAvailableException,
)
from scout.config.models import ProviderConfig, ModelConfig


# Mock Provider for testing
class MockProvider(BaseAIProvider):
    """Mock provider for testing base functionality."""

    def __init__(self, provider_config: ProviderConfig, **kwargs):
        super().__init__(
            provider_config=provider_config,
            provider_type=ProviderType.GEMINI,
            **kwargs
        )
        self.call_count = 0

    async def _make_api_call(
        self,
        messages: List[Message],
        model_config: ModelConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock API call."""
        self.call_count += 1
        return {
            "content": "Test response",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }

    def _parse_response(
        self,
        raw_response: Dict[str, Any],
        model: str
    ) -> CompletionResponse:
        """Mock response parsing."""
        return CompletionResponse(
            content=raw_response["content"],
            model=model,
            usage=raw_response["usage"]
        )

    async def _stream_api_call(
        self,
        messages: List[Message],
        model_config: ModelConfig,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """Mock streaming API call."""
        for i, chunk_text in enumerate(["Hello", " ", "World"]):
            yield {
                "delta": chunk_text,
                "index": i
            }

    def _parse_stream_chunk(
        self,
        raw_chunk: Dict[str, Any]
    ) -> Optional[StreamChunk]:
        """Mock stream chunk parsing."""
        return StreamChunk(delta=raw_chunk["delta"])


@pytest.fixture
def provider_config():
    """Create a test provider configuration."""
    return ProviderConfig(
        api_key="test-api-key",
        models={
            "test-model": ModelConfig(
                id="test-model-id",
                max_tokens=1000,
                temperature=0.7
            )
        },
        default_model="test-model"
    )


@pytest.fixture
def mock_provider(provider_config):
    """Create a mock provider instance."""
    return MockProvider(provider_config=provider_config)


@pytest.mark.asyncio
class TestBaseAIProvider:
    """Test suite for BaseAIProvider."""

    async def test_initialization(self, mock_provider, provider_config):
        """Test provider initialization."""
        assert mock_provider.config == provider_config
        assert mock_provider.provider_type == ProviderType.GEMINI
        assert mock_provider.max_retries == 3
        assert mock_provider.timeout == 60.0

    async def test_get_model_config_default(self, mock_provider):
        """Test getting default model configuration."""
        config = mock_provider._get_model_config()
        assert config.id == "test-model-id"
        assert config.max_tokens == 1000
        assert config.temperature == 0.7

    async def test_get_model_config_specific(self, mock_provider):
        """Test getting specific model configuration."""
        config = mock_provider._get_model_config("test-model")
        assert config.id == "test-model-id"

    async def test_get_model_config_invalid(self, mock_provider):
        """Test getting invalid model raises exception."""
        with pytest.raises(ModelNotAvailableException, match="Model .* not available"):
            mock_provider._get_model_config("invalid-model")

    async def test_chat_basic(self, mock_provider):
        """Test basic chat completion."""
        messages = [
            Message(role=Role.USER, content="Hello")
        ]

        response = await mock_provider.chat(messages=messages)

        assert response.content == "Test response"
        assert response.usage["total_tokens"] == 30
        assert mock_provider.call_count == 1

    async def test_chat_with_model(self, mock_provider):
        """Test chat with specific model."""
        messages = [
            Message(role=Role.USER, content="Hello")
        ]

        response = await mock_provider.chat(
            messages=messages,
            model="test-model"
        )

        assert response.content == "Test response"

    async def test_complete_string(self, mock_provider):
        """Test completion with string prompt."""
        response = await mock_provider.complete(prompt="Hello")

        assert response == "Test response"
        assert mock_provider.call_count == 1

    async def test_chat_stream(self, mock_provider):
        """Test streaming chat."""
        messages = [
            Message(role=Role.USER, content="Hello")
        ]

        chunks = []
        async for chunk in mock_provider.chat_stream(messages=messages):
            chunks.append(chunk.delta)

        assert chunks == ["Hello", " ", "World"]

    async def test_metrics_tracking(self, mock_provider):
        """Test metrics are tracked correctly."""
        messages = [Message(role=Role.USER, content="Test")]

        await mock_provider.chat(messages=messages)

        metrics = mock_provider.get_metrics()
        assert metrics["total_requests"] == 1
        assert metrics["total_tokens"] == 30
        assert metrics["successful_requests"] == 1
        assert metrics["failed_requests"] == 0

    async def test_error_handling(self, mock_provider):
        """Test error handling."""
        # Mock API call to raise exception
        async def failing_api_call(*args, **kwargs):
            raise Exception("API Error")

        mock_provider._make_api_call = failing_api_call

        messages = [Message(role=Role.USER, content="Test")]

        with pytest.raises(Exception):
            await mock_provider.chat(messages=messages)

        # Check error metrics
        metrics = mock_provider.get_metrics()
        assert metrics["failed_requests"] == 1

    async def test_cleanup(self, mock_provider):
        """Test provider cleanup."""
        await mock_provider.cleanup()
        # Should not raise any exceptions

    async def test_supports_streaming_default(self, mock_provider):
        """Test default streaming support."""
        assert mock_provider.supports_streaming() is True

    async def test_supports_vision_default(self, mock_provider):
        """Test default vision support."""
        assert mock_provider.supports_vision() is False

    async def test_supports_functions_default(self, mock_provider):
        """Test default function support."""
        assert mock_provider.supports_functions() is False


@pytest.mark.asyncio
class TestProviderExceptions:
    """Test suite for provider exceptions."""

    def test_provider_exception(self):
        """Test base ProviderException."""
        exc = ProviderException("Test error")
        assert str(exc) == "Test error"

    def test_rate_limit_exception(self):
        """Test RateLimitException."""
        exc = RateLimitException("Rate limited")
        assert str(exc) == "Rate limited"

    def test_authentication_exception(self):
        """Test AuthenticationException."""
        exc = AuthenticationException("Auth failed")
        assert str(exc) == "Auth failed"

    def test_model_not_available_exception(self):
        """Test ModelNotAvailableException."""
        exc = ModelNotAvailableException("Model not found")
        assert str(exc) == "Model not found"


@pytest.mark.asyncio
class TestMessage:
    """Test suite for Message class."""

    def test_message_creation(self):
        """Test creating a message."""
        msg = Message(role=Role.USER, content="Hello")
        assert msg.role == Role.USER
        assert msg.content == "Hello"
        assert msg.name is None
        assert msg.function_call is None

    def test_message_with_name(self):
        """Test message with name."""
        msg = Message(role=Role.FUNCTION, content="Result", name="my_function")
        assert msg.role == Role.FUNCTION
        assert msg.name == "my_function"

    def test_message_equality(self):
        """Test message equality."""
        msg1 = Message(role=Role.USER, content="Hello")
        msg2 = Message(role=Role.USER, content="Hello")
        assert msg1 == msg2

    def test_message_inequality(self):
        """Test message inequality."""
        msg1 = Message(role=Role.USER, content="Hello")
        msg2 = Message(role=Role.ASSISTANT, content="Hello")
        assert msg1 != msg2


@pytest.mark.asyncio
class TestCompletionResponse:
    """Test suite for CompletionResponse class."""

    def test_response_creation(self):
        """Test creating a completion response."""
        response = CompletionResponse(
            content="Hello",
            model="test-model",
            usage={"total_tokens": 30}
        )
        assert response.content == "Hello"
        assert response.model == "test-model"
        assert response.usage["total_tokens"] == 30

    def test_response_with_metadata(self):
        """Test response with metadata."""
        response = CompletionResponse(
            content="Hello",
            model="test-model",
            usage={"total_tokens": 30},
            metadata={"id": "test-id"}
        )
        assert response.metadata["id"] == "test-id"

    def test_response_finish_reason(self):
        """Test response with finish reason."""
        response = CompletionResponse(
            content="Hello",
            model="test-model",
            usage={"total_tokens": 30},
            finish_reason="stop"
        )
        assert response.finish_reason == "stop"


@pytest.mark.asyncio
class TestStreamChunk:
    """Test suite for StreamChunk class."""

    def test_chunk_creation(self):
        """Test creating a stream chunk."""
        chunk = StreamChunk(delta="Hello")
        assert chunk.delta == "Hello"
        assert chunk.finish_reason is None

    def test_chunk_with_finish_reason(self):
        """Test chunk with finish reason."""
        chunk = StreamChunk(delta="", finish_reason="stop")
        assert chunk.delta == ""
        assert chunk.finish_reason == "stop"

    def test_chunk_with_metadata(self):
        """Test chunk with metadata."""
        chunk = StreamChunk(delta="Hello", metadata={"index": 0})
        assert chunk.metadata["index"] == 0


@pytest.mark.asyncio
class TestProviderType:
    """Test suite for ProviderType enum."""

    def test_provider_types(self):
        """Test all provider types exist."""
        assert ProviderType.GEMINI.value == "gemini"
        assert ProviderType.OPENAI.value == "openai"
        assert ProviderType.ANTHROPIC.value == "anthropic"
        assert ProviderType.OPENROUTER.value == "openrouter"
        assert ProviderType.GROK.value == "grok"

    def test_provider_type_from_string(self):
        """Test creating provider type from string."""
        provider_type = ProviderType("gemini")
        assert provider_type == ProviderType.GEMINI


@pytest.mark.asyncio
class TestRole:
    """Test suite for Role enum."""

    def test_roles(self):
        """Test all roles exist."""
        assert Role.SYSTEM.value == "system"
        assert Role.USER.value == "user"
        assert Role.ASSISTANT.value == "assistant"
        assert Role.FUNCTION.value == "function"
        assert Role.TOOL.value == "tool"

    def test_role_from_string(self):
        """Test creating role from string."""
        role = Role("user")
        assert role == Role.USER