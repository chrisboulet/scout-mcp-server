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
Strategic Planner Tool - Iterative strategic planning with revision.

This tool provides strategic planning capabilities:
- Multi-step planning workflow
- Iterative refinement and revision
- Alternative plan branches
- Dependency tracking
- Resource estimation
- Risk identification
- Feasibility validation

Inspired by Zen MCP's planner tool.

Following Constitution Principles:
- #1: Contract-First Development (MCP schema)
- #2: Modular Architecture
- #4: AI Provider Abstraction
- #5: Robust Error Handling
- #6: Structured Logging
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum
import structlog
from datetime import datetime, timezone

from scout.core.tool_registry import (
    BaseTool,
    ToolMetadata,
    ToolSchema,
    ToolCategory,
    ToolPermission
)
from scout.providers.base import BaseAIProvider, Message, Role

# Configure structured logging
logger = structlog.get_logger(__name__)


class PlanStatus(str, Enum):
    """Status of planning process."""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    REVISED = "revised"
    FINALIZED = "finalized"


class PlanStep(BaseModel):
    """A step in the strategic plan."""

    step_number: int = Field(..., description="Step number in sequence")
    title: str = Field(..., description="Step title")
    description: str = Field(..., description="Detailed description")
    dependencies: List[int] = Field(default_factory=list, description="Step numbers this depends on")
    estimated_duration: Optional[str] = Field(None, description="Estimated time (e.g., '2 weeks')")
    estimated_cost: Optional[str] = Field(None, description="Estimated cost (e.g., '$5000')")
    resources_required: List[str] = Field(default_factory=list, description="Resources needed")
    risks: List[str] = Field(default_factory=list, description="Identified risks")
    success_criteria: List[str] = Field(default_factory=list, description="How to measure success")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PlanningIteration(BaseModel):
    """A planning iteration with refinements."""

    iteration_number: int = Field(..., description="Iteration number")
    focus: str = Field(..., description="Focus of this iteration")
    changes_made: List[str] = Field(default_factory=list, description="Changes from previous iteration")
    rationale: str = Field(..., description="Why these changes were made")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class StrategicPlannerInput(BaseModel):
    """Input schema for strategic planner."""

    objective: str = Field(
        ...,
        description="Strategic objective or goal to plan for",
        min_length=10,
        max_length=10000
    )
    context: Optional[str] = Field(
        None,
        description="Context, constraints, and requirements",
        max_length=50000
    )
    max_iterations: int = Field(
        default=3,
        description="Maximum planning iterations",
        ge=1,
        le=10
    )
    include_alternatives: bool = Field(
        default=False,
        description="Generate alternative plan branches"
    )
    focus_areas: Optional[List[str]] = Field(
        None,
        description="Specific areas to focus on (e.g., ['timeline', 'budget', 'risks'])"
    )
    team_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Team selection context (injected by server)",
        exclude=True
    )


class StrategicPlannerOutput(BaseModel):
    """Output schema for strategic planner."""

    summary: str = Field(..., description="Executive summary of the plan")
    objective: str = Field(..., description="The objective being planned for")
    status: PlanStatus = Field(..., description="Current status of the plan")
    plan_steps: List[PlanStep] = Field(..., description="Detailed plan steps")
    iterations: List[PlanningIteration] = Field(..., description="Planning iterations performed")
    timeline_overview: str = Field(..., description="Overall timeline summary")
    budget_overview: str = Field(..., description="Overall budget summary")
    critical_path: List[int] = Field(default_factory=list, description="Step numbers on critical path")
    key_risks: List[str] = Field(..., description="Major identified risks")
    recommendations: List[str] = Field(..., description="Strategic recommendations")
    alternative_plans: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Alternative plan options if requested"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Planning metadata (duration, tokens, etc.)"
    )


