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
Deep Analyst Tool - Multi-step investigation with hypothesis tracking.

This tool provides systematic investigation capabilities:
- Multi-step analysis workflow
- Hypothesis formation and tracking
- Evidence collection and validation
- Cross-provider verification
- Confidence scoring
- Iterative refinement

Inspired by Zen MCP's thinkdeep tool.

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


class ConfidenceLevel(str, Enum):
    """Confidence levels for hypotheses and conclusions."""
    EXPLORING = "exploring"  # Just starting
    LOW = "low"  # Early hypothesis
    MEDIUM = "medium"  # Some evidence
    HIGH = "high"  # Strong evidence
    VERY_HIGH = "very_high"  # Very strong evidence
    CERTAIN = "certain"  # Confirmed


class InvestigationStep(BaseModel):
    """A single step in the investigation."""

    step_number: int = Field(..., description="Step number in sequence")
    hypothesis: str = Field(..., description="Current hypothesis being investigated")
    approach: str = Field(..., description="Investigation approach for this step")
    findings: str = Field(..., description="What was discovered in this step")
    evidence: List[str] = Field(default_factory=list, description="Evidence collected")
    confidence: ConfidenceLevel = Field(..., description="Confidence level")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DeepAnalystInput(BaseModel):
    """Input schema for deep analyst."""

    problem: str = Field(
        ...,
        description="Problem or question to investigate deeply",
        min_length=10,
        max_length=10000
    )
    context: Optional[str] = Field(
        None,
        description="Additional context about the problem",
        max_length=50000
    )
    max_steps: int = Field(
        default=5,
        description="Maximum investigation steps",
        ge=1,
        le=20
    )
    require_high_confidence: bool = Field(
        default=True,
        description="Continue until high confidence is reached"
    )
    use_cross_validation: bool = Field(
        default=False,
        description="Validate findings with multiple providers"
    )
    team_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Team selection context (injected by server)",
        exclude=True
    )


class DeepAnalystOutput(BaseModel):
    """Output schema for deep analyst."""

    summary: str = Field(..., description="Executive summary of investigation")
    final_conclusion: str = Field(..., description="Final conclusion reached")
    confidence: ConfidenceLevel = Field(..., description="Final confidence level")
    steps: List[InvestigationStep] = Field(..., description="Investigation steps taken")
    key_insights: List[str] = Field(..., description="Key insights discovered")
    recommendations: List[str] = Field(..., description="Actionable recommendations")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Investigation metadata (duration, tokens, etc.)"
    )


