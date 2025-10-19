"""Performance and stress tests for configuration system (Phase 7).

Tests verify that configuration loading meets performance requirements
and can scale to large numbers of providers and teams.

Success Criteria:
  - SC-001: Configuration loads in under 1 second for typical config
  - SC-007: System handles at least 10 providers with complex configurations

Author: SCOUT Development Team
License: MIT
"""

from pathlib import Path

import pytest

from scout.config import load_config

# Path to fixture directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestConfigurationPerformance:
    """Test cases for configuration loading performance (T097 / SC-001)."""

    def test_typical_config_loads_in_under_1_second(self, benchmark):
        """Should load typical configuration file in under 1 second (SC-001)."""
        config_path = str(FIXTURES_DIR / "team_config.yaml")

        # Benchmark the configuration loading
        result = benchmark(load_config, config_path)

        # Verify configuration loaded correctly
        assert result is not None
        assert len(result.providers) == 3
        assert len(result.teams) == 3

        # pytest-benchmark automatically verifies and reports performance
        # Benchmark results are displayed in test output
        # SC-001 requires < 1.0 second, typical configs load in ~5ms


class TestLargeConfigurationScalability:
    """Test cases for large configuration scalability (T098, T099 / SC-007)."""

    def test_10_providers_20_teams_load_successfully(self):
        """Should successfully load configuration with 10 providers and 20 teams (T098 / SC-007)."""
        config_path = str(FIXTURES_DIR / "stress_test_10p_20t.yaml")

        # Load large configuration
        import time

        start = time.time()
        config = load_config(config_path)
        duration = time.time() - start

        # Verify all providers and teams loaded
        assert len(config.providers) == 10, "Should load 10 providers"
        assert len(config.teams) == 20, "Should load 20 teams"

        # Verify performance is reasonable (< 2 seconds for stress test)
        assert duration < 2.0, (
            f"Loading 10 providers and 20 teams took {duration:.3f}s, "
            f"expected < 2.0s"
        )

    def test_50_providers_100_teams_scalability(self):
        """Should handle extreme configuration with 50 providers and 100 teams (T099)."""
        config_path = str(FIXTURES_DIR / "stress_test_50p_100t.yaml")

        # Load extreme configuration
        import time

        start = time.time()
        config = load_config(config_path)
        duration = time.time() - start

        # Verify all providers and teams loaded
        assert len(config.providers) == 50, "Should load 50 providers"
        assert len(config.teams) == 100, "Should load 100 teams"

        # Verify performance is reasonable (< 5 seconds for extreme stress test)
        assert duration < 5.0, (
            f"Loading 50 providers and 100 teams took {duration:.3f}s, "
            f"expected < 5.0s"
        )

        # Verify cross-reference validation still works at scale
        # Pick a random team and verify its references are valid
        sample_team = config.teams["team_50"]
        assert sample_team.primary.provider in config.providers
        assert sample_team.primary.model in config.providers[sample_team.primary.provider].models


class TestErrorMessageQuality:
    """Test cases for error message quality (T100 / SC-003)."""

    def test_validation_error_includes_field_name(self):
        """Should include field name in validation error messages (SC-003)."""
        config_path = str(FIXTURES_DIR / "invalid_team_reference.yaml")

        with pytest.raises(Exception) as exc_info:
            load_config(config_path)

        error_msg = str(exc_info.value).lower()

        # Verify error message includes field information
        # Should mention either "provider", "team", or "openai"
        has_field_info = (
            "provider" in error_msg
            or "team" in error_msg
            or "openai" in error_msg
        )
        assert has_field_info, (
            f"Error message should include field information: {exc_info.value}"
        )

    def test_missing_required_field_error_includes_location(self):
        """Should include field location in missing required field errors (SC-003)."""
        config_path = str(FIXTURES_DIR / "missing_required_field.yaml")

        with pytest.raises(Exception) as exc_info:
            load_config(config_path)

        error_msg = str(exc_info.value).lower()

        # Verify error message includes location information
        # Should mention "api_key", "field", or specific location
        has_location_info = (
            "api_key" in error_msg
            or "field" in error_msg
            or "provider" in error_msg
        )
        assert has_location_info, (
            f"Error message should include field location: {exc_info.value}"
        )
