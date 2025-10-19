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
Unit tests for State Manager.

Tests cover:
- Session management (save/load/append/delete)
- Response caching
- Counter management
- Error handling
- Health checks

Following Constitution Principle #3: Mandatory Testing
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from scout.core.state_manager import (
    StateManager,
    StateManagerError,
    SessionNotFoundError
)
from scout.providers.base import Message, Role


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis = Mock()
    redis.ping.return_value = True
    redis.get.return_value = None
    redis.setex.return_value = True
    redis.delete.return_value = 1
    redis.incr.return_value = 1
    redis.expire.return_value = True
    redis.close.return_value = None
    return redis


@pytest.fixture
def state_manager(mock_redis):
    """Create StateManager with mocked Redis."""
    with patch('scout.core.state_manager.Redis.from_url', return_value=mock_redis):
        manager = StateManager(redis_url="redis://localhost:6379")
        return manager


@pytest.mark.unit
class TestStateManagerInitialization:
    """Test suite for state manager initialization."""

    def test_successful_initialization(self, mock_redis):
        """Test successful initialization with Redis."""
        with patch('scout.core.state_manager.Redis.from_url', return_value=mock_redis):
            manager = StateManager()

            assert manager.redis == mock_redis
            assert manager.default_ttl == 7200
            assert manager.max_history == 100
            mock_redis.ping.assert_called_once()

    def test_initialization_with_custom_params(self, mock_redis):
        """Test initialization with custom parameters."""
        with patch('scout.core.state_manager.Redis.from_url', return_value=mock_redis):
            manager = StateManager(
                redis_url="redis://custom:6380",
                default_ttl_seconds=3600,
                max_history_messages=50
            )

            assert manager.default_ttl == 3600
            assert manager.max_history == 50

    def test_initialization_connection_failure(self):
        """Test initialization fails gracefully on connection error."""
        mock_redis = Mock()
        mock_redis.ping.side_effect = RedisConnectionError("Connection refused")

        with patch('scout.core.state_manager.Redis.from_url', return_value=mock_redis):
            with pytest.raises(StateManagerError, match="Redis connection failed"):
                StateManager()

    def test_make_key(self, state_manager):
        """Test key formatting."""
        key = state_manager._make_key("session", "123")
        assert key == "scout:session:123"

        key = state_manager._make_key("cache", "abc")
        assert key == "scout:cache:abc"


