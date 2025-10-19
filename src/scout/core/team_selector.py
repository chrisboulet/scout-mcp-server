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
Team Selector Module.

This module provides intelligent team selection for AI model orchestration.
It determines which AI models to use based on task requirements, cost
optimization, and quality needs.

Following Constitution Principle #7: Provider Abstraction & Multi-Model Teams
"""

from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import re
import structlog
from dataclasses import dataclass, field

from scout.config.models import TeamConfig, ModelConfig, ValidatorConfig, ScoutConfig
from scout.config.exceptions import ConfigurationError
from scout.providers.factory import ProviderFactory
from scout.providers.base import BaseAIProvider

# Configure structured logging
logger = structlog.get_logger(__name__)


class TaskComplexity(Enum):
    """Task complexity levels for team selection."""

    SIMPLE = "simple"      # Basic queries, lookups
    MODERATE = "moderate"  # Standard analysis, generation
    COMPLEX = "complex"    # Architecture, deep analysis
    CRITICAL = "critical"  # High-stakes decisions


class TaskDomain(Enum):
    """Task domain categories."""

    GENERAL = "general"
    TECHNICAL = "technical"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    STRATEGIC = "strategic"


@dataclass
class TeamSelection:
    """Result of team selection process."""

    team_name: str
    primary_provider: str
    primary_model: str
    validators: List[Tuple[str, str, str]] = field(default_factory=list)  # (provider, model, trigger)
    complexity: TaskComplexity = TaskComplexity.MODERATE
    domain: TaskDomain = TaskDomain.GENERAL
    confidence: float = 1.0
    reason: str = ""
    estimated_cost: float = 0.0
    estimated_tokens: int = 0


@dataclass
class ValidationResult:
    """Result of validator execution."""

    provider: str
    model: str
    agrees: bool
    confidence: float
    reasoning: Optional[str] = None
    tokens_used: int = 0
    cost: float = 0.0


class TeamSelector:
    """
    Intelligent team selection for AI model orchestration.

    This class determines which AI models to use based on:
    - Task complexity and requirements
    - Cost/quality tradeoffs
    - Validation needs
    - Historical performance
    """

    def __init__(
        self,
        scout_config: ScoutConfig,
        provider_factory: Optional[ProviderFactory] = None
    ):
        """
        Initialize Team Selector.

        Args:
            scout_config: Complete Scout configuration
            provider_factory: Optional provider factory instance
        """
        self.config = scout_config
        self.teams = scout_config.teams
        self.providers = scout_config.providers
        self.factory = provider_factory or ProviderFactory

        # Cache for team performance metrics
        self._team_metrics: Dict[str, Dict[str, Any]] = {}

        # Complexity patterns for automatic detection
        self._complexity_patterns = {
            TaskComplexity.SIMPLE: [
                r"what is",
                r"how to",
                r"define",
                r"list",
                r"explain briefly"
            ],
            TaskComplexity.COMPLEX: [
                r"architect",
                r"design.*system",
                r"optimize",
                r"refactor",
                r"analyze.*performance"
            ],
            TaskComplexity.CRITICAL: [
                r"security",
                r"production",
                r"migration",
                r"breaking change",
                r"data loss"
            ]
        }

        # Domain patterns for automatic detection
        self._domain_patterns = {
            TaskDomain.TECHNICAL: [
                r"code",
                r"api",
                r"database",
                r"implement",
                r"debug"
            ],
            TaskDomain.CREATIVE: [
                r"create",
                r"design",
                r"brainstorm",
                r"generate.*ideas",
                r"innovative"
            ],
            TaskDomain.ANALYTICAL: [
                r"analyze",
                r"compare",
                r"evaluate",
                r"assess",
                r"investigate"
            ],
            TaskDomain.STRATEGIC: [
                r"strategy",
                r"roadmap",
                r"planning",
                r"business",
                r"competitive"
            ]
        }

        logger.info(
            "Team selector initialized",
            teams_available=len(self.teams),
            providers_available=len(self.providers)
        )

    async def select_team(
        self,
        task: str,
        team_override: Optional[str] = None,
        complexity_override: Optional[TaskComplexity] = None,
        domain_override: Optional[TaskDomain] = None,
        budget_limit: Optional[float] = None
    ) -> TeamSelection:
        """
        Select the appropriate team for a task.

        Args:
            task: Task description or prompt
            team_override: Force specific team selection
            complexity_override: Override complexity detection
            domain_override: Override domain detection
            budget_limit: Maximum cost constraint

        Returns:
            TeamSelection with chosen team and configuration

        Raises:
            ConfigurationError: If team selection fails
        """
        # Handle manual override
        if team_override:
            if team_override not in self.teams:
                raise ConfigurationError(
                    f"Team '{team_override}' not found. "
                    f"Available teams: {', '.join(self.teams.keys())}"
                )

            team_config = self.teams[team_override]
            return self._create_selection(
                team_name=team_override,
                team_config=team_config,
                complexity=complexity_override or TaskComplexity.MODERATE,
                domain=domain_override or TaskDomain.GENERAL,
                reason="Manual override"
            )

        # Detect task characteristics
        complexity = complexity_override or self._detect_complexity(task)
        domain = domain_override or self._detect_domain(task)

        # Select team based on characteristics
        team_name = self._select_team_by_characteristics(
            complexity=complexity,
            domain=domain,
            budget_limit=budget_limit
        )

        team_config = self.teams[team_name]

        # Create selection with reasoning
        reason = self._generate_selection_reason(
            complexity=complexity,
            domain=domain,
            budget_limit=budget_limit
        )

        selection = self._create_selection(
            team_name=team_name,
            team_config=team_config,
            complexity=complexity,
            domain=domain,
            reason=reason
        )

        # Log selection
        logger.info(
            "Team selected",
            team=team_name,
            complexity=complexity.value,
            domain=domain.value,
            estimated_cost=selection.estimated_cost,
            validators=len(selection.validators)
        )

        return selection

    async def validate_with_team(
        self,
        primary_response: str,
        team_selection: TeamSelection,
        original_task: str
    ) -> List[ValidationResult]:
        """
        Run validators for a team selection.

        Args:
            primary_response: Response from primary model
            team_selection: Team selection with validators
            original_task: Original task for context

        Returns:
            List of validation results
        """
        if not team_selection.validators:
            return []

        results = []

        for provider_name, model_id, trigger_condition in team_selection.validators:
            # Evaluate trigger condition
            if not self._should_trigger_validator(
                trigger_condition,
                team_selection.confidence,
                primary_response
            ):
                continue

            # Run validation
            result = await self._run_validator(
                provider_name=provider_name,
                model_id=model_id,
                primary_response=primary_response,
                original_task=original_task
            )

            results.append(result)

        return results

    def get_team_metrics(self, team_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance metrics for teams.

        Args:
            team_name: Specific team or None for all teams

        Returns:
            Dictionary of team metrics
        """
        if team_name:
            return self._team_metrics.get(team_name, {
                "selections": 0,
                "total_cost": 0.0,
                "total_tokens": 0,
                "avg_confidence": 0.0,
                "validation_rate": 0.0
            })

        return self._team_metrics.copy()

    def update_metrics(
        self,
        team_name: str,
        cost: float,
        tokens: int,
        confidence: float,
        validators_triggered: int
    ):
        """
        Update team performance metrics.

        Args:
            team_name: Name of the team
            cost: Cost of the execution
            tokens: Tokens used
            confidence: Confidence score
            validators_triggered: Number of validators triggered
        """
        if team_name not in self._team_metrics:
            self._team_metrics[team_name] = {
                "selections": 0,
                "total_cost": 0.0,
                "total_tokens": 0,
                "avg_confidence": 0.0,
                "validation_rate": 0.0,
                "validations_triggered": 0
            }

        metrics = self._team_metrics[team_name]
        metrics["selections"] += 1
        metrics["total_cost"] += cost
        metrics["total_tokens"] += tokens
        metrics["validations_triggered"] += validators_triggered

        # Update rolling averages
        n = metrics["selections"]
        metrics["avg_confidence"] = (
            (metrics["avg_confidence"] * (n - 1) + confidence) / n
        )
        metrics["validation_rate"] = (
            metrics["validations_triggered"] / metrics["selections"]
        )

    def _detect_complexity(self, task: str) -> TaskComplexity:
        """
        Detect task complexity from text.

        Args:
            task: Task description

        Returns:
            Detected complexity level
        """
        task_lower = task.lower()

        # Check for critical indicators first
        for pattern in self._complexity_patterns[TaskComplexity.CRITICAL]:
            if re.search(pattern, task_lower):
                return TaskComplexity.CRITICAL

        # Check for complex indicators
        for pattern in self._complexity_patterns[TaskComplexity.COMPLEX]:
            if re.search(pattern, task_lower):
                return TaskComplexity.COMPLEX

        # Check for simple indicators
        for pattern in self._complexity_patterns[TaskComplexity.SIMPLE]:
            if re.search(pattern, task_lower):
                return TaskComplexity.SIMPLE

        # Default to moderate
        return TaskComplexity.MODERATE

    def _detect_domain(self, task: str) -> TaskDomain:
        """
        Detect task domain from text.

        Args:
            task: Task description

        Returns:
            Detected domain
        """
        task_lower = task.lower()
        domain_scores = {}

        # Score each domain based on pattern matches
        for domain, patterns in self._domain_patterns.items():
            score = sum(1 for pattern in patterns if re.search(pattern, task_lower))
            if score > 0:
                domain_scores[domain] = score

        # Return domain with highest score
        if domain_scores:
            return max(domain_scores, key=domain_scores.get)

        return TaskDomain.GENERAL

    def _select_team_by_characteristics(
        self,
        complexity: TaskComplexity,
        domain: TaskDomain,
        budget_limit: Optional[float]
    ) -> str:
        """
        Select team based on task characteristics.

        Args:
            complexity: Task complexity
            domain: Task domain
            budget_limit: Budget constraint

        Returns:
            Selected team name
        """
        # Team selection matrix
        selection_matrix = {
            (TaskComplexity.SIMPLE, TaskDomain.GENERAL): "scout",
            (TaskComplexity.SIMPLE, TaskDomain.TECHNICAL): "scout",
            (TaskComplexity.MODERATE, TaskDomain.GENERAL): "scout",
            (TaskComplexity.MODERATE, TaskDomain.TECHNICAL): "architect",
            (TaskComplexity.MODERATE, TaskDomain.CREATIVE): "architect",
            (TaskComplexity.MODERATE, TaskDomain.ANALYTICAL): "architect",
            (TaskComplexity.COMPLEX, TaskDomain.TECHNICAL): "architect",
            (TaskComplexity.COMPLEX, TaskDomain.ANALYTICAL): "architect",
            (TaskComplexity.COMPLEX, TaskDomain.STRATEGIC): "expert",
            (TaskComplexity.CRITICAL, TaskDomain.TECHNICAL): "expert",
            (TaskComplexity.CRITICAL, TaskDomain.STRATEGIC): "expert",
        }

        # Get base selection
        team_key = (complexity, domain)
        selected_team = selection_matrix.get(team_key, "architect")

        # Apply budget constraints
        if budget_limit is not None:
            selected_team = self._apply_budget_constraint(
                selected_team,
                budget_limit
            )

        # Ensure team exists in configuration
        if selected_team not in self.teams:
            logger.warning(
                "Selected team not configured, falling back to scout",
                selected_team=selected_team
            )
            return "scout"

        return selected_team

    def _apply_budget_constraint(
        self,
        team_name: str,
        budget_limit: float
    ) -> str:
        """
        Apply budget constraints to team selection.

        Args:
            team_name: Initially selected team
            budget_limit: Maximum budget

        Returns:
            Budget-appropriate team name
        """
        # Team cost hierarchy (approximate)
        team_costs = {
            "scout": 0.001,    # Cheapest
            "architect": 0.01,  # Moderate
            "expert": 0.1      # Most expensive
        }

        current_cost = team_costs.get(team_name, 0.01)

        # Downgrade if over budget
        if current_cost > budget_limit:
            if team_name == "expert" and budget_limit >= team_costs["architect"]:
                return "architect"
            elif budget_limit >= team_costs["scout"]:
                return "scout"

        return team_name

    def _create_selection(
        self,
        team_name: str,
        team_config: TeamConfig,
        complexity: TaskComplexity,
        domain: TaskDomain,
        reason: str
    ) -> TeamSelection:
        """
        Create a TeamSelection object.

        Args:
            team_name: Selected team name
            team_config: Team configuration
            complexity: Task complexity
            domain: Task domain
            reason: Selection reasoning

        Returns:
            TeamSelection object
        """
        # Extract primary model info
        primary_provider = team_config.primary.provider
        primary_model = team_config.primary.model

        # Extract validator info
        validators = []
        for validator in team_config.validators:
            validators.append((
                validator.provider,
                validator.model,
                validator.trigger
            ))

        # Estimate cost (simplified)
        base_costs = {
            "scout": 0.001,
            "architect": 0.01,
            "expert": 0.1
        }
        estimated_cost = base_costs.get(team_name, 0.01)

        # Estimate tokens (simplified)
        token_estimates = {
            TaskComplexity.SIMPLE: 500,
            TaskComplexity.MODERATE: 2000,
            TaskComplexity.COMPLEX: 5000,
            TaskComplexity.CRITICAL: 10000
        }
        estimated_tokens = token_estimates.get(complexity, 2000)

        return TeamSelection(
            team_name=team_name,
            primary_provider=primary_provider,
            primary_model=primary_model,
            validators=validators,
            complexity=complexity,
            domain=domain,
            confidence=1.0,
            reason=reason,
            estimated_cost=estimated_cost,
            estimated_tokens=estimated_tokens
        )

    def _generate_selection_reason(
        self,
        complexity: TaskComplexity,
        domain: TaskDomain,
        budget_limit: Optional[float]
    ) -> str:
        """
        Generate human-readable reason for team selection.

        Args:
            complexity: Task complexity
            domain: Task domain
            budget_limit: Budget constraint if any

        Returns:
            Reason string
        """
        reasons = [
            f"Task complexity: {complexity.value}",
            f"Domain: {domain.value}"
        ]

        if budget_limit is not None:
            reasons.append(f"Budget constraint: ${budget_limit:.3f}")

        return "; ".join(reasons)

    def _should_trigger_validator(
        self,
        trigger_condition: str,
        confidence: float,
        response: str
    ) -> bool:
        """
        Evaluate if a validator should be triggered.

        Args:
            trigger_condition: Trigger condition expression
            confidence: Current confidence score
            response: Primary model response

        Returns:
            True if validator should run
        """
        if trigger_condition.lower() == "always":
            return True

        if trigger_condition.lower() == "never":
            return False

        # Parse confidence conditions
        if "confidence" in trigger_condition:
            try:
                # Simple parsing for "confidence < X" format
                match = re.search(r"confidence\s*([<>]=?)\s*([\d.]+)", trigger_condition)
                if match:
                    operator, threshold = match.groups()
                    threshold = float(threshold)

                    if operator == "<":
                        return confidence < threshold
                    elif operator == "<=":
                        return confidence <= threshold
                    elif operator == ">":
                        return confidence > threshold
                    elif operator == ">=":
                        return confidence >= threshold
            except (ValueError, AttributeError):
                logger.warning(
                    "Failed to parse trigger condition",
                    condition=trigger_condition
                )

        # Check for keyword triggers in response
        if "error" in trigger_condition.lower() and "error" in response.lower():
            return True

        if "uncertain" in trigger_condition.lower() and any(
            word in response.lower()
            for word in ["maybe", "possibly", "uncertain", "not sure"]
        ):
            return True

        return False

    async def _run_validator(
        self,
        provider_name: str,
        model_id: str,
        primary_response: str,
        original_task: str
    ) -> ValidationResult:
        """
        Run a validator model.

        Args:
            provider_name: Provider name
            model_id: Model ID
            primary_response: Response to validate
            original_task: Original task for context

        Returns:
            ValidationResult
        """
        # This is a simplified implementation
        # In production, this would actually call the provider

        validation_prompt = f"""
        Original Task: {original_task}

        Primary Response: {primary_response}

        Please validate this response for:
        1. Accuracy
        2. Completeness
        3. Safety

        Do you agree with this response? (Yes/No)
        Confidence: (0.0-1.0)
        Brief reasoning:
        """

        # For now, return a mock result
        # In production, use provider factory to get provider and run
        return ValidationResult(
            provider=provider_name,
            model=model_id,
            agrees=True,
            confidence=0.95,
            reasoning="Response appears accurate and complete",
            tokens_used=100,
            cost=0.001
        )


