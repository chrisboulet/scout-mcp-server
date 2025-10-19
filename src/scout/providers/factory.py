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
Provider Factory Module.

This module provides the factory pattern for creating AI provider instances.
It handles dynamic provider instantiation based on configuration.

Following Constitution Principle #2: Modular Architecture
Following Constitution Principle #7: Provider Abstraction
"""

from typing import Dict, Type, Optional, Any
import structlog

from scout.providers.base import (
    BaseAIProvider,
    ProviderType,
    ProviderException,
)
from scout.providers.gemini import GeminiProvider
from scout.providers.openai import OpenAIProvider
from scout.providers.anthropic import AnthropicProvider
from scout.providers.openrouter import OpenRouterProvider
from scout.providers.grok import GrokProvider
from scout.config.models import ProviderConfig, ScoutConfig
from scout.config.exceptions import ConfigurationError

# Configure structured logging
logger = structlog.get_logger(__name__)


class ProviderFactory:
    """
    Factory class for creating AI provider instances.

    This factory handles:
    - Dynamic provider instantiation
    - Provider registry management
    - Configuration validation
    - Provider lifecycle management
    """

    # Registry mapping provider types to their implementation classes
    _provider_registry: Dict[ProviderType, Type[BaseAIProvider]] = {
        ProviderType.GEMINI: GeminiProvider,
        ProviderType.OPENAI: OpenAIProvider,
        ProviderType.ANTHROPIC: AnthropicProvider,
        ProviderType.OPENROUTER: OpenRouterProvider,
        ProviderType.GROK: GrokProvider,
    }

    # Cache of created provider instances
    _provider_cache: Dict[str, BaseAIProvider] = {}

    @classmethod
    def create_provider(
        cls,
        provider_name: str,
        provider_config: ProviderConfig,
        max_retries: int = 3,
        timeout: float = 60.0,
        **kwargs
    ) -> BaseAIProvider:
        """
        Create a provider instance.

        Args:
            provider_name: Name of the provider (used as cache key)
            provider_config: Provider configuration
            max_retries: Maximum retry attempts
            timeout: Request timeout in seconds
            **kwargs: Additional provider-specific parameters

        Returns:
            Provider instance

        Raises:
            ConfigurationError: If provider type is invalid
            ProviderException: If provider creation fails
        """
        # Check cache first
        if provider_name in cls._provider_cache:
            logger.debug(
                "Returning cached provider",
                provider_name=provider_name
            )
            return cls._provider_cache[provider_name]

        # Determine provider type from name or config
        provider_type = cls._get_provider_type(provider_name, provider_config)

        # Validate provider type
        if provider_type not in cls._provider_registry:
            raise ConfigurationError(
                f"Unknown provider type: {provider_type}. "
                f"Available types: {', '.join(t.value for t in cls._provider_registry.keys())}"
            )

        # Get provider class
        provider_class = cls._provider_registry[provider_type]

        # Create provider instance
        try:
            provider = provider_class(
                provider_config=provider_config,
                max_retries=max_retries,
                timeout=timeout,
                **kwargs
            )

            # Cache the instance
            cls._provider_cache[provider_name] = provider

            logger.info(
                "Provider created",
                provider_name=provider_name,
                provider_type=provider_type.value,
                models_available=len(provider_config.models)
            )

            return provider

        except Exception as e:
            logger.error(
                "Failed to create provider",
                provider_name=provider_name,
                provider_type=provider_type.value,
                error=str(e)
            )
            raise ProviderException(f"Failed to create provider {provider_name}: {e}")

    @classmethod
    def create_from_config(
        cls,
        scout_config: ScoutConfig,
        provider_name: str,
        **kwargs
    ) -> BaseAIProvider:
        """
        Create a provider from Scout configuration.

        Args:
            scout_config: Complete Scout configuration
            provider_name: Name of the provider to create
            **kwargs: Additional provider-specific parameters

        Returns:
            Provider instance

        Raises:
            ConfigurationError: If provider not found in config
            ProviderException: If provider creation fails
        """
        # Get provider config
        if provider_name not in scout_config.providers:
            raise ConfigurationError(
                f"Provider '{provider_name}' not found in configuration. "
                f"Available providers: {', '.join(scout_config.providers.keys())}"
            )

        provider_config = scout_config.providers[provider_name]

        # Use system settings for defaults
        max_retries = kwargs.pop("max_retries", scout_config.system.max_retries)
        timeout = kwargs.pop("timeout", scout_config.system.request_timeout)

        return cls.create_provider(
            provider_name=provider_name,
            provider_config=provider_config,
            max_retries=max_retries,
            timeout=timeout,
            **kwargs
        )

    @classmethod
    def create_all_providers(
        cls,
        scout_config: ScoutConfig,
        **kwargs
    ) -> Dict[str, BaseAIProvider]:
        """
        Create all providers from configuration.

        Args:
            scout_config: Complete Scout configuration
            **kwargs: Additional provider-specific parameters

        Returns:
            Dictionary mapping provider names to instances

        Raises:
            ProviderException: If any provider creation fails
        """
        providers = {}
        failed_providers = []

        for provider_name in scout_config.providers:
            try:
                provider = cls.create_from_config(
                    scout_config=scout_config,
                    provider_name=provider_name,
                    **kwargs
                )
                providers[provider_name] = provider

            except Exception as e:
                logger.warning(
                    "Failed to create provider",
                    provider_name=provider_name,
                    error=str(e)
                )
                failed_providers.append((provider_name, str(e)))

        # Log summary
        logger.info(
            "Provider creation complete",
            successful=len(providers),
            failed=len(failed_providers),
            providers=list(providers.keys())
        )

        if failed_providers:
            logger.warning(
                "Some providers failed to initialize",
                failed_providers=failed_providers
            )

        return providers

    @classmethod
    def get_cached_provider(cls, provider_name: str) -> Optional[BaseAIProvider]:
        """
        Get a cached provider instance.

        Args:
            provider_name: Name of the provider

        Returns:
            Cached provider instance or None
        """
        return cls._provider_cache.get(provider_name)

    @classmethod
    async def cleanup_all(cls):
        """
        Clean up all cached provider instances.

        This should be called at shutdown to properly release resources.
        """
        logger.info("Cleaning up all providers", count=len(cls._provider_cache))

        for provider_name, provider in cls._provider_cache.items():
            try:
                await provider.cleanup()
                logger.debug(
                    "Provider cleaned up",
                    provider_name=provider_name
                )
            except Exception as e:
                logger.error(
                    "Failed to cleanup provider",
                    provider_name=provider_name,
                    error=str(e)
                )

        # Clear cache
        cls._provider_cache.clear()
        logger.info("All providers cleaned up")

    @classmethod
    def clear_cache(cls, provider_name: Optional[str] = None):
        """
        Clear provider cache.

        Args:
            provider_name: Specific provider to clear, or None for all
        """
        if provider_name:
            cls._provider_cache.pop(provider_name, None)
            logger.debug("Provider cache cleared", provider_name=provider_name)
        else:
            cls._provider_cache.clear()
            logger.debug("All provider caches cleared")

    @classmethod
    def register_provider(
        cls,
        provider_type: ProviderType,
        provider_class: Type[BaseAIProvider]
    ):
        """
        Register a custom provider implementation.

        This allows extending the factory with new provider types.

        Args:
            provider_type: Type identifier for the provider
            provider_class: Implementation class for the provider
        """
        cls._provider_registry[provider_type] = provider_class
        logger.info(
            "Provider registered",
            provider_type=provider_type.value,
            provider_class=provider_class.__name__
        )

    @classmethod
    def _get_provider_type(
        cls,
        provider_name: str,
        provider_config: ProviderConfig
    ) -> ProviderType:
        """
        Determine provider type from name or configuration.

        Args:
            provider_name: Name of the provider
            provider_config: Provider configuration

        Returns:
            Provider type enum

        Raises:
            ConfigurationError: If provider type cannot be determined
        """
        # Try to match provider name to type
        name_lower = provider_name.lower()

        for provider_type in ProviderType:
            if provider_type.value.lower() in name_lower:
                return provider_type

        # Check if API key hints at provider type
        api_key = provider_config.api_key or ""

        if api_key.startswith("sk-"):
            return ProviderType.OPENAI
        elif api_key.startswith("sk-ant-"):
            return ProviderType.ANTHROPIC
        elif "AIza" in api_key:
            return ProviderType.GEMINI
        elif api_key.startswith("gsk_"):
            return ProviderType.GROK

        # If we have models, check their IDs
        if provider_config.models:
            first_model = next(iter(provider_config.models.values()))
            model_id = first_model.id.lower()

            if "gpt" in model_id:
                return ProviderType.OPENAI
            elif "claude" in model_id:
                return ProviderType.ANTHROPIC
            elif "gemini" in model_id:
                return ProviderType.GEMINI
            elif "grok" in model_id:
                return ProviderType.GROK
            elif "/" in model_id:  # Many OpenRouter models have provider/model format
                return ProviderType.OPENROUTER

        # Default to OpenRouter if unclear (it supports many models)
        logger.warning(
            "Could not determine provider type, defaulting to OpenRouter",
            provider_name=provider_name
        )
        return ProviderType.OPENROUTER

    @classmethod
    async def health_check_all(cls) -> Dict[str, bool]:
        """
        Perform health checks on all cached providers.

        Returns:
            Dictionary mapping provider names to health status
        """
        results = {}

        for provider_name, provider in cls._provider_cache.items():
            try:
                is_healthy = await provider.health_check()
                results[provider_name] = is_healthy

                logger.info(
                    "Provider health check",
                    provider_name=provider_name,
                    is_healthy=is_healthy
                )

            except Exception as e:
                results[provider_name] = False
                logger.error(
                    "Provider health check failed",
                    provider_name=provider_name,
                    error=str(e)
                )

        return results

    @classmethod
    def get_provider_metrics(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get metrics for all cached providers.

        Returns:
            Dictionary mapping provider names to their metrics
        """
        metrics = {}

        for provider_name, provider in cls._provider_cache.items():
            metrics[provider_name] = provider.get_metrics()

        return metrics