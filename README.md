# CSV Chart Plotter

Interactive time-series visualizer for CSV datasets of any size. GPU-accelerated plotting with native window integration.

## Overview

CSV Chart Plotter loads CSV files containing numeric time-series data and renders interactive charts in a native desktop window. The streaming architecture handles datasets of any size—memory consumption is bounded by display requirements, not data size.

**Key Features:**

- **Streaming architecture** — handles arbitrarily large CSV files via on-demand reading with row indexing
- **GPU-accelerated rendering** — Plotly ScatterGL (WebGL) for sub-100ms zoom/pan latency
- **MinMaxLTTB downsampling** — Two-phase algorithm (10-30× faster than pure LTTB) limits display to 4,000 points per trace
- **Interactive controls** — box-zoom selection (default), pan mode toggle, Y auto-scaling, legend toggle, hover tooltips
- **Follow mode** — live file tail with 5-second debounced updates
- **Native file dialog** — select CSV files without CLI; switch files without restart
- **Light/dark themes** — switchable via UI
- **Standalone executable** — Nuitka compilation for distribution without Python

## Installation

### Prerequisites

- Python 3.13+ (via [UV](https://github.com/astral-sh/uv))
- macOS, Windows, or Linux

### Setup with UV

```bash
# Clone repository
git clone https://github.com/yourusername/csv-chart-plotter.git
cd csv-chart-plotter

# Install dependencies
uv sync
```

## Usage

### Run with CSV File

```bash
uv run csv-chart-plotter sample.csv
```

### Run Empty (File Dialog)

```bash
uv run csv-chart-plotter
```

Click "Load CSV..." to open the native file dialog.

### Follow Mode (Live Tail)

```bash
uv run csv-chart-plotter logfile.csv --follow
```

The chart auto-updates when the file grows. Zoom/pan pauses follow mode; click checkbox to resume.

### Theme Selection

```bash
uv run csv-chart-plotter sample.csv --theme dark
```

## Interactive Controls

| Control | Action |
|---------|--------|
| **Drag select** | Box-zoom to selected time range (default mode, Y auto-scales) |
| **Drag mode toggle** | Switch between Zoom and Pan modes via dropdown |
| **Scroll wheel** | Zoom in/out |
| **Double-click** | Reset to full view |
| **Click legend** | Toggle trace visibility |
| **Hover** | Show values at cursor position |

### Plotly Toolbar

The chart includes Plotly's built-in toolbar (top-right corner):

| Button | Function |
|--------|----------|
| 📷 Download plot as PNG | Save chart image |
| 🔍 Zoom | Enable box zoom mode |
| ↔️ Pan | Enable pan mode |
| 🏠 Reset axes | Reset to original view |
| ↩️ Autoscale | Auto-fit all data |

## Supported CSV Formats

### Requirements

- **First column:** Timestamp or index (used as X-axis)
- **Remaining columns:** Numeric data (non-numeric columns auto-filtered)
- **Header row:** Required
- **Delimiter:** Comma (`,`)

### Example

```csv
Timestamp,Temperature,Pressure,Humidity
2025-12-01T09:00:00Z,23.5,1013.2,45.0
2025-12-01T09:01:00Z,23.6,1013.1,45.2
2025-12-01T09:02:00Z,23.7,1013.0,45.5
```

### Timestamp Handling

- ISO 8601 UTC timestamps (`2025-12-01T09:00:00Z`) are converted to local timezone
- Other timestamp formats displayed as-is
- Non-timestamp first columns used as string index

### Data Quality

| Scenario | Behavior |
|----------|----------|
| Non-numeric column | Dropped with warning |
| Missing values (NaN) | Rendered as gaps in lines |
| Malformed rows | Skipped with warning |
| Empty columns | Dropped |

## Architecture

### Streaming Design

Unlike traditional CSV viewers that load entire files into memory, CSV Chart Plotter uses an indexed streaming approach:

1. **Index phase:** Scan file to build byte-offset index of row positions
2. **Read phase:** Load only requested row ranges from disk
3. **Downsample phase:** MinMaxLTTB (via tsdownsample) reduces to ≤4,000 display points per trace

This enables constant memory usage regardless of file size—a 10GB CSV uses the same memory as a 10KB CSV.

**MinMaxLTTB Algorithm:** Two-phase downsampling for superior performance:

- Phase 1: Min-max preselection identifies extreme values (n_out × ratio points)
- Phase 2: LTTB refinement applies triangle-area selection to preselected points
- Result: 10-30× faster than pure LTTB with comparable visual fidelity (research: <https://arxiv.org/abs/2305.00332>)

### Module Structure

```text
src/csv_chart_plotter/
├── main.py           # CLI entry, pywebview window lifecycle
├── csv_indexer.py    # Streaming CSV access with row offset indexing
├── column_filter.py  # Numeric column detection and filtering
├── lttb.py           # MinMaxLTTB downsampling (via tsdownsample)
├── chart_app.py      # Dash application, callbacks, figure creation
├── palettes.py       # Theme color definitions
├── logging_config.py # Logging setup
└── assets/
    └── styles.css    # UI styling
```

## Development

### Running Tests

```bash
uv run pytest tests/ -v
```

### Code Quality

```bash
# Format
uv run ruff format src/ tests/

# Lint
uv run ruff check src/ tests/
```

### Project Structure

```text
csv-chart-plotter/
├── src/csv_chart_plotter/   # Application source
├── tests/                   # Test suite
├── tools/                   # Utilities (synthetic CSV generator)
├── docs/                    # Specifications
├── build.py                 # Nuitka build script
├── sample.csv               # Example dataset
└── pyproject.toml           # Project configuration
```

## Building Standalone Executable

See [BUILDING.md](BUILDING.md) for compilation instructions.

Quick build:

```bash
uv add --dev nuitka
python build.py
./dist/csv-chart-plotter sample.csv
```

## Known Limitations

- **CSV format only** — no Parquet, JSON, or other formats
- **No state persistence** — zoom/pan resets between sessions
- **Single file** — no multi-file overlay or comparison view
- **WebGL required** — needs GPU with WebGL support

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

## Acknowledgements

- [Plotly](https://plotly.com/) — Interactive charting
- [Dash](https://dash.plotly.com/) — Web application framework
- [pywebview](https://pywebview.flowrl.com/) — Native window wrapper
- [Pandas](https://pandas.pydata.org/) — Data manipulation
- [tsdownsample](https://github.com/predict-idlab/tsdownsample) — High-performance MinMaxLTTB algorithm
- [UV](https://github.com/astral-sh/uv) — Python package manager
