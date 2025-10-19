"""
Consensus Builder Tool for SCOUT MCP Server.

Inspired by Zen MCP's consensus tool - queries multiple AI providers simultaneously
to synthesize consensus, identify agreements and disagreements, and provide
confidence-weighted recommendations.

This is a consultant-focused tool for decision-making and analysis requiring
multiple perspectives.
"""

import asyncio
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

import structlog
from pydantic import BaseModel, Field

from scout.providers.base import Message, Role
from scout.core.tool_registry import BaseTool, ToolCategory

# Module-level logger
logger = structlog.get_logger(__name__)


class ConfidenceLevel(str, Enum):
    """Confidence level for provider responses."""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class ProviderResponse(BaseModel):
    """Response from a single provider."""
    provider_name: str
    response_content: str
    confidence: ConfidenceLevel
    reasoning: str = ""
    timestamp: str
    tokens_used: int = 0


class Agreement(BaseModel):
    """Point of agreement across providers."""
    statement: str
    supporting_providers: List[str]
    confidence: ConfidenceLevel
    evidence: List[str] = Field(default_factory=list)


class Disagreement(BaseModel):
    """Point of disagreement across providers."""
    topic: str
    positions: Dict[str, str]  # provider_name -> position
    significance: str  # "minor", "moderate", "major"
    resolution_suggestion: Optional[str] = None


class ConsensusResult(BaseModel):
    """Final consensus synthesis."""
    consensus_statement: str
    confidence_level: ConfidenceLevel
    agreements: List[Agreement]
    disagreements: List[Disagreement]
    recommendations: List[str]
    diversity_score: float  # 0-1, measures diversity of opinions
    providers_consulted: List[str]
    total_tokens_used: int
    duration_seconds: float


