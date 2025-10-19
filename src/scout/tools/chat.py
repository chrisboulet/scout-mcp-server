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
Chat Tool - Conversational AI with multi-provider support.

This tool provides:
- Natural language conversations with AI models
- Automatic team selection based on task complexity
- Conversation history management
- Multi-turn dialogue support
- Cost and token tracking

Following Constitution Principles:
- #1: Contract-First Development (MCP schema)
- #2: Modular Architecture (provider abstraction)
- #4: AI Provider Abstraction (team-based routing)
- #5: Robust Error Handling
- #6: Structured Logging
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import structlog

from scout.core.tool_registry import (
    BaseTool,
    ToolMetadata,
    ToolSchema,
    ToolCategory,
    ToolPermission
)
from scout.providers.base import Message, Role, BaseAIProvider
from scout.core.state_manager import StateManager, SessionNotFoundError

# Configure structured logging
logger = structlog.get_logger(__name__)


class ChatInput(BaseModel):
    """Input schema for chat tool."""

    message: str = Field(
        ...,
        description="User message to send to the AI",
        min_length=1,
        max_length=100000
    )
    session_id: Optional[str] = Field(
        None,
        description="Session ID for conversation continuity (optional)"
    )
    system_prompt: Optional[str] = Field(
        None,
        description="System prompt to guide AI behavior (optional)",
        max_length=10000
    )
    max_tokens: Optional[int] = Field(
        None,
        description="Maximum tokens in response (optional)",
        gt=0,
        le=100000
    )
    temperature: Optional[float] = Field(
        None,
        description="Sampling temperature (0.0-2.0, optional)",
        ge=0.0,
        le=2.0
    )
    team_override: Optional[str] = Field(
        None,
        description="Override automatic team selection (optional)"
    )
    team_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Team selection context (injected by server)",
        exclude=True  # Internal use only, excluded from serialization
    )


class ChatOutput(BaseModel):
    """Output schema for chat tool."""

    response: str = Field(
        ...,
        description="AI response to the user message"
    )
    session_id: str = Field(
        ...,
        description="Session ID for conversation continuity"
    )
    team_used: str = Field(
        ...,
        description="Team that handled the request"
    )
    provider_used: str = Field(
        ...,
        description="AI provider that generated the response"
    )
    model_used: str = Field(
        ...,
        description="Specific model used"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Response metadata (tokens, cost, latency, etc.)"
    )


