# Project Context

## Project Overview

CSV Chart Plotter is an interactive time-series visualizer for CSV datasets of any size. It uses a streaming/indexed architecture to handle arbitrarily large files without loading them entirely into memory. The application embeds a Dash web app inside a native desktop window via pywebview, providing GPU-accelerated WebGL rendering through Plotly's ScatterGL.

**Core Purpose:** Load numeric time-series CSV data and render interactive line charts with pan/zoom/legend controls. Optionally tail-follow growing log files.

**Technology Stack:**

- Python 3.13+
- Dash (web framework)
- Plotly (ScatterGL for GPU rendering)
- pywebview (native window wrapper)
- pandas (CSV parsing, data manipulation)
- numpy (array operations)
- tsdownsample (MinMaxLTTB downsampling algorithm)
- watchdog (filesystem monitoring for follow mode)

**Key Architectural Principle:** Memory consumption is bounded by display requirements (~1MB for 4,000 points × N columns), not source data size. A 10GB CSV uses the same memory as a 10KB CSV because we stream from disk and downsample to exactly 4,000 points per trace via MinMaxLTTB (two-phase min-max preselection + LTTB refinement, 10-30× faster than pure LTTB).

## Architecture

### Module Structure

```
src/csv_chart_plotter/
├── main.py              # CLI entry, Flask server lifecycle, pywebview window
├── csv_indexer.py       # Streaming CSV with byte-offset index for random access
├── column_filter.py     # Numeric column detection, NaN analysis, quality logging
├── lttb.py              # LTTB downsampling algorithm (4,000 points max)
├── chart_app.py         # Dash app, ScatterGL traces, callbacks, layout
├── csv_monitor.py       # Watchdog-based file change detection for follow mode
├── palettes.py          # Light/dark theme color definitions (colorblind-safe)
├── logging_config.py    # Logging setup
└── assets/
    └── styles.css       # UI styling with CSS variables for theming
```

### Data Flow (Streaming Model)

```text
CLI Argument → Validate File → Build Row Index (byte offsets)
                                       ↓
                        Sample rows for type detection
                                       ↓
                        Numeric Column Filtering (headers only)
                                       ↓
          ┌────────────────────────────┴────────────────────────────┐
          │              Viewport Request                            │
          │   (initial: full range; zoom/pan: user bounds)           │
          └────────────────────────────┬────────────────────────────┘
                                       ↓
                        Read indexed row range from disk
                                       ↓
                        MinMaxLTTB Downsample to ≤4,000 points
                                       ↓
                        ScatterGL Trace Construction
                                       ↓
                        Dash Layout Assembly
                                       ↓
    ┌──────────────────────────────────┴──────────────────────────────┐
    │                                                                  │
    ↓                                                                  ↓
Flask (background thread)                               pywebview Window (main thread)
    │                                                                  │
    └────────────────── HTTP localhost ─────────────────────────────→ │
```

**Threading Model:**

- Flask server runs in daemon background thread
- pywebview window blocks on main thread until closed
- Watchdog observer (follow mode) runs in background thread
- Dash callbacks execute in Flask request threads

### Component Responsibilities

| Module              | Purpose                                                                                                                                                                |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `main.py`           | CLI parsing, file validation, port discovery, Flask background thread startup, pywebview window creation (blocking), graceful exit                                     |
| `csv_indexer.py`    | Build byte-offset index for rows; provide `read_range(start_row, end_row)` API; support incremental index updates for appended data                                    |
| `column_filter.py`  | Dtype-based numeric filtering (`int64`, `float64`, `int32`, `float32`), NaN ratio calculation, all-NaN column removal, quality issue logging                           |
| `chart_app.py`      | Dash app factory, ScatterGL trace construction, MinMaxLTTB downsampling integration, layout assembly, follow mode callbacks, dragmode toggle, file loading callbacks |
| `csv_monitor.py`    | Watchdog filesystem observer, debounced modification handling, trigger index refresh on file growth                                                                    |
| `lttb.py`           | MinMaxLTTB downsampling via tsdownsample library; two-phase algorithm (min-max preselection + LTTB refinement) preserves visual shape with superior performance         |
| `palettes.py`       | Theme color definitions (light/dark); 20-color palette rotation based on Okabe-Ito, Tol, and Kelly maximum-contrast palettes                                           |
| `logging_config.py` | Root logger configuration with consistent format                                                                                                                       |

## Development Commands