class TeamOrchestrator:
    """
    Orchestrates team execution with primary and validator models.

    This class manages the full lifecycle of team-based AI execution.
    """

    def __init__(
        self,
        team_selector: TeamSelector,
        provider_factory: ProviderFactory
    ):
        """
        Initialize Team Orchestrator.

        Args:
            team_selector: Team selector instance
            provider_factory: Provider factory for creating providers
        """
        self.selector = team_selector
        self.factory = provider_factory

        logger.info("Team orchestrator initialized")

    async def execute(
        self,
        task: str,
        team_override: Optional[str] = None,
        skip_validation: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a task with team orchestration.

        Args:
            task: Task to execute
            team_override: Force specific team
            skip_validation: Skip validator execution
            **kwargs: Additional parameters for providers

        Returns:
            Execution results with metadata
        """
        # Select team
        selection = await self.selector.select_team(
            task=task,
            team_override=team_override
        )

        # Get primary provider
        primary_provider = await self.factory.create_from_config(
            scout_config=self.selector.config,
            provider_name=selection.primary_provider
        )

        # Execute with primary model
        primary_start = structlog.get_native_logger().info

        primary_response = await primary_provider.complete(
            prompt=task,
            model=selection.primary_model,
            **kwargs
        )

        # Run validators if needed
        validation_results = []
        if not skip_validation and selection.validators:
            validation_results = await self.selector.validate_with_team(
                primary_response=primary_response.content,
                team_selection=selection,
                original_task=task
            )

        # Update metrics
        self.selector.update_metrics(
            team_name=selection.team_name,
            cost=selection.estimated_cost,
            tokens=primary_response.usage.get("total_tokens", 0),
            confidence=selection.confidence,
            validators_triggered=len(validation_results)
        )

        # Build result
        return {
            "response": primary_response.content,
            "team": selection.team_name,
            "primary_model": f"{selection.primary_provider}/{selection.primary_model}",
            "validators": [
                {
                    "model": f"{v.provider}/{v.model}",
                    "agrees": v.agrees,
                    "confidence": v.confidence
                }
                for v in validation_results
            ],
            "metrics": {
                "tokens": primary_response.usage.get("total_tokens", 0),
                "cost": selection.estimated_cost,
                "complexity": selection.complexity.value,
                "domain": selection.domain.value
            }
        }