class ChatTool(BaseTool):
    """
    Chat Tool - Conversational AI with intelligent routing.

    This tool enables natural language conversations with AI models,
    automatically selecting the best team/provider based on task complexity.

    Features:
    - Multi-turn conversations with session management
    - Automatic team selection via TeamSelector
    - Support for all configured AI providers
    - Conversation history (when state manager is available)
    - Token usage and cost tracking
    - Customizable system prompts
    - Temperature and max_tokens control

    Example Usage:
        Simple chat:
        {
            "message": "Explain microservices architecture"
        }

        Multi-turn conversation:
        {
            "message": "What are the trade-offs?",
            "session_id": "conv-123"
        }

        With customization:
        {
            "message": "Write a Python function",
            "system_prompt": "You are a Python expert",
            "temperature": 0.2,
            "max_tokens": 2000
        }
    """

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        return ToolMetadata(
            name="chat",
            description="Have natural language conversations with AI models",
            category=ToolCategory.UTILITY,
            version="1.0.0",
            author="SCOUT Team",
            permissions={ToolPermission.READ, ToolPermission.WRITE},
            tags=["chat", "conversation", "ai", "llm"],
            examples=[
                {
                    "message": "What is quantum computing?"
                },
                {
                    "message": "Explain the previous concept in simpler terms",
                    "session_id": "session-123"
                },
                {
                    "message": "Write production-ready code",
                    "system_prompt": "You are a senior software engineer",
                    "temperature": 0.2
                }
            ],
            cost_estimate=0.01,
            avg_latency_ms=2000
        )

    def get_schema(self) -> ToolSchema:
        """Get tool schema."""
        return ToolSchema(
            input_model=ChatInput,
            output_model=ChatOutput
        )

    async def execute(
        self,
        message: str,
        session_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        team_override: Optional[str] = None,
        team_context: Optional[Dict[str, Any]] = None,
        provider: Optional[BaseAIProvider] = None,
        state_manager: Optional[StateManager] = None
    ) -> Dict[str, Any]:
        """
        Execute chat conversation with real AI provider.

        Args:
            message: User message
            session_id: Session ID for conversation continuity
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            team_override: Force specific team
            team_context: Team context injected by server
            provider: AI provider instance (injected by server)
            state_manager: State manager for conversation history

        Returns:
            Chat response with metadata
        """
        log = logger.bind(
            tool="chat",
            session_id=session_id,
            has_system_prompt=system_prompt is not None,
            has_provider=provider is not None
        )

        try:
            log.info("Chat execution started", message_length=len(message))

            # Extract team information
            team_used = "default"
            provider_used = "unknown"
            model_used = "unknown"

            if team_context:
                team_used = team_context.get("team", "default")
                provider_used = team_context.get("provider", "unknown")
                model_used = team_context.get("model", "unknown")

                log.debug(
                    "Team context available",
                    team=team_used,
                    provider=provider_used,
                    model=model_used
                )

            # Generate session ID if not provided
            if not session_id:
                import uuid
                session_id = f"chat-{uuid.uuid4().hex[:12]}"
                log.debug("Generated new session", session_id=session_id)

            # Build conversation messages
            messages: List[Message] = []

            # Add system prompt if provided
            if system_prompt:
                messages.append(Message(
                    role=Role.SYSTEM,
                    content=system_prompt
                ))

            # Load conversation history from state manager if available
            if state_manager and session_id:
                try:
                    session_data = await state_manager.load_session(session_id)
                    history_messages = session_data["messages"]

                    # Add historical messages (skip system prompt if we added one)
                    for hist_msg in history_messages:
                        if not system_prompt or hist_msg.role != Role.SYSTEM:
                            messages.append(hist_msg)

                    log.debug(
                        "Loaded conversation history",
                        history_length=len(history_messages)
                    )
                except SessionNotFoundError:
                    log.debug("No existing session found, starting new conversation")
                except Exception as e:
                    log.warning(
                        "Failed to load session history",
                        error=str(e)
                    )

            # Add user message
            user_message = Message(
                role=Role.USER,
                content=message
            )
            messages.append(user_message)

            # Call real AI provider if available
            if provider:
                log.debug("Calling AI provider", provider=provider.provider_type)

                # Prepare provider parameters
                provider_params = {}
                if max_tokens:
                    provider_params["max_tokens"] = max_tokens
                if temperature is not None:
                    provider_params["temperature"] = temperature

                # Call provider
                response = await provider.chat(
                    messages=messages,
                    model=model_used,
                    **provider_params
                )

                response_text = response.content
                input_tokens = response.usage.get("prompt_tokens", 0)
                output_tokens = response.usage.get("completion_tokens", 0)
                total_tokens = response.total_tokens

                # Calculate actual cost using the model config
                model_config = provider.config.models.get(model_used)
                if model_config:
                    cost_usd = (
                        (input_tokens / 1000) * model_config.cost_per_1k_input +
                        (output_tokens / 1000) * model_config.cost_per_1k_output
                    )
                else:
                    cost_usd = 0.0

                metadata = {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "cost_usd": round(cost_usd, 6),
                    "temperature": temperature or (model_config.temperature if model_config else 0.7),
                    "max_tokens": max_tokens,
                    "cached": False,
                    "latency_ms": response.metadata.get("latency_ms", 0)
                }

                # Add assistant response to messages
                assistant_message = Message(
                    role=Role.ASSISTANT,
                    content=response_text
                )
                messages.append(assistant_message)

                log.info(
                    "AI provider response received",
                    tokens=total_tokens,
                    cost_usd=metadata["cost_usd"]
                )

            else:
                # Fallback: placeholder response when no provider available
                log.warning("No provider available, using placeholder response")

                response_text = (
                    f"This is a placeholder response from the {team_used} team "
                    f"using {provider_used}/{model_used}. "
                    f"Provider not available for real AI integration. "
                    f"\n\nYour message: {message[:100]}..."
                )

                # Estimate metadata
                input_tokens = len(message.split()) * 2
                output_tokens = len(response_text.split()) * 2
                total_tokens = input_tokens + output_tokens

                metadata = {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "cost_usd": 0.0,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "cached": False,
                    "latency_ms": 0
                }

                assistant_message = Message(
                    role=Role.ASSISTANT,
                    content=response_text
                )
                messages.append(assistant_message)

            # Save conversation to state manager if available
            if state_manager:
                try:
                    await state_manager.save_session(
                        session_id=session_id,
                        messages=messages,
                        metadata={
                            "team": team_used,
                            "provider": provider_used,
                            "model": model_used,
                            "total_cost": metadata["cost_usd"]
                        }
                    )
                    log.debug("Conversation saved to state manager")
                except Exception as e:
                    log.error(
                        "Failed to save conversation",
                        error=str(e)
                    )

            log.info(
                "Chat execution completed",
                tokens=metadata["total_tokens"],
                cost_usd=metadata["cost_usd"]
            )

            return {
                "response": response_text,
                "session_id": session_id,
                "team_used": team_used,
                "provider_used": provider_used,
                "model_used": model_used,
                "metadata": metadata
            }

        except Exception as e:
            log.error(
                "Chat execution failed",
                error=str(e),
                exc_info=True
            )
            raise