```bash
# Install dependencies
uv sync

# Run with sample CSV
uv run csv-chart-plotter sample.csv

# Run with follow mode (tail log files)
uv run csv-chart-plotter logfile.csv --follow

# Run with dark theme
uv run csv-chart-plotter data.csv --theme dark

# Run without file (shows file dialog)
uv run csv-chart-plotter

# Run tests
uv run pytest tests/ -v

# Format code
uv run ruff format src/ tests/

# Lint code
uv run ruff check src/ tests/

# Build standalone executable
python build.py
```

## Code Conventions

### Naming Conventions

- **Modules:** `snake_case` (e.g., `csv_indexer.py`, `chart_app.py`)
- **Classes:** `PascalCase` (e.g., `CSVIndexer`, `PyWebViewAPI`)
- **Functions/methods:** `snake_case` (e.g., `create_app()`, `build_index()`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `MAX_DISPLAY_POINTS`, `TAIL_THRESHOLD_RATIO`)
- **Private methods:** Leading underscore (e.g., `_parse_csv_row()`, `_convert_timestamps()`)

### Type Hints

Use comprehensive type hints for all function signatures:

```python
def read_range(self, start_row: int, end_row: int) -> pd.DataFrame:
    """Read a range of rows from the indexed CSV."""
    ...

def create_app(
    df: Optional[pd.DataFrame] = None,
    csv_filename: Optional[str] = None,
    theme: str = "light",
) -> dash.Dash:
    """Create the Dash application."""
    ...
```

### Docstring Format

Use triple-quoted docstrings with structured sections:

```python
def build_index(self) -> CSVIndex:
    """
    Build byte-offset index by scanning the file.

    Reads the file line by line in binary mode, recording the byte
    offset of each data row. The header row is parsed to extract
    column names but is not included in the row offsets.

    Returns:
        CSVIndex with row offsets and metadata.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file is empty or has no header.
    """
```

### Error Handling Patterns

**File Operations:**

- Raise `FileNotFoundError` for missing files
- Raise `ValueError` for malformed or invalid CSV content
- Log warnings for recoverable issues (malformed rows, high NaN ratios)

**Data Validation:**

- Use `column_filter.filter_numeric_columns()` which raises `ValueError` if no numeric columns remain
- Log INFO for dropped non-numeric columns
- Log WARNING for all-NaN columns

**Exit Codes (main.py):**

- `0` — Success (window closed normally)
- `1` — Data error (file not found, no numeric columns)
- `2` — Unexpected error (exceptions)

### Logging Practices

```python
import logging
logger = logging.getLogger(__name__)

# DEBUG: trace-level details
logger.debug("Found available port: %d", port)

# INFO: operational progress
logger.info("Indexed %d rows, %d columns", row_count, column_count)

# WARNING: data quality issues
logger.warning("All-NaN column dropped: %s", column_name)

# ERROR: recoverable failures
logger.error("File modification callback error: %s", e)

# EXCEPTION: unrecoverable errors (includes traceback)
logger.exception("Unexpected error: %s", e)
```

**Log Format:** `%(asctime)s - %(levelname)s - %(message)s`

### Async/Threading Conventions

- Flask server runs in daemon background thread (`threading.Thread(daemon=True)`)
- pywebview window runs on main thread (blocking call to `webview.start()`)
- File reads open fresh handles per request (no shared state)
- Row index is immutable after build; rebuilt atomically on file changes

## Common Tasks

### Adding a New Configuration Option

1. Add constant to appropriate module (e.g., `chart_app.py` for display settings)
2. Pass as parameter through `create_app()` if user-configurable
3. Add CLI argument in `main.py` if exposed to users
4. Update docstrings and README.md

Example:

```python
# chart_app.py
MAX_DISPLAY_POINTS = 4000  # Configurable display limit

def create_app(max_points: int = MAX_DISPLAY_POINTS, ...):
    """Create Dash app with configurable point limit."""
    ...
```

### Modifying Downsampling Configuration

The `MAX_DISPLAY_POINTS` constant in `chart_app.py` controls the maximum points per trace. Changing this affects:

- Visual fidelity (higher = more detail)
- Rendering performance (higher = slower pan/zoom)
- Memory consumption (linear with point count)

```python
# chart_app.py
MAX_DISPLAY_POINTS = 4000  # Change here for global effect
MINMAX_RATIO = 4           # Preselection ratio (higher = faster, less detail)
```

The MinMaxLTTB algorithm in `lttb.py` (via tsdownsample) receives this threshold and guarantees output ≤ threshold.

**MinMaxLTTB Parameters:**
- `minmax_ratio`: Higher values prioritize speed over mid-range detail (default: 4)
- `parallel`: Enable Rust-level multi-threading for large datasets (default: False)