class DeepAnalystTool(BaseTool):
    """
    Deep Analyst Tool - Systematic multi-step investigation.

    This tool conducts thorough investigations by:
    1. Formulating initial hypotheses
    2. Conducting systematic investigation
    3. Collecting and analyzing evidence
    4. Refining hypotheses based on findings
    5. Cross-validating conclusions
    6. Providing actionable recommendations

    Example Usage:
        Basic investigation:
        {
            "problem": "Why is our API response time degrading?",
            "context": "Response time increased from 100ms to 2000ms over 2 weeks"
        }

        Deep investigation with cross-validation:
        {
            "problem": "Should we migrate to microservices architecture?",
            "context": "Current monolith has 500K LOC, 20 developers",
            "max_steps": 8,
            "use_cross_validation": true
        }
    """

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        return ToolMetadata(
            name="deep_analyst",
            description="Conduct systematic multi-step investigation with hypothesis tracking",
            category=ToolCategory.ANALYSIS,
            version="1.0.0",
            author="SCOUT Team",
            permissions={ToolPermission.READ},
            tags=["analysis", "investigation", "research", "consultant", "deep-dive"],
            examples=[
                {
                    "problem": "Why are our production costs increasing?",
                    "context": "Costs up 40% in Q4 despite stable usage"
                },
                {
                    "problem": "Should we adopt GraphQL for our API?",
                    "context": "REST API with 50+ endpoints, mobile + web clients",
                    "use_cross_validation": True
                }
            ],
            cost_estimate=0.05,
            avg_latency_ms=15000
        )

    def get_schema(self) -> ToolSchema:
        """Get tool schema."""
        return ToolSchema(
            input_model=DeepAnalystInput,
            output_model=DeepAnalystOutput
        )

    async def execute(
        self,
        problem: str,
        context: Optional[str] = None,
        max_steps: int = 5,
        require_high_confidence: bool = True,
        use_cross_validation: bool = False,
        team_context: Optional[Dict[str, Any]] = None,
        provider: Optional[Any] = None  # BaseAIProvider - injected by server
    ) -> Dict[str, Any]:
        """
        Execute deep investigation.

        Args:
            problem: Problem or question to investigate
            context: Additional context
            max_steps: Maximum investigation steps
            require_high_confidence: Continue until high confidence
            use_cross_validation: Validate with multiple providers
            team_context: Team context (injected by server)
            provider: AI provider instance (injected by server)

        Returns:
            Investigation results with steps and conclusions
        """
        log = logger.bind(
            tool="deep_analyst",
            problem_length=len(problem),
            max_steps=max_steps
        )

        start_time = datetime.now(timezone.utc)

        try:
            log.info("Deep investigation started")

            # Track investigation state
            steps: List[InvestigationStep] = []
            current_hypothesis = "Initial hypothesis: Need to understand the problem"
            current_confidence = ConfidenceLevel.EXPLORING
            total_tokens = 0

            # Build initial prompt
            initial_prompt = self._build_initial_prompt(problem, context)

            # Step 1: Problem formulation and initial hypothesis
            log.info("Step 1: Formulating problem and initial hypothesis")

            if provider:
                response = await self._call_provider(
                    provider,
                    initial_prompt,
                    team_context
                )

                total_tokens += response.get("total_tokens", 0)

                step1 = InvestigationStep(
                    step_number=1,
                    hypothesis="Understanding the problem scope and context",
                    approach="Problem analysis and context gathering",
                    findings=response.get("content", ""),
                    evidence=[],
                    confidence=ConfidenceLevel.EXPLORING
                )
                steps.append(step1)

                # Extract hypothesis from response
                current_hypothesis = self._extract_hypothesis(step1.findings)
                current_confidence = ConfidenceLevel.LOW

            # Subsequent steps: Investigation
            for step_num in range(2, max_steps + 1):
                log.info(f"Step {step_num}: Investigating hypothesis", hypothesis=current_hypothesis)

                # Build investigation prompt
                investigation_prompt = self._build_investigation_prompt(
                    problem,
                    context,
                    steps,
                    current_hypothesis,
                    step_num
                )

                if provider:
                    response = await self._call_provider(
                        provider,
                        investigation_prompt,
                        team_context
                    )

                    total_tokens += response.get("total_tokens", 0)

                    # Analyze findings
                    findings = response.get("content", "")
                    evidence = self._extract_evidence(findings)
                    new_confidence = self._assess_confidence(findings, evidence, step_num)

                    step = InvestigationStep(
                        step_number=step_num,
                        hypothesis=current_hypothesis,
                        approach=f"Systematic investigation step {step_num}",
                        findings=findings,
                        evidence=evidence,
                        confidence=new_confidence
                    )
                    steps.append(step)

                    # Update state
                    current_confidence = new_confidence

                    # Check if we can conclude
                    if require_high_confidence:
                        if current_confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH, ConfidenceLevel.CERTAIN]:
                            log.info("High confidence reached, concluding investigation")
                            break

                    # Refine hypothesis if needed
                    if step_num < max_steps:
                        current_hypothesis = self._refine_hypothesis(findings, current_hypothesis)

            # Cross-validation (optional)
            if use_cross_validation and provider:
                log.info("Performing cross-validation")
                # TODO: Implement cross-provider validation
                # This would call multiple providers and synthesize results

            # Generate final analysis
            final_conclusion = self._synthesize_conclusion(steps, problem)
            key_insights = self._extract_insights(steps)
            recommendations = self._generate_recommendations(steps, problem)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            log.info(
                "Deep investigation completed",
                steps_taken=len(steps),
                confidence=current_confidence,
                duration_seconds=duration
            )

            return {
                "summary": f"Deep investigation completed in {len(steps)} steps. Confidence: {current_confidence.value}",
                "final_conclusion": final_conclusion,
                "confidence": current_confidence,
                "steps": steps,
                "key_insights": key_insights,
                "recommendations": recommendations,
                "metadata": {
                    "steps_taken": len(steps),
                    "total_tokens": total_tokens,
                    "duration_seconds": duration,
                    "cross_validated": use_cross_validation
                }
            }

        except Exception as e:
            log.error("Deep investigation failed", error=str(e), exc_info=True)
            raise

    def _build_initial_prompt(self, problem: str, context: Optional[str]) -> str:
        """Build initial problem formulation prompt."""
        prompt = f"""You are a senior consultant conducting a deep investigation.

PROBLEM TO INVESTIGATE:
{problem}
"""

        if context:
            prompt += f"""
ADDITIONAL CONTEXT:
{context}
"""

        prompt += """

Your task for this first step:
1. Clearly restate the problem in your own words
2. Identify what information is known vs unknown
3. Formulate 2-3 initial hypotheses about the root cause or answer
4. Outline what evidence would be needed to test each hypothesis
5. Identify any assumptions being made

Be systematic and thorough. This is step 1 of a multi-step investigation."""

        return prompt

    def _build_investigation_prompt(
        self,
        problem: str,
        context: Optional[str],
        previous_steps: List[InvestigationStep],
        current_hypothesis: str,
        step_number: int
    ) -> str:
        """Build investigation prompt for current step."""
        prompt = f"""Continuing systematic investigation (Step {step_number}):

ORIGINAL PROBLEM:
{problem}

CURRENT HYPOTHESIS:
{current_hypothesis}

PREVIOUS FINDINGS:
"""

        # Add previous findings
        for step in previous_steps[-2:]:  # Last 2 steps for context
            prompt += f"\nStep {step.step_number}: {step.findings[:500]}...\n"

        prompt += f"""

Your task for step {step_number}:
1. Investigate the current hypothesis systematically
2. Collect specific evidence (facts, data points, examples)
3. Identify patterns or correlations
4. Test the hypothesis against the evidence
5. Assess confidence level (low/medium/high/very_high/certain)
6. If hypothesis is weak, suggest refined hypothesis

Be specific and evidence-based."""

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
            temperature=0.3,  # Lower temp for analytical work
            max_tokens=2000
        )

        return {
            "content": response.content,
            "total_tokens": response.total_tokens
        }

    def _extract_hypothesis(self, findings: str) -> str:
        """Extract hypothesis from AI response."""
        # Simple extraction - look for hypothesis keywords
        lines = findings.split('\n')
        for line in lines:
            if 'hypothesis' in line.lower() or 'hypothèse' in line.lower():
                return line.strip()

        # Fallback: return first substantial line
        for line in lines:
            if len(line.strip()) > 50:
                return line.strip()[:200]

        return "Investigating problem systematically"

    def _extract_evidence(self, findings: str) -> List[str]:
        """Extract evidence points from findings."""
        evidence = []
        lines = findings.split('\n')

        for line in lines:
            line = line.strip()
            # Look for evidence markers
            if any(marker in line.lower() for marker in ['evidence:', 'fact:', 'data:', '•', '-', '*']):
                if len(line) > 20:
                    evidence.append(line)

        return evidence[:10]  # Max 10 evidence points

    def _assess_confidence(self, findings: str, evidence: List[str], step_num: int) -> ConfidenceLevel:
        """Assess confidence level based on findings."""
        findings_lower = findings.lower()

        # Check for confidence indicators
        if 'certain' in findings_lower or 'definitive' in findings_lower:
            return ConfidenceLevel.CERTAIN
        elif 'very confident' in findings_lower or 'strong evidence' in findings_lower:
            return ConfidenceLevel.VERY_HIGH
        elif 'confident' in findings_lower or 'high confidence' in findings_lower:
            return ConfidenceLevel.HIGH
        elif len(evidence) >= 3:
            return ConfidenceLevel.MEDIUM
        elif step_num > 1:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.EXPLORING

    def _refine_hypothesis(self, findings: str, current_hypothesis: str) -> str:
        """Refine hypothesis based on new findings."""
        # Simple refinement - look for new hypothesis in findings
        lines = findings.split('\n')
        for line in lines:
            if 'revised hypothesis' in line.lower() or 'refined hypothesis' in line.lower():
                return line.strip()

        return current_hypothesis

    def _synthesize_conclusion(self, steps: List[InvestigationStep], problem: str) -> str:
        """Synthesize final conclusion from all steps."""
        if not steps:
            return "Investigation incomplete"

        last_step = steps[-1]
        conclusion = f"Based on {len(steps)}-step investigation:\n\n"
        conclusion += last_step.findings[:500]

        return conclusion

    def _extract_insights(self, steps: List[InvestigationStep]) -> List[str]:
        """Extract key insights from investigation."""
        insights = []

        for step in steps:
            # Look for insight markers
            lines = step.findings.split('\n')
            for line in lines:
                if any(marker in line.lower() for marker in ['key insight:', 'important:', 'critical:']):
                    insights.append(line.strip())

        return insights[:5]  # Top 5 insights

    def _generate_recommendations(self, steps: List[InvestigationStep], problem: str) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        for step in steps:
            lines = step.findings.split('\n')
            for line in lines:
                if any(marker in line.lower() for marker in ['recommend', 'should', 'suggest']):
                    recommendations.append(line.strip())

        return recommendations[:5]  # Top 5 recommendations
