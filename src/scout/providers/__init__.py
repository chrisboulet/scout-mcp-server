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
Providers Module - AI provider implementations for SCOUT.

This module provides unified interfaces to multiple AI providers.
Each provider adapter implements the BaseAIProvider contract.

Constitution Principle #7: Provider Abstraction
"""

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

# Import providers as they are implemented
from scout.providers.gemini import GeminiProvider
from scout.providers.openai import OpenAIProvider
from scout.providers.anthropic import AnthropicProvider
from scout.providers.openrouter import OpenRouterProvider
from scout.providers.grok import GrokProvider

__all__ = [
    # Base classes
    "BaseAIProvider",
    "Message",
    "CompletionResponse",
    "StreamChunk",
    "Role",
    "ProviderType",
    # Exceptions
    "ProviderException",
    "RateLimitException",
    "AuthenticationException",
    "ModelNotAvailableException",
    # Provider implementations
    "GeminiProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "OpenRouterProvider",
    "GrokProvider",
]
