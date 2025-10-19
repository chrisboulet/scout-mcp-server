"""
Grok Provider Implementation.

This module provides the X.AI Grok API provider adapter.
Grok offers high-performance language models with real-time information access.

Following Constitution Principle #7: Provider Abstraction
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import os
import json
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

# Default Grok API endpoint
DEFAULT_GROK_API_URL = "https://api.x.ai/v1"


class GrokProvider(BaseAIProvider):
    """
    X.AI Grok API provider implementation.

    Grok provides:
    - High-performance language models
    - Real-time information access
    - OpenAI-compatible API
    - Fast inference speeds

    Supports:
    - Chat completions
    - Streaming responses
    - System messages
    - Function calling (planned)
    """

    def __init__(
        self,
        provider_config: ProviderConfig,
        max_retries: int = 3,
        timeout: float = 60.0,
        api_url: Optional[str] = None
    ):
        """
        Initialize Grok provider.

        Args:
            provider_config: Provider configuration from config system
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
            api_url: Optional custom API URL (defaults to X.AI's API)
        """
        super().__init__(
            provider_config=provider_config,
            provider_type=ProviderType.GROK,
            max_retries=max_retries,
            timeout=timeout
        )

        # Set API URL (allow override from environment or parameter)
        self.api_url = (
            api_url or
            os.getenv("GROK_API_URL") or
            DEFAULT_GROK_API_URL
        )

        # Update HTTP client with appropriate headers
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "SCOUT-MCP-Server/0.1.0"
            }
        )

    def _convert_messages(
        self,
        messages: List[Message]
    ) -> List[Dict[str, Any]]:
        """
        Convert unified messages to Grok format.

        Grok uses OpenAI-compatible format.

        Args:
            messages: List of unified messages

        Returns:
            List of Grok-formatted messages
        """
        grok_messages = []

        for message in messages:
            # Map role to Grok format (OpenAI-compatible)
            role_map = {
                Role.SYSTEM: "system",
                Role.USER: "user",
                Role.ASSISTANT: "assistant",
                Role.FUNCTION: "function",
                Role.TOOL: "tool",
            }

            grok_msg = {
                "role": role_map[message.role],
                "content": message.content
            }

            # Add optional fields
            if message.name:
                grok_msg["name"] = message.name

            if message.function_call:
                grok_msg["function_call"] = message.function_call

            if message.tool_calls:
                grok_msg["tool_calls"] = message.tool_calls

            grok_messages.append(grok_msg)

        return grok_messages

    async def _make_api_call(
        self,
        messages: List[Message],
        model_config: ModelConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make API call to Grok.

        Args:
            messages: List of messages to send
            model_config: Model configuration to use
            **kwargs: Additional parameters

        Returns:
            Raw API response as dictionary
        """
        try:
            # Convert messages
            grok_messages = self._convert_messages(messages)

            # Prepare request body
            request_body = {
                "model": model_config.id,
                "messages": grok_messages,
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

            if "response_format" in kwargs:
                request_body["response_format"] = kwargs["response_format"]

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
            raise ProviderException(f"Grok request failed: {e}")
        except Exception as e:
            self._handle_api_error(e)

    def _parse_response(
        self,
        raw_response: Dict[str, Any],
        model: str
    ) -> CompletionResponse:
        """
        Parse Grok response into unified format.

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
            "model": raw_response.get("model"),
            "object": raw_response.get("object"),
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
        Make streaming API call to Grok.

        Args:
            messages: List of messages to send
            model_config: Model configuration to use
            **kwargs: Additional parameters

        Yields:
            Raw streaming chunks as dictionaries
        """
        try:
            # Convert messages
            grok_messages = self._convert_messages(messages)

            # Prepare request body
            request_body = {
                "model": model_config.id,
                "messages": grok_messages,
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

            if "response_format" in kwargs:
                request_body["response_format"] = kwargs["response_format"]

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
            raise ProviderException(f"Grok streaming request failed: {e}")
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

    def _handle_status_code(self, status_code: int, error_msg: str):
        """
        Handle HTTP status codes from Grok.

        Args:
            status_code: HTTP status code
            error_msg: Error message

        Raises:
            ProviderException: Appropriate exception based on status code
        """
        if status_code == 401:
            raise AuthenticationException(f"Grok authentication failed: {error_msg}")
        elif status_code == 429:
            raise RateLimitException(f"Grok rate limit exceeded: {error_msg}")
        elif status_code == 404:
            raise ModelNotAvailableException(f"Grok model not found: {error_msg}")
        elif status_code == 400:
            raise ProviderException(f"Grok bad request: {error_msg}")
        else:
            raise ProviderException(f"Grok API error ({status_code}): {error_msg}")

    def _handle_api_error(self, error: Exception):
        """
        Convert Grok API errors to provider exceptions.

        Args:
            error: The original exception

        Raises:
            ProviderException: Converted exception
        """
        error_str = str(error).lower()

        if "rate" in error_str or "limit" in error_str:
            raise RateLimitException(f"Grok rate limit exceeded: {error}")
        elif "auth" in error_str or "unauthorized" in error_str:
            raise AuthenticationException(f"Grok authentication failed: {error}")
        elif "model" in error_str and ("not" in error_str or "invalid" in error_str):
            raise ModelNotAvailableException(f"Grok model not available: {error}")
        else:
            raise ProviderException(f"Grok API error: {error}")

    async def health_check(self) -> bool:
        """
        Check if Grok provider is healthy.

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
                    "Grok health check passed",
                    available_models=model_count
                )
                return True
            else:
                self.logger.warning(
                    "Grok health check failed",
                    status_code=response.status_code
                )
                return False

        except Exception as e:
            self.logger.error(
                "Grok health check failed",
                error=str(e)
            )
            return False

    async def list_available_models(self) -> List[str]:
        """
        List available models from Grok.

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
                    "Failed to list Grok models",
                    status_code=response.status_code
                )
                return []

        except Exception as e:
            self.logger.error(
                "Error listing Grok models",
                error=str(e)
            )
            return []

    def supports_realtime_info(self, model: Optional[str] = None) -> bool:
        """
        Check if model supports real-time information access.

        Grok models are designed with real-time information capabilities.

        Args:
            model: Model name to check

        Returns:
            True if model supports real-time info
        """
        # All Grok models support real-time information
        return True

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

        # Check for models with function support
        # This may need to be updated as Grok adds features
        function_models = ["grok-2", "grok-beta"]

        return any(fm in model_id for fm in function_models)