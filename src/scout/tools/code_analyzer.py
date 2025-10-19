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
Code Analyzer Tool - Example MCP tool for code analysis.

This tool demonstrates:
- BaseTool implementation
- Pydantic schema validation
- AI provider integration via team context
- MCP tool registration
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from scout.core.tool_registry import (
    BaseTool,
    ToolMetadata,
    ToolSchema,
    ToolCategory,
    ToolPermission
)


class CodeAnalyzerInput(BaseModel):
    """Input schema for code analyzer."""

    code: str = Field(
        ...,
        description="Code to analyze",
        min_length=1
    )
    language: str = Field(
        default="python",
        description="Programming language",
        pattern="^(python|javascript|typescript|java|go|rust)$"
    )
    analysis_type: str = Field(
        default="general",
        description="Type of analysis to perform",
        pattern="^(general|security|performance|style|complexity)$"
    )
    _team_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Team selection context (injected by server)"
    )


class CodeAnalyzerOutput(BaseModel):
    """Output schema for code analyzer."""

    analysis: str = Field(..., description="Analysis results")
    language: str = Field(..., description="Detected/specified language")
    issues_found: int = Field(default=0, description="Number of issues found")
    suggestions: list[str] = Field(
        default_factory=list,
        description="List of improvement suggestions"
    )
    complexity_score: Optional[float] = Field(
        None,
        description="Code complexity score (0-10)",
        ge=0,
        le=10
    )
    team_used: Optional[str] = Field(
        None,
        description="Team that performed analysis"
    )


class CodeAnalyzerTool(BaseTool):
    """
    Code Analyzer MCP Tool.

    Analyzes code for various aspects including:
    - Code quality
    - Security issues
    - Performance concerns
    - Style violations
    - Complexity metrics

    Uses intelligent team selection to route analysis to appropriate AI model.
    """

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        return ToolMetadata(
            name="code_analyzer",
            description="Analyze code for quality, security, performance, and complexity",
            category=ToolCategory.ANALYSIS,
            version="1.0.0",
            author="SCOUT Team",
            permissions={ToolPermission.READ},
            tags=["code", "analysis", "quality", "security"],
            examples=[
                {
                    "code": "def hello(): print('world')",
                    "language": "python",
                    "analysis_type": "general"
                },
                {
                    "code": "function sum(a, b) { return a + b; }",
                    "language": "javascript",
                    "analysis_type": "style"
                }
            ],
            cost_estimate=0.01,
            avg_latency_ms=500
        )

    def get_schema(self) -> ToolSchema:
        """Get tool schema."""
        return ToolSchema(
            input_model=CodeAnalyzerInput,
            output_model=CodeAnalyzerOutput
        )

    async def execute(
        self,
        code: str,
        language: str = "python",
        analysis_type: str = "general",
        _team_context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute code analysis.

        Args:
            code: Code to analyze
            language: Programming language
            analysis_type: Type of analysis
            _team_context: Team selection context (injected)
            **kwargs: Additional parameters

        Returns:
            Analysis results
        """
        # Extract team information
        team_used = None
        if _team_context:
            team_used = _team_context.get("team")

        # Perform basic analysis (this is a simplified example)
        # In a real implementation, this would use the AI provider
        # specified in _team_context to perform deeper analysis

        lines = code.split('\n')
        suggestions = []

        # Basic heuristics
        if len(lines) > 50:
            suggestions.append("Consider breaking down into smaller functions")

        if analysis_type == "security":
            if "eval(" in code or "exec(" in code:
                suggestions.append("Security: Avoid using eval() or exec()")
            if "password" in code.lower() and "=" in code:
                suggestions.append("Security: Avoid hardcoding passwords")

        if analysis_type == "performance":
            if "for" in code and "for" in code:
                suggestions.append("Performance: Consider optimizing nested loops")

        if analysis_type == "style":
            if "\t" in code:
                suggestions.append("Style: Use spaces instead of tabs")

        # Calculate simple complexity score
        complexity = min(10.0, len(lines) / 10 + code.count('if') + code.count('for'))

        return {
            "analysis": f"{analysis_type.title()} analysis of {language} code completed",
            "language": language,
            "issues_found": len(suggestions),
            "suggestions": suggestions,
            "complexity_score": round(complexity, 2),
            "team_used": team_used
        }
