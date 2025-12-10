"""
Chart Application - Dash-based interactive time-series visualization.

Creates a ScatterGL chart with LTTB downsampling for efficient rendering
of arbitrarily large datasets.
"""

from pathlib import Path
from typing import Any, Optional
import logging

import dash
from dash import dcc, html, Input, Output, State, no_update
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from .lttb import lttb_downsample, compute_lttb_indices, DEFAULT_MINMAX_RATIO
from .palettes import get_trace_color, LIGHT_PALETTE, DARK_PALETTE

logger = logging.getLogger(__name__)

MAX_DISPLAY_POINTS = 4000
MINMAX_RATIO = DEFAULT_MINMAX_RATIO  # MinMaxLTTB preselection ratio
FOLLOW_INTERVAL_MS = 5000
TAIL_THRESHOLD_RATIO = 0.05
TAIL_THRESHOLD_MAX = 100_000


def create_app(
    df: Optional[pd.DataFrame] = None,
    csv_filename: Optional[str] = None,
    csv_filepath: Optional[str] = None,
    theme: str = "light",
    follow_mode: bool = False,
    indexer: Any = None,
) -> dash.Dash:
    """
    Create the Dash application.

    Args:
        df: DataFrame with numeric columns (None for empty state).
        csv_filename: Name of the CSV file (for display).
        csv_filepath: Full path to CSV file (for follow mode reloading).
        theme: Initial theme ('light' or 'dark').
        follow_mode: Whether follow mode is available.
        indexer: CSVIndexer instance (for follow mode data refresh).

    Returns:
        Configured Dash application.
    """
    # Determine assets folder location
    assets_folder = Path(__file__).parent / "assets"

    app = dash.Dash(
        __name__,
        assets_folder=str(assets_folder),
        title=f"CSV Chart Plotter - {csv_filename}" if csv_filename else "CSV Chart Plotter",
        update_title=None,
    )

    # Store references for callbacks
    app._csv_indexer = indexer
    app._csv_filepath = csv_filepath
    app._pywebview_window = None  # Set by main.py after window creation

    # Build initial figure
    if df is not None and not df.empty:
        x_values = _get_x_values(df)
        figure = create_figure(df, x_values, theme)
        latest_timestamp = _format_timestamp(df.index[-1])
        has_data = True
    else:
        figure = create_empty_figure(theme)
        latest_timestamp = "No data"
        has_data = False

    # Determine theme colors for initial styling
    bg_color = "#1a1a1a" if theme == "dark" else "#ffffff"
    
    # Build layout
    app.layout = html.Div(
        id="app-container",
        className="app-container",
        style={"backgroundColor": bg_color},
        **{"data-theme": theme},  # Set initial theme for CSS variables
        children=[
            # Stores for state management
            dcc.Store(id="theme-store", data=theme),
            dcc.Store(id="dragmode-store", data="zoom"),  # Default to box-zoom
            dcc.Store(id="follow-active-store", data=follow_mode),
            dcc.Store(id="legend-state-store", data={}),
            dcc.Store(id="viewport-store", data={}),
            dcc.Store(id="last-render-time-store", data=0),
            dcc.Store(id="selected-file-store", data=None),  # For file dialog result

            # Control bar
            html.Div(
                className="control-bar",
                children=[
                    html.Button(
                        "Load CSV...",
                        id="load-csv-btn",
                        className="btn",
                    ),
                    html.Button(
                        "Reload",
                        id="reload-btn",
                        className="btn",
                        disabled=not has_data,
                    ),
                    html.Span("Theme:", className="control-label"),
                    dcc.Dropdown(
                        id="theme-dropdown",
                        options=[
                            {"label": "Light", "value": "light"},
                            {"label": "Dark", "value": "dark"},
                        ],
                        value=theme,
                        clearable=False,
                        className="theme-dropdown",
                    ),
                    html.Span("Drag:", className="control-label"),
                    dcc.Dropdown(
                        id="dragmode-dropdown",
                        options=[
                            {"label": "Zoom", "value": "zoom"},
                            {"label": "Pan", "value": "pan"},
                        ],
                        value="zoom",
                        clearable=False,
                        className="dragmode-dropdown",
                    ),
                    # Follow mode controls (visible when file is loaded)
                    html.Div(
                        id="follow-controls",
                        className="follow-controls",
                        style={"display": "flex" if has_data else "none"},
                        children=[
                            dcc.Checklist(
                                id="follow-checkbox",
                                options=[{"label": " Follow Mode", "value": "follow"}],
                                value=["follow"] if follow_mode else [],
                                className="checkbox-label",
                            ),
                        ],
                    ),
                    # Status text (always visible, right-aligned)
                    html.Span(
                        id="status-text",
                        className="status-text",
                        children=f"Latest: {latest_timestamp}",
                    ),
                ],
            ),

            # Chart container
            html.Div(
                id="chart-container",
                className="chart-container",
                children=[
                    dcc.Graph(
                        id="main-chart",
                        figure=figure,
                        config={
                            "displayModeBar": True,
                            "modeBarButtonsToRemove": ["select2d", "lasso2d"],
                            "displaylogo": False,
                            "scrollZoom": True,
                        },
                        style={"height": "100%"},
                    ),
                ]
                if has_data
                else [
                    html.Div(
                        className="empty-state",
                        children=[
                            html.P("No file loaded"),
                            html.P(
                                "Click 'Load CSV...' to open a file",
                                style={"fontSize": "var(--font-sm)"},
                            ),
                        ],
                    ),
                ],
            ),

            # Follow mode interval (disabled/enabled via checkbox callback)
            dcc.Interval(
                id="follow-interval",
                interval=FOLLOW_INTERVAL_MS,
                disabled=True,  # Initially disabled; controlled by checkbox callback
            ),
        ],
    )

    # -------------------------------------------------------------------------
    # Callbacks
    # -------------------------------------------------------------------------

    @app.callback(
        Output("app-container", "data-theme"),
        Output("app-container", "style"),
        Output("main-chart", "figure", allow_duplicate=True),
        Input("theme-dropdown", "value"),
        State("main-chart", "figure"),
        prevent_initial_call=True,
    )
    def update_theme(new_theme: str, current_figure: dict) -> tuple[str, dict, dict]:
        """Update theme across the application."""
        # Update background color based on theme
        bg_color = "#1a1a1a" if new_theme == "dark" else "#ffffff"
        style = {"backgroundColor": bg_color}
        
        if current_figure is None:
            return new_theme, style, no_update

        # Update figure colors for new theme
        updated_figure = _update_figure_theme(current_figure, new_theme)
        return new_theme, style, updated_figure

    @app.callback(
        Output("main-chart", "figure", allow_duplicate=True),
        Input("dragmode-dropdown", "value"),
        State("main-chart", "figure"),
        prevent_initial_call=True,
    )
    def update_dragmode(new_dragmode: str, current_figure: dict) -> dict:
        """Update chart drag interaction mode (zoom or pan)."""
        if current_figure is None:
            return no_update
        
        updated_figure = dict(current_figure)
        if "layout" in updated_figure:
            layout = dict(updated_figure["layout"])
            layout["dragmode"] = new_dragmode
            updated_figure["layout"] = layout
        
        return updated_figure

    @app.callback(
        Output("main-chart", "figure", allow_duplicate=True),
        Output("status-text", "children", allow_duplicate=True),
        Output("last-render-time-store", "data", allow_duplicate=True),
        Input("follow-interval", "n_intervals"),
        State("follow-checkbox", "value"),
        State("theme-dropdown", "value"),
        State("main-chart", "figure"),
        State("last-render-time-store", "data"),
        prevent_initial_call=True,
    )
    def follow_mode_update(
        n_intervals: int,
        follow_value: list,
        current_theme: str,
        current_figure: dict,
        last_render_time: float,
    ) -> tuple:
        """Handle follow mode data refresh."""
        import time

        # Skip if follow mode not active
        if not follow_value or "follow" not in follow_value:
            return no_update, no_update, no_update

        # Skip if no indexer
        if app._csv_indexer is None:
            return no_update, no_update, no_update

        # Debounce check
        current_time = time.time()
        if current_time - last_render_time < (FOLLOW_INTERVAL_MS / 1000):
            return no_update, no_update, no_update

        try:
            # Check for new data
            new_rows = app._csv_indexer.update_index()

            if new_rows == 0:
                logger.debug("Follow mode: no new rows")
                return no_update, no_update, current_time

            logger.info("Follow mode: %d new rows detected", new_rows)

            # Re-read data and rebuild figure
            from .column_filter import filter_numeric_columns

            index = app._csv_indexer.index
            df = app._csv_indexer.read_range(0, index.row_count)
            df_numeric = filter_numeric_columns(df)

            x_values = _get_x_values(df_numeric)
            new_figure = create_figure(df_numeric, x_values, current_theme)

            # Preserve legend visibility state from current figure
            if current_figure and "data" in current_figure:
                _preserve_legend_state(current_figure, new_figure)

            latest_timestamp = _format_timestamp(df_numeric.index[-1])
            status = f"Latest: {latest_timestamp}"

            return new_figure, status, current_time

        except Exception as e:
            logger.error("Follow mode update failed: %s", e)
            return no_update, no_update, no_update

    @app.callback(
        Output("main-chart", "figure", allow_duplicate=True),
        Output("status-text", "children", allow_duplicate=True),
        Output("reload-btn", "disabled", allow_duplicate=True),
        Input("reload-btn", "n_clicks"),
        State("theme-dropdown", "value"),
        State("main-chart", "figure"),
        prevent_initial_call=True,
    )
    def reload_data(
        n_clicks: int,
        current_theme: str,
        current_figure: dict,
    ) -> tuple:
        """Handle manual reload button click."""
        if n_clicks is None or app._csv_indexer is None:
            return no_update, no_update, no_update

        try:
            logger.info("Manual reload triggered")

            # Rebuild index from scratch
            from .column_filter import filter_numeric_columns

            app._csv_indexer.index = None
            index = app._csv_indexer.build_index()

            df = app._csv_indexer.read_range(0, index.row_count)
            df_numeric = filter_numeric_columns(df)

            x_values = _get_x_values(df_numeric)
            new_figure = create_figure(df_numeric, x_values, current_theme)

            # Preserve legend visibility
            if current_figure and "data" in current_figure:
                _preserve_legend_state(current_figure, new_figure)

            latest_timestamp = _format_timestamp(df_numeric.index[-1])
            status = f"Reloaded {index.row_count} rows | Latest: {latest_timestamp}"

            return new_figure, status, False

        except FileNotFoundError:
            logger.warning("File no longer exists")
            return no_update, "Error: File not found", True

        except Exception as e:
            logger.error("Reload failed: %s", e)
            return no_update, f"Error: {e}", no_update

    @app.callback(
        Output("follow-checkbox", "value"),
        Output("status-text", "children", allow_duplicate=True),
        Output("main-chart", "figure", allow_duplicate=True),
        Input("main-chart", "relayoutData"),
        State("follow-checkbox", "value"),
        State("status-text", "children"),
        State("main-chart", "figure"),
        prevent_initial_call=True,
    )
    def handle_viewport_change(
        relayout_data: dict,
        follow_value: list,
        current_status: str,
        current_figure: dict,
    ) -> tuple:
        """
        Handle viewport changes (zoom/pan).

        For time-series, X-axis zoom should auto-scale Y to fit visible data.
        This callback resets Y-axis to autorange when X changes.
        Auto-unchecks follow mode when user pans away from tail.
        """
        if relayout_data is None:
            return no_update, no_update, no_update

        # Check if X-axis range changed (zoom or pan)
        x_range_changed = any(
            key.startswith("xaxis.range") for key in relayout_data.keys()
        )

        # Check if this is a reset (autorange or double-click)
        is_reset = (
            relayout_data.get("xaxis.autorange") is True
            or relayout_data.get("autosize") is True
        )

        # Handle Y-axis auto-scaling on X zoom
        figure_update = no_update
        if x_range_changed and current_figure and not is_reset:
            # User zoomed X-axis - reset Y to autorange
            # This ensures Y always fits the visible X range
            updated_figure = dict(current_figure)
            if "layout" in updated_figure:
                layout = dict(updated_figure["layout"])
                yaxis = dict(layout.get("yaxis", {}))
                yaxis["autorange"] = True
                # Remove any explicit range to trigger autorange
                yaxis.pop("range", None)
                layout["yaxis"] = yaxis
                updated_figure["layout"] = layout
                figure_update = updated_figure

        # Handle follow mode auto-pause when user navigates away from tail
        status_update = no_update
        checkbox_update = no_update
        if x_range_changed and app._csv_indexer is not None:
            if follow_value and "follow" in follow_value:
                # User was in follow mode but panned/zoomed - auto-disable follow mode
                checkbox_update = []  # Uncheck the checkbox
                if "Latest:" in current_status:
                    status_update = current_status.replace("Latest:", "Paused | Latest:")

        return checkbox_update, status_update, figure_update

    @app.callback(
        Output("follow-interval", "disabled"),
        Output("status-text", "children", allow_duplicate=True),
        Input("follow-checkbox", "value"),
        State("status-text", "children"),
        prevent_initial_call=True,
    )
    def toggle_follow_interval(
        follow_value: list,
        current_status: str,
    ) -> tuple:
        """
        Enable/disable the follow interval based on checkbox state.
        """
        is_following = follow_value and "follow" in follow_value
        
        # Update status text to reflect follow mode state
        if current_status and "Paused |" in current_status and is_following:
            # User re-enabled follow mode - remove "Paused" prefix
            new_status = current_status.replace("Paused | ", "")
        else:
            new_status = no_update
        
        # Enable interval when following, disable when not
        return not is_following, new_status

    @app.callback(
        Output("main-chart", "figure", allow_duplicate=True),
        Output("status-text", "children", allow_duplicate=True),
        Output("reload-btn", "disabled", allow_duplicate=True),
        Output("follow-controls", "style", allow_duplicate=True),
        Output("follow-checkbox", "value", allow_duplicate=True),
        Input("load-csv-btn", "n_clicks"),
        State("theme-dropdown", "value"),
        prevent_initial_call=True,
    )
    def handle_load_csv(
        n_clicks: int,
        current_theme: str,
    ) -> tuple:
        """
        Handle Load CSV button click.

        Opens native file dialog via pywebview API, loads selected file.
        Resets follow mode to disabled state.
        """
        if n_clicks is None:
            return no_update, no_update, no_update, no_update, no_update

        # Access pywebview window via app reference
        window = getattr(app, "_pywebview_window", None)
        if window is None:
            logger.warning("No pywebview window available for file dialog")
            return no_update, "Error: File dialog unavailable", no_update, no_update

        try:
            import webview

            # Open file dialog (must use evaluate_js or direct call)
            result = window.create_file_dialog(
                webview.OPEN_DIALOG,
                file_types=("CSV files (*.csv)",),
            )

            if not result or len(result) == 0:
                logger.debug("File dialog cancelled")
                return no_update, no_update, no_update, no_update, no_update

            selected_path = result[0]
            logger.info("Loading file from dialog: %s", selected_path)

            # Import dependencies for loading
            from pathlib import Path
            from .csv_indexer import CSVIndexer
            from .column_filter import filter_numeric_columns

            # Build index and load data
            csv_path = Path(selected_path)
            indexer = CSVIndexer(csv_path)
            index = indexer.build_index()

            df = indexer.read_range(0, index.row_count)
            df_numeric = filter_numeric_columns(df)

            # Update app state
            app._csv_indexer = indexer

            # Create figure
            x_values = _get_x_values(df_numeric)
            new_figure = create_figure(df_numeric, x_values, current_theme)

            # Update window title if possible
            try:
                window.set_title(f"CSV Chart Plotter - {csv_path.name}")
            except Exception:
                pass  # Ignore title update failures

            latest_timestamp = _format_timestamp(df_numeric.index[-1])
            status = f"Loaded {index.row_count} rows from {csv_path.name} | Latest: {latest_timestamp}"

            logger.info(
                "Loaded %d rows, %d columns from %s",
                index.row_count,
                len(df_numeric.columns),
                csv_path.name,
            )

            # Enable reload button, show follow controls, reset follow mode to disabled
            return new_figure, status, False, {"display": "flex"}, []

        except FileNotFoundError as e:
            logger.error("File not found: %s", e)
            return no_update, f"Error: File not found - {e}", no_update, no_update, no_update

        except ValueError as e:
            logger.error("Data error: %s", e)
            return no_update, f"Error: {e}", no_update, no_update, no_update

        except Exception as e:
            logger.exception("Load failed: %s", e)
            return no_update, f"Error: {e}", no_update, no_update, no_update

    return app


