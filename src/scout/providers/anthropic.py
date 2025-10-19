"""
Anthropic Provider Implementation.

This module provides the Anthropic Claude API provider adapter.
Supports chat, streaming, and vision with Claude models.

Following Constitution Principle #7: Provider Abstraction
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json
from anthropic import AsyncAnthropic
from anthropic.types import Message as AnthropicMessage
import structlog

from scout.providers.base import (
    BaseAIProvider,
    Message,
    CompletionResponse,
    StreamChunk,
    Role,
    ProviderType,
    ProviderException,
    RateLimitException,
    AuthenticationException,
    ModelNotAvailableException,
)
from scout.config.models import ModelConfig, ProviderConfig

# Configure structured logging
logger = structlog.get_logger(__name__)


class AnthropicProvider(BaseAIProvider):
    """
    Anthropic Claude API provider implementation.

    Supports:
    - Claude 3 family (Opus, Sonnet, Haiku)
    - Claude 3.5 Sonnet
    - Chat completions with system messages
    - Streaming responses
    - Vision capabilities
    - Long context windows
    """

    def __init__(
        self,
        provider_config: ProviderConfig,
        max_retries: int = 3,
        timeout: float = 60.0
    ):
        """
        Initialize Anthropic provider.

        Args:
            provider_config: Provider configuration from config system
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
        """
        super().__init__(
            provider_config=provider_config,
            provider_type=ProviderType.ANTHROPIC,
            max_retries=max_retries,
            timeout=timeout
        )

        # Initialize Anthropic client
        self.client = AsyncAnthropic(
            api_key=self.config.api_key,
            timeout=timeout,
            max_retries=max_retries,
        )

    async def cleanup(self):
        """Clean up Anthropic provider resources."""
        # Close the Anthropic client
        await self.client.close()
        await super().cleanup()

    def _convert_messages(
        self,
        messages: List[Message]
    ) -> tuple[Optional[str], List[Dict[str, Any]]]:
        """
        Convert unified messages to Anthropic format.

        Anthropic has specific requirements:
        - System message is passed separately
        - Messages must alternate between user and assistant
        - Content can be string or list of content blocks

        Args:
            messages: List of unified messages

        Returns:
            Tuple of (system_message, anthropic_messages)
        """
        system_message = None
        anthropic_messages = []

        for message in messages:
            if message.role == Role.SYSTEM:
                # Anthropic uses system message separately
                system_message = message.content
            else:
                # Map role to Anthropic format
                role_map = {
                    Role.USER: "user",
                    Role.ASSISTANT: "assistant",
                    # Anthropic doesn't have function/tool roles, map to assistant
                    Role.FUNCTION: "assistant",
                    Role.TOOL: "assistant",
                }

                anthropic_msg = {
                    "role": role_map[message.role],
                    "content": message.content
                }

                anthropic_messages.append(anthropic_msg)

        # Ensure messages alternate between user and assistant
        # Anthropic requires this strict alternation
        cleaned_messages = self._ensure_alternation(anthropic_messages)

        return system_message, cleaned_messages

    def _ensure_alternation(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Ensure messages alternate between user and assistant.

        Anthropic requires strict alternation. This method
        combines consecutive messages from the same role.

        Args:
            messages: List of messages

        Returns:
            List of properly alternating messages
        """
        if not messages:
            return messages

        cleaned = []
        current_role = None
        current_content = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == current_role:
                # Combine with previous message
                current_content.append(content)
            else:
                # Save previous message if exists
                if current_role is not None:
                    combined_content = "\n\n".join(current_content)
                    cleaned.append({
                        "role": current_role,
                        "content": combined_content
                    })

                # Start new message
                current_role = role
                current_content = [content]

        # Don't forget the last message
        if current_role is not None:
            combined_content = "\n\n".join(current_content)
            cleaned.append({
                "role": current_role,
                "content": combined_content
            })

        # Ensure it starts with user message
        if cleaned and cleaned[0]["role"] != "user":
            # Prepend a user message
            cleaned.insert(0, {
                "role": "user",
                "content": "Please respond to the following:"
            })

        # Ensure it ends with user message (Anthropic requirement)
        if cleaned and cleaned[-1]["role"] != "user":
            # If last message is assistant, add a continuation prompt
            cleaned.append({
                "role": "user",
                "content": "Please continue."
            })

        return cleaned

    async def _make_api_call(
        self,
        messages: List[Message],
        model_config: ModelConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make API call to Anthropic.

        Args:
            messages: List of messages to send
            model_config: Model configuration to use
            **kwargs: Additional parameters

        Returns:
            Raw API response as dictionary
        """
        try:
            # Convert messages
            system_message, anthropic_messages = self._convert_messages(messages)

            # Prepare parameters
            params = {
                "model": model_config.id,
                "messages": anthropic_messages,
                "max_tokens": kwargs.get("max_tokens", model_config.max_tokens),
            }

            # Add system message if present
            if system_message:
                params["system"] = system_message

            # Add temperature if specified
            temperature = kwargs.get("temperature", model_config.temperature)
            if temperature is not None:
                params["temperature"] = temperature

            # Add optional parameters
            if "top_p" in kwargs:
                params["top_p"] = kwargs["top_p"]

            if "top_k" in kwargs:
                params["top_k"] = kwargs["top_k"]

            if "stop_sequences" in kwargs:
                params["stop_sequences"] = kwargs["stop_sequences"]

            # Make the API call
            response: AnthropicMessage = await self.client.messages.create(**params)

            # Convert to dictionary
            return response.model_dump()

        except Exception as e:
            self._handle_api_error(e)

    def _parse_response(
        self,
        raw_response: Dict[str, Any],
        model: str
    ) -> CompletionResponse:
        """
        Parse Anthropic response into unified format.

        Args:
            raw_response: Raw API response
            model: Model identifier used

        Returns:
            Unified CompletionResponse
        """
        # Extract content from content blocks
        content_blocks = raw_response.get("content", [])
        content = ""

        for block in content_blocks:
            if block.get("type") == "text":
                content += block.get("text", "")

        # Extract usage
        usage_data = raw_response.get("usage", {})
        usage = {
            "prompt_tokens": usage_data.get("input_tokens", 0),
            "completion_tokens": usage_data.get("output_tokens", 0),
            "total_tokens": (
                usage_data.get("input_tokens", 0) +
                usage_data.get("output_tokens", 0)
            ),
        }

        # Get stop reason
        finish_reason = raw_response.get("stop_reason")

        # Build metadata
        metadata = {
            "id": raw_response.get("id"),
            "type": raw_response.get("type"),
            "role": raw_response.get("role"),
            "stop_sequence": raw_response.get("stop_sequence"),
        }

        return CompletionResponse(
            content=content,
            model=model,
            usage=usage,
            finish_reason=finish_reason,
            metadata=metadata
        )

    async def _stream_api_call(
        self,
        messages: List[Message],
        model_config: ModelConfig,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Make streaming API call to Anthropic.

        Args:
            messages: List of messages to send
            model_config: Model configuration to use
            **kwargs: Additional parameters

        Yields:
            Raw streaming chunks as dictionaries
        """
        try:
            # Convert messages
            system_message, anthropic_messages = self._convert_messages(messages)

            # Prepare parameters
            params = {
                "model": model_config.id,
                "messages": anthropic_messages,
                "max_tokens": kwargs.get("max_tokens", model_config.max_tokens),
            }

            # Add system message if present
            if system_message:
                params["system"] = system_message

            # Add temperature if specified
            temperature = kwargs.get("temperature", model_config.temperature)
            if temperature is not None:
                params["temperature"] = temperature

            # Add optional parameters
            if "top_p" in kwargs:
                params["top_p"] = kwargs["top_p"]

            if "top_k" in kwargs:
                params["top_k"] = kwargs["top_k"]

            if "stop_sequences" in kwargs:
                params["stop_sequences"] = kwargs["stop_sequences"]

            # Make streaming API call
            async with self.client.messages.stream(**params) as stream:
                async for chunk in stream:
                    # Convert chunk to dictionary
                    if hasattr(chunk, "model_dump"):
                        yield chunk.model_dump()
                    else:
                        # Handle different chunk types
                        yield {
                            "type": getattr(chunk, "type", "unknown"),
                            "delta": getattr(chunk, "delta", {}),
                        }

        except Exception as e:
            self._handle_api_error(e)

    def _parse_stream_chunk(
        self,
        raw_chunk: Dict[str, Any]
    ) -> Optional[StreamChunk]:
        """
        Parse streaming chunk into unified format.

        Args:
            raw_chunk: Raw streaming chunk

        Returns:
            Unified StreamChunk or None if chunk should be skipped
        """
        # Handle different event types
        chunk_type = raw_chunk.get("type")

        if chunk_type == "content_block_delta":
            # Extract text delta
            delta = raw_chunk.get("delta", {})
            text = delta.get("text", "")

            if text:
                return StreamChunk(delta=text)

        elif chunk_type == "message_stop":
            # Stream ended
            return StreamChunk(
                delta="",
                finish_reason=raw_chunk.get("stop_reason")
            )

        # Skip other chunk types
        return None

    def _handle_api_error(self, error: Exception):
        """
        Convert Anthropic API errors to provider exceptions.

        Args:
            error: The original exception

        Raises:
            ProviderException: Converted exception
        """
        error_str = str(error).lower()
        error_type = type(error).__name__

        # Check for specific Anthropic exceptions
        if "RateLimitError" in error_type or "rate_limit" in error_str:
            raise RateLimitException(f"Anthropic rate limit exceeded: {error}")
        elif "AuthenticationError" in error_type or "authentication" in error_str:
            raise AuthenticationException(f"Anthropic authentication failed: {error}")
        elif "NotFoundError" in error_type or "model_not_found" in error_str:
            raise ModelNotAvailableException(f"Anthropic model not available: {error}")
        else:
            raise ProviderException(f"Anthropic API error: {error}")

    async def health_check(self) -> bool:
        """
        Check if Anthropic provider is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try a minimal completion
            response = await self.client.messages.create(
                model="claude-3-haiku-20240307",  # Use cheapest model
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=1
            )

            if response:
                self.logger.info("Anthropic health check passed")
                return True
            else:
                self.logger.warning("Anthropic health check: no response")
                return False

        except Exception as e:
            self.logger.error(
                "Anthropic health check failed",
                error=str(e)
            )
            return False

    def supports_vision(self, model: Optional[str] = None) -> bool:
        """
        Check if model supports vision/image inputs.

        Args:
            model: Model name to check

        Returns:
            True if model supports vision
        """
        model_config = self._get_model_config(model)
        model_id = model_config.id.lower()

        # All Claude 3 models support vision
        vision_models = ["claude-3", "claude-3.5"]

        return any(vm in model_id for vm in vision_models)

    def supports_long_context(self, model: Optional[str] = None) -> bool:
        """
        Check if model supports long context windows.

        Args:
            model: Model name to check

        Returns:
            True if model supports long context (>100k tokens)
        """
        model_config = self._get_model_config(model)
        model_id = model_config.id.lower()

        # Claude models with 100k+ context
        long_context_models = ["claude-3-opus", "claude-3-sonnet", "claude-3.5-sonnet"]

        return any(lcm in model_id for lcm in long_context_models)