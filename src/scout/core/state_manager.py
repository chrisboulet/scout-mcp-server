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
State Manager - Redis-based state and session management.

This module provides:
- Conversation history storage
- Session management
- Response caching
- Rate limiting data
- State persistence

Following Constitution Principles:
- #2: Modular Architecture
- #5: Robust Error Handling
- #6: Structured Logging
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import asdict
import json
import structlog
from redis import Redis
from redis.exceptions import RedisError, ConnectionError

from scout.providers.base import Message, Role

# Configure structured logging
logger = structlog.get_logger(__name__)


class StateManagerError(Exception):
    """Base exception for state manager errors."""
    pass


class SessionNotFoundError(StateManagerError):
    """Raised when session is not found."""
    pass


class StateManager:
    """
    State Manager for Redis-based persistence.

    This class manages:
    - Conversation sessions and history
    - Response caching
    - Rate limiting counters
    - Temporary state storage

    All data is stored in Redis with appropriate TTLs.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_ttl_seconds: int = 7200,  # 2 hours
        max_history_messages: int = 100
    ):
        """
        Initialize State Manager.

        Args:
            redis_url: Redis connection URL
            default_ttl_seconds: Default TTL for stored data
            max_history_messages: Maximum messages to store per session

        Raises:
            StateManagerError: If Redis connection fails
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl_seconds
        self.max_history = max_history_messages
        self.logger = logger.bind(component="state_manager")

        try:
            self.redis = Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis.ping()
            self.logger.info("State manager initialized", redis_url=redis_url)

        except (RedisError, ConnectionError) as e:
            self.logger.error(
                "Failed to connect to Redis",
                error=str(e),
                redis_url=redis_url
            )
            raise StateManagerError(f"Redis connection failed: {e}") from e

    def _make_key(self, prefix: str, identifier: str) -> str:
        """
        Create Redis key with prefix.

        Args:
            prefix: Key prefix (e.g., "session", "cache")
            identifier: Unique identifier

        Returns:
            Formatted Redis key
        """
        return f"scout:{prefix}:{identifier}"

    async def save_session(
        self,
        session_id: str,
        messages: List[Message],
        metadata: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Save conversation session.

        Args:
            session_id: Unique session identifier
            messages: List of conversation messages
            metadata: Optional session metadata
            ttl_seconds: Time to live (uses default if None)

        Raises:
            StateManagerError: If save fails
        """
        ttl = ttl_seconds or self.default_ttl
        key = self._make_key("session", session_id)

        try:
            # Limit history size
            if len(messages) > self.max_history:
                messages = messages[-self.max_history:]

            # Prepare session data
            # Convert messages to dicts with Role converted to string
            messages_data = []
            for msg in messages:
                msg_dict = asdict(msg)
                msg_dict['role'] = msg_dict['role'].value  # Convert Role enum to string
                messages_data.append(msg_dict)

            session_data = {
                "messages": messages_data,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            # Save to Redis
            self.redis.setex(
                key,
                ttl,
                json.dumps(session_data)
            )

            self.logger.debug(
                "Session saved",
                session_id=session_id,
                message_count=len(messages),
                ttl=ttl
            )

        except RedisError as e:
            self.logger.error(
                "Failed to save session",
                session_id=session_id,
                error=str(e)
            )
            raise StateManagerError(f"Session save failed: {e}") from e

    async def load_session(self, session_id: str) -> Dict[str, Any]:
        """
        Load conversation session.

        Args:
            session_id: Session identifier

        Returns:
            Session data with messages and metadata

        Raises:
            SessionNotFoundError: If session doesn't exist
            StateManagerError: If load fails
        """
        key = self._make_key("session", session_id)

        try:
            data = self.redis.get(key)

            if not data:
                raise SessionNotFoundError(f"Session '{session_id}' not found")

            session_data = json.loads(data)

            # Convert message dicts back to Message objects
            messages = [
                Message(
                    role=Role(msg["role"]),
                    content=msg["content"]
                )
                for msg in session_data["messages"]
            ]

            self.logger.debug(
                "Session loaded",
                session_id=session_id,
                message_count=len(messages)
            )

            return {
                "messages": messages,
                "metadata": session_data.get("metadata", {}),
                "created_at": session_data.get("created_at"),
                "updated_at": session_data.get("updated_at")
            }

        except SessionNotFoundError:
            raise
        except (RedisError, json.JSONDecodeError) as e:
            self.logger.error(
                "Failed to load session",
                session_id=session_id,
                error=str(e)
            )
            raise StateManagerError(f"Session load failed: {e}") from e

    async def append_message(
        self,
        session_id: str,
        message: Message,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Append message to existing session.

        Args:
            session_id: Session identifier
            message: Message to append
            ttl_seconds: TTL to extend

        Raises:
            SessionNotFoundError: If session doesn't exist
            StateManagerError: If append fails
        """
        try:
            # Load existing session
            session = await self.load_session(session_id)
            messages = session["messages"]
            metadata = session["metadata"]

            # Append new message
            messages.append(message)

            # Save updated session
            await self.save_session(
                session_id,
                messages,
                metadata,
                ttl_seconds
            )

            self.logger.debug(
                "Message appended to session",
                session_id=session_id,
                total_messages=len(messages)
            )

        except (SessionNotFoundError, StateManagerError):
            raise

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete conversation session.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        key = self._make_key("session", session_id)

        try:
            deleted = self.redis.delete(key)
            self.logger.debug("Session deleted", session_id=session_id)
            return bool(deleted)

        except RedisError as e:
            self.logger.error(
                "Failed to delete session",
                session_id=session_id,
                error=str(e)
            )
            return False

    async def cache_response(
        self,
        cache_key: str,
        response: Any,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Cache AI response.

        Args:
            cache_key: Unique cache key (e.g., hash of prompt)
            response: Response to cache
            ttl_seconds: Cache TTL

        Raises:
            StateManagerError: If caching fails
        """
        ttl = ttl_seconds or self.default_ttl
        key = self._make_key("cache", cache_key)

        try:
            self.redis.setex(
                key,
                ttl,
                json.dumps(response)
            )

            self.logger.debug("Response cached", cache_key=cache_key, ttl=ttl)

        except (RedisError, TypeError) as e:
            self.logger.error(
                "Failed to cache response",
                cache_key=cache_key,
                error=str(e)
            )
            raise StateManagerError(f"Cache save failed: {e}") from e

    async def get_cached_response(self, cache_key: str) -> Optional[Any]:
        """
        Retrieve cached response.

        Args:
            cache_key: Cache key

        Returns:
            Cached response or None if not found
        """
        key = self._make_key("cache", cache_key)

        try:
            data = self.redis.get(key)

            if data:
                self.logger.debug("Cache hit", cache_key=cache_key)
                return json.loads(data)
            else:
                self.logger.debug("Cache miss", cache_key=cache_key)
                return None

        except (RedisError, json.JSONDecodeError) as e:
            self.logger.warning(
                "Cache retrieval failed",
                cache_key=cache_key,
                error=str(e)
            )
            return None

    async def increment_counter(
        self,
        counter_key: str,
        ttl_seconds: Optional[int] = None
    ) -> int:
        """
        Increment counter (for rate limiting).

        Args:
            counter_key: Counter identifier
            ttl_seconds: Counter TTL

        Returns:
            New counter value

        Raises:
            StateManagerError: If increment fails
        """
        key = self._make_key("counter", counter_key)
        ttl = ttl_seconds or 3600  # Default 1 hour for counters

        try:
            # Increment counter
            value = self.redis.incr(key)

            # Set TTL on first increment
            if value == 1:
                self.redis.expire(key, ttl)

            return value

        except RedisError as e:
            self.logger.error(
                "Failed to increment counter",
                counter_key=counter_key,
                error=str(e)
            )
            raise StateManagerError(f"Counter increment failed: {e}") from e

    async def get_counter(self, counter_key: str) -> int:
        """
        Get counter value.

        Args:
            counter_key: Counter identifier

        Returns:
            Counter value (0 if not found)
        """
        key = self._make_key("counter", counter_key)

        try:
            value = self.redis.get(key)
            return int(value) if value else 0

        except (RedisError, ValueError) as e:
            self.logger.warning(
                "Failed to get counter",
                counter_key=counter_key,
                error=str(e)
            )
            return 0

    async def health_check(self) -> bool:
        """
        Check Redis connection health.

        Returns:
            True if healthy, False otherwise
        """
        try:
            self.redis.ping()
            return True
        except RedisError:
            return False

    async def cleanup(self) -> None:
        """Clean up Redis connections."""
        try:
            self.redis.close()
            self.logger.info("State manager cleanup complete")
        except Exception as e:
            self.logger.error("Cleanup failed", error=str(e))
