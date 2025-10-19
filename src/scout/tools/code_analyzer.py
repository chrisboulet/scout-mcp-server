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
Code Analyzer Tool - Professional code analysis with AI integration.

This tool provides:
- AST-based code structure analysis
- Cyclomatic complexity calculation
- Maintainability index
- Code smell detection
- AI-powered deep analysis
- Security vulnerability scanning
- Performance bottleneck identification

Following Constitution Principles:
- #1: Contract-First Development (MCP schema)
- #2: Modular Architecture
- #4: AI Provider Abstraction
- #5: Robust Error Handling
- #6: Structured Logging
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import ast
import structlog

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


class CodeMetrics(BaseModel):
    """Code metrics computed from analysis."""

    lines_of_code: int = Field(..., description="Total lines of code")
    lines_of_comments: int = Field(default=0, description="Lines of comments")
    blank_lines: int = Field(default=0, description="Blank lines")
    cyclomatic_complexity: int = Field(default=1, description="Cyclomatic complexity")
    functions_count: int = Field(default=0, description="Number of functions/methods")
    classes_count: int = Field(default=0, description="Number of classes")
    maintainability_index: float = Field(default=0.0, description="Maintainability index (0-100)")


class CodeIssue(BaseModel):
    """A single code issue or smell."""

    severity: str = Field(..., description="Severity: critical, high, medium, low, info")
    category: str = Field(..., description="Category: security, performance, style, complexity, smell")
    message: str = Field(..., description="Issue description")
    line: Optional[int] = Field(None, description="Line number where issue occurs")
    suggestion: Optional[str] = Field(None, description="Suggested fix")


class CodeAnalyzerInput(BaseModel):
    """Input schema for code analyzer."""

    code: str = Field(
        ...,
        description="Code to analyze",
        min_length=1,
        max_length=100000
    )
    language: str = Field(
        default="python",
        description="Programming language (python, javascript, typescript, java, go, rust)"
    )
    analysis_type: str = Field(
        default="comprehensive",
        description="Type of analysis: comprehensive, security, performance, quality, complexity"
    )
    use_ai: bool = Field(
        default=True,
        description="Use AI for deep analysis (costs tokens)"
    )
    team_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Team selection context (injected by server)",
        exclude=True
    )


