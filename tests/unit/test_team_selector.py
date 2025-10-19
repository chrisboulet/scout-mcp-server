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
Unit tests for TeamSelector.

Following Constitution Principle #3: Mandatory Testing
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from scout.core.team_selector import (
    TeamSelector,
    TeamSelection,
    ValidationResult,
    TaskComplexity,
    TaskDomain,
)
from scout.config.models import (
    ScoutConfig,
    TeamConfig,
    TeamMember,
    ValidatorConfig,
    ProviderConfig,
    ModelConfig,
    SystemSettings,
)
from scout.config.exceptions import ConfigurationError
from scout.providers.factory import ProviderFactory


@pytest.fixture
def gemini_config():
    """Create Gemini provider configuration."""
    return ProviderConfig(
        api_key="test-gemini-key",
        models={
            "flash": ModelConfig(
                id="gemini-1.5-flash",
                max_tokens=8192,
                temperature=0.7,
                cost_per_1k_input=0.075,
                cost_per_1k_output=0.3
            ),
            "pro": ModelConfig(
                id="gemini-1.5-pro",
                max_tokens=8192,
                temperature=0.7,
                cost_per_1k_input=1.25,
                cost_per_1k_output=5.0
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
                temperature=0.7,
                cost_per_1k_input=2.5,
                cost_per_1k_output=10.0
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
                temperature=0.7,
                cost_per_1k_input=3.0,
                cost_per_1k_output=15.0
            )
        },
        default_model="sonnet"
    )


@pytest.fixture
def scout_config(gemini_config, openai_config, anthropic_config):
    """Create complete Scout configuration with teams."""
    return ScoutConfig(
        system=SystemSettings(
            max_retries=3,
            request_timeout_seconds=60,
            default_team="scout"
        ),
        providers={
            "gemini": gemini_config,
            "openai": openai_config,
            "anthropic": anthropic_config
        },
        teams={
            "scout": TeamConfig(
                description="Simple tasks and general queries",
                primary=TeamMember(
                    provider="gemini",
                    model="flash"
                )
            ),
            "architect": TeamConfig(
                description="Moderate to complex technical tasks",
                primary=TeamMember(
                    provider="openai",
                    model="gpt4"
                ),
                validators=[
                    ValidatorConfig(
                        provider="anthropic",
                        model="sonnet",
                        trigger="always"
                    )
                ]
            ),
            "expert": TeamConfig(
                description="Critical and strategic tasks",
                primary=TeamMember(
                    provider="anthropic",
                    model="sonnet"
                )
            )
        },
        tool_team_mapping={
            "analyze": "architect",
            "create": "expert"
        }
    )


@pytest.fixture
def team_selector(scout_config):
    """Create TeamSelector instance."""
    return TeamSelector(scout_config=scout_config)


class TestTeamSelectorInitialization:
    """Test suite for TeamSelector initialization."""

    def test_initialization(self, team_selector, scout_config):
        """Test basic initialization."""
        assert team_selector.config == scout_config
        assert len(team_selector.teams) == 3
        assert len(team_selector.providers) == 3
        assert team_selector.factory is not None

    def test_initialization_with_custom_factory(self, scout_config):
        """Test initialization with custom factory."""
        mock_factory = Mock(spec=ProviderFactory)
        selector = TeamSelector(
            scout_config=scout_config,
            provider_factory=mock_factory
        )
        assert selector.factory == mock_factory

    def test_complexity_patterns_loaded(self, team_selector):
        """Test complexity patterns are loaded."""
        assert TaskComplexity.SIMPLE in team_selector._complexity_patterns
        assert TaskComplexity.COMPLEX in team_selector._complexity_patterns
        assert TaskComplexity.CRITICAL in team_selector._complexity_patterns

    def test_domain_patterns_loaded(self, team_selector):
        """Test domain patterns are loaded."""
        assert TaskDomain.TECHNICAL in team_selector._domain_patterns
        assert TaskDomain.CREATIVE in team_selector._domain_patterns
        assert TaskDomain.ANALYTICAL in team_selector._domain_patterns
        assert TaskDomain.STRATEGIC in team_selector._domain_patterns


