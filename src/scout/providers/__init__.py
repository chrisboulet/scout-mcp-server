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
]