### Adding a New Color Palette

Palettes are defined in `palettes.py` with separate lists for light and dark themes:

```python
# palettes.py
LIGHT_PALETTE = [
    '#E69F00',  # orange (Okabe-Ito)
    '#0072B2',  # blue (Okabe-Ito)
    # ... add more colors
]

DARK_PALETTE = [
    '#FFA94D',  # lightened orange
    '#5BA3E8',  # lightened blue
    # ... match light palette order
]
```

**Requirements for new colors:**

- Meet WCAG AA contrast (≥3:1 for graphics) against plot background
- Test with colorblind simulators (Coblis, Colorblindor)
- Maintain perceptual distinctness across adjacent colors
- Provide matched light/dark variants

### Extending CSV Format Support

Currently supports:

- Comma delimiter only
- First column as index (timestamp or numeric)
- Remaining columns as numeric traces

To add format support:

1. **Custom delimiter:** Modify `csv_indexer.py` `_parse_csv_row()` to accept delimiter parameter
2. **Multi-column index:** Requires rethinking x-axis mapping; currently assumes single index
3. **Timestamp parsing:** Add patterns to `_UTC_TIMESTAMP_PATTERN` in `csv_indexer.py`

### Adding a New Dash Callback

Follow this pattern from `chart_app.py`:

```python
@app.callback(
    Output('chart', 'figure'),
    Input('some-button', 'n_clicks'),
    State('theme-store', 'data'),
    prevent_initial_call=True,
)
def callback_name(n_clicks, theme):
    """
    Handle button click to update chart.

    Args:
        n_clicks: Button click count.
        theme: Current theme ('light' or 'dark').

    Returns:
        Updated Plotly figure or no_update.
    """
    if n_clicks is None:
        return no_update

    # ... callback logic
    return updated_figure
```

**Callback conventions:**

- Use descriptive names matching their purpose (e.g., `update_theme`, `reload_csv`)
- Include comprehensive docstrings
- Use `prevent_initial_call=True` for action-triggered callbacks
- Return `no_update` when no changes needed
- Access stored objects via `app._attribute` (e.g., `app._csv_indexer`)

### Testing a New Feature

Add tests to appropriate test file in `tests/`:

```python
# tests/test_csv_indexer.py
def test_new_indexer_feature(tmp_path):
    """Test description of what behavior is verified."""
    # Arrange: create test CSV
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("col1,col2\n1,2\n3,4\n")

    # Act: exercise feature
    indexer = CSVIndexer(csv_path)
    result = indexer.build_index()

    # Assert: verify expectations
    assert result.row_count == 2
    assert result.columns == ['col1', 'col2']
```

**Testing conventions:**

- Use pytest fixtures from `conftest.py` (`sample_csv_path`, `numeric_df`)
- Use `tmp_path` fixture for temporary files
- Follow Arrange-Act-Assert pattern
- Name tests `test_<module>_<behavior>` (e.g., `test_filter_drops_all_nan_columns`)

## Important Constraints and Non-Obvious Behaviors

### Memory Model

**Critical Design Decision:** Unlike traditional CSV viewers that load entire files into memory, this application uses a streaming/indexed architecture:

- **Row index:** ~24 bytes per row (byte offset + metadata)
- **Viewport buffer:** ≤4,000 rows × columns × 8 bytes (float64)
- **Display traces:** ≤4,000 points × columns × 16 bytes (x,y pairs)

**Example:** A 10 million row × 40 column CSV (3.2 GB if fully loaded) uses:

- ~240 MB for row index
- ~1.3 MB for viewport buffer
- ~2.6 MB for display traces
- **Total: ~244 MB** (constant regardless of file size)

**Implication:** There are NO row or column limits. The `MAX_ROWS` and `MAX_COLUMNS` constants from earlier implementations have been removed.

### MinMaxLTTB Downsampling Behavior

The MinMaxLTTB algorithm (via tsdownsample) uses a two-phase approach for superior performance:

**Phase 1: Min-max preselection**
- Selects n_out × minmax_ratio extreme points (default ratio: 4)
- Guarantees capture of peaks and troughs

**Phase 2: LTTB refinement**
- Applies Largest-Triangle-Three-Buckets to preselected points
- Maximizes triangle areas to preserve visual shape

**Key behaviors:**

1. **First and last points always retained** — ensures viewport boundaries are exact
2. **Peaks and troughs prioritized** — min-max preselection guarantees extreme value retention
3. **Smooth regions simplified** — flat sections represented by fewer points
4. **Deterministic** — same input always produces same output
5. **High performance** — 10-30× faster than pure LTTB (Rust implementation)