@pytest.mark.unit
@pytest.mark.asyncio
class TestSessionManagement:
    """Test suite for session management."""

    async def test_save_session(self, state_manager, mock_redis):
        """Test saving conversation session."""
        messages = [
            Message(role=Role.USER, content="Hello"),
            Message(role=Role.ASSISTANT, content="Hi there!")
        ]

        await state_manager.save_session("session-1", messages)

        # Verify Redis was called
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "scout:session:session-1"
        assert call_args[0][1] == 7200  # default TTL

    async def test_save_session_with_metadata(self, state_manager, mock_redis):
        """Test saving session with metadata."""
        messages = [Message(role=Role.USER, content="Test")]
        metadata = {"user_id": "user-123", "tags": ["important"]}

        await state_manager.save_session(
            "session-1",
            messages,
            metadata=metadata
        )

        mock_redis.setex.assert_called_once()

    async def test_save_session_with_custom_ttl(self, state_manager, mock_redis):
        """Test saving session with custom TTL."""
        messages = [Message(role=Role.USER, content="Test")]

        await state_manager.save_session(
            "session-1",
            messages,
            ttl_seconds=1800
        )

        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 1800  # custom TTL

    async def test_save_session_limits_history(self, state_manager, mock_redis):
        """Test session history is limited to max_history."""
        # Create more messages than max_history
        messages = [
            Message(role=Role.USER, content=f"Message {i}")
            for i in range(150)  # max_history is 100
        ]

        await state_manager.save_session("session-1", messages)

        # Should only save last 100 messages
        call_args = mock_redis.setex.call_args
        import json
        saved_data = json.loads(call_args[0][2])
        assert len(saved_data["messages"]) == 100

    async def test_save_session_redis_error(self, state_manager, mock_redis):
        """Test save session handles Redis errors."""
        mock_redis.setex.side_effect = RedisError("Write failed")

        messages = [Message(role=Role.USER, content="Test")]

        with pytest.raises(StateManagerError, match="Session save failed"):
            await state_manager.save_session("session-1", messages)

    async def test_load_session(self, state_manager, mock_redis):
        """Test loading conversation session."""
        import json

        # Mock stored session data
        session_data = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi!"}
            ],
            "metadata": {"user_id": "123"},
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:01:00"
        }
        mock_redis.get.return_value = json.dumps(session_data)

        result = await state_manager.load_session("session-1")

        assert len(result["messages"]) == 2
        assert result["messages"][0].role == Role.USER
        assert result["messages"][0].content == "Hello"
        assert result["metadata"]["user_id"] == "123"

    async def test_load_session_not_found(self, state_manager, mock_redis):
        """Test loading non-existent session raises error."""
        mock_redis.get.return_value = None

        with pytest.raises(SessionNotFoundError, match="not found"):
            await state_manager.load_session("nonexistent")

    async def test_load_session_redis_error(self, state_manager, mock_redis):
        """Test load session handles Redis errors."""
        mock_redis.get.side_effect = RedisError("Read failed")

        with pytest.raises(StateManagerError, match="Session load failed"):
            await state_manager.load_session("session-1")

    async def test_append_message(self, state_manager, mock_redis):
        """Test appending message to existing session."""
        import json

        # Mock existing session
        session_data = {
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "metadata": {},
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00"
        }
        mock_redis.get.return_value = json.dumps(session_data)

        new_message = Message(role=Role.ASSISTANT, content="Hi!")
        await state_manager.append_message("session-1", new_message)

        # Verify save was called with updated messages
        mock_redis.setex.assert_called_once()

    async def test_delete_session(self, state_manager, mock_redis):
        """Test deleting session."""
        mock_redis.delete.return_value = 1

        result = await state_manager.delete_session("session-1")

        assert result is True
        mock_redis.delete.assert_called_once_with("scout:session:session-1")

    async def test_delete_nonexistent_session(self, state_manager, mock_redis):
        """Test deleting non-existent session."""
        mock_redis.delete.return_value = 0

        result = await state_manager.delete_session("nonexistent")

        assert result is False

    async def test_delete_session_redis_error(self, state_manager, mock_redis):
        """Test delete session handles Redis errors gracefully."""
        mock_redis.delete.side_effect = RedisError("Delete failed")

        result = await state_manager.delete_session("session-1")

        assert result is False  # Should not raise, returns False


@pytest.mark.unit
@pytest.mark.asyncio
class TestResponseCaching:
    """Test suite for response caching."""

    async def test_cache_response(self, state_manager, mock_redis):
        """Test caching AI response."""
        response = {"text": "This is a response", "tokens": 10}

        await state_manager.cache_response("cache-key-1", response)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "scout:cache:cache-key-1"

    async def test_cache_response_with_custom_ttl(self, state_manager, mock_redis):
        """Test caching with custom TTL."""
        response = {"text": "Response"}

        await state_manager.cache_response("key", response, ttl_seconds=600)

        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 600

    async def test_cache_response_redis_error(self, state_manager, mock_redis):
        """Test cache response handles Redis errors."""
        mock_redis.setex.side_effect = RedisError("Write failed")

        with pytest.raises(StateManagerError, match="Cache save failed"):
            await state_manager.cache_response("key", {"data": "test"})

    async def test_get_cached_response_hit(self, state_manager, mock_redis):
        """Test cache hit."""
        import json
        cached_data = {"text": "Cached response"}
        mock_redis.get.return_value = json.dumps(cached_data)

        result = await state_manager.get_cached_response("cache-key")

        assert result == cached_data

    async def test_get_cached_response_miss(self, state_manager, mock_redis):
        """Test cache miss."""
        mock_redis.get.return_value = None

        result = await state_manager.get_cached_response("nonexistent")

        assert result is None

    async def test_get_cached_response_redis_error(self, state_manager, mock_redis):
        """Test get cache handles Redis errors gracefully."""
        mock_redis.get.side_effect = RedisError("Read failed")

        result = await state_manager.get_cached_response("key")

        assert result is None  # Should not raise, returns None


