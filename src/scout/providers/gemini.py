"""
Gemini Provider Implementation.

This module provides the Google Gemini AI provider adapter.
Supports chat, streaming, and function calling with Gemini models.

Following Constitution Principle #7: Provider Abstraction
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json
from dataclasses import dataclass
import google.generativeai as genai
from google.generativeai.types import (
    GenerationConfig,
    HarmCategory,
    HarmBlockThreshold,
    ContentType,
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


class GeminiProvider(BaseAIProvider):
    """
    Google Gemini AI provider implementation.

    Supports:
    - Chat completions with system messages
    - Streaming responses
    - Function calling
    - Vision capabilities (for models that support it)
    - Safety settings configuration
    """

    def __init__(
        self,
        provider_config: ProviderConfig,
        max_retries: int = 3,
        timeout: float = 60.0
    ):
        """
        Initialize Gemini provider.

        Args:
            provider_config: Provider configuration from config system
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
        """
        super().__init__(
            provider_config=provider_config,
            provider_type=ProviderType.GEMINI,
            max_retries=max_retries,
            timeout=timeout
        )

        # Configure Gemini API
        genai.configure(api_key=self.config.api_key)

        # Store model instances
        self._models: Dict[str, genai.GenerativeModel] = {}

        # Default safety settings (can be overridden)
        self._safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

    async def initialize(self):
        """Initialize Gemini provider resources."""
        await super().initialize()

        # Pre-load models
        for model_name, model_config in self.config.models.items():
            try:
                self._models[model_name] = genai.GenerativeModel(
                    model_name=model_config.id,
                    safety_settings=self._safety_settings,
                )
                self.logger.info(
                    "Gemini model loaded",
                    model_name=model_name,
                    model_id=model_config.id
                )
            except Exception as e:
                self.logger.error(
                    "Failed to load Gemini model",
                    model_name=model_name,
                    model_id=model_config.id,
                    error=str(e)
                )

    def _convert_messages(
        self,
        messages: List[Message]
    ) -> tuple[Optional[str], List[Dict[str, Any]]]:
        """
        Convert unified messages to Gemini format.

        Gemini expects a different format:
        - System message is separate
        - User/assistant messages in conversation format

        Args:
            messages: List of unified messages

        Returns:
            Tuple of (system_instruction, gemini_messages)
        """
        system_instruction = None
        gemini_messages = []

        for message in messages:
            if message.role == Role.SYSTEM:
                # Gemini uses system instruction separately
                system_instruction = message.content
            else:
                # Convert role to Gemini format
                role = "user" if message.role == Role.USER else "model"

                # Handle content
                content = message.content

                # Add to messages
                gemini_messages.append({
                    "role": role,
                    "parts": [content]
                })

        return system_instruction, gemini_messages

    async def _make_api_call(
        self,
        messages: List[Message],
        model_config: ModelConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make API call to Gemini.

        Args:
            messages: List of messages to send
            model_config: Model configuration to use
            **kwargs: Additional parameters

        Returns:
            Raw API response as dictionary
        """
        try:
            # Get model instance
            model_name = next(
                (k for k, v in self.config.models.items() if v == model_config),
                None
            )
            if not model_name or model_name not in self._models:
                raise ModelNotAvailableException(
                    f"Model {model_config.id} not initialized"
                )

            model = self._models[model_name]

            # Convert messages
            system_instruction, gemini_messages = self._convert_messages(messages)

            # Create generation config
            generation_config = GenerationConfig(
                temperature=kwargs.get("temperature", model_config.temperature),
                max_output_tokens=kwargs.get("max_tokens", model_config.max_tokens),
                top_p=kwargs.get("top_p"),
                top_k=kwargs.get("top_k"),
            )

            # Handle system instruction if present
            if system_instruction:
                model = genai.GenerativeModel(
                    model_name=model_config.id,
                    system_instruction=system_instruction,
                    safety_settings=self._safety_settings,
                )

            # Start chat session
            chat = model.start_chat(
                history=gemini_messages[:-1] if len(gemini_messages) > 1 else []
            )

            # Send the last message
            last_message = gemini_messages[-1]["parts"][0] if gemini_messages else ""

            # Generate response
            response = await chat.send_message_async(
                last_message,
                generation_config=generation_config,
            )

            # Convert to dictionary
            return {
                "text": response.text,
                "candidates": response.candidates,
                "prompt_feedback": response.prompt_feedback,
                "usage": {
                    "prompt_tokens": response.usage_metadata.prompt_token_count
                    if hasattr(response, "usage_metadata") else 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count
                    if hasattr(response, "usage_metadata") else 0,
                    "total_tokens": response.usage_metadata.total_token_count
                    if hasattr(response, "usage_metadata") else 0,
                },
            }

        except Exception as e:
            self._handle_api_error(e)

    def _parse_response(
        self,
        raw_response: Dict[str, Any],
        model: str
    ) -> CompletionResponse:
        """
        Parse Gemini response into unified format.

        Args:
            raw_response: Raw API response
            model: Model identifier used

        Returns:
            Unified CompletionResponse
        """
        # Extract content
        content = raw_response.get("text", "")

        # Extract usage
        usage = raw_response.get("usage", {})

        # Get finish reason from first candidate
        finish_reason = None
        if "candidates" in raw_response and raw_response["candidates"]:
            candidate = raw_response["candidates"][0]
            finish_reason = candidate.get("finish_reason", "").lower()

        return CompletionResponse(
            content=content,
            model=model,
            usage=usage,
            finish_reason=finish_reason,
            metadata={
                "prompt_feedback": raw_response.get("prompt_feedback"),
            }
        )

    async def _stream_api_call(
        self,
        messages: List[Message],
        model_config: ModelConfig,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Make streaming API call to Gemini.

        Args:
            messages: List of messages to send
            model_config: Model configuration to use
            **kwargs: Additional parameters

        Yields:
            Raw streaming chunks as dictionaries
        """
        try:
            # Get model instance
            model_name = next(
                (k for k, v in self.config.models.items() if v == model_config),
                None
            )
            if not model_name or model_name not in self._models:
                raise ModelNotAvailableException(
                    f"Model {model_config.id} not initialized"
                )

            model = self._models[model_name]

            # Convert messages
            system_instruction, gemini_messages = self._convert_messages(messages)

            # Create generation config
            generation_config = GenerationConfig(
                temperature=kwargs.get("temperature", model_config.temperature),
                max_output_tokens=kwargs.get("max_tokens", model_config.max_tokens),
                top_p=kwargs.get("top_p"),
                top_k=kwargs.get("top_k"),
            )

            # Handle system instruction if present
            if system_instruction:
                model = genai.GenerativeModel(
                    model_name=model_config.id,
                    system_instruction=system_instruction,
                    safety_settings=self._safety_settings,
                )

            # Start chat session
            chat = model.start_chat(
                history=gemini_messages[:-1] if len(gemini_messages) > 1 else []
            )

            # Send the last message with streaming
            last_message = gemini_messages[-1]["parts"][0] if gemini_messages else ""

            # Generate streaming response
            response = await chat.send_message_async(
                last_message,
                generation_config=generation_config,
                stream=True,
            )

            # Stream chunks
            async for chunk in response:
                yield {
                    "text": chunk.text if hasattr(chunk, "text") else "",
                    "candidates": chunk.candidates if hasattr(chunk, "candidates") else [],
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
        # Extract text
        text = raw_chunk.get("text", "")

        if not text:
            return None

        # Get finish reason from candidates
        finish_reason = None
        if "candidates" in raw_chunk and raw_chunk["candidates"]:
            candidate = raw_chunk["candidates"][0]
            finish_reason = candidate.get("finish_reason", "").lower()

        return StreamChunk(
            delta=text,
            finish_reason=finish_reason,
        )

    def _handle_api_error(self, error: Exception):
        """
        Convert Gemini API errors to provider exceptions.

        Args:
            error: The original exception

        Raises:
            ProviderException: Converted exception
        """
        error_str = str(error).lower()

        if "quota" in error_str or "rate" in error_str:
            raise RateLimitException(f"Gemini rate limit exceeded: {error}")
        elif "api_key" in error_str or "auth" in error_str or "unauthorized" in error_str:
            raise AuthenticationException(f"Gemini authentication failed: {error}")
        elif "model" in error_str and "not found" in error_str:
            raise ModelNotAvailableException(f"Gemini model not available: {error}")
        else:
            raise ProviderException(f"Gemini API error: {error}")

    async def health_check(self) -> bool:
        """
        Check if Gemini provider is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # List available models to verify API key
            models = genai.list_models()

            # Try to access the first model
            if models:
                self.logger.info(
                    "Gemini health check passed",
                    available_models=len(list(models))
                )
                return True
            else:
                self.logger.warning("Gemini health check: no models available")
                return False

        except Exception as e:
            self.logger.error(
                "Gemini health check failed",
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

        # Gemini Pro Vision and newer models support vision
        vision_models = ["gemini-pro-vision", "gemini-1.5", "gemini-2"]

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

        # Most Gemini models support function calling
        # except the legacy text-only models
        return "gemini" in model_id and "vision" not in model_id