**When downsampling is applied:**

- Every viewport change (zoom/pan)
- On initial load if row count > 4,000
- On follow mode data append

**When downsampling is skipped:**

- Viewport contains ≤4,000 rows (no reduction needed)

**Configuration:**
- `minmax_ratio`: Default 4 (empirically optimal per research)
- `parallel`: Optional multi-threading (disabled by default)

**Reference:** https://arxiv.org/abs/2305.00332

### Viewport State Synchronization

The application tracks multiple viewport concepts:

| Concept                | Definition                                    | Location                 |
| ---------------------- | --------------------------------------------- | ------------------------ |
| **User Viewport**      | What the user has zoomed/panned to            | Client-side Plotly state |
| **Requested Viewport** | Viewport for which data is being fetched      | Server-side metadata     |
| **Displayed Viewport** | Viewport for which data is currently rendered | Server-side metadata     |

**Race Condition Scenario:**

1. User zooms to region A → backend starts fetching A
2. User immediately pans to region B (while A still loading)
3. Backend completes fetch for A
4. **Problem:** Should we display stale data A or discard and fetch B?

**Solution:** Request versioning with monotonic counter. When response arrives, check if viewport version matches request version. If mismatch, discard response and fetch current viewport.

### Follow Mode and Manual Interaction

**Behavior:** When follow mode is active and user manually pans away from the tail, follow mode auto-disables with visual feedback.

**Tail Threshold:**

```python
tail_threshold = min(
    total_rows * 0.05,      # 5% of data
    100_000,                 # Hard cap
)
```

**Status Display:**

- Following: `Latest: 2025-12-09 10:30:07`
- Paused: `Paused | Latest: 2025-12-09 10:30:07`

Timestamp is **always** the last row timestamp (not viewport end), so users know data availability even when viewing historical ranges.

### File Loading State Machine

```text
      ┌─────────────────────────────────────────┐
      │             EMPTY STATE                 │
      │   • No CSV loaded                       │
      │   • "Load CSV..." button visible       │
      └─────────────────────────────────────────┘
                      │
                      │ User clicks "Load CSV..."
                      ↓
      ┌─────────────────────────────────────────┐
      │         FILE DIALOG OPEN                │
      │   • Native pywebview.create_file_dialog │
      └─────────────────────────────────────────┘
                      │
            ┌─────────┴─────────┐
            │                   │
  User selects file    User cancels
            │                   │
            ↓                   ↓
      ┌─────────────┐    ┌──────────┐
      │  LOADING    │    │  EMPTY   │
      │  • Index    │    │  STATE   │
      │  • Filter   │    └──────────┘
      │  • Render   │
      └─────────────┘
            │
            ↓
      ┌─────────────────────────────────────────┐
      │           DATA LOADED                   │
      │   • Chart visible                       │
      │   • "Reload" button enabled            │
      │   • Follow mode available              │
      └─────────────────────────────────────────┘
```

### CSV Format Expectations

**Valid:**

```csv
Timestamp,Temperature,Pressure
2025-12-01T09:00:00Z,23.5,1013.2
2025-12-01T09:01:00Z,23.6,1013.1
```

**Edge Cases:**

- **Non-numeric columns:** Dropped with INFO log (e.g., `Status,Online` → dropped)
- **All-NaN columns:** Dropped with WARNING log
- **High NaN ratio (>50%):** Retained with INFO log noting ratio
- **Malformed rows:** Skipped silently with WARNING log (count reported at end)
- **Empty final row:** Skipped (common with trailing newline)
- **UTC timestamps:** Converted to local timezone, `Z` suffix removed
- **Non-UTC timestamps:** Displayed as-is (no conversion)

**Validation Failures:**

- Empty file → `ValueError`
- No header → `ValueError`
- All columns non-numeric → `ValueError` (raised by `column_filter`)
- Inconsistent column count → malformed row (skipped)

### Dragmode Interaction Toggle

Users can switch between two drag interaction modes via dropdown:

**Zoom mode (default):**
- Drag creates selection box for precise time-range zooming
- Double-click resets to full view
- Preferred for scientific analysis requiring precision

**Pan mode:**
- Drag navigates/scrolls through data
- Scroll wheel still zooms
- Traditional panning behavior

**Implementation:**
- Dropdown in control bar: `dragmode-dropdown`
- Callback updates `layout.dragmode` property
- Default: `dragmode='zoom'` (box zoom)

### Plotly Trace Configuration

All traces use this configuration:

