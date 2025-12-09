# CSV Chart Plotter

Interactive time-series visualizer for large CSV datasets. GPU-accelerated plotting with native window integration.

## Overview

CSV Chart Plotter loads CSV files containing numeric time-series data and renders interactive charts in a native desktop window. Built for datasets with up to 1 million rows and 40 numeric columns.

**Key Features:**

- Handles datasets up to 1M rows without excessive memory consumption (<2GB)
- GPU-accelerated rendering using Plotly ScatterGL (WebGL)
- Interactive zoom/pan/legend controls
- Automatic column type detection (numeric columns only)
- Malformed CSV handling with row skipping
- Native desktop window (no browser required)
- Standalone executable compilation (no Python installation required)

## Installation

### Prerequisites

- Python 3.13+ (via [UV](https://github.com/astral-sh/uv))
- Windows OS (tested on Windows 11)

### Setup with UV

1. Clone repository:

   ```powershell
   git clone https://github.com/yourusername/CsvChartPlotter.git
   cd CsvChartPlotter
   ```

2. Install dependencies:

   ```powershell
   uv sync
   ```

3. Activate virtual environment (optional):

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

## Usage

### Development Workflow

Run directly with UV (no installation required):

```powershell
uv run csv-chart-plotter sample.csv
```

### Standalone Executable

For distribution without Python installation:

1. Install build dependencies:

   ```powershell
   uv add --optional nuitka
   ```

2. Compile to executable:

   ```powershell
   python build.py
   ```

3. Run standalone executable:

   ```powershell
   .\dist\csv-chart-plotter.exe sample.csv
   ```

**Note:** First compilation takes 5-15 minutes. Subsequent builds reuse cached modules.

## Supported CSV Formats

### Data Requirements

- **First column:** Index or timestamp (string/datetime format)
- **Remaining columns:** Numeric data (int/float)
- **Header row:** Column names (required)
- **Delimiter:** Comma (`,`)

### Example Structure

```csv
Timestamp,MetricA,MetricB,MetricC
2025-12-01T09:00:00Z,123.45,67.89,42.10
2025-12-01T09:01:00Z,124.56,68.01,42.15
2025-12-01T09:02:00Z,125.67,68.23,42.20
```

### Data Quality Handling

| Scenario | Behavior |
|----------|----------|
| Non-numeric column | Dropped with warning (except first column) |
| Missing values (NaN) | Rendered as gaps in line plots |
| Malformed rows | Skipped with warning |
| Empty columns | Dropped with warning |

### Tested Dataset: sample.csv

- **Rows:** 107
- **Columns:** 23 (first column is timestamp, 22 numeric metrics)
- **Domain:** Process memory and GC statistics
- **Size:** ~20 KB

Load with: `uv run csv-chart-plotter sample.csv`

## Performance Characteristics

### Target Specifications

| Metric | Target | Measured (1M rows × 23 cols) |
|--------|--------|------------------------------|
| Peak Memory | < 2 GB | 1.44 GB ✓ |
| Load Time | — | 3.73 seconds |
| App Creation | < 5 seconds | 4.78 seconds ✓ |
| Zoom/Pan Latency | < 100 ms | <100 ms (GPU-bound) ✓ |

### Dataset Limits

- **Maximum rows:** 1,000,000
- **Maximum columns:** ~40 numeric columns (at 1M rows)
- **Maximum file size:** ~420 MB (1M × 23 columns)
- **Memory scaling:** ~0.65 KB per row

For detailed performance analysis, see [PERFORMANCE.md](PERFORMANCE.md).

## Known Limitations

### Functional Constraints

- **No state persistence:** Zoom/pan state resets between sessions
- **CSV format only:** No support for Parquet, JSON, or other formats
- **Time-series assumption:** First column treated as index/timestamp
- **No real-time updates:** Static visualization of loaded data

### Performance Constraints

- **Column count:** ~40 numeric columns at 1M rows (memory limit)
- **Row count:** 1M rows (performance degradation beyond this point)
- **Load time with malformed CSVs:** 10-20x slower (Python parser fallback)

### Platform Support

- **Windows only:** Tested on Windows 11 (pywebview dependencies may vary on Linux/macOS)
- **GPU requirement:** WebGL-capable GPU for ScatterGL rendering (all modern integrated GPUs supported)

## Interactive Controls

Once the chart window opens:

- **Pan:** Click and drag chart area
- **Zoom:** Scroll wheel or box selection (click and drag rectangle)
- **Reset:** Double-click chart area
- **Toggle series:** Click legend items to show/hide traces
- **Hover:** Mouse over data points to see values

## Development

### Running Tests

Full test suite:

```powershell
uv run pytest tests/ -v
```

Performance validation (includes 1M row synthetic dataset generation):

```powershell
uv run pytest tests/test_performance_validation.py -v -s
```

**Test Duration:** ~85 seconds (20 seconds for synthetic CSV generation)

### Project Structure

```
CsvChartPlotter/
├── src/csv_chart_plotter/
│   ├── main.py              # CLI entry point
│   ├── csv_loader.py        # Chunked CSV reading
│   ├── column_filter.py     # Numeric column filtering
│   ├── chart_app.py         # Dash application
│   └── logging_config.py    # Logging configuration
├── tests/                   # Pytest test suite
├── build.py                 # Nuitka compilation script
├── sample.csv               # Example dataset (107 rows)
├── pyproject.toml           # UV project configuration
└── README.md                # This file
```

### Adding Dependencies

Add runtime dependency:

```powershell
uv add <package_name>
```

Add development dependency:

```powershell
uv add --dev <package_name>
```

### Code Quality

Format code with:

```powershell
uv run ruff format src/ tests/
```

Lint code with:

```powershell
uv run ruff check src/ tests/
```

## Building for Distribution

See [BUILDING.md](BUILDING.md) for detailed compilation instructions, troubleshooting, and platform-specific considerations.

## Contributing

1. Fork repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Write tests for new functionality
4. Ensure all tests pass: `uv run pytest`
5. Submit pull request

## License

MIT License. See LICENSE file for details.

## Acknowledgements

- [Plotly](https://plotly.com/) - Interactive charting library
- [Dash](https://dash.plotly.com/) - Python web framework for data applications
- [Pandas](https://pandas.pydata.org/) - Data manipulation library
- [pywebview](https://pywebview.flowrl.com/) - Native window wrapper
- [Nuitka](https://nuitka.net/) - Python compiler for standalone executables
- [UV](https://github.com/astral-sh/uv) - Fast Python package manager

## Contact

Report issues at: <https://github.com/yourusername/CsvChartPlotter/issues>