class CodeAnalyzerOutput(BaseModel):
    """Output schema for code analyzer."""

    summary: str = Field(..., description="Executive summary of analysis")
    language: str = Field(..., description="Detected/specified language")
    metrics: CodeMetrics = Field(..., description="Code metrics")
    issues: List[CodeIssue] = Field(
        default_factory=list,
        description="List of detected issues"
    )
    quality_score: float = Field(
        ...,
        description="Overall quality score (0-100)",
        ge=0,
        le=100
    )
    ai_insights: Optional[str] = Field(
        None,
        description="AI-generated insights and recommendations"
    )
    team_used: Optional[str] = Field(
        None,
        description="Team that performed analysis"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class CodeAnalyzerTool(BaseTool):
    """
    Professional Code Analyzer with AI integration.

    Features:
    - AST-based structural analysis (Python)
    - Cyclomatic complexity calculation
    - Maintainability index
    - Code smell detection
    - Security vulnerability scanning
    - Performance analysis
    - AI-powered deep insights

    Example Usage:
        Basic analysis:
        {
            "code": "def factorial(n):\\n    return 1 if n <= 1 else n * factorial(n-1)",
            "language": "python",
            "analysis_type": "comprehensive"
        }

        Security-focused:
        {
            "code": "password = 'hardcoded123'\\neval(user_input)",
            "language": "python",
            "analysis_type": "security",
            "use_ai": true
        }
    """

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        return ToolMetadata(
            name="code_analyzer",
            description="Analyze code for quality, security, performance, and complexity with AI insights",
            category=ToolCategory.ANALYSIS,
            version="2.0.0",
            author="SCOUT Team",
            permissions={ToolPermission.READ},
            tags=["code", "analysis", "quality", "security", "metrics", "ast"],
            examples=[
                {
                    "code": "def factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)",
                    "language": "python",
                    "analysis_type": "comprehensive"
                },
                {
                    "code": "password = 'secret123'\neval(user_input)",
                    "language": "python",
                    "analysis_type": "security"
                },
                {
                    "code": "for i in range(n):\n    for j in range(m):\n        result[i][j] = matrix[i][j] * 2",
                    "language": "python",
                    "analysis_type": "performance"
                }
            ],
            cost_estimate=0.02,
            avg_latency_ms=1500
        )

    def get_schema(self) -> ToolSchema:
        """Get tool schema."""
        return ToolSchema(
            input_model=CodeAnalyzerInput,
            output_model=CodeAnalyzerOutput
        )

    def _analyze_python_ast(self, code: str) -> Dict[str, Any]:
        """
        Analyze Python code using AST.

        Args:
            code: Python source code

        Returns:
            Dictionary with AST-based metrics and issues
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "error": f"Syntax error at line {e.lineno}: {e.msg}",
                "metrics": {
                    "lines_of_code": len(code.split('\n')),
                    "cyclomatic_complexity": 0,
                    "functions_count": 0,
                    "classes_count": 0
                },
                "issues": [
                    {
                        "severity": "critical",
                        "category": "syntax",
                        "message": f"Syntax error: {e.msg}",
                        "line": e.lineno,
                        "suggestion": "Fix syntax error before analysis"
                    }
                ]
            }

        # Count various code elements
        functions = []
        classes = []
        complexity = 1  # Base complexity

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
                # Add complexity for decision points
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                        complexity += 1
                    elif isinstance(child, ast.BoolOp):
                        complexity += len(child.values) - 1

            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)

        lines = code.split('\n')
        loc = len([l for l in lines if l.strip()])
        comments = len([l for l in lines if l.strip().startswith('#')])
        blank = len([l for l in lines if not l.strip()])

        # Calculate maintainability index (simplified)
        # MI = 171 - 5.2 * ln(V) - 0.23 * G - 16.2 * ln(LOC)
        # Where V = Halstead Volume, G = Cyclomatic Complexity
        import math
        if loc > 0:
            mi = max(0, min(100, 171 - 5.2 * math.log(max(1, loc)) -
                           0.23 * complexity - 16.2 * math.log(loc)))
        else:
            mi = 0

        metrics = {
            "lines_of_code": loc,
            "lines_of_comments": comments,
            "blank_lines": blank,
            "cyclomatic_complexity": complexity,
            "functions_count": len(functions),
            "classes_count": len(classes),
            "maintainability_index": round(mi, 2)
        }

        return {
            "metrics": metrics,
            "functions": functions,
            "classes": classes,
            "complexity": complexity
        }

    def _detect_code_smells(
        self,
        code: str,
        language: str,
        analysis_type: str,
        ast_result: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect code smells and issues.

        Args:
            code: Source code
            language: Programming language
            analysis_type: Type of analysis
            ast_result: AST analysis results

        Returns:
            List of detected issues
        """
        issues = []
        lines = code.split('\n')

        # Security checks
        if analysis_type in ["comprehensive", "security"]:
            # Check for eval/exec
            if "eval(" in code or "exec(" in code:
                issues.append({
                    "severity": "critical",
                    "category": "security",
                    "message": "Dangerous use of eval() or exec() detected",
                    "suggestion": "Use safer alternatives like ast.literal_eval() or remove dynamic code execution"
                })

            # Check for hardcoded passwords/secrets
            for i, line in enumerate(lines, 1):
                if any(word in line.lower() for word in ["password", "secret", "api_key", "token"]):
                    if "=" in line and ("'" in line or '"' in line):
                        issues.append({
                            "severity": "high",
                            "category": "security",
                            "message": "Potential hardcoded secret detected",
                            "line": i,
                            "suggestion": "Use environment variables or secure configuration"
                        })

            # Check for SQL injection risks
            if "execute(" in code and ("%" in code or "format(" in code):
                issues.append({
                    "severity": "high",
                    "category": "security",
                    "message": "Potential SQL injection vulnerability",
                    "suggestion": "Use parameterized queries instead of string formatting"
                })

        # Performance checks
        if analysis_type in ["comprehensive", "performance"]:
            # Check for nested loops
            nested_loops = code.count("for") >= 2 or code.count("while") >= 2
            if nested_loops:
                issues.append({
                    "severity": "medium",
                    "category": "performance",
                    "message": "Nested loops detected - potential O(n²) or worse complexity",
                    "suggestion": "Consider using dict/set lookups or vectorized operations"
                })

            # Check for inefficient string concatenation
            if "+=" in code and "str" in code.lower():
                issues.append({
                    "severity": "low",
                    "category": "performance",
                    "message": "String concatenation in loop may be inefficient",
                    "suggestion": "Use ''.join() for better performance"
                })

        # Complexity checks
        if analysis_type in ["comprehensive", "complexity"]:
            if ast_result:
                complexity = ast_result.get("complexity", 1)
                if complexity > 10:
                    issues.append({
                        "severity": "high",
                        "category": "complexity",
                        "message": f"High cyclomatic complexity ({complexity}) - code is hard to test and maintain",
                        "suggestion": "Break down into smaller functions"
                    })
                elif complexity > 5:
                    issues.append({
                        "severity": "medium",
                        "category": "complexity",
                        "message": f"Moderate cyclomatic complexity ({complexity}) - consider refactoring",
                        "suggestion": "Extract complex logic into separate functions"
                    })

        # Style checks
        if analysis_type in ["comprehensive", "quality"]:
            # Check for tabs vs spaces
            if "\t" in code:
                issues.append({
                    "severity": "low",
                    "category": "style",
                    "message": "Mixed tabs and spaces detected",
                    "suggestion": "Use 4 spaces for indentation (PEP 8)"
                })

            # Check for long lines
            for i, line in enumerate(lines, 1):
                if len(line) > 88:  # PEP 8 recommends 79, Black uses 88
                    issues.append({
                        "severity": "low",
                        "category": "style",
                        "message": f"Line {i} exceeds recommended length ({len(line)} > 88)",
                        "line": i,
                        "suggestion": "Break long lines for better readability"
                    })

            # Check for missing docstrings
            if language == "python" and ("def " in code or "class " in code):
                if '"""' not in code and "'''" not in code:
                    issues.append({
                        "severity": "low",
                        "category": "quality",
                        "message": "Missing docstrings",
                        "suggestion": "Add docstrings to functions and classes"
                    })

        return issues

    async def _get_ai_insights(
        self,
        code: str,
        language: str,
        metrics: Dict[str, Any],
        issues: List[Dict[str, Any]],
        provider: Optional[BaseAIProvider] = None,
        model: str = "unknown"
    ) -> Optional[str]:
        """
        Get AI-powered insights about the code.

        Args:
            code: Source code
            language: Programming language
            metrics: Code metrics
            issues: Detected issues
            provider: AI provider instance
            model: Model to use

        Returns:
            AI-generated insights or None
        """
        if not provider:
            return None

        log = logger.bind(tool="code_analyzer", language=language)

        try:
            log.debug("Requesting AI insights")

            # Build analysis prompt
            prompt = f"""Analyze this {language} code and provide expert insights:

CODE:
```{language}
{code[:2000]}
```

METRICS:
- Lines of Code: {metrics.get('lines_of_code', 0)}
- Cyclomatic Complexity: {metrics.get('cyclomatic_complexity', 0)}
- Functions: {metrics.get('functions_count', 0)}
- Maintainability Index: {metrics.get('maintainability_index', 0):.1f}/100

DETECTED ISSUES: {len(issues)}

Please provide:
1. Overall code quality assessment
2. Key strengths and weaknesses
3. Specific refactoring recommendations
4. Best practices that should be applied

Keep your response concise (max 500 words)."""

            messages = [Message(role=Role.USER, content=prompt)]

            response = await provider.chat(
                messages=messages,
                model=model,
                max_tokens=1000,
                temperature=0.3  # Lower temperature for more factual analysis
            )

            log.info("AI insights generated", tokens=response.total_tokens)
            return response.content

        except Exception as e:
            log.error("Failed to get AI insights", error=str(e))
            return None

    async def execute(
        self,
        code: str,
        language: str = "python",
        analysis_type: str = "comprehensive",
        use_ai: bool = True,
        team_context: Optional[Dict[str, Any]] = None,
        provider: Optional[BaseAIProvider] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute comprehensive code analysis.

        Args:
            code: Code to analyze
            language: Programming language
            analysis_type: Type of analysis to perform
            use_ai: Whether to use AI for deep insights
            team_context: Team context (injected by server)
            provider: AI provider (injected by server)
            **kwargs: Additional parameters

        Returns:
            Comprehensive analysis results
        """
        log = logger.bind(
            tool="code_analyzer",
            language=language,
            analysis_type=analysis_type,
            code_length=len(code)
        )

        log.info("Code analysis started")

        # Extract team information
        team_used = "default"
        provider_used = "none"
        model_used = "none"

        if team_context:
            team_used = team_context.get("team", "default")
            provider_used = team_context.get("provider", "none")
            model_used = team_context.get("model", "none")

        try:
            # Perform language-specific analysis
            if language == "python":
                ast_result = self._analyze_python_ast(code)

                if "error" in ast_result:
                    # Syntax error - return early
                    return {
                        "summary": f"Analysis failed: {ast_result['error']}",
                        "language": language,
                        "metrics": CodeMetrics(**ast_result["metrics"]),
                        "issues": [CodeIssue(**issue) for issue in ast_result["issues"]],
                        "quality_score": 0.0,
                        "ai_insights": None,
                        "team_used": team_used,
                        "metadata": {
                            "analysis_type": analysis_type,
                            "provider": provider_used,
                            "model": model_used
                        }
                    }

                metrics = ast_result["metrics"]
                base_issues = ast_result.get("issues", [])

            else:
                # Basic analysis for other languages
                lines = code.split('\n')
                loc = len([l for l in lines if l.strip()])
                comments = len([l for l in lines if l.strip().startswith(('//','#','/*','*'))])
                blank = len([l for l in lines if not l.strip()])

                metrics = {
                    "lines_of_code": loc,
                    "lines_of_comments": comments,
                    "blank_lines": blank,
                    "cyclomatic_complexity": 1,
                    "functions_count": 0,
                    "classes_count": 0,
                    "maintainability_index": 50.0
                }
                base_issues = []
                ast_result = {"metrics": metrics}

            # Detect code smells and issues
            detected_issues = self._detect_code_smells(
                code, language, analysis_type, ast_result
            )
            all_issues = base_issues + detected_issues

            # Calculate quality score based on metrics and issues
            # Start with maintainability index
            quality = metrics["maintainability_index"]

            # Penalize for issues
            for issue in all_issues:
                severity = issue.get("severity", "low")
                if severity == "critical":
                    quality -= 20
                elif severity == "high":
                    quality -= 10
                elif severity == "medium":
                    quality -= 5
                elif severity == "low":
                    quality -= 2

            quality_score = max(0.0, min(100.0, quality))

            # Get AI insights if requested
            ai_insights = None
            if use_ai and provider:
                ai_insights = await self._get_ai_insights(
                    code, language, metrics, all_issues, provider, model_used
                )

            # Generate summary
            severity_counts = {}
            for issue in all_issues:
                sev = issue.get("severity", "low")
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

            summary_parts = [
                f"{language.title()} code analysis complete.",
                f"Quality Score: {quality_score:.1f}/100.",
                f"Found {len(all_issues)} issues"
            ]

            if severity_counts:
                sev_list = [f"{count} {sev}" for sev, count in severity_counts.items()]
                summary_parts.append(f"({', '.join(sev_list)})")

            summary = " ".join(summary_parts)

            log.info(
                "Code analysis completed",
                issues_found=len(all_issues),
                quality_score=quality_score
            )

            return {
                "summary": summary,
                "language": language,
                "metrics": CodeMetrics(**metrics),
                "issues": [CodeIssue(**issue) for issue in all_issues],
                "quality_score": round(quality_score, 2),
                "ai_insights": ai_insights,
                "team_used": team_used,
                "metadata": {
                    "analysis_type": analysis_type,
                    "provider": provider_used,
                    "model": model_used,
                    "used_ai": use_ai and ai_insights is not None,
                    "ast_analysis": language == "python"
                }
            }

        except Exception as e:
            log.error("Code analysis failed", error=str(e), exc_info=True)
            raise
