"""Unit tests for column filter module."""

import pytest
import pandas as pd
import numpy as np

from csv_chart_plotter.column_filter import (
    filter_numeric_columns,
    calculate_nan_ratio,
    validate_data_quality,
)


class TestFilterNumericColumns:
    """Tests for filter_numeric_columns()."""

    def test_filter_numeric_columns_mixed(self, mixed_dataframe):
        """Filter retains only numeric columns from mixed DataFrame."""
        result = filter_numeric_columns(mixed_dataframe)

        assert "numeric1" in result.columns
        assert "numeric2" in result.columns
        assert "string_col" not in result.columns
        assert "date_col" not in result.columns
        assert len(result.columns) == 2

    def test_filter_all_numeric_retained(self, numeric_dataframe):
        """All columns retained when DataFrame is entirely numeric."""
        result = filter_numeric_columns(numeric_dataframe)

        assert list(result.columns) == ["col1", "col2", "col3"]
        assert len(result) == 5

    def test_filter_no_numeric_raises(self):
        """Raise ValueError when no numeric columns remain."""
        df = pd.DataFrame({
            "string1": ["a", "b", "c"],
            "string2": ["x", "y", "z"],
        })

        with pytest.raises(ValueError, match="No numeric columns"):
            filter_numeric_columns(df)

    def test_filter_drops_all_nan_columns(self, dataframe_with_nans):
        """All-NaN columns are dropped even if numeric dtype."""
        result = filter_numeric_columns(dataframe_with_nans)

        assert "all_nan" not in result.columns
        assert "no_nan" in result.columns
        assert "some_nan" in result.columns

    def test_filter_empty_dataframe_raises(self):
        """Raise ValueError for empty DataFrame."""
        df = pd.DataFrame()

        with pytest.raises(ValueError, match="No numeric columns"):
            filter_numeric_columns(df)


class TestCalculateNanRatio:
    """Tests for calculate_nan_ratio()."""

    def test_nan_ratio_calculation(self):
        """Calculate correct NaN ratio for various patterns."""
        # No NaN
        series_clean = pd.Series([1.0, 2.0, 3.0, 4.0])
        assert calculate_nan_ratio(series_clean) == 0.0

        # 50% NaN
        series_half = pd.Series([1.0, np.nan, 3.0, np.nan])
        assert calculate_nan_ratio(series_half) == 0.5

        # All NaN
        series_all_nan = pd.Series([np.nan, np.nan, np.nan])
        assert calculate_nan_ratio(series_all_nan) == 1.0

    def test_nan_ratio_empty_series(self):
        """Return 0.0 for empty series."""
        empty_series = pd.Series([], dtype=float)
        assert calculate_nan_ratio(empty_series) == 0.0


class TestValidateDataQuality:
    """Tests for validate_data_quality()."""

    def test_validate_data_quality_returns_ratios(self, dataframe_with_nans):
        """Return dictionary of NaN ratios per column."""
        ratios = validate_data_quality(dataframe_with_nans)

        assert isinstance(ratios, dict)
        assert ratios["no_nan"] == 0.0
        assert ratios["some_nan"] == 0.5
        assert ratios["all_nan"] == 1.0
        assert ratios["high_nan"] == 0.75

    def test_validate_data_quality_logs_high_nan(self, dataframe_with_nans, caplog):
        """Log INFO for columns with >50% NaN."""
        import logging

        with caplog.at_level(logging.INFO):
            validate_data_quality(dataframe_with_nans)

        # Should log warnings for high_nan (75%) and all_nan (100%)
        log_text = caplog.text
        assert "high_nan" in log_text or "all_nan" in log_text
