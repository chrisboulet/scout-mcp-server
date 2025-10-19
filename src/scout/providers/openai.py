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
OpenAI Provider Implementation.

This module provides the OpenAI API provider adapter.
Supports chat, streaming, function calling, and vision with OpenAI models.

Following Constitution Principle #7: Provider Abstraction
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessage,
    ChatCompletionChunk,
)
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


class OpenAIProvider(BaseAIProvider):
    """
    OpenAI API provider implementation.

    Supports:
    - GPT-4, GPT-4o, GPT-4o-mini, o3-mini models
    - Chat completions with system messages
    - Streaming responses
    - Function calling
    - Vision capabilities (for models that support it)
    - JSON mode
    """

    def __init__(
        self,
        provider_config: ProviderConfig,
        max_retries: int = 3,
        timeout: float = 60.0
    ):
        """
        Initialize OpenAI provider.

        Args:
            provider_config: Provider configuration from config system
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
        """
        super().__init__(
            provider_config=provider_config,
            provider_type=ProviderType.OPENAI,
            max_retries=max_retries,
            timeout=timeout
        )

        # Initialize OpenAI client
        self.client = AsyncOpenAI(
            api_key=self.config.api_key,
            timeout=timeout,
            max_retries=max_retries,
        )

    async def cleanup(self):
        """Clean up OpenAI provider resources."""
        # Close the OpenAI client
        await self.client.close()
        await super().cleanup()

    def _convert_messages(
        self,
        messages: List[Message]
    ) -> List[Dict[str, Any]]:
        """
        Convert unified messages to OpenAI format.

        Args:
            messages: List of unified messages

        Returns:
            List of OpenAI-formatted messages
        """
        openai_messages = []

        for message in messages:
            # Map role to OpenAI format
            role_map = {
                Role.SYSTEM: "system",
                Role.USER: "user",
                Role.ASSISTANT: "assistant",
                Role.FUNCTION: "function",
                Role.TOOL: "tool",
            }

            openai_msg = {
                "role": role_map[message.role],
                "content": message.content
            }

            # Add optional fields
            if message.name:
                openai_msg["name"] = message.name

            if message.function_call:
                openai_msg["function_call"] = message.function_call

            if message.tool_calls:
                openai_msg["tool_calls"] = message.tool_calls

            openai_messages.append(openai_msg)

        return openai_messages

    async def _make_api_call(
        self,
        messages: List[Message],
        model_config: ModelConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make API call to OpenAI.

        Args:
            messages: List of messages to send
            model_config: Model configuration to use
            **kwargs: Additional parameters

        Returns:
            Raw API response as dictionary
        """
        try:
            # Convert messages
            openai_messages = self._convert_messages(messages)

            # Prepare parameters
            params = {
                "model": model_config.id,
                "messages": openai_messages,
                "temperature": kwargs.get("temperature", model_config.temperature),
                "max_tokens": kwargs.get("max_tokens", model_config.max_tokens),
            }

            # Add optional parameters
            if "top_p" in kwargs:
                params["top_p"] = kwargs["top_p"]

            if "frequency_penalty" in kwargs:
                params["frequency_penalty"] = kwargs["frequency_penalty"]

            if "presence_penalty" in kwargs:
                params["presence_penalty"] = kwargs["presence_penalty"]

            if "response_format" in kwargs:
                params["response_format"] = kwargs["response_format"]

            if "tools" in kwargs:
                params["tools"] = kwargs["tools"]

            if "tool_choice" in kwargs:
                params["tool_choice"] = kwargs["tool_choice"]

            # Make the API call
            response: ChatCompletion = await self.client.chat.completions.create(
                **params
            )

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
        Parse OpenAI response into unified format.

        Args:
            raw_response: Raw API response
            model: Model identifier used

        Returns:
            Unified CompletionResponse
        """
        # Extract the first choice
        choice = raw_response["choices"][0] if raw_response.get("choices") else {}

        # Extract message content
        message = choice.get("message", {})
        content = message.get("content", "")

        # Extract usage
        usage_data = raw_response.get("usage", {})
        usage = {
            "prompt_tokens": usage_data.get("prompt_tokens", 0),
            "completion_tokens": usage_data.get("completion_tokens", 0),
            "total_tokens": usage_data.get("total_tokens", 0),
        }

        # Get finish reason
        finish_reason = choice.get("finish_reason")

        # Build metadata
        metadata = {
            "id": raw_response.get("id"),
            "created": raw_response.get("created"),
            "system_fingerprint": raw_response.get("system_fingerprint"),
        }

        # Add function/tool calls if present
        if message.get("function_call"):
            metadata["function_call"] = message["function_call"]

        if message.get("tool_calls"):
            metadata["tool_calls"] = message["tool_calls"]

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
        Make streaming API call to OpenAI.

        Args:
            messages: List of messages to send
            model_config: Model configuration to use
            **kwargs: Additional parameters

        Yields:
            Raw streaming chunks as dictionaries
        """
        try:
            # Convert messages
            openai_messages = self._convert_messages(messages)

            # Prepare parameters
            params = {
                "model": model_config.id,
                "messages": openai_messages,
                "temperature": kwargs.get("temperature", model_config.temperature),
                "max_tokens": kwargs.get("max_tokens", model_config.max_tokens),
                "stream": True,
            }

            # Add optional parameters
            if "top_p" in kwargs:
                params["top_p"] = kwargs["top_p"]

            if "frequency_penalty" in kwargs:
                params["frequency_penalty"] = kwargs["frequency_penalty"]

            if "presence_penalty" in kwargs:
                params["presence_penalty"] = kwargs["presence_penalty"]

            if "response_format" in kwargs:
                params["response_format"] = kwargs["response_format"]

            if "tools" in kwargs:
                params["tools"] = kwargs["tools"]

            if "tool_choice" in kwargs:
                params["tool_choice"] = kwargs["tool_choice"]

            # Make streaming API call
            stream = await self.client.chat.completions.create(**params)

            # Stream chunks
            async for chunk in stream:
                yield chunk.model_dump()

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
        # Extract delta from first choice
        choices = raw_chunk.get("choices", [])
        if not choices:
            return None

        choice = choices[0]
        delta = choice.get("delta", {})

        # Extract content
        content = delta.get("content", "")
        if not content and "function_call" not in delta and "tool_calls" not in delta:
            return None

        # Get finish reason
        finish_reason = choice.get("finish_reason")

        # Build metadata
        metadata = {}
        if "function_call" in delta:
            metadata["function_call"] = delta["function_call"]

        if "tool_calls" in delta:
            metadata["tool_calls"] = delta["tool_calls"]

        return StreamChunk(
            delta=content,
            finish_reason=finish_reason,
            metadata=metadata
        )

    def _handle_api_error(self, error: Exception):
        """
        Convert OpenAI API errors to provider exceptions.

        Args:
            error: The original exception

        Raises:
            ProviderException: Converted exception
        """
        error_str = str(error).lower()
        error_type = type(error).__name__

        # Check for specific OpenAI exceptions
        if "RateLimitError" in error_type or "rate_limit" in error_str:
            raise RateLimitException(f"OpenAI rate limit exceeded: {error}")
        elif "AuthenticationError" in error_type or "authentication" in error_str:
            raise AuthenticationException(f"OpenAI authentication failed: {error}")
        elif "NotFoundError" in error_type or "model_not_found" in error_str:
            raise ModelNotAvailableException(f"OpenAI model not available: {error}")
        else:
            raise ProviderException(f"OpenAI API error: {error}")

    async def health_check(self) -> bool:
        """
        Check if OpenAI provider is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # List available models to verify API key
            models = await self.client.models.list()

            if models.data:
                self.logger.info(
                    "OpenAI health check passed",
                    available_models=len(models.data)
                )
                return True
            else:
                self.logger.warning("OpenAI health check: no models available")
                return False

        except Exception as e:
            self.logger.error(
                "OpenAI health check failed",
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

        # GPT-4 Vision and GPT-4o models support vision
        vision_models = ["gpt-4-vision", "gpt-4o", "gpt-4o-mini"]

        return any(vm in model_id for vm in vision_models)

    def supports_functions(self, model: Optional[str] = None) -> bool:
        """
        Check if model supports function calling.

        Args:
            model: Model name to check

        Returns:
            True if model supports functions
        """
        model_config = self._get_model_config(model)
        model_id = model_config.id.lower()

        # Most modern OpenAI models support function calling
        # except the base GPT-3.5 models
        function_models = ["gpt-4", "gpt-3.5-turbo-1106", "gpt-4o", "o3"]

        return any(fm in model_id for fm in function_models)

    def supports_json_mode(self, model: Optional[str] = None) -> bool:
        """
        Check if model supports JSON mode.

        Args:
            model: Model name to check

        Returns:
            True if model supports JSON mode
        """
        model_config = self._get_model_config(model)
        model_id = model_config.id.lower()

        # Models that support JSON mode
        json_models = ["gpt-4-1106", "gpt-4o", "gpt-3.5-turbo-1106", "o3"]

        return any(jm in model_id for jm in json_models)