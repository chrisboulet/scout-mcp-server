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
SCOUT MCP Server - Main entry point.

This module provides the command-line interface for running the SCOUT MCP server.

Usage:
    scout [--config CONFIG_PATH] [--debug] [--version] [--health-check]

Examples:
    # Run with default configuration
    scout

    # Run with specific config file
    scout --config /path/to/config.yaml

    # Enable debug logging
    scout --debug

    # Check server health
    scout --health-check
"""

import sys
import asyncio
import argparse
from pathlib import Path
from typing import Optional
import structlog

from scout.server import ScoutMCPServer
from scout.config.exceptions import ConfigurationError

# Server metadata
__version__ = "0.1.0"
__author__ = "Christian Boulet / Boulet Stratégies TI"
__license__ = "Apache-2.0"


def configure_logging(debug: bool = False) -> None:
    """
    Configure structured logging.

    Args:
        debug: Enable debug level logging
    """
    import logging

    log_level = logging.DEBUG if debug else logging.INFO

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="SCOUT - Strategic CTO Operations and Unified Tooling MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          Run with default configuration
  %(prog)s --config config.yaml     Run with specific config file
  %(prog)s --debug                  Enable debug logging
  %(prog)s --health-check           Check server health and exit

For more information, visit: https://github.com/cboulware/scout
        """
    )

    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        help="Path to configuration file (YAML or JSON)",
        metavar="PATH"
    )

    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug logging"
    )

    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Perform health check and exit"
    )

    parser.add_argument(
        "--info",
        action="store_true",
        help="Display server information and exit"
    )

    return parser.parse_args()


async def run_health_check(server: ScoutMCPServer) -> int:
    """
    Run health check and display results.

    Args:
        server: SCOUT MCP Server instance

    Returns:
        Exit code (0 if healthy, 1 otherwise)
    """
    logger = structlog.get_logger()

    try:
        await server.initialize()
        health = await server.health_check()

        # Display results
        print("\n=== SCOUT MCP Server Health Check ===\n")
        print(f"Server Status: {health['server']}")
        print(f"Version: {health['version']}")
        print(f"\nTools: {health['tools']['available']}/{health['tools']['total']} available")

        print("\nProviders:")
        all_healthy = True
        for provider, status in health['providers'].items():
            symbol = "✓" if status == "healthy" else "✗"
            print(f"  {symbol} {provider}: {status}")
            if status != "healthy":
                all_healthy = False

        if all_healthy and health['server'] == 'healthy':
            print("\n✅ All systems operational")
            return 0
        else:
            print("\n⚠️  Some systems are unhealthy")
            return 1

    except Exception as e:
        logger.error("Health check failed", error=str(e))
        print(f"\n❌ Health check failed: {e}")
        return 1
    finally:
        await server.cleanup()


async def run_info(server: ScoutMCPServer) -> int:
    """
    Display server information.

    Args:
        server: SCOUT MCP Server instance

    Returns:
        Exit code (always 0)
    """
    try:
        await server.initialize()
        info = server.get_server_info()

        print("\n=== SCOUT MCP Server Information ===\n")
        print(f"Name: {info['name']}")
        print(f"Version: {info['version']}")
        print(f"Status: {'Running' if info['running'] else 'Stopped'}")
        print(f"\nTeams: {', '.join(info['teams'])}")
        print(f"Providers: {', '.join(info['providers'])}")
        print(f"\nTools Statistics:")
        print(f"  Total: {info['tools']['total_tools']}")
        print(f"  Deprecated: {info['tools']['deprecated_tools']}")
        print(f"  Categories:")
        for category, count in info['tools']['categories'].items():
            if count > 0:
                print(f"    {category}: {count}")

        return 0

    except Exception as e:
        print(f"\n❌ Failed to get server info: {e}")
        return 1
    finally:
        await server.cleanup()


async def run_server(
    config_path: Optional[Path] = None,
    debug: bool = False
) -> int:
    """
    Run the SCOUT MCP server.

    Args:
        config_path: Path to configuration file
        debug: Enable debug logging

    Returns:
        Exit code
    """
    logger = structlog.get_logger()

    try:
        # Create server instance
        server = ScoutMCPServer(config_path=config_path)

        # Display startup banner
        print(f"""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   SCOUT - Strategic CTO Operations and Unified Tooling       ║
║   MCP Server v{__version__:<50}║
║                                                               ║
║   Licensed under Apache License 2.0                           ║
║   Copyright 2025 Christian Boulet / Boulet Stratégies TI     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
        """)

        logger.info("Starting SCOUT MCP Server")
        logger.info(
            "Server configuration",
            teams=len(server.config.teams),
            providers=len(server.config.providers)
        )

        # Run server
        await server.run()

        return 0

    except ConfigurationError as e:
        logger.error("Configuration error", error=str(e))
        print(f"\n❌ Configuration Error: {e}")
        print("\nPlease check your configuration file and try again.")
        return 1

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        print("\n\n👋 SCOUT MCP Server stopped")
        return 0

    except Exception as e:
        logger.error("Server error", error=str(e), exc_info=True)
        print(f"\n❌ Server Error: {e}")
        return 1


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code
    """
    # Parse arguments
    args = parse_args()

    # Configure logging
    configure_logging(debug=args.debug)

    # Create event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Create server
        server = ScoutMCPServer(config_path=args.config)

        # Run appropriate command
        if args.health_check:
            return loop.run_until_complete(run_health_check(server))
        elif args.info:
            return loop.run_until_complete(run_info(server))
        else:
            return loop.run_until_complete(run_server(
                config_path=args.config,
                debug=args.debug
            ))

    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        return 1

    finally:
        loop.close()


if __name__ == "__main__":
    sys.exit(main())