```python
go.Scattergl(
    x=x_downsampled,
    y=y_downsampled,
    mode='lines',              # Line chart (not markers)
    name=column_name,          # Appears in legend
    line=dict(color=color),    # From palette rotation
    connectgaps=False,         # NaN renders as gap (not interpolated)
    hovertemplate='%{x}<br>%{y:.2f}<extra>%{fullData.name}</extra>',
)
```

**Why ScatterGL (not Scatter):**

- WebGL rendering (GPU-accelerated)
- Sub-100ms pan/zoom latency for 4,000 points
- Handles up to ~100k points before degradation (we cap at 4k)

**Why `connectgaps=False`:**

- Missing data (NaN) should appear as discontinuity, not interpolated
- Prevents misleading visual impression of continuity

### Theme Switching Mechanism

Uses CSS custom properties with `[data-theme="dark"]` selector:

```css
:root {
  --color-base: #ffffff;
  --color-text-primary: #1a1a1a;
}

[data-theme="dark"] {
  --color-base: #1a1a1a;
  --color-text-primary: #e8e8e8;
}
```

**Flow:**

1. User selects theme from dropdown
2. `update_theme` callback updates `theme-store`
3. Callback updates `app-container` `data-theme` attribute
4. CSS custom properties auto-switch
5. Chart figure rebuilds with new palette colors

### Build System (Nuitka)

`build.py` compiles to standalone executable:

```bash
python build.py
# Output: dist/csv-chart-plotter[.exe]
```

**Important Nuitka flags:**

- `--standalone` — Bundle Python interpreter
- `--onefile` — Single executable (not folder)
- `--follow-imports` — Recursively include imports
- `--include-package=dash,plotly,pandas,numpy` — Explicit dependencies
- `--include-data-dir=src/csv_chart_plotter/assets=csv_chart_plotter/assets` — Bundle CSS
- `--nofollow-import-to=pytest,unittest` — Exclude test frameworks
- `--windows-console-mode=disable` — GUI-only (no console window on Windows)
- `--msvc=latest` — Force latest MSVC detection (required for Python 3.13)
- `--jobs=1` — Disable parallel compilation (prevents SCons environment issues)

**Cross-platform notes:**

- Must build on target platform (no cross-compilation)
- Windows: requires MSVC with Windows SDK (Python 3.13 requirement; MinGW not supported)
- macOS/Linux: requires platform-specific pywebview dependencies

**Important Build flags:**
- `--msvc=latest` — Use newest MSVC (helps SCons detection)
- `--jobs=1` — Disable parallel compilation (avoids threading environment issues)

## Reference Index

Quick lookup for common modifications:

| Domain           | Files                              | Keywords                                                     |
| ---------------- | ---------------------------------- | ------------------------------------------------------------ |
| CSV Parsing      | `csv_indexer.py`                   | `build_index`, `read_range`, `_parse_csv_row`, `row_offsets` |
| Column Filtering | `column_filter.py`                 | `filter_numeric_columns`, `compute_nan_ratio`                |
| Downsampling     | `lttb.py`, `chart_app.py`          | `lttb_downsample`, `compute_lttb_indices`, `MAX_DISPLAY_POINTS`, `MINMAX_RATIO` |
| Chart Rendering  | `chart_app.py`                     | `create_figure`, `create_trace`, `ScatterGL`                 |
| Follow Mode      | `csv_monitor.py`, `chart_app.py`   | `CSVFileMonitor`, `update_on_follow_interval`                |
| Theming          | `palettes.py`, `assets/styles.css` | `LIGHT_PALETTE`, `DARK_PALETTE`, `[data-theme]`              |
| CLI Interface    | `main.py`                          | `argparse`, `validate_file`, `find_available_port`           |
| File Dialog      | `main.py`, `chart_app.py`          | `PyWebViewAPI.open_file_dialog`, `load_csv_callback`         |

## Known Issues and Future Enhancements

**Current Limitations:**

- CSV format only (no Parquet, JSON, Arrow)
- No state persistence (zoom/pan resets between sessions)
- Single file display (no multi-file overlay)
- WebGL required (needs GPU with WebGL 1.0 support)
- No column selection UI (all numeric columns displayed)

**Potential Enhancements:**

- Progressive data loading (show full-view cache immediately, sharpen on viewport fetch)
- Configurable downsampling threshold per trace
- Export visible data range to CSV
- Bookmark/annotation system for time ranges
- Multi-file comparison mode (overlay traces from multiple CSVs)
- Column visibility toggles (hide/show individual traces)
- Keyboard shortcuts for common actions
