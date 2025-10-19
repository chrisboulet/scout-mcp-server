# Code Analyzer Tool

Professional code analysis tool with AI-powered insights, security scanning, and quality metrics.

## Overview

The Code Analyzer Tool provides comprehensive static code analysis for Python codebases, including:

- **AST-based structural analysis** - Deep understanding of code organization
- **Cyclomatic complexity** - Measure code complexity objectively
- **Maintainability index** - Quantify how maintainable code is (0-100 scale)
- **Security vulnerability scanning** - Detect common security issues
- **Performance bottleneck identification** - Find inefficient code patterns
- **Quality scoring** - Overall code quality score (0-100)
- **AI-powered insights** - Get expert recommendations from AI models

## Features

### Metrics Calculated

- **Lines of Code (LOC)** - Non-blank, non-comment lines
- **Cyclomatic Complexity** - Number of decision paths through code
- **Maintainability Index** - Composite metric (0-100, higher is better)
- **Function Count** - Number of functions and methods
- **Class Count** - Number of classes

### Issue Detection

#### Security Issues (Critical/High)
- `eval()` and `exec()` usage - Dangerous dynamic code execution
- Hardcoded secrets - Passwords, API keys, tokens in code
- SQL injection risks - String formatting in queries
- Command injection risks - Unsafe shell command construction

#### Performance Issues (Medium/Low)
- Nested loops - O(n²) or worse time complexity
- Inefficient operations - Known performance anti-patterns

#### Complexity Issues (Medium/Low)
- High cyclomatic complexity - Functions with too many decision points
- Deep nesting - Code that's hard to read and maintain

#### Style Issues (Low/Info)
- Missing docstrings - Functions/classes without documentation
- Long lines - Lines exceeding recommended length
- Mixed indentation - Tabs vs spaces inconsistency

### Quality Scoring

Code receives a quality score from 0-100 based on:
- Severity and number of issues detected
- Code complexity metrics
- Maintainability index
- Best practices adherence

**Scoring Penalties:**
- Critical issue: -25 points
- High severity issue: -15 points
- Medium severity issue: -10 points
- Low severity issue: -5 points

## Usage

### Basic Analysis

```python
from scout.server import ScoutMCPServer

# Initialize server
server = ScoutMCPServer(config_path="config.yaml")
await server.initialize()

# Analyze code
result = await server.execute_tool(
    "code_analyzer",
    {
        "code": your_code_string,
        "language": "python",
        "analysis_type": "comprehensive"
    }
)

# View results
print(f"Quality Score: {result['quality_score']}/100")
print(f"Issues Found: {len(result['issues'])}")
```

### Analysis Types

#### 1. Quick Analysis
Fast, basic metrics without deep inspection.

```python
result = await server.execute_tool(
    "code_analyzer",
    {
        "code": code,
        "language": "python",
        "analysis_type": "quick"
    }
)
```

**Returns:** Basic metrics (LOC, complexity, functions/classes count)

#### 2. Comprehensive Analysis (Recommended)
Full analysis including all checks and metrics.

```python
result = await server.execute_tool(
    "code_analyzer",
    {
        "code": code,
        "language": "python",
        "analysis_type": "comprehensive",
        "use_ai": True  # Include AI insights
    }
)
```

**Returns:** All metrics + security/performance/complexity/style issues + AI insights

#### 3. Security-Focused Analysis
Prioritizes security vulnerability detection.

```python
result = await server.execute_tool(
    "code_analyzer",
    {
        "code": code,
        "language": "python",
        "analysis_type": "security"
    }
)
```

**Returns:** Security-focused scan with detailed vulnerability reports

### With AI Insights

Enable AI-powered analysis for expert recommendations:

```python
result = await server.execute_tool(
    "code_analyzer",
    {
        "code": code,
        "language": "python",
        "analysis_type": "comprehensive",
        "use_ai": True  # Enable AI insights
    }
)

# Access AI insights
if result.get('ai_insights'):
    print(result['ai_insights'])
```

**Note:** AI insights require a configured provider (Gemini, OpenAI, or Anthropic) and will consume tokens.

## Output Format

```python
{
    "summary": "Python code analysis complete. Quality Score: 85/100...",
    "quality_score": 85,  # 0-100

    "metrics": {
        "lines_of_code": 120,
        "lines_of_comments": 30,
        "blank_lines": 15,
        "cyclomatic_complexity": 8,
        "functions_count": 12,
        "classes_count": 3,
        "maintainability_index": 75.5  # 0-100
    },

    "issues": [
        {
            "severity": "critical",  # critical, high, medium, low
            "category": "security",  # security, performance, complexity, style
            "message": "Dangerous use of eval() detected",
            "line": 42,  # Line number (optional)
            "suggestion": "Use ast.literal_eval() instead"
        }
    ],

    "ai_insights": "This code demonstrates good practices..." # Optional, if use_ai=True
}
```

## Examples

### Example 1: Analyze a Python File

