"""Unit tests for chart application module."""

import pytest
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from csv_chart_plotter.chart_app import (
    create_traces,
    create_figure,
    create_empty_figure,
    create_layout,
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
