"""Unit tests for LTTB downsampling module."""

import pytest
import numpy as np

from csv_chart_plotter.lttb import lttb_downsample, downsample_dataframe


class TestLttbDownsample:
    """Tests for lttb_downsample()."""

    def test_lttb_below_threshold_unchanged(self):
        """Return original arrays when length <= threshold."""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([10.0, 20.0, 30.0, 40.0, 50.0])

        result_x, result_y = lttb_downsample(x, y, threshold=10)

        np.testing.assert_array_equal(result_x, x)
        np.testing.assert_array_equal(result_y, y)

    def test_lttb_basic_downsampling(self, large_numeric_arrays):
        """Downsample large array to specified threshold."""
        x, y = large_numeric_arrays
        threshold = 100

        result_x, result_y = lttb_downsample(x, y, threshold=threshold)

        assert len(result_x) == threshold
        assert len(result_y) == threshold
        # First and last points always preserved
        assert result_x[0] == x[0]
        assert result_x[-1] == x[-1]

    def test_lttb_empty_array(self):
        """Return empty arrays for empty input."""
        x = np.array([])
        y = np.array([])

        result_x, result_y = lttb_downsample(x, y, threshold=10)

        assert len(result_x) == 0
        assert len(result_y) == 0

    def test_lttb_threshold_too_small_raises(self):
        """Raise ValueError when threshold < 2."""
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([10.0, 20.0, 30.0])

        with pytest.raises(ValueError, match="threshold must be >= 2"):
            lttb_downsample(x, y, threshold=1)

    def test_lttb_handles_nan_values(self):
        """Handle NaN values in y-array without crashing."""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        y = np.array([1.0, np.nan, 3.0, 4.0, np.nan, 6.0, 7.0, 8.0, 9.0, 10.0])

        # Should not raise
        result_x, result_y = lttb_downsample(x, y, threshold=5)

        assert len(result_x) == 5
        assert len(result_y) == 5

    def test_lttb_preserves_endpoints(self):
        """First and last points always included in output."""
        x = np.arange(100, dtype=np.float64)
        y = np.random.random(100)

        result_x, result_y = lttb_downsample(x, y, threshold=10)

        assert result_x[0] == 0.0
        assert result_x[-1] == 99.0
        assert result_y[0] == y[0]
        assert result_y[-1] == y[-1]


class TestDownsampleDataframe:
    """Tests for downsample_dataframe()."""

    def test_downsample_dataframe_basic(self, numeric_dataframe):
        """Downsample DataFrame with multiple columns."""
        import pandas as pd

        # Create larger DataFrame for meaningful downsampling
        n = 1000
        df = pd.DataFrame({
            "col1": np.random.random(n),
            "col2": np.random.random(n),
        })
        x_values = np.arange(n, dtype=np.float64)

        result_x, result_df = downsample_dataframe(df, x_values, threshold=100)

        assert len(result_x) == 100
        assert len(result_df) == 100
        assert list(result_df.columns) == ["col1", "col2"]

    def test_downsample_dataframe_below_threshold(self, numeric_dataframe):
        """Return unchanged when below threshold."""
        x_values = np.arange(len(numeric_dataframe), dtype=np.float64)

        result_x, result_df = downsample_dataframe(
            numeric_dataframe, x_values, threshold=100
        )

        assert len(result_x) == len(numeric_dataframe)
        assert len(result_df) == len(numeric_dataframe)

    def test_downsample_dataframe_length_mismatch_raises(self, numeric_dataframe):
        """Raise ValueError when x_values length mismatches DataFrame."""
        x_values = np.arange(100, dtype=np.float64)  # Wrong length

        with pytest.raises(ValueError, match="length.*must match"):
            downsample_dataframe(numeric_dataframe, x_values, threshold=10)