```python
import asyncio
from pathlib import Path
from scout.server import ScoutMCPServer

async def analyze_file(file_path: str):
    # Read code
    code = Path(file_path).read_text()

    # Initialize server
    server = ScoutMCPServer(config_path="config.yaml")
    await server.initialize()

    # Analyze
    result = await server.execute_tool(
        "code_analyzer",
        {
            "code": code,
            "language": "python",
            "analysis_type": "comprehensive",
            "use_ai": True
        }
    )

    # Report results
    print(f"\\n{'='*70}")
    print(f"Code Analysis: {file_path}")
    print(f"{'='*70}")
    print(f"\\nQuality Score: {result['quality_score']}/100")
    print(f"\\nMetrics:")
    print(f"  LOC: {result['metrics'].lines_of_code}")
    print(f"  Complexity: {result['metrics'].cyclomatic_complexity}")
    print(f"  Maintainability: {result['metrics'].maintainability_index:.1f}/100")

    if result['issues']:
        print(f"\\n⚠️  Issues Found: {len(result['issues'])}")
        for issue in result['issues'][:5]:  # Show first 5
            print(f"  [{issue.severity.upper()}] {issue.message}")
            if issue.suggestion:
                print(f"    💡 {issue.suggestion}")

    if result.get('ai_insights'):
        print(f"\\n🤖 AI Insights:")
        print(f"  {result['ai_insights'][:500]}...")

    await server.cleanup()

# Run
asyncio.run(analyze_file("my_code.py"))
```

### Example 2: Security Audit

```python
async def security_audit(code: str):
    server = ScoutMCPServer(config_path="config.yaml")
    await server.initialize()

    result = await server.execute_tool(
        "code_analyzer",
        {
            "code": code,
            "language": "python",
            "analysis_type": "security"
        }
    )

    # Filter security issues
    security_issues = [
        i for i in result['issues']
        if i.category == "security"
    ]

    print(f"🔒 Security Audit Results:")
    print(f"  Critical: {len([i for i in security_issues if i.severity == 'critical'])}")
    print(f"  High: {len([i for i in security_issues if i.severity == 'high'])}")

    for issue in security_issues:
        if issue.severity in ['critical', 'high']:
            line_info = f" (line {issue.line})" if issue.line else ""
            print(f"\\n[{issue.severity.upper()}]{line_info}")
            print(f"  {issue.message}")
            if issue.suggestion:
                print(f"  💡 {issue.suggestion}")

    await server.cleanup()
```

### Example 3: Batch Analysis

```python
from pathlib import Path

async def batch_analyze(directory: str):
    """Analyze all Python files in a directory."""
    server = ScoutMCPServer(config_path="config.yaml")
    await server.initialize()

    results = {}

    # Find all Python files
    for py_file in Path(directory).rglob("*.py"):
        code = py_file.read_text()

        result = await server.execute_tool(
            "code_analyzer",
            {
                "code": code,
                "language": "python",
                "analysis_type": "comprehensive",
                "use_ai": False  # Faster without AI
            }
        )

        results[str(py_file)] = {
            "score": result['quality_score'],
            "issues": len(result['issues']),
            "complexity": result['metrics'].cyclomatic_complexity
        }

    # Summary report
    print(f"\\n{'='*70}")
    print(f"Batch Analysis Report: {directory}")
    print(f"{'='*70}")

    avg_score = sum(r['score'] for r in results.values()) / len(results)
    total_issues = sum(r['issues'] for r in results.values())

    print(f"\\nFiles Analyzed: {len(results)}")
    print(f"Average Quality Score: {avg_score:.1f}/100")
    print(f"Total Issues: {total_issues}")

    # Top/bottom performers
    sorted_files = sorted(results.items(), key=lambda x: x[1]['score'], reverse=True)

    print(f"\\n✅ Best Quality:")
    for file, data in sorted_files[:3]:
        print(f"  {file}: {data['score']}/100")

    print(f"\\n⚠️  Needs Attention:")
    for file, data in sorted_files[-3:]:
        print(f"  {file}: {data['score']}/100 ({data['issues']} issues)")

    await server.cleanup()
```

## Configuration

### Enable/Disable AI Insights

AI insights are optional and can be toggled:

```python
result = await server.execute_tool(
    "code_analyzer",
    {
        "code": code,
        "language": "python",
        "use_ai": False  # Disable AI for faster analysis
    }
)
```

### Supported Languages

Currently supported:
- ✅ Python (full support with AST analysis)

Future support planned:
- JavaScript/TypeScript
- Java
- Go
- Rust

## Best Practices

### 1. Regular Analysis

Run analysis regularly during development:
- Before commits (via pre-commit hooks)
- During CI/CD pipeline
- Weekly code quality reports

### 2. Set Quality Thresholds

Enforce minimum quality standards:

```python
MIN_QUALITY_SCORE = 70

if result['quality_score'] < MIN_QUALITY_SCORE:
    print(f"❌ Quality score {result['quality_score']} below threshold {MIN_QUALITY_SCORE}")
    exit(1)
```

