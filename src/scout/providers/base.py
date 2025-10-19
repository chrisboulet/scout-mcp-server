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
Base Provider Module - Abstract interface for all AI providers.

This module defines the contract that all AI provider implementations must follow.
Provides unified interface for chat, completion, and generation operations.
Includes built-in error handling, retry logic, and response normalization.

Following Constitution Principle #2: Modular Architecture
Following Constitution Principle #5: Robust Error Handling
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Union, AsyncIterator, Literal
from enum import Enum
import asyncio
from datetime import datetime
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)
import httpx

from scout.config.models import ModelConfig, ProviderConfig
from scout.config.exceptions import ConfigurationError

# Configure structured logging
logger = structlog.get_logger(__name__)


class ProviderType(Enum):
    """Supported AI provider types."""
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    GROK = "grok"


class Role(Enum):
    """Message role types."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


@dataclass
class Message:
    """
    Unified message format for all providers.

    Attributes:
        role: The role of the message sender
        content: The message content
        name: Optional name for function/tool messages
        function_call: Optional function call details
        tool_calls: Optional tool calls
        metadata: Additional provider-specific metadata
    """
    role: Role
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format."""
        data = {
            "role": self.role.value,
            "content": self.content
        }
        if self.name:
            data["name"] = self.name
        if self.function_call:
            data["function_call"] = self.function_call
        if self.tool_calls:
            data["tool_calls"] = self.tool_calls
        if self.metadata:
            data.update(self.metadata)
        return data


@dataclass
class CompletionResponse:
    """
    Unified response format for all providers.

    Attributes:
        content: The generated content
        model: Model identifier used
        usage: Token usage statistics
        finish_reason: Why generation stopped
        metadata: Additional provider-specific data
    """
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        """Get total token count."""
        return self.usage.get("total_tokens", 0)

    @property
    def completion_tokens(self) -> int:
        """Get completion token count."""
        return self.usage.get("completion_tokens", 0)

    @property
    def prompt_tokens(self) -> int:
        """Get prompt token count."""
        return self.usage.get("prompt_tokens", 0)


@dataclass
class StreamChunk:
    """
    Chunk of streaming response.

    Attributes:
        delta: The incremental content
        finish_reason: Why streaming stopped (if applicable)
        metadata: Additional chunk metadata
    """
    delta: str
    finish_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProviderException(Exception):
    """Base exception for provider-related errors."""
    pass


class RateLimitException(ProviderException):
    """Raised when provider rate limit is exceeded."""
    pass


class AuthenticationException(ProviderException):
    """Raised when provider authentication fails."""
    pass


class ModelNotAvailableException(ProviderException):
    """Raised when requested model is not available."""
    pass


