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
Unit tests for ProviderFactory.

Following Constitution Principle #3: Mandatory Testing
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from scout.providers.factory import ProviderFactory
from scout.providers.base import BaseAIProvider, ProviderType, ProviderException
from scout.providers.gemini import GeminiProvider
from scout.providers.openai import OpenAIProvider
from scout.providers.anthropic import AnthropicProvider
from scout.providers.openrouter import OpenRouterProvider
from scout.providers.grok import GrokProvider
from scout.config.models import ProviderConfig, ModelConfig, ScoutConfig, SystemSettings
from scout.config.exceptions import ConfigurationError


@pytest.fixture
def gemini_config():
    """Create Gemini provider configuration."""
    return ProviderConfig(
        api_key="test-gemini-key",
        models={
            "flash": ModelConfig(
                id="gemini-1.5-flash",
                max_tokens=8192,
                temperature=0.7
            )
        },
        default_model="flash"
    )


@pytest.fixture
def openai_config():
    """Create OpenAI provider configuration."""
    return ProviderConfig(
        api_key="sk-test-openai-key",
        models={
            "gpt4": ModelConfig(
                id="gpt-4o",
                max_tokens=4096,
                temperature=0.7
            )
        },
        default_model="gpt4"
    )


@pytest.fixture
def anthropic_config():
    """Create Anthropic provider configuration."""
    return ProviderConfig(
        api_key="sk-ant-test-key",
        models={
            "sonnet": ModelConfig(
                id="claude-sonnet-4",
                max_tokens=4096,
                temperature=0.7
            )
        },
        default_model="sonnet"
    )


@pytest.fixture
def scout_config(gemini_config, openai_config, anthropic_config):
    """Create complete Scout configuration."""
    from scout.config.models import TeamConfig, TeamMember

    return ScoutConfig(
        system=SystemSettings(
            max_retries=3,
            request_timeout_seconds=60
        ),
        providers={
            "gemini": gemini_config,
            "openai": openai_config,
            "anthropic": anthropic_config
        },
        teams={
            "test_team": TeamConfig(
                description="Test team",
                primary=TeamMember(
                    provider="gemini",
                    model="flash"
                )
            )
        },
        tool_team_mapping={"test_tool": "test_team"}
    )


