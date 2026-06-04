"""
TokenLens - Unit tests for the analyzer intelligence engine.
Run with: python3 -m pytest tests/ -v
"""
import sys
import tempfile
import unittest
from pathlib import Path

# Allow importing from parent directory
sys.path.insert(0, str(Path(__file__).parent.parent))

import analyzer
import scanner


class TestEfficiencyScore(unittest.TestCase):
    """Tests for _calc_efficiency_score — the core scoring algorithm."""

    def test_perfect_cache_usage_scores_high(self):
        """High cache hit rate + warm cache + decent output should score C grade (>58)."""
        score = analyzer._calc_efficiency_score(
            cache_read=900_000,
            cache_write=50_000,
            fresh_input=50_000,
            output=100_000,
        )
        # Expected ≈ 68.7: cache(36) + output_density(3.2) + warm(20) + ctx(9.5)
        # Output density is low (100K output / 950K context) which is realistic for agentic work
        self.assertGreater(score, 58, "High cache hit rate should yield at least C grade")
        self.assertGreater(score, 60, "Score should be solidly above 60 with 90% cache hits")

    def test_zero_cache_scores_low(self):
        """No caching at all should score below 40 (F grade)."""
        score = analyzer._calc_efficiency_score(
            cache_read=0,
            cache_write=0,
            fresh_input=1_000_000,
            output=10_000,
        )
        self.assertLess(score, 40, "Zero cache usage should yield F grade")

    def test_cache_warm_but_no_hits_gets_partial_credit(self):
        """Writing to cache but never reading still earns the 20pt warm-rate credit."""
        score = analyzer._calc_efficiency_score(
            cache_read=0,
            cache_write=100_000,
            fresh_input=100_000,
            output=10_000,
        )
        self.assertGreaterEqual(score, 20, "Cache warm rate alone should contribute ≥20pts")

    def test_all_zeros_returns_zero(self):
        """Empty session should score 0, not crash."""
        score = analyzer._calc_efficiency_score(0, 0, 0, 0)
        self.assertEqual(score, 0.0)

    def test_score_bounded_0_to_100(self):
        """Score must never exceed 100 or go below 0."""
        score_high = analyzer._calc_efficiency_score(
            cache_read=10_000_000,
            cache_write=1_000_000,
            fresh_input=1,
            output=10_000_000,
        )
        score_low = analyzer._calc_efficiency_score(0, 0, 10_000_000, 0)
        self.assertLessEqual(score_high, 100.0)
        self.assertGreaterEqual(score_low, 0.0)

    def test_grade_a_threshold(self):
        """Score >= 88 should yield A."""
        self.assertEqual(analyzer._efficiency_grade(88.0), "A")
        self.assertEqual(analyzer._efficiency_grade(95.5), "A")
        self.assertEqual(analyzer._efficiency_grade(100.0), "A")

    def test_grade_f_threshold(self):
        """Score < 40 should yield F."""
        self.assertEqual(analyzer._efficiency_grade(0.0), "F")
        self.assertEqual(analyzer._efficiency_grade(39.9), "F")

    def test_grade_d_range(self):
        """40–57 should yield D."""
        self.assertEqual(analyzer._efficiency_grade(40.0), "D")
        self.assertEqual(analyzer._efficiency_grade(57.0), "D")

    def test_grade_b_range(self):
        """74–87 should yield B."""
        self.assertEqual(analyzer._efficiency_grade(74.0), "B")
        self.assertEqual(analyzer._efficiency_grade(87.9), "B")