class StrategicPlannerTool(BaseTool):
    """
    Strategic Planner Tool - Iterative strategic planning.

    This tool creates comprehensive strategic plans through:
    1. Understanding the objective and constraints
    2. Breaking down into actionable steps
    3. Identifying dependencies
    4. Estimating resources and timeline
    5. Identifying risks
    6. Iteratively refining the plan
    7. Validating feasibility

    Example Usage:
        Simple planning:
        {
            "objective": "Migrate legacy system to cloud",
            "context": "On-premise system, 50 users, $100K budget, 6 months"
        }

        Detailed planning with alternatives:
        {
            "objective": "Launch new product line",
            "context": "B2B SaaS, competitive market, existing customer base",
            "max_iterations": 5,
            "include_alternatives": true,
            "focus_areas": ["timeline", "budget", "risks", "go-to-market"]
        }
    """

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        return ToolMetadata(
            name="strategic_planner",
            description="Create comprehensive strategic plans with iterative refinement",
            category=ToolCategory.GENERATION,
            version="1.0.0",
            author="SCOUT Team",
            permissions={ToolPermission.READ, ToolPermission.WRITE},
            tags=["planning", "strategy", "roadmap", "consultant", "project"],
            examples=[
                {
                    "objective": "Implement DevOps practices across organization",
                    "context": "10 development teams, legacy CI/CD, 6-month timeline"
                },
                {
                    "objective": "Reduce operational costs by 30%",
                    "context": "Cloud infrastructure, $500K annual spend",
                    "include_alternatives": True
                }
            ],
            cost_estimate=0.03,
            avg_latency_ms=10000
        )

    def get_schema(self) -> ToolSchema:
        """Get tool schema."""
        return ToolSchema(
            input_model=StrategicPlannerInput,
            output_model=StrategicPlannerOutput
        )

    async def execute(
        self,
        objective: str,
        context: Optional[str] = None,
        max_iterations: int = 3,
        include_alternatives: bool = False,
        focus_areas: Optional[List[str]] = None,
        team_context: Optional[Dict[str, Any]] = None,
        provider: Optional[BaseAIProvider] = None
    ) -> Dict[str, Any]:
        """
        Execute strategic planning.

        Args:
            objective: Strategic objective to plan for
            context: Context and constraints
            max_iterations: Maximum planning iterations
            include_alternatives: Generate alternative plans
            focus_areas: Specific areas to focus on
            team_context: Team context (injected by server)
            provider: AI provider instance (injected by server)

        Returns:
            Strategic plan with steps, timeline, and recommendations
        """
        log = logger.bind(
            tool="strategic_planner",
            objective_length=len(objective),
            max_iterations=max_iterations
        )

        start_time = datetime.now(timezone.utc)

        try:
            log.info("Strategic planning started")

            # Track planning state
            plan_steps: List[PlanStep] = []
            iterations: List[PlanningIteration] = []
            total_tokens = 0

            # Iteration 1: Initial plan creation
            log.info("Iteration 1: Creating initial plan")

            initial_prompt = self._build_initial_prompt(objective, context, focus_areas)

            if provider:
                response = await self._call_provider(provider, initial_prompt, team_context)
                total_tokens += response.get("total_tokens", 0)

                # Parse plan steps from response
                plan_steps = self._parse_plan_steps(response.get("content", ""))

                iteration1 = PlanningIteration(
                    iteration_number=1,
                    focus="Initial plan creation and decomposition",
                    changes_made=["Created initial plan structure"],
                    rationale="Establishing baseline plan from objective analysis"
                )
                iterations.append(iteration1)

            # Subsequent iterations: Refinement
            for iteration_num in range(2, max_iterations + 1):
                log.info(f"Iteration {iteration_num}: Refining plan")

                refinement_prompt = self._build_refinement_prompt(
                    objective,
                    context,
                    plan_steps,
                    iterations,
                    focus_areas,
                    iteration_num
                )

                if provider:
                    response = await self._call_provider(provider, refinement_prompt, team_context)
                    total_tokens += response.get("total_tokens", 0)

                    # Update plan based on refinement
                    changes = self._extract_changes(response.get("content", ""))
                    plan_steps = self._apply_refinements(plan_steps, response.get("content", ""))

                    iteration = PlanningIteration(
                        iteration_number=iteration_num,
                        focus=f"Refinement iteration {iteration_num}",
                        changes_made=changes,
                        rationale=self._extract_rationale(response.get("content", ""))
                    )
                    iterations.append(iteration)

            # Generate alternative plans if requested
            alternative_plans = None
            if include_alternatives and provider:
                log.info("Generating alternative plans")
                alternative_plans = await self._generate_alternatives(
                    objective,
                    context,
                    plan_steps,
                    provider,
                    team_context
                )

            # Analyze plan
            timeline_overview = self._generate_timeline_overview(plan_steps)
            budget_overview = self._generate_budget_overview(plan_steps)
            critical_path = self._identify_critical_path(plan_steps)
            key_risks = self._consolidate_risks(plan_steps)
            recommendations = self._generate_recommendations(plan_steps, objective)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            log.info(
                "Strategic planning completed",
                iterations=len(iterations),
                steps=len(plan_steps),
                duration_seconds=duration
            )

            return {
                "summary": self._generate_summary(objective, plan_steps, iterations),
                "objective": objective,
                "status": PlanStatus.FINALIZED,
                "plan_steps": plan_steps,
                "iterations": iterations,
                "timeline_overview": timeline_overview,
                "budget_overview": budget_overview,
                "critical_path": critical_path,
                "key_risks": key_risks,
                "recommendations": recommendations,
                "alternative_plans": alternative_plans,
                "metadata": {
                    "iterations_performed": len(iterations),
                    "total_steps": len(plan_steps),
                    "total_tokens": total_tokens,
                    "duration_seconds": duration,
                    "has_alternatives": alternative_plans is not None
                }
            }

        except Exception as e:
            log.error("Strategic planning failed", error=str(e), exc_info=True)
            raise

    def _build_initial_prompt(
        self,
        objective: str,
        context: Optional[str],
        focus_areas: Optional[List[str]]
    ) -> str:
        """Build initial planning prompt."""
        prompt = f"""You are a senior strategic consultant creating a comprehensive plan.

OBJECTIVE:
{objective}
"""

        if context:
            prompt += f"""
CONTEXT & CONSTRAINTS:
{context}
"""

        if focus_areas:
            prompt += f"""
FOCUS AREAS:
{', '.join(focus_areas)}
"""

        prompt += """

Create a detailed strategic plan with the following structure for EACH step:

Step [NUMBER]: [TITLE]
Description: [What needs to be done]
Dependencies: [Which steps must be completed first]
Duration: [Estimated time]
Cost: [Estimated cost]
Resources: [People, tools, infrastructure needed]
Risks: [Potential issues]
Success Criteria: [How to measure success]

Provide 5-10 concrete, actionable steps that will achieve the objective.
Be specific about timelines, costs, and dependencies."""

        return prompt

    def _build_refinement_prompt(
        self,
        objective: str,
        context: Optional[str],
        current_steps: List[PlanStep],
        iterations: List[PlanningIteration],
        focus_areas: Optional[List[str]],
        iteration_num: int
    ) -> str:
        """Build refinement prompt for iteration."""
        prompt = f"""Refining strategic plan (Iteration {iteration_num}):

OBJECTIVE:
{objective}

CURRENT PLAN ({len(current_steps)} steps):
"""

        for step in current_steps[:5]:  # Show first 5 steps
            prompt += f"\nStep {step.step_number}: {step.title}"
            prompt += f"\n  Duration: {step.estimated_duration or 'TBD'}"
            prompt += f"\n  Cost: {step.estimated_cost or 'TBD'}"
            if step.risks:
                prompt += f"\n  Risks: {len(step.risks)} identified"

        prompt += f"""

PREVIOUS ITERATIONS:
"""
        for iter in iterations[-2:]:  # Last 2 iterations
            prompt += f"\nIteration {iter.iteration_number}: {iter.focus}"
            prompt += f"\n  Changes: {', '.join(iter.changes_made[:3])}"

        prompt += f"""

Your task for iteration {iteration_num}:
1. Review the current plan critically
2. Identify gaps, overlaps, or unrealistic estimates
3. Refine timelines and costs based on dependencies
4. Add missing steps or consolidate redundant ones
5. Enhance risk mitigation strategies
6. Improve success criteria clarity

Provide your refinements in the same format as the original plan."""

        return prompt

    async def _call_provider(
        self,
        provider: BaseAIProvider,
        prompt: str,
        team_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Call AI provider with prompt."""
        messages = [Message(role=Role.USER, content=prompt)]

        model = team_context.get("model", "unknown") if team_context else "unknown"

        response = await provider.chat(
            messages=messages,
            model=model,
            temperature=0.4,  # Balanced for creative planning
            max_tokens=3000
        )

        return {
            "content": response.content,
            "total_tokens": response.total_tokens
        }

    def _parse_plan_steps(self, content: str) -> List[PlanStep]:
        """Parse plan steps from AI response - flexible parsing."""
        import re
        steps = []
        lines = content.split('\n')

        current_step = None
        current_description_lines = []

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Flexible step header detection
            # Matches: "Step 1:", "### Step 1:", "**Step 1:**", "1.", "1)", etc.
            step_match = re.match(r'^[#*\s]*(?:Step\s+)?(\d+)[.:\)]\s*(.+?)(?:\*\*)?$', line_stripped, re.IGNORECASE)

            if step_match:
                # Save previous step
                if current_step:
                    if current_description_lines:
                        current_step.description = ' '.join(current_description_lines).strip()
                    steps.append(current_step)

                step_num = int(step_match.group(1))
                title = step_match.group(2).strip().strip('*').strip(':').strip()

                current_step = PlanStep(
                    step_number=step_num,
                    title=title,
                    description="",
                    dependencies=[],
                    resources_required=[],
                    risks=[],
                    success_criteria=[]
                )
                current_description_lines = []

            elif current_step and line_stripped:
                # Parse metadata fields
                if ':' in line_stripped:
                    key_lower = line_stripped.split(':', 1)[0].lower().strip('*-#').strip()
                    value = line_stripped.split(':', 1)[1].strip()

                    if 'duration' in key_lower or 'timeline' in key_lower:
                        current_step.estimated_duration = value
                    elif 'cost' in key_lower or 'budget' in key_lower:
                        current_step.estimated_cost = value
                    elif 'resource' in key_lower:
                        current_step.resources_required = [r.strip() for r in value.split(',') if r.strip()]
                    elif 'risk' in key_lower:
                        current_step.risks = [r.strip() for r in value.split(';') if r.strip()]
                    elif 'depend' in key_lower:
                        deps = re.findall(r'\d+', value)
                        current_step.dependencies = [int(d) for d in deps]
                    elif 'success' in key_lower or 'criteria' in key_lower:
                        current_step.success_criteria = [value.strip()]
                    elif 'description' in key_lower:
                        current_step.description = value
                    else:
                        # Accumulate as description
                        current_description_lines.append(value)
                else:
                    # Regular text - add to description
                    if len(line_stripped) > 10:  # Ignore very short lines
                        current_description_lines.append(line_stripped)

        # Save last step
        if current_step:
            if current_description_lines:
                current_step.description = ' '.join(current_description_lines).strip()
            steps.append(current_step)

        return steps

    def _extract_changes(self, content: str) -> List[str]:
        """Extract changes made in refinement."""
        changes = []
        lines = content.split('\n')

        for line in lines:
            if any(keyword in line.lower() for keyword in ['added', 'removed', 'updated', 'refined', 'changed']):
                changes.append(line.strip())

        return changes[:5]  # Top 5 changes

    def _extract_rationale(self, content: str) -> str:
        """Extract rationale for changes."""
        lines = content.split('\n')

        for line in lines:
            if 'rationale' in line.lower() or 'because' in line.lower():
                return line.strip()

        return "Plan refinement based on analysis"

    def _apply_refinements(self, current_steps: List[PlanStep], content: str) -> List[PlanStep]:
        """Apply refinements to current plan."""
        # For now, parse new steps from refinement
        # In a more sophisticated version, this would merge/update existing steps
        refined_steps = self._parse_plan_steps(content)

        if refined_steps:
            return refined_steps

        return current_steps

    async def _generate_alternatives(
        self,
        objective: str,
        context: Optional[str],
        base_plan: List[PlanStep],
        provider: BaseAIProvider,
        team_context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate alternative plan options."""
        prompt = f"""Generate 2 alternative approaches to achieve this objective:

OBJECTIVE:
{objective}

BASELINE PLAN:
{len(base_plan)} steps, estimated duration: {self._calculate_total_duration(base_plan)}

Create 2 alternative plans:
1. FAST TRACK: Optimized for speed (higher risk, potentially higher cost)
2. CONSERVATIVE: Lower risk, potentially longer timeline

For each alternative, provide brief summary and key trade-offs."""

        response = await self._call_provider(provider, prompt, team_context)

        # Parse alternatives (simplified)
        return [
            {
                "name": "Fast Track",
                "description": "Speed-optimized approach",
                "trade_offs": "Higher risk, potentially higher cost"
            },
            {
                "name": "Conservative",
                "description": "Risk-minimized approach",
                "trade_offs": "Longer timeline, more resources"
            }
        ]

    def _calculate_total_duration(self, steps: List[PlanStep]) -> str:
        """Calculate total estimated duration."""
        # Simplified - just return first step's duration or estimate
        if steps and steps[0].estimated_duration:
            return f"{len(steps)} x {steps[0].estimated_duration}"

        return f"{len(steps)} steps"

    def _generate_timeline_overview(self, steps: List[PlanStep]) -> str:
        """Generate timeline overview."""
        total_steps = len(steps)
        steps_with_duration = len([s for s in steps if s.estimated_duration])

        return f"Plan consists of {total_steps} steps. {steps_with_duration} steps have duration estimates."

    def _generate_budget_overview(self, steps: List[PlanStep]) -> str:
        """Generate budget overview."""
        steps_with_cost = len([s for s in steps if s.estimated_cost])

        return f"{steps_with_cost}/{len(steps)} steps have cost estimates."

    def _identify_critical_path(self, steps: List[PlanStep]) -> List[int]:
        """Identify critical path through plan."""
        # Simplified - return steps with dependencies
        critical = []
        for step in steps:
            if step.dependencies or step.risks:
                critical.append(step.step_number)

        return critical[:5]  # Top 5

    def _consolidate_risks(self, steps: List[PlanStep]) -> List[str]:
        """Consolidate all risks from steps."""
        all_risks = []
        for step in steps:
            all_risks.extend(step.risks)

        # Deduplicate and return top risks
        unique_risks = list(set(all_risks))
        return unique_risks[:10]

    def _generate_recommendations(self, steps: List[PlanStep], objective: str) -> List[str]:
        """Generate strategic recommendations."""
        recommendations = []

        # Check for common issues
        if len(steps) > 10:
            recommendations.append("Consider consolidating steps to reduce complexity")

        steps_without_duration = [s for s in steps if not s.estimated_duration]
        if len(steps_without_duration) > len(steps) / 2:
            recommendations.append("Add duration estimates to improve timeline planning")

        if not any(step.risks for step in steps):
            recommendations.append("Conduct thorough risk assessment for each step")

        return recommendations

    def _generate_summary(
        self,
        objective: str,
        steps: List[PlanStep],
        iterations: List[PlanningIteration]
    ) -> str:
        """Generate executive summary."""
        return (
            f"Strategic plan for: {objective}\n"
            f"Developed through {len(iterations)} iterations.\n"
            f"Plan consists of {len(steps)} actionable steps."
        )