@pytest.mark.asyncio
class TestProviderFactory:
    """Test suite for ProviderFactory."""

    def test_registry_populated(self):
        """Test provider registry is populated with all providers."""
        registry = ProviderFactory._provider_registry

        assert ProviderType.GEMINI in registry
        assert ProviderType.OPENAI in registry
        assert ProviderType.ANTHROPIC in registry
        assert ProviderType.OPENROUTER in registry
        assert ProviderType.GROK in registry

        assert registry[ProviderType.GEMINI] == GeminiProvider
        assert registry[ProviderType.OPENAI] == OpenAIProvider
        assert registry[ProviderType.ANTHROPIC] == AnthropicProvider
        assert registry[ProviderType.OPENROUTER] == OpenRouterProvider
        assert registry[ProviderType.GROK] == GrokProvider

    def test_create_gemini_provider(self, gemini_config):
        """Test creating Gemini provider."""
        provider = ProviderFactory.create_provider(
            provider_name="gemini",
            provider_config=gemini_config
        )

        assert isinstance(provider, GeminiProvider)
        assert provider.config == gemini_config

    def test_create_openai_provider(self, openai_config):
        """Test creating OpenAI provider."""
        provider = ProviderFactory.create_provider(
            provider_name="openai",
            provider_config=openai_config
        )

        assert isinstance(provider, OpenAIProvider)
        assert provider.config == openai_config

    def test_create_anthropic_provider(self, anthropic_config):
        """Test creating Anthropic provider."""
        provider = ProviderFactory.create_provider(
            provider_name="anthropic",
            provider_config=anthropic_config
        )

        assert isinstance(provider, AnthropicProvider)
        assert provider.config == anthropic_config

    def test_provider_caching(self, gemini_config):
        """Test providers are cached."""
        # Clear cache first
        ProviderFactory.clear_cache()

        provider1 = ProviderFactory.create_provider(
            provider_name="gemini_test",
            provider_config=gemini_config
        )

        provider2 = ProviderFactory.create_provider(
            provider_name="gemini_test",
            provider_config=gemini_config
        )

        # Should return same instance
        assert provider1 is provider2

        # Clean up
        ProviderFactory.clear_cache()

    def test_create_from_config(self, scout_config):
        """Test creating provider from Scout configuration."""
        provider = ProviderFactory.create_from_config(
            scout_config=scout_config,
            provider_name="gemini"
        )

        assert isinstance(provider, GeminiProvider)

    def test_create_from_config_invalid_provider(self, scout_config):
        """Test creating invalid provider raises exception."""
        with pytest.raises(ConfigurationError, match="Provider .* not found"):
            ProviderFactory.create_from_config(
                scout_config=scout_config,
                provider_name="invalid_provider"
            )

    def test_create_all_providers(self, scout_config):
        """Test creating all providers from configuration."""
        # Clear cache first
        ProviderFactory.clear_cache()

        providers = ProviderFactory.create_all_providers(scout_config=scout_config)

        assert len(providers) == 3
        assert "gemini" in providers
        assert "openai" in providers
        assert "anthropic" in providers

        assert isinstance(providers["gemini"], GeminiProvider)
        assert isinstance(providers["openai"], OpenAIProvider)
        assert isinstance(providers["anthropic"], AnthropicProvider)

        # Clean up
        ProviderFactory.clear_cache()

    def test_get_cached_provider(self, gemini_config):
        """Test getting cached provider."""
        # Clear cache first
        ProviderFactory.clear_cache()

        # Create provider
        ProviderFactory.create_provider(
            provider_name="gemini_cached",
            provider_config=gemini_config
        )

        # Get cached
        cached = ProviderFactory.get_cached_provider("gemini_cached")
        assert cached is not None
        assert isinstance(cached, GeminiProvider)

        # Try non-existent
        not_cached = ProviderFactory.get_cached_provider("nonexistent")
        assert not_cached is None

        # Clean up
        ProviderFactory.clear_cache()

    def test_clear_cache_specific(self, gemini_config):
        """Test clearing specific provider from cache."""
        ProviderFactory.clear_cache()

        ProviderFactory.create_provider(
            provider_name="provider1",
            provider_config=gemini_config
        )
        ProviderFactory.create_provider(
            provider_name="provider2",
            provider_config=gemini_config
        )

        # Clear only provider1
        ProviderFactory.clear_cache("provider1")

        assert ProviderFactory.get_cached_provider("provider1") is None
        assert ProviderFactory.get_cached_provider("provider2") is not None

        # Clean up
        ProviderFactory.clear_cache()

    def test_clear_cache_all(self, gemini_config):
        """Test clearing all providers from cache."""
        ProviderFactory.clear_cache()

        ProviderFactory.create_provider(
            provider_name="provider1",
            provider_config=gemini_config
        )
        ProviderFactory.create_provider(
            provider_name="provider2",
            provider_config=gemini_config
        )

        # Clear all
        ProviderFactory.clear_cache()

        assert ProviderFactory.get_cached_provider("provider1") is None
        assert ProviderFactory.get_cached_provider("provider2") is None

    async def test_cleanup_all(self, gemini_config):
        """Test cleaning up all providers."""
        ProviderFactory.clear_cache()

        # Create some providers
        ProviderFactory.create_provider(
            provider_name="provider1",
            provider_config=gemini_config
        )
        ProviderFactory.create_provider(
            provider_name="provider2",
            provider_config=gemini_config
        )

        # Cleanup all
        await ProviderFactory.cleanup_all()

        # Cache should be empty
        assert len(ProviderFactory._provider_cache) == 0

    def test_provider_type_detection_from_name(self):
        """Test provider type detection from name."""
        # Test with different naming patterns
        test_cases = [
            ("gemini", ProviderType.GEMINI),
            ("my_gemini_provider", ProviderType.GEMINI),
            ("openai", ProviderType.OPENAI),
            ("my_openai", ProviderType.OPENAI),
            ("anthropic", ProviderType.ANTHROPIC),
            ("claude_provider", ProviderType.ANTHROPIC),
        ]

        for name, expected_type in test_cases:
            config = ProviderConfig(
                api_key="test",
                models={
                    "test": ModelConfig(
                        id="test-model",
                        max_tokens=1000,
                        temperature=0.7
                    )
                },
                default_model="test"
            )
            detected = ProviderFactory._get_provider_type(name, config)
            assert detected == expected_type

    def test_provider_type_detection_from_api_key(self):
        """Test provider type detection from API key format."""
        test_cases = [
            ("sk-test", ProviderType.OPENAI),
            ("sk-ant-test", ProviderType.ANTHROPIC),
            ("AIzatest", ProviderType.GEMINI),
            ("gsk_test", ProviderType.GROK),
        ]

        for api_key, expected_type in test_cases:
            config = ProviderConfig(
                api_key=api_key,
                models={
                    "test": ModelConfig(
                        id="test-model",
                        max_tokens=1000,
                        temperature=0.7
                    )
                },
                default_model="test"
            )
            detected = ProviderFactory._get_provider_type("unknown", config)
            assert detected == expected_type

    def test_provider_type_detection_from_model_id(self):
        """Test provider type detection from model ID."""
        test_cases = [
            ("gpt-4", ProviderType.OPENAI),
            ("claude-3", ProviderType.ANTHROPIC),
            ("gemini-pro", ProviderType.GEMINI),
            ("grok-2", ProviderType.GROK),
            ("meta/llama", ProviderType.OPENROUTER),
        ]

        for model_id, expected_type in test_cases:
            config = ProviderConfig(
                api_key="test",
                models={
                    "test": ModelConfig(
                        id=model_id,
                        max_tokens=1000,
                        temperature=0.7
                    )
                },
                default_model="test"
            )
            detected = ProviderFactory._get_provider_type("unknown", config)
            assert detected == expected_type

    def test_invalid_provider_type(self):
        """Test creating provider with invalid type raises exception."""
        # Create a custom provider type not in registry
        class CustomProviderType:
            value = "custom"

        config = ProviderConfig(
            api_key="test",
            models={
                "test": ModelConfig(
                    id="test-model",
                    max_tokens=1000,
                    temperature=0.7
                )
            },
            default_model="test"
        )

        # Manually set type to invalid (normally _get_provider_type handles this)
        # This would need to bypass type detection, so we test the registry check
        with pytest.raises(ConfigurationError, match="Unknown provider type"):
            # This will fail in _get_provider_type which defaults to OPENROUTER
            # So let's test by registering a bad type
            bad_registry = ProviderFactory._provider_registry.copy()
            ProviderFactory._provider_registry.clear()

            try:
                ProviderFactory.create_provider(
                    provider_name="test",
                    provider_config=config
                )
            finally:
                # Restore registry
                ProviderFactory._provider_registry = bad_registry

    async def test_health_check_all(self, scout_config):
        """Test health check for all providers."""
        ProviderFactory.clear_cache()

        # Create providers
        ProviderFactory.create_all_providers(scout_config)

        # Mock health checks
        with patch.object(BaseAIProvider, 'health_check', new_callable=AsyncMock) as mock_health:
            mock_health.return_value = True

            results = await ProviderFactory.health_check_all()

            assert len(results) >= 3
            assert all(isinstance(v, bool) for v in results.values())

        ProviderFactory.clear_cache()

    def test_get_provider_metrics(self, gemini_config):
        """Test getting metrics for all providers."""
        ProviderFactory.clear_cache()

        # Create provider
        provider = ProviderFactory.create_provider(
            provider_name="test_provider",
            provider_config=gemini_config
        )

        # Get metrics
        metrics = ProviderFactory.get_provider_metrics()

        assert "test_provider" in metrics
        assert isinstance(metrics["test_provider"], dict)

        ProviderFactory.clear_cache()

    def test_register_custom_provider(self):
        """Test registering a custom provider type."""
        # Create a custom provider class
        class CustomProvider(BaseAIProvider):
            async def _make_api_call(self, messages, model_config, **kwargs):
                return {}

            def _parse_response(self, raw_response, model):
                return None

            async def _stream_api_call(self, messages, model_config, **kwargs):
                yield {}

            def _parse_stream_chunk(self, raw_chunk):
                return None

        # Register it
        class CustomType:
            value = "custom"

        ProviderFactory.register_provider(
            provider_type=CustomType(),
            provider_class=CustomProvider
        )

        # Verify it's registered
        assert CustomType() in ProviderFactory._provider_registry

        # Clean up - remove custom provider
        del ProviderFactory._provider_registry[CustomType()]