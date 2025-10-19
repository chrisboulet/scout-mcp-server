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
SCOUT Core Package.

This package contains the core orchestration components:
- Team Selector: Intelligent AI model selection based on task requirements
- Tool Registry: Dynamic tool registration and discovery for MCP protocol
"""

from scout.core.team_selector import (
    TeamSelector,
    TeamOrchestrator,
    TeamSelection,
    ValidationResult,
    TaskComplexity,
    TaskDomain,
)

from scout.core.tool_registry import (
    ToolRegistry,
    BaseTool,
    ToolMetadata,
    ToolSchema,
    RegisteredTool,
    ToolCategory,
    ToolPermission,
    get_registry,
    register_tool,
)

__all__ = [
    # Team Selector
    "TeamSelector",
    "TeamOrchestrator",
    "TeamSelection",
    "ValidationResult",
    "TaskComplexity",
    "TaskDomain",
    # Tool Registry
    "ToolRegistry",
    "BaseTool",
    "ToolMetadata",
    "ToolSchema",
    "RegisteredTool",
    "ToolCategory",
    "ToolPermission",
    "get_registry",
    "register_tool",
]