### 3. Focus on Critical Issues First

Prioritize fixes by severity:

```python
critical_issues = [i for i in result['issues'] if i.severity == 'critical']
high_issues = [i for i in result['issues'] if i.severity == 'high']

if critical_issues:
    print("⚠️  FIX IMMEDIATELY:")
    for issue in critical_issues:
        print(f"  {issue.message}")
```

### 4. Track Progress Over Time

Monitor code quality trends:

```python
# Store results
import json
from datetime import datetime

history = {
    "timestamp": datetime.utcnow().isoformat(),
    "score": result['quality_score'],
    "issues_count": len(result['issues']),
    "complexity": result['metrics'].cyclomatic_complexity
}

with open("quality_history.jsonl", "a") as f:
    f.write(json.dumps(history) + "\\n")
```

### 5. Use AI Sparingly

AI insights are powerful but costly:
- Use for complex/unfamiliar code
- Use for architecture decisions
- Skip for routine/simple analysis

## Interpreting Results

### Quality Score Ranges

- **90-100:** Excellent - Production-ready code
- **70-89:** Good - Minor improvements possible
- **50-69:** Fair - Needs attention
- **30-49:** Poor - Significant issues
- **0-29:** Critical - Major refactoring needed

### Cyclomatic Complexity

- **1-10:** Simple - Easy to test
- **11-20:** Moderate - Acceptable
- **21-50:** Complex - Consider refactoring
- **50+:** Very Complex - Difficult to maintain

### Maintainability Index

- **80-100:** Highly maintainable
- **60-79:** Moderately maintainable
- **40-59:** Low maintainability
- **0-39:** Difficult to maintain

## Troubleshooting

### Issue: No AI Insights Generated

**Cause:** Provider not configured or `use_ai=False`

**Solution:**
1. Verify provider is configured in `config.yaml`
2. Ensure `use_ai=True` in request
3. Check API keys in `.env` file

### Issue: Syntax Errors in Analysis

**Cause:** Code has syntax errors

**Solution:**
The analyzer will report syntax errors as critical issues. Fix syntax errors before running full analysis.

### Issue: Low Quality Score on Good Code

**Cause:** May have legitimate complexity or missing docs

**Solution:**
Review individual issues to understand penalties:
- Add docstrings where missing
- Refactor complex functions
- Fix legitimate issues found

### Issue: Analysis Too Slow

**Cause:** AI insights enabled on large files

**Solution:**
1. Disable AI for quick checks: `use_ai=False`
2. Use `analysis_type="quick"` for basic metrics
3. Analyze smaller code segments

## Integration Examples

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

python -c "
import asyncio
import sys
from pathlib import Path
from scout.server import ScoutMCPServer

async def check():
    server = ScoutMCPServer(config_path='config.yaml')
    await server.initialize()

    # Check staged Python files
    for file in Path('.').rglob('*.py'):
        code = file.read_text()
        result = await server.execute_tool('code_analyzer', {
            'code': code,
            'language': 'python',
            'analysis_type': 'security'
        })

        critical = [i for i in result['issues'] if i.severity == 'critical']
        if critical:
            print(f'❌ Critical issues in {file}')
            for issue in critical:
                print(f'  {issue.message}')
            sys.exit(1)

    await server.cleanup()

asyncio.run(check())
"
```

### CI/CD Pipeline (GitHub Actions)

```yaml
name: Code Quality

on: [push, pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e .

      - name: Analyze code quality
        run: |
          python -m tests.analyze_all --min-score 70
```

## API Reference

### Input Schema

```python
class CodeAnalyzerInput(BaseModel):
    code: str  # Code to analyze (max 100,000 chars)
    language: str = "python"  # Language
    analysis_type: str = "comprehensive"  # Type of analysis
    use_ai: bool = True  # Enable AI insights
```

### Output Schema

```python
class CodeAnalyzerOutput(BaseModel):
    summary: str  # Human-readable summary
    quality_score: int  # 0-100 quality score
    metrics: CodeMetrics  # Detailed metrics
    issues: List[CodeIssue]  # List of issues found
    ai_insights: Optional[str]  # AI recommendations (if use_ai=True)
```

### CodeMetrics

```python
class CodeMetrics(BaseModel):
    lines_of_code: int
    lines_of_comments: int
    blank_lines: int
    cyclomatic_complexity: int
    functions_count: int
    classes_count: int
    maintainability_index: float  # 0-100
```

### CodeIssue

```python
class CodeIssue(BaseModel):
    severity: str  # "critical", "high", "medium", "low"
    category: str  # "security", "performance", "complexity", "style"
    message: str  # Issue description
    line: Optional[int]  # Line number
    suggestion: Optional[str]  # Suggested fix
```

## License

Copyright 2025 Christian Boulet / Boulet Stratégies TI

Licensed under the Apache License, Version 2.0.
