"""Unit tests for chart application module."""

import pytest
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dash import no_update

from csv_chart_plotter.chart_app import (
    create_traces,
    create_figure,
    create_empty_figure,
    create_layout,
    _compute_y_range_for_x_viewport,
)


class TestCreateTraces:
    """Tests for create_traces()."""

    def test_create_traces_generates_correct_count(self, numeric_dataframe):
        """Generate one trace per DataFrame column."""
        x_array = np.arange(len(numeric_dataframe), dtype=np.float64)
        x_values = (x_array, x_array)  # (display_x, numeric_x) tuple

        traces = create_traces(numeric_dataframe, x_values, theme="light")

        assert len(traces) == 3  # col1, col2, col3

    def test_traces_use_line_mode(self, numeric_dataframe):
        """All traces use 'lines' mode."""
        x_array = np.arange(len(numeric_dataframe), dtype=np.float64)
        x_values = (x_array, x_array)

        traces = create_traces(numeric_dataframe, x_values, theme="light")

        for trace in traces:
            assert trace.mode == "lines"

    def test_traces_have_connectgaps_false(self, numeric_dataframe):
        """All traces have connectgaps=False for NaN handling."""
        x_array = np.arange(len(numeric_dataframe), dtype=np.float64)
        x_values = (x_array, x_array)

        traces = create_traces(numeric_dataframe, x_values, theme="light")

        for trace in traces:
            assert trace.connectgaps is False

    def test_traces_are_scattergl(self, numeric_dataframe):
        """All traces are ScatterGL for performance."""
        x_array = np.arange(len(numeric_dataframe), dtype=np.float64)
        x_values = (x_array, x_array)

        traces = create_traces(numeric_dataframe, x_values, theme="light")

        for trace in traces:
            assert isinstance(trace, go.Scattergl)

    def test_traces_have_column_names(self, numeric_dataframe):
        """Trace names match DataFrame column names."""
        x_array = np.arange(len(numeric_dataframe), dtype=np.float64)
        x_values = (x_array, x_array)

        traces = create_traces(numeric_dataframe, x_values, theme="light")

        trace_names = [t.name for t in traces]
        assert trace_names == ["col1", "col2", "col3"]


class TestCreateEmptyFigure:
    """Tests for create_empty_figure()."""

    def test_create_empty_figure(self):
        """Create figure with no data and appropriate annotation."""
        fig = create_empty_figure(theme="light")

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0

        # Should have "No data loaded" annotation
        annotations = fig.layout.annotations
        assert len(annotations) == 1
        assert "No data" in annotations[0].text

    def test_empty_figure_respects_theme(self):
        """Empty figure applies theme colors."""
        fig_light = create_empty_figure(theme="light")
        fig_dark = create_empty_figure(theme="dark")

        assert fig_light.layout.paper_bgcolor == "#ffffff"
        assert fig_dark.layout.paper_bgcolor == "#1a1a1a"


class TestCreateFigure:
    """Tests for create_figure()."""

    def test_create_figure_with_data(self, numeric_dataframe):
        """Create complete figure with data and layout."""
        x_array = np.arange(len(numeric_dataframe), dtype=np.float64)
        x_values = (x_array, x_array)

        fig = create_figure(numeric_dataframe, x_values, theme="light")

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 3  # Three traces

    def test_create_figure_theme_colors(self, numeric_dataframe):
        """Figure layout reflects theme setting."""
        x_array = np.arange(len(numeric_dataframe), dtype=np.float64)
        x_values = (x_array, x_array)

        fig = create_figure(numeric_dataframe, x_values, theme="dark")

        assert fig.layout.paper_bgcolor == "#1a1a1a"
        assert fig.layout.plot_bgcolor == "#1a1a1a"