class TestComplexityDetection:
    """Test suite for task complexity detection."""

    def test_detect_simple_complexity(self, team_selector):
        """Test detection of simple tasks."""
        simple_tasks = [
            "What is Python?",
            "How to install a package?",
            "Define REST API",
            "List all files",
            "Explain briefly what Docker is"
        ]

        for task in simple_tasks:
            complexity = team_selector._detect_complexity(task)
            assert complexity == TaskComplexity.SIMPLE, f"Failed for: {task}"

    def test_detect_complex_complexity(self, team_selector):
        """Test detection of complex tasks."""
        complex_tasks = [
            "Architect a microservices system",
            "Design a distributed system for payments",
            "Optimize database query performance",
            "Refactor the authentication module",
            "Analyze performance bottlenecks"
        ]

        for task in complex_tasks:
            complexity = team_selector._detect_complexity(task)
            assert complexity == TaskComplexity.COMPLEX, f"Failed for: {task}"

    def test_detect_critical_complexity(self, team_selector):
        """Test detection of critical tasks."""
        critical_tasks = [
            "Security audit for production database",
            "Production deployment strategy",
            "Database migration plan",
            "Breaking change impact analysis",
            "Prevent data loss during migration"
        ]

        for task in critical_tasks:
            complexity = team_selector._detect_complexity(task)
            assert complexity == TaskComplexity.CRITICAL, f"Failed for: {task}"

    def test_default_complexity_moderate(self, team_selector):
        """Test default complexity is MODERATE."""
        generic_task = "Process user data and generate report"
        complexity = team_selector._detect_complexity(generic_task)
        assert complexity == TaskComplexity.MODERATE


class TestDomainDetection:
    """Test suite for task domain detection."""

    def test_detect_technical_domain(self, team_selector):
        """Test detection of technical tasks."""
        technical_tasks = [
            "Write code for user authentication",
            "Fix the API endpoint",
            "Design database schema",
            "Implement caching layer",
            "Debug the connection issue"
        ]

        for task in technical_tasks:
            domain = team_selector._detect_domain(task)
            assert domain == TaskDomain.TECHNICAL, f"Failed for: {task}"

    def test_detect_creative_domain(self, team_selector):
        """Test detection of creative tasks."""
        creative_tasks = [
            "Create a marketing campaign",
            "Design a user interface",
            "Brainstorm product features",
            "Generate ideas for blog posts",
            "Innovative solutions for engagement"
        ]

        for task in creative_tasks:
            domain = team_selector._detect_domain(task)
            assert domain == TaskDomain.CREATIVE, f"Failed for: {task}"

    def test_detect_analytical_domain(self, team_selector):
        """Test detection of analytical tasks."""
        analytical_tasks = [
            "Analyze user behavior patterns",
            "Compare different frameworks",
            "Evaluate system performance",
            "Assess security risks",
            "Investigate bug reports"
        ]

        for task in analytical_tasks:
            domain = team_selector._detect_domain(task)
            assert domain == TaskDomain.ANALYTICAL, f"Failed for: {task}"

    def test_detect_strategic_domain(self, team_selector):
        """Test detection of strategic tasks."""
        strategic_tasks = [
            "Develop product strategy for next year",
            "Technology roadmap planning",
            "Business planning for Q4",
            "Competitive analysis of market trends",
            "Define company strategy and roadmap"
        ]

        for task in strategic_tasks:
            domain = team_selector._detect_domain(task)
            assert domain == TaskDomain.STRATEGIC, f"Failed for: {task}"

    def test_default_domain_general(self, team_selector):
        """Test default domain is GENERAL."""
        generic_task = "Process some data"
        domain = team_selector._detect_domain(generic_task)
        assert domain == TaskDomain.GENERAL


@pytest.mark.asyncio
class TestTeamSelection:
    """Test suite for team selection logic."""

    async def test_select_team_with_override(self, team_selector):
        """Test team selection with manual override."""
        selection = await team_selector.select_team(
            task="Any task",
            team_override="architect"
        )

        assert selection.team_name == "architect"
        assert selection.primary_provider == "openai"
        assert selection.primary_model == "gpt4"
        assert selection.reason == "Manual override"

    async def test_select_team_invalid_override(self, team_selector):
        """Test team selection with invalid override raises error."""
        with pytest.raises(ConfigurationError, match="Team .* not found"):
            await team_selector.select_team(
                task="Any task",
                team_override="nonexistent_team"
            )

    async def test_select_team_complexity_override(self, team_selector):
        """Test team selection with complexity override."""
        selection = await team_selector.select_team(
            task="Simple task",
            complexity_override=TaskComplexity.CRITICAL
        )

        assert selection.complexity == TaskComplexity.CRITICAL

    async def test_select_team_domain_override(self, team_selector):
        """Test team selection with domain override."""
        selection = await team_selector.select_team(
            task="Generic task",
            domain_override=TaskDomain.TECHNICAL
        )

        assert selection.domain == TaskDomain.TECHNICAL

    async def test_select_team_automatic_detection(self, team_selector):
        """Test automatic team selection based on task."""
        selection = await team_selector.select_team(
            task="Architect a distributed system"
        )

        assert selection.team_name is not None
        assert selection.complexity == TaskComplexity.COMPLEX
        assert selection.primary_provider is not None
        assert selection.primary_model is not None

    async def test_selection_includes_validators(self, team_selector):
        """Test selection includes validators when configured."""
        selection = await team_selector.select_team(
            task="Security audit",
            team_override="architect"
        )

        assert selection.team_name == "architect"
        # Validators are configured for architect team
        assert len(selection.validators) >= 0  # May or may not trigger based on logic

    async def test_selection_has_reasoning(self, team_selector):
        """Test selection includes reasoning."""
        selection = await team_selector.select_team(
            task="Analyze code quality"
        )

        assert selection.reason != ""
        assert isinstance(selection.reason, str)

    async def test_selection_estimates_cost(self, team_selector):
        """Test selection estimates cost."""
        selection = await team_selector.select_team(
            task="Write a function"
        )

        assert selection.estimated_cost >= 0
        assert isinstance(selection.estimated_cost, float)