@pytest.mark.unit
@pytest.mark.asyncio
class TestCounterManagement:
    """Test suite for counter management."""

    async def test_increment_counter(self, state_manager, mock_redis):
        """Test incrementing counter."""
        mock_redis.incr.return_value = 1

        value = await state_manager.increment_counter("user-123")

        assert value == 1
        mock_redis.incr.assert_called_once_with("scout:counter:user-123")
        mock_redis.expire.assert_called_once()  # TTL set on first increment

    async def test_increment_counter_multiple_times(self, state_manager, mock_redis):
        """Test incrementing counter multiple times."""
        mock_redis.incr.side_effect = [1, 2, 3]

        value1 = await state_manager.increment_counter("user-123")
        mock_redis.reset_mock()

        mock_redis.incr.return_value = 2
        value2 = await state_manager.increment_counter("user-123")

        assert value1 == 1
        assert value2 == 2

    async def test_increment_counter_with_custom_ttl(self, state_manager, mock_redis):
        """Test counter with custom TTL."""
        mock_redis.incr.return_value = 1

        await state_manager.increment_counter("counter", ttl_seconds=1800)

        mock_redis.expire.assert_called_once()
        call_args = mock_redis.expire.call_args
        assert call_args[0][1] == 1800

    async def test_increment_counter_redis_error(self, state_manager, mock_redis):
        """Test increment counter handles Redis errors."""
        mock_redis.incr.side_effect = RedisError("Increment failed")

        with pytest.raises(StateManagerError, match="Counter increment failed"):
            await state_manager.increment_counter("counter")

    async def test_get_counter(self, state_manager, mock_redis):
        """Test getting counter value."""
        mock_redis.get.return_value = "42"

        value = await state_manager.get_counter("counter")

        assert value == 42

    async def test_get_counter_not_found(self, state_manager, mock_redis):
        """Test getting non-existent counter returns 0."""
        mock_redis.get.return_value = None

        value = await state_manager.get_counter("nonexistent")

        assert value == 0

    async def test_get_counter_redis_error(self, state_manager, mock_redis):
        """Test get counter handles Redis errors gracefully."""
        mock_redis.get.side_effect = RedisError("Read failed")

        value = await state_manager.get_counter("counter")

        assert value == 0  # Should not raise, returns 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestHealthCheck:
    """Test suite for health check."""

    async def test_health_check_healthy(self, state_manager, mock_redis):
        """Test health check when Redis is healthy."""
        mock_redis.ping.return_value = True

        is_healthy = await state_manager.health_check()

        assert is_healthy is True

    async def test_health_check_unhealthy(self, state_manager, mock_redis):
        """Test health check when Redis is down."""
        mock_redis.ping.side_effect = RedisError("Connection lost")

        is_healthy = await state_manager.health_check()

        assert is_healthy is False


@pytest.mark.unit
@pytest.mark.asyncio
class TestCleanup:
    """Test suite for cleanup."""

    async def test_cleanup(self, state_manager, mock_redis):
        """Test cleanup closes Redis connection."""
        await state_manager.cleanup()

        mock_redis.close.assert_called_once()

    async def test_cleanup_error_handled(self, state_manager, mock_redis):
        """Test cleanup handles errors gracefully."""
        mock_redis.close.side_effect = Exception("Close failed")

        # Should not raise
        await state_manager.cleanup()