def create_figure(
    df: pd.DataFrame,
    x_values: np.ndarray,
    theme: str = "light",
) -> go.Figure:
    """
    Create a complete figure with all traces.

    Args:
        df: DataFrame with numeric columns.
        x_values: X-axis values (index values).
        theme: Color theme.

    Returns:
        Plotly Figure object.
    """
    traces = create_traces(df, x_values, theme)
    layout = create_layout(theme)

    fig = go.Figure(data=traces, layout=layout)
    return fig


def create_traces(
    df: pd.DataFrame,
    x_values: tuple[np.ndarray, np.ndarray],
    theme: str = "light",
) -> list[go.Scattergl]:
    """
    Create ScatterGL traces for all numeric columns.

    Applies LTTB downsampling if data exceeds MAX_DISPLAY_POINTS.

    Args:
        df: DataFrame with numeric columns only.
        x_values: Tuple of (display_x, numeric_x) from _get_x_values().
        theme: Color theme for palette selection.

    Returns:
        List of ScatterGL trace objects.
    """
    traces = []
    display_x, numeric_x = x_values

    for i, col in enumerate(df.columns):
        y_values = df[col].to_numpy()

        # Apply MinMaxLTTB downsampling if needed
        if len(numeric_x) > MAX_DISPLAY_POINTS:
            # Use numeric values for downsampling calculation
            indices = compute_lttb_indices(numeric_x, y_values, MAX_DISPLAY_POINTS, MINMAX_RATIO)
            x_plot = display_x[indices]
            y_plot = y_values[indices]
        else:
            x_plot, y_plot = display_x, y_values

        trace = go.Scattergl(
            x=x_plot,
            y=y_plot,
            mode="lines",
            name=col,
            connectgaps=False,
            line=dict(color=get_trace_color(i, theme)),
            hovertemplate="%{y:.2f}<extra>%{fullData.name}</extra>",
        )
        traces.append(trace)

    logger.debug("Created %d traces with up to %d points each", len(traces), MAX_DISPLAY_POINTS)
    return traces