class BaseAIProvider(ABC):
    """
    Abstract base class for all AI provider implementations.

    This class defines the contract that all providers must implement.
    Includes built-in retry logic, error handling, and logging.

    Constitution Principles:
    - #2: Modular Architecture - Clear separation of provider logic
    - #5: Robust Error Handling - Built-in retry and error management
    - #6: Structured Logging - Comprehensive logging with correlation
    - #7: Provider Abstraction - Unified interface for all providers
    """

    def __init__(
        self,
        provider_config: ProviderConfig,
        provider_type: ProviderType,
        max_retries: int = 3,
        timeout: float = 60.0
    ):
        """
        Initialize the base provider.

        Args:
            provider_config: Provider configuration from config system
            provider_type: Type of provider
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
        """
        self.config = provider_config
        self.provider_type = provider_type
        self.max_retries = max_retries
        self.timeout = timeout
        self.logger = logger.bind(provider=provider_type.value)

        # HTTP client for API calls
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": "SCOUT-MCP-Server/0.1.0"}
        )

        # Track metrics
        self._request_count = 0
        self._error_count = 0
        self._total_tokens = 0

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()

    async def initialize(self):
        """
        Initialize provider resources.
        Override in subclasses for custom initialization.
        """
        self.logger.info("Provider initialized")

    async def cleanup(self):
        """
        Clean up provider resources.
        Override in subclasses for custom cleanup.
        """
        await self.client.aclose()
        self.logger.info(
            "Provider cleanup complete",
            request_count=self._request_count,
            error_count=self._error_count,
            total_tokens=self._total_tokens
        )

    @abstractmethod
    async def _make_api_call(
        self,
        messages: List[Message],
        model_config: ModelConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make the actual API call to the provider.

        This method must be implemented by each provider.

        Args:
            messages: List of messages to send
            model_config: Model configuration to use
            **kwargs: Additional provider-specific parameters

        Returns:
            Raw API response as dictionary
        """
        pass

    @abstractmethod
    def _parse_response(
        self,
        raw_response: Dict[str, Any],
        model: str
    ) -> CompletionResponse:
        """
        Parse provider response into unified format.

        This method must be implemented by each provider.

        Args:
            raw_response: Raw API response
            model: Model identifier used

        Returns:
            Unified CompletionResponse
        """
        pass

    @abstractmethod
    async def _stream_api_call(
        self,
        messages: List[Message],
        model_config: ModelConfig,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Make streaming API call to the provider.

        This method must be implemented by each provider.

        Args:
            messages: List of messages to send
            model_config: Model configuration to use
            **kwargs: Additional provider-specific parameters

        Yields:
            Raw streaming chunks as dictionaries
        """
        pass

    @abstractmethod
    def _parse_stream_chunk(
        self,
        raw_chunk: Dict[str, Any]
    ) -> Optional[StreamChunk]:
        """
        Parse streaming chunk into unified format.

        This method must be implemented by each provider.

        Args:
            raw_chunk: Raw streaming chunk

        Returns:
            Unified StreamChunk or None if chunk should be skipped
        """
        pass

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(RateLimitException),
        before_sleep=before_sleep_log(logger, structlog.INFO),
        after=after_log(logger, structlog.INFO)
    )
    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> CompletionResponse:
        """
        Send chat messages and get response.

        Args:
            messages: List of messages in the conversation
            model: Model to use (defaults to provider's default)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            Unified completion response

        Raises:
            ProviderException: On API errors
            RateLimitException: When rate limited
            AuthenticationException: On auth failures
        """
        # Get model configuration
        model_config = self._get_model_config(model)

        # Apply defaults
        if temperature is None:
            temperature = model_config.temperature
        if max_tokens is None:
            max_tokens = model_config.max_tokens

        # Log request
        request_id = self._generate_request_id()
        self.logger.info(
            "Chat request",
            request_id=request_id,
            model=model_config.id,
            message_count=len(messages),
            temperature=temperature,
            max_tokens=max_tokens
        )

        try:
            # Make API call
            self._request_count += 1
            raw_response = await self._make_api_call(
                messages=messages,
                model_config=model_config,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            # Parse response
            response = self._parse_response(raw_response, model_config.id)

            # Update metrics
            self._total_tokens += response.total_tokens

            # Log success
            self.logger.info(
                "Chat response",
                request_id=request_id,
                tokens_used=response.total_tokens,
                finish_reason=response.finish_reason
            )

            return response

        except Exception as e:
            self._error_count += 1
            self.logger.error(
                "Chat request failed",
                request_id=request_id,
                error=str(e),
                exc_info=True
            )
            raise

    async def chat_stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream chat response chunks.

        Args:
            messages: List of messages in the conversation
            model: Model to use (defaults to provider's default)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Yields:
            Streaming response chunks

        Raises:
            ProviderException: On API errors
        """
        # Get model configuration
        model_config = self._get_model_config(model)

        # Apply defaults
        if temperature is None:
            temperature = model_config.temperature
        if max_tokens is None:
            max_tokens = model_config.max_tokens

        # Log request
        request_id = self._generate_request_id()
        self.logger.info(
            "Stream request",
            request_id=request_id,
            model=model_config.id,
            message_count=len(messages)
        )

        try:
            # Stream API call
            self._request_count += 1
            total_chunks = 0

            async for raw_chunk in self._stream_api_call(
                messages=messages,
                model_config=model_config,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            ):
                # Parse chunk
                chunk = self._parse_stream_chunk(raw_chunk)
                if chunk:
                    total_chunks += 1
                    yield chunk

            # Log completion
            self.logger.info(
                "Stream complete",
                request_id=request_id,
                total_chunks=total_chunks
            )

        except Exception as e:
            self._error_count += 1
            self.logger.error(
                "Stream request failed",
                request_id=request_id,
                error=str(e),
                exc_info=True
            )
            raise

    async def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Simple text completion.

        Args:
            prompt: The prompt to complete
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            Completed text
        """
        # Convert to message format
        messages = [Message(role=Role.USER, content=prompt)]

        # Get completion
        response = await self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        return response.content

    def _get_model_config(self, model: Optional[str] = None) -> ModelConfig:
        """
        Get model configuration by name.

        Args:
            model: Model name or None for default

        Returns:
            Model configuration

        Raises:
            ModelNotAvailableException: If model not found
        """
        if model is None:
            # Use first available model as default
            if not self.config.models:
                raise ModelNotAvailableException(
                    f"No models configured for provider {self.provider_type.value}"
                )
            return next(iter(self.config.models.values()))

        if model not in self.config.models:
            raise ModelNotAvailableException(
                f"Model '{model}' not available for provider {self.provider_type.value}"
            )

        return self.config.models[model]

    def _generate_request_id(self) -> str:
        """Generate unique request ID for tracking."""
        import uuid
        return str(uuid.uuid4())[:8]

    async def health_check(self) -> bool:
        """
        Check if provider is healthy and accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try simple completion
            await self.complete(
                prompt="Hello",
                max_tokens=1
            )
            return True
        except Exception as e:
            self.logger.warning(
                "Health check failed",
                error=str(e)
            )
            return False

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get provider metrics.

        Returns:
            Dictionary of metrics
        """
        return {
            "provider": self.provider_type.value,
            "request_count": self._request_count,
            "error_count": self._error_count,
            "total_tokens": self._total_tokens,
            "error_rate": self._error_count / max(self._request_count, 1),
            "average_tokens": self._total_tokens / max(self._request_count, 1)
        }