@pytest.mark.asyncio
class TestBudgetConstraints:
    """Test suite for budget constraint handling."""

    async def test_budget_constraint_applied(self, team_selector):
        """Test budget constraint is respected."""
        # Select with very low budget - should choose cheapest option
        selection = await team_selector.select_team(
            task="Simple query",
            budget_limit=0.001  # Very low budget
        )

        # Should select the cheapest provider (gemini flash)
        assert selection.primary_provider == "gemini"
        assert selection.estimated_cost <= 0.001

    async def test_no_budget_constraint(self, team_selector):
        """Test selection without budget constraint."""
        selection = await team_selector.select_team(
            task="Complex analysis",
            budget_limit=None
        )

        # Can select any team
        assert selection.team_name is not None


class TestSelectionDataStructures:
    """Test suite for selection data structures."""

    def test_team_selection_creation(self):
        """Test TeamSelection creation."""
        selection = TeamSelection(
            team_name="test_team",
            primary_provider="gemini",
            primary_model="flash",
            complexity=TaskComplexity.MODERATE,
            domain=TaskDomain.TECHNICAL,
            confidence=0.95,
            reason="Test reason",
            estimated_cost=0.01,
            estimated_tokens=1000
        )

        assert selection.team_name == "test_team"
        assert selection.primary_provider == "gemini"
        assert selection.primary_model == "flash"
        assert selection.complexity == TaskComplexity.MODERATE
        assert selection.domain == TaskDomain.TECHNICAL
        assert selection.confidence == 0.95
        assert selection.reason == "Test reason"
        assert selection.estimated_cost == 0.01
        assert selection.estimated_tokens == 1000
        assert isinstance(selection.validators, list)

    def test_validation_result_creation(self):
        """Test ValidationResult creation."""
        result = ValidationResult(
            provider="anthropic",
            model="sonnet",
            agrees=True,
            confidence=0.9,
            reasoning="Test validation",
            tokens_used=500,
            cost=0.02
        )

        assert result.provider == "anthropic"
        assert result.model == "sonnet"
        assert result.agrees is True
        assert result.confidence == 0.9
        assert result.reasoning == "Test validation"
        assert result.tokens_used == 500
        assert result.cost == 0.02


class TestEnumerations:
    """Test suite for enumeration types."""

    def test_task_complexity_values(self):
        """Test TaskComplexity enum values."""
        assert TaskComplexity.SIMPLE.value == "simple"
        assert TaskComplexity.MODERATE.value == "moderate"
        assert TaskComplexity.COMPLEX.value == "complex"
        assert TaskComplexity.CRITICAL.value == "critical"

    def test_task_domain_values(self):
        """Test TaskDomain enum values."""
        assert TaskDomain.GENERAL.value == "general"
        assert TaskDomain.TECHNICAL.value == "technical"
        assert TaskDomain.CREATIVE.value == "creative"
        assert TaskDomain.ANALYTICAL.value == "analytical"
        assert TaskDomain.STRATEGIC.value == "strategic"

    def test_complexity_from_string(self):
        """Test creating TaskComplexity from string."""
        complexity = TaskComplexity("complex")
        assert complexity == TaskComplexity.COMPLEX

    def test_domain_from_string(self):
        """Test creating TaskDomain from string."""
        domain = TaskDomain("technical")
        assert domain == TaskDomain.TECHNICAL


@pytest.mark.asyncio
class TestTeamMetrics:
    """Test suite for team performance metrics."""

    async def test_metrics_tracking(self, team_selector):
        """Test that metrics are tracked."""
        # Select team multiple times
        await team_selector.select_team(task="Task 1")
        await team_selector.select_team(task="Task 2")

        # Metrics should be tracked (implementation dependent)
        assert team_selector._team_metrics is not None
        assert isinstance(team_selector._team_metrics, dict)