class TestROICalculation(unittest.TestCase):
    """Tests for _calc_roi — the developer ROI model."""

    def test_basic_roi_calculation(self):
        """Known inputs should produce consistent, expected outputs."""
        roi = analyzer._calc_roi(
            output_tokens=1_000_000,
            ai_cost_usd=100.0,
            dev_hourly_rate=125.0,
            attribution_rate=0.40,
        )
        # 1M tokens × 4 chars/token = 4M chars
        # 4M chars / 200 chars/min × 0.40 attribution = 8000 min = 133.3 hours
        # 133.3h × $125/hr = $16,667
        # ROI = $16,667 / $100 = 166.7×
        self.assertAlmostEqual(roi["dev_hours_saved"], 133.3, delta=1.0)
        self.assertAlmostEqual(roi["dev_cost_saved"], 16666.67, delta=10.0)
        self.assertAlmostEqual(roi["roi_multiplier"], 166.7, delta=1.0)

    def test_zero_cost_returns_zero_roi(self):
        """Zero AI cost should not cause division by zero."""
        roi = analyzer._calc_roi(output_tokens=1_000_000, ai_cost_usd=0.0)
        self.assertEqual(roi["roi_multiplier"], 0.0)

    def test_zero_output_returns_zero_savings(self):
        """No output tokens means no developer time saved."""
        roi = analyzer._calc_roi(output_tokens=0, ai_cost_usd=50.0)
        self.assertEqual(roi["dev_hours_saved"], 0.0)
        self.assertEqual(roi["dev_cost_saved"], 0.0)

    def test_custom_dev_rate_scales_linearly(self):
        """Doubling the dev rate should double the savings and ROI."""
        roi_125 = analyzer._calc_roi(1_000_000, 100.0, dev_hourly_rate=125.0)
        roi_250 = analyzer._calc_roi(1_000_000, 100.0, dev_hourly_rate=250.0)
        self.assertAlmostEqual(roi_250["dev_cost_saved"],  roi_125["dev_cost_saved"] * 2, delta=1.0)
        self.assertAlmostEqual(roi_250["roi_multiplier"], roi_125["roi_multiplier"] * 2, delta=0.5)

    def test_attribution_rate_stored_in_result(self):
        """Attribution rate used should be returned in the result dict for transparency."""
        roi = analyzer._calc_roi(1_000_000, 100.0, attribution_rate=0.55)
        self.assertEqual(roi["attribution_rate"], 0.55)

    def test_result_keys_present(self):
        """All expected keys must be present in the result."""
        roi = analyzer._calc_roi(500_000, 50.0)
        required_keys = [
            "output_tokens", "dev_hours_saved", "dev_cost_saved",
            "ai_cost", "roi_multiplier", "dev_hourly_rate", "attribution_rate"
        ]
        for key in required_keys:
            self.assertIn(key, roi, f"Missing key: {key}")


class TestCostCalculation(unittest.TestCase):
    """Tests for _calc_cost — per-message cost computation."""

    def test_sonnet_pricing(self):
        """Sonnet input cost at known price should match."""
        # 1M input tokens × $3.00/MTok = $3.00
        cost = scanner._calc_cost("claude-sonnet-4-6", 1_000_000, 0, 0, 0)
        self.assertAlmostEqual(cost, 3.00, places=4)

    def test_opus_output_more_expensive(self):
        """Opus output should cost more than sonnet output per token."""
        opus_cost   = scanner._calc_cost("claude-opus-4-7",   0, 1_000_000, 0, 0)
        sonnet_cost = scanner._calc_cost("claude-sonnet-4-6", 0, 1_000_000, 0, 0)
        self.assertGreater(opus_cost, sonnet_cost)

    def test_cache_read_cheaper_than_input(self):
        """Cache read tokens should cost less than fresh input tokens."""
        fresh_cost = scanner._calc_cost("claude-sonnet-4-6", 1_000_000, 0, 0, 0)
        cache_cost = scanner._calc_cost("claude-sonnet-4-6", 0, 0, 0, 1_000_000)
        self.assertLess(cache_cost, fresh_cost)

    def test_unknown_model_returns_zero(self):
        """Unknown model names should return 0 cost, not crash."""
        cost = scanner._calc_cost("some-future-model-xyz", 1_000_000, 1_000_000, 0, 0)
        self.assertEqual(cost, 0.0)

    def test_all_zeros_returns_zero(self):
        """Zero tokens should always return zero cost."""
        cost = scanner._calc_cost("claude-sonnet-4-6", 0, 0, 0, 0)
        self.assertEqual(cost, 0.0)


class TestDBIntegration(unittest.TestCase):
    """Integration tests against a temporary in-memory-style database."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = Path(self.tmp.name)
        scanner.init_db(self.db_path)

    def tearDown(self):
        self.db_path.unlink(missing_ok=True)

    def test_empty_db_summary_returns_zeros(self):
        """An empty database should return zeroed summary without crashing."""
        s = analyzer.get_summary(db_path=self.db_path)
        self.assertEqual(s["total_cost"], 0.0)
        self.assertEqual(s["total_sessions"], 0)
        self.assertEqual(s["cache_efficiency"], 0.0)

    def test_empty_db_projects_returns_empty_list(self):
        s = analyzer.get_projects(db_path=self.db_path)
        self.assertEqual(s, [])

    def test_empty_db_sessions_returns_empty_list(self):
        s = analyzer.get_sessions(db_path=self.db_path)
        self.assertEqual(s, [])

    def test_prune_on_empty_db_returns_zero_deleted(self):
        result = analyzer.prune_before("2030-01-01", db_path=self.db_path)
        self.assertEqual(result["deleted_sessions"], 0)
        self.assertEqual(result["deleted_messages"], 0)

    def test_prune_invalid_date_returns_error(self):
        result = analyzer.prune_before("not-a-date", db_path=self.db_path)
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