class ConsensusBuilderTool(BaseTool):
    """
    Multi-provider consensus building tool.

    Queries multiple AI providers simultaneously to gather diverse perspectives,
    then synthesizes a consensus while identifying agreements and disagreements.

    Inspired by Zen MCP's consensus tool for consultant decision-making.
    """

    def get_metadata(self) -> 'ToolMetadata':
        """Get tool metadata."""
        from scout.core.tool_registry import ToolMetadata, ToolPermission
        return ToolMetadata(
            name="consensus_builder",
            description="Build consensus across multiple AI providers for robust decision-making",
            category=ToolCategory.ANALYSIS,
            version="1.0.0",
            author="SCOUT Team",
            permissions={ToolPermission.READ},
            tags=["consensus", "multi-provider", "synthesis", "consultant", "decision-making"],
            examples=[
                {
                    "question": "Should we migrate to microservices architecture?",
                    "context": "100K LOC monolith, 20 developers, growing quickly"
                }
            ]
        )

    def get_schema(self) -> 'ToolSchema':
        """Get tool schema."""
        from scout.core.tool_registry import ToolSchema
        from pydantic import BaseModel, Field
        from typing import List, Optional

        class ConsensusBuilderInput(BaseModel):
            question: str = Field(..., description="Question or decision to get consensus on")
            context: Optional[str] = Field(None, description="Additional context for the question")
            providers_to_query: Optional[List[str]] = Field(None, description="List of provider names to query")
            require_unanimity: bool = Field(False, description="Require all providers to agree")
            tie_breaking: bool = Field(True, description="Use additional provider for tie-breaking")
            min_confidence: str = Field("medium", description="Minimum confidence level")

        class ConsensusBuilderOutput(BaseModel):
            consensus_statement: str
            confidence_level: str
            providers_consulted: List[str]
            agreements: List[dict]
            disagreements: List[dict]
            recommendations: List[str]
            diversity_score: float
            total_tokens_used: int

        return ToolSchema(
            input_model=ConsensusBuilderInput,
            output_model=ConsensusBuilderOutput
        )

    async def execute(
        self,
        question: str,
        context: Optional[str] = None,
        providers_to_query: Optional[List[str]] = None,
        require_unanimity: bool = False,
        tie_breaking: bool = True,
        min_confidence: str = "medium",
        # Runtime dependencies (injected by server, not in tool schema)
        provider: Optional[Any] = None,  # BaseAIProvider
        state_manager: Optional[Any] = None,
        available_providers: Optional[Dict[str, Any]] = None,  # Dict[str, BaseAIProvider]
        team_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build consensus across multiple AI providers.

        Args:
            question: Question or decision to get consensus on
            context: Additional context for the question
            providers_to_query: List of provider names to query (default: all available)
            require_unanimity: If True, require all providers to agree
            tie_breaking: If True, use additional provider for tie-breaking when needed
            min_confidence: Minimum confidence level required ("low", "medium", "high")
            provider: AI provider (injected by server)
            state_manager: State manager (injected by server)
            available_providers: All available providers (injected by server)
            team_context: Team context (injected by server)

        Returns:
            Dict containing consensus results with agreements, disagreements, and recommendations
        """
        start_time = datetime.now(timezone.utc)

        logger.info(
            "Consensus building started",
            question_length=len(question),
            providers_requested=len(providers_to_query) if providers_to_query else "all",
            tool="consensus_builder"
        )

        # Get available providers
        if not available_providers:
            raise ValueError("No AI providers available for consensus building")

        # Select providers to query
        selected_providers = self._select_providers(
            available_providers,
            providers_to_query
        )

        if len(selected_providers) < 2:
            raise ValueError("Consensus requires at least 2 providers")

        logger.info(
            f"Querying {len(selected_providers)} providers",
            providers=list(selected_providers.keys()),
            tool="consensus_builder"
        )

        # Step 1: Query all providers in parallel
        provider_responses = await self._query_providers_parallel(
            selected_providers,
            question,
            context,
            team_context
        )

        if len(provider_responses) < 2:
            raise ValueError(f"Insufficient responses: got {len(provider_responses)}, need at least 2")

        # Step 2: Analyze responses for patterns
        agreements, disagreements = self._analyze_responses(provider_responses)

        # Step 3: Check if tie-breaking needed
        if tie_breaking and self._needs_tie_breaking(disagreements, provider_responses):
            logger.info("Tie detected, initiating tie-breaking", tool="consensus_builder")
            tie_breaker_response = await self._perform_tie_breaking(
                selected_providers,
                provider_responses,
                question,
                context,
                disagreements,
                team_context
            )
            if tie_breaker_response:
                provider_responses.append(tie_breaker_response)
                # Re-analyze with tie-breaker
                agreements, disagreements = self._analyze_responses(provider_responses)

        # Step 4: Build consensus statement
        consensus_statement = self._build_consensus_statement(
            provider_responses,
            agreements,
            disagreements
        )

        # Step 5: Assess overall confidence
        consensus_confidence = self._assess_consensus_confidence(
            provider_responses,
            agreements,
            disagreements
        )

        # Step 6: Generate recommendations
        recommendations = self._generate_recommendations(
            consensus_statement,
            agreements,
            disagreements,
            provider_responses
        )

        # Step 7: Calculate diversity score
        diversity_score = self._calculate_diversity_score(provider_responses)

        # Step 8: Check unanimity requirement
        if require_unanimity and disagreements:
            logger.warning(
                "Unanimity required but disagreements found",
                disagreement_count=len(disagreements),
                tool="consensus_builder"
            )

        # Calculate stats
        total_tokens = sum(r.tokens_used for r in provider_responses)
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        result = ConsensusResult(
            consensus_statement=consensus_statement,
            confidence_level=consensus_confidence,
            agreements=agreements,
            disagreements=disagreements,
            recommendations=recommendations,
            diversity_score=diversity_score,
            providers_consulted=[r.provider_name for r in provider_responses],
            total_tokens_used=total_tokens,
            duration_seconds=duration
        )

        logger.info(
            "Consensus building completed",
            providers=len(provider_responses),
            agreements=len(agreements),
            disagreements=len(disagreements),
            confidence=consensus_confidence,
            diversity=f"{diversity_score:.2f}",
            duration_seconds=duration,
            tool="consensus_builder"
        )

        return result.model_dump()

    def _select_providers(
        self,
        available_providers: Dict[str, Any],
        requested_providers: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Select providers for consensus building."""
        if requested_providers:
            selected = {
                name: provider
                for name, provider in available_providers.items()
                if name in requested_providers
            }
            if not selected:
                raise ValueError(f"None of requested providers {requested_providers} are available")
            return selected

        # Use all available providers
        return available_providers

    async def _query_providers_parallel(
        self,
        providers: Dict[str, Any],
        question: str,
        context: Optional[str],
        team_context: Optional[Dict[str, Any]]
    ) -> List[ProviderResponse]:
        """Query multiple providers in parallel."""
        prompt = self._build_consensus_prompt(question, context)

        # Create tasks for parallel execution
        tasks = [
            self._query_single_provider(provider_name, provider, prompt, team_context)
            for provider_name, provider in providers.items()
        ]

        # Execute in parallel
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out failures
        valid_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                provider_name = list(providers.keys())[i]
                logger.error(
                    f"Provider {provider_name} failed",
                    error=str(response),
                    tool="consensus_builder"
                )
            else:
                valid_responses.append(response)

        return valid_responses

    def _build_consensus_prompt(self, question: str, context: Optional[str]) -> str:
        """Build prompt for consensus query."""
        prompt = f"""You are being consulted as part of a multi-provider consensus building process.

QUESTION:
{question}
"""

        if context:
            prompt += f"""
CONTEXT:
{context}
"""

        prompt += """

Your task:
1. Provide your best answer to the question
2. Explain your reasoning clearly
3. Indicate your confidence level (very_low, low, medium, high, very_high)
4. Identify any assumptions you're making

Format your response as:

ANSWER:
[Your answer here]

REASONING:
[Your reasoning here]

CONFIDENCE:
[Your confidence level]

ASSUMPTIONS:
[Any assumptions you're making]
"""

        return prompt

    async def _query_single_provider(
        self,
        provider_name: str,
        provider: Any,
        prompt: str,
        team_context: Optional[Dict[str, Any]]
    ) -> ProviderResponse:
        """Query a single provider."""
        messages = [Message(role=Role.USER, content=prompt)]

        # Use provider's default model (don't use team_context model which is specific to one provider)
        # Each provider will use its own default model
        logger.debug(
            f"Querying provider {provider_name}",
            tool="consensus_builder"
        )

        response = await provider.chat(
            messages=messages,
            model=None,  # Use provider's default model
            temperature=0.3,  # Lower temperature for consistency
            max_tokens=2000
        )

        # Extract confidence from response
        confidence = self._extract_confidence(response.content)

        return ProviderResponse(
            provider_name=provider_name,
            response_content=response.content,
            confidence=confidence,
            timestamp=datetime.now(timezone.utc).isoformat(),
            tokens_used=response.total_tokens or 0
        )

    def _extract_confidence(self, content: str) -> ConfidenceLevel:
        """Extract confidence level from response."""
        content_lower = content.lower()

        if "very_high" in content_lower or "very high" in content_lower:
            return ConfidenceLevel.VERY_HIGH
        elif "high" in content_lower:
            return ConfidenceLevel.HIGH
        elif "medium" in content_lower or "moderate" in content_lower:
            return ConfidenceLevel.MEDIUM
        elif "very_low" in content_lower or "very low" in content_lower:
            return ConfidenceLevel.VERY_LOW
        elif "low" in content_lower:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.MEDIUM  # Default

    def _analyze_responses(
        self,
        responses: List[ProviderResponse]
    ) -> Tuple[List[Agreement], List[Disagreement]]:
        """Analyze responses to identify agreements and disagreements."""
        agreements = []
        disagreements = []

        # Extract key statements from each response
        statements_by_provider = {}
        for response in responses:
            statements = self._extract_key_statements(response.response_content)
            statements_by_provider[response.provider_name] = statements

        # Find common statements (agreements)
        all_statements = [stmt for stmts in statements_by_provider.values() for stmt in stmts]

        # Simple agreement detection: statements mentioned by multiple providers
        from collections import Counter
        statement_counts = Counter(all_statements)

        for statement, count in statement_counts.items():
            if count >= len(responses) // 2 + 1:  # Majority agreement
                supporting = [
                    prov for prov, stmts in statements_by_provider.items()
                    if statement in stmts
                ]
                agreements.append(Agreement(
                    statement=statement,
                    supporting_providers=supporting,
                    confidence=ConfidenceLevel.HIGH if count == len(responses) else ConfidenceLevel.MEDIUM,
                    evidence=[f"Supported by {len(supporting)}/{len(responses)} providers"]
                ))

        # Find disagreements: different answers to the same aspect
        # For simplicity, compare response lengths and confidence variance
        confidences = [self._confidence_to_numeric(r.confidence) for r in responses]
        if max(confidences) - min(confidences) >= 2:  # Significant confidence variance
            positions = {r.provider_name: f"{r.confidence.value} confidence" for r in responses}
            disagreements.append(Disagreement(
                topic="confidence_level",
                positions=positions,
                significance="moderate",
                resolution_suggestion="Review evidence supporting different confidence levels"
            ))

        return agreements, disagreements

    def _extract_key_statements(self, content: str) -> List[str]:
        """Extract key statements from response content."""
        statements = []

        # Extract sentences that look like definitive statements
        sentences = re.split(r'[.!?]\s+', content)

        for sentence in sentences:
            # Look for strong assertions
            if any(word in sentence.lower() for word in ['should', 'will', 'must', 'recommend', 'suggest']):
                if len(sentence.split()) >= 5:  # Substantive statements
                    statements.append(sentence.strip())

        return statements[:5]  # Top 5 key statements

    def _confidence_to_numeric(self, confidence: ConfidenceLevel) -> int:
        """Convert confidence level to numeric value."""
        mapping = {
            ConfidenceLevel.VERY_LOW: 1,
            ConfidenceLevel.LOW: 2,
            ConfidenceLevel.MEDIUM: 3,
            ConfidenceLevel.HIGH: 4,
            ConfidenceLevel.VERY_HIGH: 5
        }
        return mapping.get(confidence, 3)

    def _needs_tie_breaking(
        self,
        disagreements: List[Disagreement],
        responses: List[ProviderResponse]
    ) -> bool:
        """Check if tie-breaking is needed."""
        # Tie-breaking needed if:
        # 1. Exactly 2 providers with conflicting high-confidence responses
        # 2. Even number of providers with split opinion

        if len(responses) == 2:
            conf1, conf2 = self._confidence_to_numeric(responses[0].confidence), self._confidence_to_numeric(responses[1].confidence)
            if abs(conf1 - conf2) == 0 and conf1 >= 3:  # Both medium+ confidence
                return True

        if len(responses) % 2 == 0 and len(disagreements) > 0:
            # Even split possible
            return True

        return False

    async def _perform_tie_breaking(
        self,
        all_providers: Dict[str, Any],
        current_responses: List[ProviderResponse],
        question: str,
        context: Optional[str],
        disagreements: List[Disagreement],
        team_context: Optional[Dict[str, Any]]
    ) -> Optional[ProviderResponse]:
        """Perform tie-breaking with an additional provider."""
        # Find a provider not yet used
        used_providers = {r.provider_name for r in current_responses}
        available_tie_breakers = {
            name: provider
            for name, provider in all_providers.items()
            if name not in used_providers
        }

        if not available_tie_breakers:
            logger.warning("No additional provider available for tie-breaking", tool="consensus_builder")
            return None

        # Use the first available tie-breaker
        tie_breaker_name, tie_breaker = next(iter(available_tie_breakers.items()))

        # Build enhanced prompt with disagreement context
        prompt = self._build_tie_breaking_prompt(question, context, disagreements)

        return await self._query_single_provider(
            tie_breaker_name,
            tie_breaker,
            prompt,
            team_context
        )

    def _build_tie_breaking_prompt(
        self,
        question: str,
        context: Optional[str],
        disagreements: List[Disagreement]
    ) -> str:
        """Build tie-breaking prompt."""
        prompt = f"""You are being consulted as a TIE-BREAKER in a multi-provider consensus process.

ORIGINAL QUESTION:
{question}
"""

        if context:
            prompt += f"""
CONTEXT:
{context}
"""

        prompt += f"""
CURRENT DISAGREEMENTS:
"""
        for dis in disagreements:
            prompt += f"\n- {dis.topic}: {len(dis.positions)} different positions"

        prompt += """

Your task as tie-breaker:
1. Provide your independent answer to the question
2. Explain which aspects have strongest evidence
3. Indicate your confidence level
4. Suggest how to resolve the disagreements

Format your response as before (ANSWER, REASONING, CONFIDENCE, ASSUMPTIONS).
"""

        return prompt

    def _build_consensus_statement(
        self,
        responses: List[ProviderResponse],
        agreements: List[Agreement],
        disagreements: List[Disagreement]
    ) -> str:
        """Build final consensus statement."""
        if not agreements and not disagreements:
            # Synthesize from responses directly
            return self._synthesize_from_responses(responses)

        statement = "CONSENSUS SYNTHESIS:\n\n"

        if agreements:
            statement += "Points of Agreement:\n"
            for i, agreement in enumerate(agreements[:3], 1):
                statement += f"{i}. {agreement.statement} "
                statement += f"(supported by {len(agreement.supporting_providers)} providers)\n"

        if disagreements:
            statement += "\nPoints of Disagreement:\n"
            for i, disagreement in enumerate(disagreements[:3], 1):
                statement += f"{i}. {disagreement.topic} - {disagreement.significance} significance\n"

        return statement

    def _synthesize_from_responses(self, responses: List[ProviderResponse]) -> str:
        """Synthesize consensus from raw responses."""
        # Extract first substantive sentence from each response
        synthesis = "Based on multi-provider consultation:\n\n"

        for response in responses:
            lines = response.response_content.split('\n')
            for line in lines:
                if len(line.split()) >= 10:  # Substantive line
                    synthesis += f"- {response.provider_name}: {line[:200]}...\n"
                    break

        return synthesis

    def _assess_consensus_confidence(
        self,
        responses: List[ProviderResponse],
        agreements: List[Agreement],
        disagreements: List[Disagreement]
    ) -> ConfidenceLevel:
        """Assess overall consensus confidence."""
        # Calculate average confidence from providers
        confidences = [self._confidence_to_numeric(r.confidence) for r in responses]
        avg_confidence = sum(confidences) / len(confidences)

        # Adjust based on agreements/disagreements
        if len(agreements) >= len(responses) and not disagreements:
            avg_confidence += 0.5  # Boost for strong agreement
        elif disagreements:
            avg_confidence -= 0.3 * len(disagreements)  # Penalty for disagreements

        # Convert back to ConfidenceLevel
        avg_confidence = max(1, min(5, round(avg_confidence)))

        mapping = {
            1: ConfidenceLevel.VERY_LOW,
            2: ConfidenceLevel.LOW,
            3: ConfidenceLevel.MEDIUM,
            4: ConfidenceLevel.HIGH,
            5: ConfidenceLevel.VERY_HIGH
        }

        return mapping[avg_confidence]

    def _generate_recommendations(
        self,
        consensus_statement: str,
        agreements: List[Agreement],
        disagreements: List[Disagreement],
        responses: List[ProviderResponse]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Recommendation based on agreement strength
        if len(agreements) >= len(responses):
            recommendations.append(
                f"Strong consensus achieved across {len(responses)} providers - "
                "proceed with high confidence"
            )
        else:
            recommendations.append(
                "Moderate consensus - consider additional validation before proceeding"
            )

        # Recommendations for disagreements
        for disagreement in disagreements[:2]:
            if disagreement.resolution_suggestion:
                recommendations.append(disagreement.resolution_suggestion)
            else:
                recommendations.append(
                    f"Investigate '{disagreement.topic}' further to resolve {disagreement.significance} disagreement"
                )

        # Confidence-based recommendations
        high_conf_providers = [r for r in responses if self._confidence_to_numeric(r.confidence) >= 4]
        if len(high_conf_providers) == len(responses):
            recommendations.append("All providers show high confidence - strong recommendation to proceed")
        elif not high_conf_providers:
            recommendations.append("Low confidence across providers - gather more information before deciding")

        return recommendations[:5]  # Top 5 recommendations

    def _calculate_diversity_score(self, responses: List[ProviderResponse]) -> float:
        """Calculate diversity score (0-1) based on response variance."""
        # Measure diversity based on:
        # 1. Confidence variance
        # 2. Response length variance
        # 3. Unique key statements

        confidences = [self._confidence_to_numeric(r.confidence) for r in responses]
        conf_variance = sum((c - sum(confidences)/len(confidences))**2 for c in confidences) / len(confidences)
        conf_diversity = min(1.0, conf_variance / 2.0)

        lengths = [len(r.response_content) for r in responses]
        length_variance = sum((l - sum(lengths)/len(lengths))**2 for l in lengths) / len(lengths)
        length_diversity = min(1.0, length_variance / 100000)

        # Average the diversity measures
        diversity = (conf_diversity + length_diversity) / 2.0

        return round(diversity, 2)


# Register the tool
def create_tool() -> BaseTool:
    """Factory function to create tool instance."""
    return ConsensusBuilderTool()
