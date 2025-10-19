# Attribution and Derived Works

## About This Document

This document provides detailed attribution for code and architectural patterns derived from other open-source projects, particularly the Zen MCP Server.

## Primary Derivation: Zen MCP Server

### Original Project Information
- **Project Name**: Zen MCP Server
- **Copyright Holder**: BeehiveInnovations
- **License**: Apache License 2.0
- **Repository**: https://github.com/BeehiveInnovations/zen-mcp-server
- **Description**: Multi-model AI orchestration server with MCP protocol support

### Derived Components

#### 1. Core Architecture Patterns
**Original Location**: `zen-mcp-server/src/core/`
**SCOUT Location**: `src/scout/core/`

The following architectural patterns were adapted from Zen MCP Server:
- **Tool Registry Pattern**: The concept of dynamic tool registration and discovery
- **Provider Abstraction**: The base pattern for abstracting AI provider interfaces
- **Message Flow**: The unified message handling and routing system

**Modifications**:
- Extended tool registry to support YAML-based configuration
- Enhanced provider abstraction with retry logic and circuit breakers
- Added team-based model selection layer

#### 2. MCP Protocol Implementation
**Original Location**: `zen-mcp-server/src/mcp/`
**SCOUT Location**: Uses FastMCP instead

While Zen MCP Server provided the conceptual framework for MCP implementation, SCOUT uses FastMCP as its MCP server implementation, representing a complete reimplementation.

#### 3. Provider Patterns
**Original Concepts**: Multi-provider support with unified interface
**SCOUT Implementation**: `src/scout/providers/`

The concept of supporting multiple AI providers through a unified interface was inspired by Zen MCP Server. However, SCOUT's implementation is entirely original, including:
- Custom provider implementations for Gemini, OpenAI, Anthropic, OpenRouter, and Grok
- Factory pattern for provider instantiation
- Provider-specific error handling and retry logic

### Architectural Influences

The following high-level architectural decisions were influenced by Zen MCP Server:

1. **Separation of Concerns**: Clear separation between providers, tools, and core logic
2. **Async-First Design**: Use of async/await patterns throughout
3. **Error Handling Strategy**: Comprehensive exception hierarchy for provider errors
4. **Logging Architecture**: Structured logging with contextual information

## Other Inspirations

### FastMCP
- **Purpose**: MCP server implementation
- **License**: MIT
- **How Used**: Direct dependency, not derivation

### SpecKit Pattern
- **Source**: Internal Boulet Stratégies TI methodology
- **Description**: Specification-driven development framework
- **Implementation**: Original work

## Statement of Originality

While SCOUT derives certain architectural patterns and concepts from Zen MCP Server, the following components are entirely original:

1. **Configuration System**: Complete YAML-based configuration with Pydantic v2 models
2. **Redis State Management**: Original implementation for distributed state
3. **Team Selection System**: Novel approach to model selection based on task requirements
4. **Business Tools**: All tools specific to Fractional CTO workflows
5. **Constitution-Based Governance**: Original framework for project principles
6. **Provider Implementations**: All provider adapters written from scratch

## License Compliance

SCOUT complies with the Apache 2.0 license requirements by:
1. Including the full Apache 2.0 license text
2. Providing clear attribution in NOTICE file
3. Documenting modifications and extensions
4. Maintaining copyright notices
5. Using Apache 2.0 for SCOUT itself, ensuring license compatibility

## Contact for Questions

For questions about attribution or licensing:
- **Author**: Christian Boulet
- **Email**: christian@bouletstrategies.com
- **Organization**: Boulet Stratégies TI
- **Website**: https://bouletstrategies.com

---

*Last Updated: January 2025*