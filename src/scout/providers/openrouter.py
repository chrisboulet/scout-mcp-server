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
OpenRouter Provider Implementation.

This module provides the OpenRouter API provider adapter.
OpenRouter provides unified access to multiple AI models from various providers.

Following Constitution Principle #7: Provider Abstraction
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import os
import structlog
import httpx

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

# Default OpenRouter API endpoint
DEFAULT_OPENROUTER_API_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider(BaseAIProvider):
    """
    OpenRouter API provider implementation.

    OpenRouter provides unified access to models from:
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude)
    - Google (PaLM, Gemini)
    - Meta (Llama)
    - And many more...

    Supports:
    - Chat completions
    - Streaming responses
    - Model routing and fallbacks
    - Usage tracking and cost optimization
    """

    def __init__(
        self,
        provider_config: ProviderConfig,
        max_retries: int = 3,
        timeout: float = 60.0,
        api_url: Optional[str] = None
    ):
        """
        Initialize OpenRouter provider.

        Args:
            provider_config: Provider configuration from config system
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
            api_url: Optional custom API URL (defaults to OpenRouter's API)
        """
        super().__init__(
            provider_config=provider_config,
            provider_type=ProviderType.OPENROUTER,
            max_retries=max_retries,
            timeout=timeout
        )

        # Set API URL (allow override from environment or parameter)
        self.api_url = (
            api_url or
            os.getenv("OPENROUTER_API_URL") or
            DEFAULT_OPENROUTER_API_URL
        )

        # Update HTTP client with appropriate headers
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "https://github.com/BouletStratiges/SCOUT"),
                "X-Title": "SCOUT MCP Server",
                "User-Agent": "SCOUT-MCP-Server/0.1.0"
            }
        )

    def _convert_messages(
        self,
        messages: List[Message]
    ) -> List[Dict[str, Any]]:
        """
        Convert unified messages to OpenRouter format.

        OpenRouter uses OpenAI-compatible format.

        Args:
            messages: List of unified messages

        Returns:
            List of OpenRouter-formatted messages
        """
        openrouter_messages = []

        for message in messages:
            # Map role to OpenRouter format (OpenAI-compatible)
            role_map = {
                Role.SYSTEM: "system",
                Role.USER: "user",
                Role.ASSISTANT: "assistant",
                Role.FUNCTION: "function",
                Role.TOOL: "tool",
            }

            openrouter_msg = {
                "role": role_map[message.role],
                "content": message.content
            }

            # Add optional fields
            if message.name:
                openrouter_msg["name"] = message.name

            if message.function_call:
                openrouter_msg["function_call"] = message.function_call

            if message.tool_calls:
                openrouter_msg["tool_calls"] = message.tool_calls

            openrouter_messages.append(openrouter_msg)

        return openrouter_messages

    async def _make_api_call(
        self,
        messages: List[Message],
        model_config: ModelConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make API call to OpenRouter.

        Args:
            messages: List of messages to send
            model_config: Model configuration to use
            **kwargs: Additional parameters

        Returns:
            Raw API response as dictionary
        """
        try:
            # Convert messages
            openrouter_messages = self._convert_messages(messages)

            # Prepare request body
            request_body = {
                "model": model_config.id,
                "messages": openrouter_messages,
                "temperature": kwargs.get("temperature", model_config.temperature),
                "max_tokens": kwargs.get("max_tokens", model_config.max_tokens),
            }

            # Add optional parameters
            if "top_p" in kwargs:
                request_body["top_p"] = kwargs["top_p"]

            if "top_k" in kwargs:
                request_body["top_k"] = kwargs["top_k"]

            if "frequency_penalty" in kwargs:
                request_body["frequency_penalty"] = kwargs["frequency_penalty"]

            if "presence_penalty" in kwargs:
                request_body["presence_penalty"] = kwargs["presence_penalty"]

            if "stop" in kwargs:
                request_body["stop"] = kwargs["stop"]

            # Add OpenRouter-specific parameters
            if "provider" in kwargs:
                # Allow specifying preferred provider
                request_body["provider"] = kwargs["provider"]

            if "fallbacks" in kwargs:
                # Allow specifying fallback models
                request_body["fallbacks"] = kwargs["fallbacks"]

            # Make the API call
            response = await self.client.post(
                f"{self.api_url}/chat/completions",
                json=request_body
            )

            # Check for errors
            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", response.text)
                self._handle_status_code(response.status_code, error_msg)

            # Parse response
            return response.json()

        except httpx.RequestError as e:
            raise ProviderException(f"OpenRouter request failed: {e}")
        except Exception as e:
            self._handle_api_error(e)

    def _parse_response(
        self,
        raw_response: Dict[str, Any],
        model: str
    ) -> CompletionResponse:
        """
        Parse OpenRouter response into unified format.

        Args:
            raw_response: Raw API response
            model: Model identifier used

        Returns:
            Unified CompletionResponse
        """
        # Extract the first choice
        choice = raw_response.get("choices", [{}])[0]

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
            "model": raw_response.get("model"),  # Actual model used
            "object": raw_response.get("object"),
        }

        # Add OpenRouter-specific metadata if present
        if "provider" in raw_response:
            metadata["provider"] = raw_response["provider"]

        if "usage" in raw_response and "cost" in raw_response["usage"]:
            metadata["cost"] = raw_response["usage"]["cost"]

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
        Make streaming API call to OpenRouter.

        Args:
            messages: List of messages to send
            model_config: Model configuration to use
            **kwargs: Additional parameters

        Yields:
            Raw streaming chunks as dictionaries
        """
        try:
            # Convert messages
            openrouter_messages = self._convert_messages(messages)

            # Prepare request body
            request_body = {
                "model": model_config.id,
                "messages": openrouter_messages,
                "temperature": kwargs.get("temperature", model_config.temperature),
                "max_tokens": kwargs.get("max_tokens", model_config.max_tokens),
                "stream": True,
            }

            # Add optional parameters
            if "top_p" in kwargs:
                request_body["top_p"] = kwargs["top_p"]

            if "top_k" in kwargs:
                request_body["top_k"] = kwargs["top_k"]

            if "frequency_penalty" in kwargs:
                request_body["frequency_penalty"] = kwargs["frequency_penalty"]

            if "presence_penalty" in kwargs:
                request_body["presence_penalty"] = kwargs["presence_penalty"]

            if "stop" in kwargs:
                request_body["stop"] = kwargs["stop"]

            # Add OpenRouter-specific parameters
            if "provider" in kwargs:
                request_body["provider"] = kwargs["provider"]

            if "fallbacks" in kwargs:
                request_body["fallbacks"] = kwargs["fallbacks"]

            # Make streaming API call
            async with self.client.stream(
                "POST",
                f"{self.api_url}/chat/completions",
                json=request_body
            ) as response:
                # Check for errors
                if response.status_code != 200:
                    error_text = await response.aread()
                    self._handle_status_code(response.status_code, error_text.decode())

                # Stream SSE chunks
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix

                        if data == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data)
                            yield chunk
                        except json.JSONDecodeError:
                            # Skip malformed chunks
                            continue

        except httpx.RequestError as e:
            raise ProviderException(f"OpenRouter streaming request failed: {e}")
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

        # Add model info if present (OpenRouter sometimes includes this)
        if "model" in raw_chunk:
            metadata["model"] = raw_chunk["model"]

        return StreamChunk(
            delta=content,
            finish_reason=finish_reason,
            metadata=metadata
        )

    def _handle_status_code(self, status_code: int, error_msg: str):
        """
        Handle HTTP status codes from OpenRouter.

        Args:
            status_code: HTTP status code
            error_msg: Error message

        Raises:
            ProviderException: Appropriate exception based on status code
        """
        if status_code == 401:
            raise AuthenticationException(f"OpenRouter authentication failed: {error_msg}")
        elif status_code == 429:
            raise RateLimitException(f"OpenRouter rate limit exceeded: {error_msg}")
        elif status_code == 404:
            raise ModelNotAvailableException(f"OpenRouter model not found: {error_msg}")
        else:
            raise ProviderException(f"OpenRouter API error ({status_code}): {error_msg}")

    def _handle_api_error(self, error: Exception):
        """
        Convert OpenRouter API errors to provider exceptions.

        Args:
            error: The original exception

        Raises:
            ProviderException: Converted exception
        """
        error_str = str(error).lower()

        if "rate" in error_str or "limit" in error_str:
            raise RateLimitException(f"OpenRouter rate limit exceeded: {error}")
        elif "auth" in error_str or "unauthorized" in error_str:
            raise AuthenticationException(f"OpenRouter authentication failed: {error}")
        elif "model" in error_str and "not" in error_str:
            raise ModelNotAvailableException(f"OpenRouter model not available: {error}")
        else:
            raise ProviderException(f"OpenRouter API error: {error}")

    async def health_check(self) -> bool:
        """
        Check if OpenRouter provider is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to list available models
            response = await self.client.get(f"{self.api_url}/models")

            if response.status_code == 200:
                data = response.json()
                model_count = len(data.get("data", []))
                self.logger.info(
                    "OpenRouter health check passed",
                    available_models=model_count
                )
                return True
            else:
                self.logger.warning(
                    "OpenRouter health check failed",
                    status_code=response.status_code
                )
                return False

        except Exception as e:
            self.logger.error(
                "OpenRouter health check failed",
                error=str(e)
            )
            return False

    async def list_available_models(self) -> List[str]:
        """
        List available models from OpenRouter.

        Returns:
            List of available model IDs
        """
        try:
            response = await self.client.get(f"{self.api_url}/models")

            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
                return [model["id"] for model in models]
            else:
                self.logger.warning(
                    "Failed to list OpenRouter models",
                    status_code=response.status_code
                )
                return []

        except Exception as e:
            self.logger.error(
                "Error listing OpenRouter models",
                error=str(e)
            )
            return []