def create_layout(theme: str = "light") -> go.Layout:
    """
    Create chart layout with theme-appropriate colors.

    Args:
        theme: Color theme ('light' or 'dark').

    Returns:
        Plotly Layout object.
    """
    if theme == "dark":
        bg_color = "#1a1a1a"
        grid_color = "#3a3a3a"
        text_color = "#e8e8e8"
    else:
        bg_color = "#ffffff"
        grid_color = "#e0e0e0"
        text_color = "#1a1a1a"

    return go.Layout(
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        font=dict(color=text_color, family="Roboto, Helvetica, Arial, sans-serif"),
        margin=dict(l=60, r=200, t=60, b=60),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
        ),
        xaxis=dict(
            gridcolor=grid_color,
            linecolor=grid_color,
            zerolinecolor=grid_color,
            type="date",  # Display as datetime
        ),
        yaxis=dict(
            gridcolor=grid_color,
            linecolor=grid_color,
            zerolinecolor=grid_color,
            autorange=True,  # Auto-scale Y axis
        ),
        hovermode="x unified",
        dragmode="zoom",  # Drag to zoom (not pan)
    )


def create_empty_figure(theme: str = "light") -> go.Figure:
    """
    Create an empty figure for the initial/no-data state.

    Args:
        theme: Color theme.

    Returns:
        Empty Plotly Figure with styled layout.
    """
    layout = create_layout(theme)
    layout.annotations = [
        dict(
            text="No data loaded",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16),
        )
    ]
    return go.Figure(data=[], layout=layout)