class TestCreateLayout:
    """Tests for create_layout()."""

    def test_create_layout_light_theme(self):
        """Light theme has white background."""
        layout = create_layout(theme="light")

        assert layout.paper_bgcolor == "#ffffff"
        assert layout.plot_bgcolor == "#ffffff"

    def test_create_layout_dark_theme(self):
        """Dark theme has dark background."""
        layout = create_layout(theme="dark")

        assert layout.paper_bgcolor == "#1a1a1a"
        assert layout.plot_bgcolor == "#1a1a1a"

    def test_layout_has_legend_config(self):
        """Layout includes legend configuration."""
        layout = create_layout(theme="light")

        assert layout.legend is not None
        assert layout.legend.orientation == "v"

    def test_layout_has_yaxis_fixedrange(self):
        """Y-axis has fixedrange=True for X-only zoom behavior."""
        layout = create_layout(theme="light")

        assert layout.yaxis.fixedrange is True


class TestComputeYRangeForXViewport:
    """Tests for _compute_y_range_for_x_viewport()."""

    def test_computes_y_range_from_visible_data(self):
        """Compute Y range from data within visible X range."""
        # Create DataFrame with datetime index
        dates = pd.date_range("2025-01-01", periods=10, freq="h")
        df = pd.DataFrame(
            {"value": [1, 2, 10, 4, 5, 6, 7, 8, 9, 100]},
            index=dates,
        )

        # Current figure with layout
        current_figure = {
            "layout": {"yaxis": {"autorange": True}},
            "data": [],
        }

        # Zoom to middle portion (rows 2-5 with values 10, 4, 5, 6)
        relayout_data = {
            "xaxis.range[0]": dates[2].isoformat(),
            "xaxis.range[1]": dates[5].isoformat(),
        }

        result = _compute_y_range_for_x_viewport(current_figure, relayout_data, df)

        assert result != no_update
        assert "layout" in result
        y_range = result["layout"]["yaxis"]["range"]
        # Y range should be based on values 10, 4, 5, 6 (min=4, max=10) with padding
        assert y_range[0] < 4  # Lower bound with padding
        assert y_range[1] > 10  # Upper bound with padding

    def test_returns_no_update_when_no_df(self):
        """Return no_update when DataFrame is None."""
        result = _compute_y_range_for_x_viewport({}, {}, None)
        assert result == no_update

    def test_returns_no_update_when_missing_x_range(self):
        """Return no_update when relayout_data lacks X range."""
        df = pd.DataFrame({"value": [1, 2, 3]})
        result = _compute_y_range_for_x_viewport({}, {"autosize": True}, df)
        assert result == no_update

    def test_handles_xaxis_range_list_format(self):
        """Handle alternative xaxis.range list format."""
        dates = pd.date_range("2025-01-01", periods=5, freq="h")
        df = pd.DataFrame({"value": [1, 5, 3, 7, 2]}, index=dates)

        current_figure = {"layout": {"yaxis": {}}, "data": []}
        relayout_data = {
            "xaxis.range": [dates[1].isoformat(), dates[3].isoformat()],
        }

        result = _compute_y_range_for_x_viewport(current_figure, relayout_data, df)

        assert result != no_update
        y_range = result["layout"]["yaxis"]["range"]
        # Values in range: 5, 3, 7 (min=3, max=7)
        assert y_range[0] < 3
        assert y_range[1] > 7

    def test_handles_numeric_index(self):
        """Handle DataFrames with numeric (non-datetime) index."""
        df = pd.DataFrame(
            {"value": [10, 20, 30, 40, 50]},
            index=[0, 1, 2, 3, 4],  # Numeric index
        )

        current_figure = {"layout": {"yaxis": {}}, "data": []}
        relayout_data = {
            "xaxis.range[0]": "1",
            "xaxis.range[1]": "3",
        }

        result = _compute_y_range_for_x_viewport(current_figure, relayout_data, df)

        assert result != no_update
        y_range = result["layout"]["yaxis"]["range"]
        # Values in range [1, 3]: 20, 30, 40 (min=20, max=40)
        assert y_range[0] < 20
        assert y_range[1] > 40