def _get_x_values(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """
    Extract x-axis values from DataFrame index.

    Returns both display values (datetime) and numeric values (for LTTB).

    Args:
        df: DataFrame with index.

    Returns:
        Tuple of (display_x, numeric_x) arrays.
        display_x: Original values for chart display.
        numeric_x: Numeric values for LTTB downsampling.
    """
    if hasattr(df.index, "to_numpy"):
        display_x = df.index.to_numpy()
    else:
        display_x = np.array(df.index)

    # Convert datetime to numeric for LTTB algorithm
    if np.issubdtype(display_x.dtype, np.datetime64):
        numeric_x = display_x.astype("int64")
    else:
        numeric_x = display_x.copy()

    return display_x, numeric_x


def _format_timestamp(value: Any) -> str:
    """
    Format a timestamp value for display.

    Args:
        value: Index value (datetime or other).

    Returns:
        Formatted string.
    """
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def _update_figure_theme(figure_dict: dict, theme: str) -> dict:
    """
    Update figure colors for a new theme.

    Args:
        figure_dict: Current figure as dictionary.
        theme: New theme ('light' or 'dark').

    Returns:
        Updated figure dictionary.
    """
    if theme == "dark":
        bg_color = "#1a1a1a"
        grid_color = "#3a3a3a"
        text_color = "#e8e8e8"
    else:
        bg_color = "#ffffff"
        grid_color = "#e0e0e0"
        text_color = "#1a1a1a"

    # Update layout
    layout = figure_dict.get("layout", {})
    layout["paper_bgcolor"] = bg_color
    layout["plot_bgcolor"] = bg_color
    layout["font"] = {"color": text_color, "family": "Roboto, Helvetica, Arial, sans-serif"}

    # Update axis colors
    for axis in ["xaxis", "yaxis"]:
        if axis in layout:
            layout[axis]["gridcolor"] = grid_color
            layout[axis]["linecolor"] = grid_color
            layout[axis]["zerolinecolor"] = grid_color

    # Update trace colors
    palette = DARK_PALETTE if theme == "dark" else LIGHT_PALETTE
    for i, trace in enumerate(figure_dict.get("data", [])):
        if "line" in trace:
            trace["line"]["color"] = palette[i % len(palette)]

    return figure_dict


def _preserve_legend_state(old_figure: dict, new_figure: go.Figure) -> None:
    """
    Preserve legend visibility state from old figure to new figure.

    Args:
        old_figure: Previous figure as dictionary.
        new_figure: New Figure object to update.
    """
    old_traces = old_figure.get("data", [])
    visibility_map = {}

    for trace in old_traces:
        name = trace.get("name")
        visible = trace.get("visible", True)
        if name:
            visibility_map[name] = visible

    for trace in new_figure.data:
        if trace.name in visibility_map:
            trace.visible = visibility_map[trace.name]
