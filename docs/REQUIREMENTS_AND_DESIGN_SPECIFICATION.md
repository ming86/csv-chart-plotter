# CSV Chart Plotter — Requirements and Design Specification

> **Document Purpose:** Complete specification for rebuilding this application from scratch.  
> **Generated:** 2025-12-09  
> **Revised:** 2025-12-09 — Architecture evolved to streaming model; obsolete constraints removed  
> **Source:** Extracted from existing codebase analysis with design corrections

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Functional Requirements](#2-functional-requirements)
3. [Technical Specifications](#3-technical-specifications)
4. [User Interface Design](#4-user-interface-design)
5. [Behavioral Specifications](#5-behavioural-specifications)
6. [Test Coverage Summary](#6-test-coverage-summary)
7. [Build and Distribution](#7-build-and-distribution)
8. [Appendices](#appendices)

---

## 1. Project Overview

### 1.1 Purpose and Goals

CSV Chart Plotter is an interactive time-series visualisation tool designed for **arbitrarily large** CSV datasets. The application renders numeric data as line charts within a native desktop window, using embedded WebGL rendering via pywebview.

The core objectives are:

1. **Handle datasets of any size** — no artificial row or column limits; memory consumption bounded by display requirements, not data size
2. **Provide GPU-accelerated rendering** — using Plotly ScatterGL (WebGL) to ensure sub-100ms pan/zoom latency
3. **Operate as a standalone executable** — compiled via Nuitka for distribution without Python installation
4. **Maintain simplicity** — CLI-driven operation requiring only a CSV file path argument

### 1.2 Design Philosophy: Streaming Over Loading

The key architectural insight: **MinMaxLTTB downsampling to 4,000 points means display memory is constant regardless of source data size.** This enables a streaming/indexed architecture similar to log viewers like glogg/klogg:

| Aspect | Old Design (Obsolete) | Target Design |
|--------|----------------------|---------------|
| Data loading | Load entire CSV into RAM | Stream/index from disk |
| Memory model | Bounded by row×column limits | Bounded by display buffer only |
| Row limits | 1,000,000 max | **None** |
| Column limits | 40 max | **None** (practical limit: legend readability) |
| Initial load | Parse entire file | Build index, sample for initial view |
| Viewport change | Slice cached DataFrame | Read indexed range, downsample |

### 1.3 Target Users

- Data analysts examining process metrics, memory statistics, or time-series telemetry
- Developers investigating performance logs or diagnostic exports
- Technical users comfortable with command-line tools but desiring native GUI interaction
- Users who prefer GUI file selection over CLI arguments

### 1.4 Key Features Summary

| Feature | Description |
|---------|-------------|
| Flexible file loading | CLI argument or native file browser dialog; switch files without restart |
| Streaming CSV access | On-demand reading with row indexing; no full-file memory requirement |
| Numeric column filtering | Automatic type detection; non-numeric columns excluded from display |
| ScatterGL line charts | One trace per numeric column with GPU acceleration |
| NaN gap handling | Missing values render as discontinuities |
| Interactive controls | Pan, zoom, legend toggle, hover tooltips |
| Live follow mode | 5-second debounced file tail with viewport preservation |
| MinMaxLTTB downsampling | Two-phase algorithm (min-max + LTTB) limits display to 4,000 points per trace; 10-30× faster than pure LTTB |
| File reload | Manual reload button to refresh current file |
| Standalone compilation | Nuitka-based Windows executable generation |
| Light/dark theming | Configurable colour palettes |

---

## 2. Functional Requirements

### 2.1 CSV File Handling

#### 2.1.1 Loading Requirements

| Requirement ID | Description |
|----------------|-------------|
| FR-LOAD-01 | Accept CSV file path as CLI argument (optional) |
| FR-LOAD-02 | If no CLI argument provided, show empty state with file browser button |
| FR-LOAD-03 | Provide native file dialog via pywebview for file selection |
| FR-LOAD-04 | Support loading new CSV file at any time (file switching without restart) |
| FR-LOAD-05 | Validate file existence before processing |
| FR-LOAD-06 | Build row offset index on first open (enables random access) |
| FR-LOAD-07 | Support streaming reads—never require entire file in memory |
| FR-LOAD-08 | Support comma delimiter exclusively |
| FR-LOAD-09 | ~~Dimension validation~~ **REMOVED** — no row/column limits |

#### 2.1.2 Parsing and Validation

| Requirement ID | Description |
|----------------|-------------|
| FR-PARSE-01 | First column becomes DataFrame index |
| FR-PARSE-02 | Convert non-numeric first column to string |
| FR-PARSE-03 | Detect UTC timestamps (ISO 8601 with `Z` suffix) |
| FR-PARSE-04 | Convert UTC timestamps to local timezone |
| FR-PARSE-05 | ~~Validate dimensions against memory budget~~ **REMOVED** — streaming eliminates need |
| FR-PARSE-06 | ~~Estimate row count from file size~~ **CHANGED** — build actual row index instead |

#### 2.1.3 Malformed Row Handling

| Requirement ID | Description |
|----------------|-------------|
| FR-MALFORM-01 | Skip malformed rows silently when `on_bad_lines='skip'` |
| FR-MALFORM-02 | Log warning for skipped rows |
| FR-MALFORM-03 | Continue processing after malformed rows (no abort) |

### 2.2 Column Filtering and Selection

| Requirement ID | Description |
|----------------|-------------|
| FR-FILTER-01 | Retain columns with `int64`, `float64`, `int32`, `float32` dtypes |
| FR-FILTER-02 | Drop non-numeric columns with INFO log |
| FR-FILTER-03 | Drop all-NaN columns with WARNING log |
| FR-FILTER-04 | Log INFO for columns with >50% NaN ratio |
| FR-FILTER-05 | Raise `ValueError` when no numeric columns remain |

### 2.3 Chart Rendering Capabilities

| Requirement ID | Description |
|----------------|-------------|
| FR-CHART-01 | Create one ScatterGL trace per numeric column |
| FR-CHART-02 | Use `mode='lines'` for trace rendering |
| FR-CHART-03 | Preserve NaN gaps with `connectgaps=False` |
| FR-CHART-04 | Display trace name in legend |
| FR-CHART-05 | Apply colour from palette (23-colour rotation) |
| FR-CHART-06 | Set hover template to `'%{x}<br>%{y:.2f}<extra>%{fullData.name}</extra>'` |
| FR-CHART-07 | Apply MinMaxLTTB downsampling to maximum 4,000 points per trace |

### 2.4 File Monitoring and Auto-Reload (Follow Mode)

| Requirement ID | Description |
|----------------|-------------|
| FR-FOLLOW-01 | `--follow` flag sets initial state of follow mode (user can toggle via checkbox) |
| FR-FOLLOW-02 | Poll for file changes every 5 seconds |
| FR-FOLLOW-03 | Debounce updates to minimum 5-second interval |
| FR-FOLLOW-04 | Detect new rows appended to file (tail follow) |
| FR-FOLLOW-05 | Preserve legend visibility state across updates |
| FR-FOLLOW-06 | Preserve viewport when user is examining middle section |
| FR-FOLLOW-07 | Extend viewport end time when following tail |
| FR-FOLLOW-08 | Toggle follow mode via UI checkbox |
| FR-FOLLOW-09 | Provide manual reload button for explicit file refresh |

### 2.5 User Interactions

| Requirement ID | Description |
|----------------|-------------|
| FR-INTERACT-01 | Pan via click-and-drag |
| FR-INTERACT-02 | Zoom via scroll wheel or box selection |
| FR-INTERACT-03 | Reset view via double-click |
| FR-INTERACT-04 | Toggle trace visibility via legend click |
| FR-INTERACT-05 | Hover to display values |
| FR-INTERACT-06 | Toggle theme via UI dropdown (light/dark) |
| FR-INTERACT-07 | Preserve UI state via `dcc.Store` |

### 2.6 Error Handling Behaviours

| Error Condition | Exit Code |
|-----------------|-----------|
| File not found | 1 |
| No numeric columns | 1 |
| ~~CSV dimension exceeded~~ | ~~1~~ **REMOVED** — no dimension limits |
| Unexpected exception | 2 |
| Missing CLI argument | 2 (argparse default) |

---

## 3. Technical Specifications

### 3.1 Architecture Overview

**Target Architecture (Streaming Model):**

```text
┌─────────────────────────────────────────────────────────────────────┐
│                          main.py (CLI Entry Point)                  │
│  • Argument parsing                                                 │
│  • Orchestration flow                                               │
│  • Port discovery                                                   │
│  • Server/window lifecycle                                          │
└──────────────┬──────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────┐   ┌──────────────────────────┐
│     csv_indexer.py       │   │    column_filter.py      │
│  • Build row offset map  │──▶│  • Numeric type filter   │
│  • Random access reads   │   │  • NaN detection         │
│  • Streaming iteration   │   │  • Quality logging       │
└──────────────────────────┘   └─────────────┬────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         chart_app.py (Dash Application)             │
│  • ScatterGL trace construction                                     │
│  • LTTB downsampling (4,000 points max per trace)                   │
│  • Layout configuration                                             │
│  • Viewport-driven data fetching                                    │
│  • Callback registration (follow mode, zoom resampling)             │
└──────────────┬──────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────┐   ┌──────────────────────────┐
│      csv_monitor.py      │   │     pywebview window     │
│  • Watchdog observer     │   │  • Native window frame   │
│  • Tail change detection │   │  • WebGL rendering       │
│  • Index update trigger  │   │  • User interaction      │
└──────────────────────────┘   └──────────────────────────┘
```

### 3.2 Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `main.py` | CLI argument parsing, file validation, port discovery, Flask server startup in background thread, pywebview window creation (blocking), graceful exit handling |
| `csv_indexer.py` | **NEW** — Build byte-offset index for rows; provide `read_range(start_row, end_row)` API; support index updates for appended data |
| `column_filter.py` | Dtype-based numeric filtering, NaN ratio calculation, all-NaN column removal, quality issue logging |
| `chart_app.py` | Dash application factory, ScatterGL trace construction, MinMaxLTTB downsampling, layout configuration, follow mode callbacks, dragmode toggle |
| `csv_monitor.py` | Watchdog-based filesystem observation, debounced modification handling, trigger index refresh on file growth |
| `logging_config.py` | Root logger configuration, consistent format `%(asctime)s - %(levelname)s - %(message)s` |

### 3.3 Data Flow (Streaming Model)

```text
CLI Argument ─▶ File Path Validation ─▶ Build Row Index (byte offsets)
                                                │
                                                ▼
                              Sample rows for column type detection
                                                │
                                                ▼
                              Numeric Column Filtering (header only)
                                                │
                                                ▼
              ┌─────────────────────────────────┴─────────────────────────────────┐
              │                     Viewport Request                              │
              │  (initial: full range; subsequent: user zoom/pan bounds)          │
              └─────────────────────────────────┬─────────────────────────────────┘
                                                │
                                                ▼
                              Read indexed row range from disk
                                                │
                                                ▼
                              MinMaxLTTB Downsample to ≤4,000 points
                                                │
                                                ▼
                              ScatterGL Trace Construction
                                                │
                                                ▼
                              Dash App Layout Assembly
                                                │
    ┌───────────────────────────────────────────┴───────────────────────────────────┐
    │                                                                               │
    ▼                                                                               ▼
Flask Server (background thread)                                          pywebview Window
    │                                                                               │
    └──────────────────────────── HTTP localhost ─────────────────────────────────▶│
```

**Key Difference from Old Architecture:** Data flows from disk → viewport slice → downsample → display. The full dataset never resides in memory simultaneously.

### 3.4 Dependencies and Frameworks

| Dependency | Version | Purpose |
|------------|---------|---------|
| `dash` | ≥3.3.0 | Web application framework for interactive visualisation |
| `plotly` | ≥6.5.0 | Charting library with WebGL ScatterGL support |
| `pandas` | ≥2.3.3 | DataFrame operations, CSV parsing, type inference |
| `numpy` | ≥2.0.0 | Numerical arrays for operations |
| `tsdownsample` | ≥0.1.4 | Rust-accelerated MinMaxLTTB downsampling |
| `pywebview` | ≥6.1 | Native window wrapper for embedded browser |
| `watchdog` | ≥3.0.0 | Filesystem event monitoring for follow mode |

**Development Dependencies:**

| Dependency | Version | Purpose |
|------------|---------|---------|
| `pytest` | ≥9.0.1 | Unit and integration testing |
| `nuitka` | ≥2.8.9 | Standalone executable compilation (optional) |

### 3.5 Configuration Options

| Configuration | Value | Notes |
|---------------|-------|-------|
| ~~Maximum rows~~ | ~~1,000,000~~ | **REMOVED** — no limit |
| ~~Maximum columns~~ | ~~40~~ | **REMOVED** — no limit |
| ~~Chunk size~~ | ~~50,000~~ | **REMOVED** — streaming replaces chunking |
| Maximum display points | 4,000 | **RETAINED** — WebGL rendering constraint |
| Tail follow threshold | 5% | `chart_app.py` |
| Follow mode interval | 5,000ms | `chart_app.py` dcc.Interval |
| Window dimensions | 1200×800 | `main.py` |
| Default theme | `'light'` | Switchable via UI dropdown |
| Trace color palette size | 20 colors | Okabe-Ito + Tol + Kelly variants |

### 3.6 Logging System

**Log Format:** `%(asctime)s - %(levelname)s - %(message)s`

**Log Levels by Message Type:**

| Level | Message Category | Examples |
|-------|------------------|----------|
| DEBUG | Trace-level details | Port discovery, chunk loads, trace counts |
| INFO | Operational progress | CSV dimensions, rows loaded, columns retained |
| WARNING | Data quality issues | All-NaN columns, skipped rows |
| ERROR | Recoverable failures | File modification callback errors |

---

## 4. User Interface Design

### 4.1 Layout Structure

```text
┌────────────────────────────────────────────────────────────────────────────────┐
│ Window Title: "CSV Chart Plotter - {filename}"                                 │
├────────────────────────────────────────────────────────────────────────────────┤
│ [Load CSV...]  [Reload]  │  Theme: [Light ▾]  │  ☑ Follow Mode  │  Latest: ... │
│ ┌──────────────────────────────────────────────────────────┬─────────────────┐│
│ │                                                          │  Legend         ││
│ │                                                          │  ┌───────────┐  ││
│ │              ScatterGL Chart Area                        │  │ Column1   │  ││
│ │                                                          │  │ Column2   │  ││
│ │              (80vh height)                               │  │ Column3   │  ││
│ │                                                          │  │ ...       │  ││
│ │                                                          │  └───────────┘  ││
│ └──────────────────────────────────────────────────────────┴─────────────────┘│
└────────────────────────────────────────────────────────────────────────────────┘
```

**Layout Notes:**
- Control bar: single horizontal line, compact (~30px height)
  - **[Load CSV...] button**: Opens native file dialog via `pywebview.create_file_dialog()`
  - **[Reload] button**: Manual refresh for current file
  - **Theme dropdown**: Light/Dark theme selector; persists via `dcc.Store`
  - **☑ Follow Mode checkbox**: Toggle for tail-follow behavior; visible when data is loaded; `--follow` flag sets initial checked state
  - **Status text**: Always shows latest data timestamp, right-aligned
- Timestamp format: **local time** (not UTC), `YYYY-MM-DD HH:MM:SS`
- Empty state: If no CLI argument provided, show only [Load CSV...] button with message "No file loaded"

### 4.2 Styling Specifications

**Typography:**
- Font family: Roboto, Helvetica, Arial, sans-serif
- Size scale: xs=10px, sm=11px, base=12px, md=13px, lg=14px, xl=16px, 2xl=20px

**Light Theme Colours:**
| Element | Value | Contrast vs Text |
|---------|-------|------------------|
| Base | `#ffffff` | 21:1 (AAA) |
| Surface | `#f5f5f5` | 18.5:1 (AAA) |
| Border | `#c0c0c0` | 4.6:1 (AA) |
| Text primary | `#1a1a1a` | — |
| Accent | `#d84315` | 5.9:1 (AA) |
| Plot background | `#ffffff` | 21:1 (AAA) |
| Grid | `#e0e0e0` | 1.3:1 (decorative) |

**Dark Theme Colours:**
| Element | Value | Contrast vs Text |
|---------|-------|------------------|
| Base | `#1a1a1a` | 17.8:1 (AAA) |
| Surface | `#242424` | 14.2:1 (AAA) |
| Border | `#3a3a3a` | 7.2:1 (AAA) |
| Text primary | `#e8e8e8` | — |
| Accent | `#ff6b35` | 4.6:1 (AA) |
| Plot background | `#1a1a1a` | 17.8:1 (AAA) |
| Grid | `#3a3a3a` | 1.4:1 (decorative) |

### 4.3 Interactive Elements

| Element | Behaviour |
|---------|-----------|
| Follow Mode Checkbox | Checked = enabled; unchecked = disabled; auto-unchecks when user pans away from tail |
| Status Text | **Always shows latest data timestamp** (last row) in local time; lets user know data availability even when viewing historical range; prefix changes: "Latest: ..." (following) or "Paused \| Latest: ..." (viewing historical) |
| Legend Items | Click to toggle trace visibility; state preserved across data updates |
| Chart Area | Drag to pan; scroll to zoom; double-click to reset |
| Modebar | Zoom, pan, reset, download buttons (select/lasso removed) |

### 4.4 Responsive Behaviour

- Chart occupies 80vh height
- Legend positioned vertically at right edge (`orientation='v'`)
- Margins: left=60, right=200 (legend), top=60, bottom=60
- Y-axis fixed range (`fixedrange=True`) to prevent vertical zoom; auto-scales to visible data

---

## 5. Behavioural Specifications

### 5.1 Edge Cases Handled

| Edge Case | Behaviour |
|-----------|-----------|
| Empty CSV | Raises `ValueError` |
| CSV with only header | Empty DataFrame → `ValueError` |
| All columns non-numeric | Drops all, raises `ValueError` |
| All rows malformed | Loads zero rows → may raise `ValueError` |
| Column with 100% NaN | Dropped with WARNING log |
| Column with >50% NaN | Retained with INFO log noting ratio |
| Timestamps in UTC | Converted to local timezone, `Z` suffix removed |
| Numeric first column | Retained as numeric index |
| ~~File size >420MB~~ | ~~May exceed dimension validation~~ **REMOVED** — no size limits |
| Very large files (10GB+) | Handled via streaming; only viewport data in memory |

### 5.2 Error States and Recovery

| Error State | Recovery Strategy |
|-------------|-------------------|
| File deleted during follow mode | Log warning, continue polling |
| CSV modified but no new rows | Skip update, log debug message |
| Viewport update failure | Log warning, preserve existing viewport |
| Trace rebuild failure | Log error with traceback, return unmodified figure |
| File truncation (shrink) | Detect via file size; reset viewport to valid range; rebuild index |
| Column schema change mid-follow | Detect column mismatch; re-initialize traces; warn user |
| Concurrent write (partial row) | Skip incomplete final row; retry on next poll |
| ~~Memory exhaustion~~ | **N/A** — streaming architecture prevents this |

### 5.3 Performance Considerations

**Memory Model (Streaming Architecture):**

| Component | Memory Usage |
|-----------|--------------|
| Row index | ~24 bytes per row (offset + length) |
| X-value sparse index | ~16 bytes per 1000 rows (for viewport mapping) |
| Viewport buffer | ≤4,000 rows × columns × 8 bytes |
| Display traces | ≤4,000 points × columns × 16 bytes |
| **Total for 10M row file** | ~240MB row index + ~160KB x-index + ~1MB display buffer |

**Timing Targets:**

| Operation | Target |
|-----------|--------|
| Initial index build | <10 seconds for 10M rows |
| Viewport slice read | <500ms for any range |
| MinMaxLTTB downsample | <10ms for 100k input points (10-30× faster than pure LTTB) |
| Zoom/pan latency | <100ms (GPU-bound, WebGL rendering) |

**Downsampling Strategy:**

| Aspect | Specification |
|--------|---------------|
| Algorithm | MinMaxLTTB (Min-Max preselection + LTTB refinement) |
| Output limit | 4,000 points per trace |
| Trigger | Every viewport change (zoom/pan) |
| Input | Viewport-bounded rows from indexed file |

### 5.4 File Loading and Reloading

#### 5.4.1 Initial Load Behaviour

| Mode | Behaviour |
|------|-----------|
| CLI argument provided | Load file immediately on startup; show chart |
| No CLI argument | Show empty state: [Load CSV...] button with message "No file loaded" |

#### 5.4.2 File Browser Integration

| Action | Implementation |
|--------|---------------|
| [Load CSV...] button click | Trigger `pywebview.create_file_dialog(webview.OPEN_DIALOG, file_types=('CSV files (*.csv)',))` |
| User selects file | Load selected CSV; replace current chart; update window title |
| User cancels dialog | No action (preserve current state) |
| File fails to load | Display error message in UI; log error; preserve previous chart if any |

#### 5.4.3 Manual Reload

| Trigger | Behaviour |
|---------|-----------|
| [Reload] button click | Re-read current CSV from disk; rebuild row index; refresh chart |
| No file loaded | [Reload] button disabled (greyed out) |
| File deleted on disk | Show error message: "File no longer exists"; disable [Reload] button |

### 5.5 Threading and Asynchronous Behaviour

| Component | Thread | Behaviour |
|-----------|--------|-----------|
| Flask server | Background daemon thread | Started via `threading.Thread(daemon=True)` |
| pywebview window | Main thread | Blocking call until window closes |
| Watchdog observer | Background thread | Created by `csv_monitor.py` |
| Dash callbacks | Flask request threads | Handled by Werkzeug threaded mode |

**Thread Safety:**

| Aspect | Approach |
|--------|----------|
| Row index | Immutable after build; rebuilt atomically on file change |
| File reads | Each viewport request opens file handle, reads range, closes |
| Display state | `dcc.Store` components serialize to client (JSON) |
| Interval triggers | Client-side; callbacks execute server-side |

### 5.5 MinMaxLTTB Downsampling Edge Cases

This section documents subtle behaviours when LTTB interacts with dynamic data and viewport changes.

#### 5.5.1 Tail Follow with Data Append

**Scenario:** User is viewing the tail of the data (viewport end within threshold of data end). New rows are appended to the CSV.

**Behaviour:**

| Step | Action |
|------|--------|
| 1 | File monitor detects growth (size increase) |
| 2 | Incrementally index new rows (append to existing index) |
| 3 | Check if viewport was "tailing" before append |
| 4 | If tailing: expand viewport end to include new data; preserve viewport start |
| 5 | Read expanded row range from disk |
| 6 | Apply LTTB to full expanded range → 4,000 points |
| 7 | Update traces; visual density increases proportionally |

**Tail Threshold Scaling Problem:**

| Total Rows | 5% Threshold | Issue |
|------------|--------------|-------|
| 100k | 5,000 rows | Acceptable |
| 1M | 50,000 rows | Acceptable |
| 100M | 5,000,000 rows | Viewport jumps dramatically on append |

**Mitigation:** Use hybrid threshold:

```python
tail_threshold = min(
    total_rows * 0.05,      # 5% of data
    100_000,                 # Hard cap: 100k rows
    time_based_equivalent    # Or: last 5 minutes for timestamp index
)
```

#### 5.5.2 Viewport Range Change (Zoom/Pan)

**Problem:** User specifies viewport in x-axis units (timestamps or values), but LTTB requires row indices for disk reads.

**Required Mapping:**

```text
Viewport bounds (x-values) → Row indices → Byte offsets → Disk read → LTTB
```

**X-Value to Row Index Mapping:**

| Index Type | Mapping Strategy |
|------------|------------------|
| Numeric (sequential) | Direct calculation: `row = x_value - x_start` |
| Numeric (non-sequential) | Binary search on sparse sample |
| Timestamp | Sparse timestamp index + binary search |

**Sparse Index Design:**

- Store every Nth row's x-value (e.g., N=1000)
- Memory: 16 bytes per sample → 160KB for 10M rows
- Lookup: Binary search sparse index for approximate bounds, then linear scan

**Non-Monotonic X-Values:**

| Scenario | Behaviour |
|----------|-----------|
| Timestamps not sorted | **Unsupported** — document as precondition |
| Duplicate timestamps | Allowed — binary search returns first match |
| Gaps in timestamps | Allowed — viewport may include empty regions |

#### 5.5.3 Debounce Timing

**Requirement:** Debounce interval should measure from render *completion*, not trigger.

**Problem with Trigger-Based Debounce:**

```text
t=0s:  Interval fires, callback starts
t=3s:  Callback completes (slow render)
t=5s:  Interval fires again ← Only 2s since last render completed
```

**Solution — Completion-Based Debounce:**

```python
# In update callback:
DEBOUNCE_INTERVAL = 5.0  # seconds

current_time = time.time()
last_complete = metadata.get('last_render_complete_time', 0)

if current_time - last_complete < DEBOUNCE_INTERVAL:
    # Skip this update cycle
    return dash.no_update

# ... perform update ...

# Record completion time AFTER all processing
metadata['last_render_complete_time'] = time.time()
```

**Note:** This measures server-side completion. Client-side WebGL render time (~50-100ms) is not captured but is generally consistent and small relative to debounce interval.

### 5.6 Viewport State Management

This section documents the synchronisation between user interactions, backend processing, and UI state.

#### 5.6.1 The Three Viewport Concepts

| Concept | Definition | Location |
|---------|------------|----------|
| **User Viewport** | What the user has zoomed/panned to (current intent) | Client-side Plotly state |
| **Requested Viewport** | The viewport for which data is currently being fetched | Server-side metadata |
| **Displayed Viewport** | The viewport for which data is currently rendered | Server-side metadata |

**Race Condition Example:**

```text
t=0.0s: User zooms to region A
        → User Viewport = A
        → Backend starts fetching A
        → Requested Viewport = A
        
t=0.3s: User pans to region B (while A still loading)
        → User Viewport = B
        → Requested Viewport = A (still fetching)
        → MISMATCH: User sees old data, expects B
        
t=0.8s: Backend returns data for A
        → Should we display A? NO — user has moved on
        → Discard A, fetch B instead
```

#### 5.6.2 Request Versioning

Track viewport changes with monotonic version numbers to detect stale responses:

```python
# Metadata schema
{
    'viewport_version': 42,           # Incremented on EVERY viewport change
    'pending_request_version': 41,    # Version of in-flight request (None if idle)
    'displayed_version': 40,          # Version of currently rendered data
    'viewport_bounds': {              # Current viewport (user intent)
        'x_start': '2025-01-01T10:00:00',
        'x_end': '2025-01-01T11:00:00'
    },
}
```

**On viewport change (relayoutData callback):**

```python
metadata['viewport_version'] += 1

if metadata['pending_request_version'] is None:
    # No request in flight — start new fetch
    metadata['pending_request_version'] = metadata['viewport_version']
    start_data_fetch(viewport_bounds)
else:
    # Request already in flight — it will be stale when it arrives
    # Do NOT start new fetch yet (avoid request flood)
    pass
```

**On data fetch completion:**

```python
if metadata['pending_request_version'] == metadata['viewport_version']:
    # Response matches current viewport — display it
    update_traces(fetched_data)
    metadata['displayed_version'] = metadata['viewport_version']
    metadata['pending_request_version'] = None
else:
    # Response is STALE — discard and fetch current viewport
    metadata['pending_request_version'] = metadata['viewport_version']
    start_data_fetch(metadata['viewport_bounds'])
```

#### 5.6.3 Viewport State Machine

```text
                    ┌─────────────────────────────────────────┐
                    │                                         │
                    ▼                                         │
              ┌──────────┐                                    │
              │   IDLE   │◀────────────────────────┐          │
              └────┬─────┘                         │          │
                   │                               │          │
     User changes  │                     Response  │          │
     viewport      │                     matches   │          │
                   ▼                     viewport  │          │
              ┌──────────┐                         │          │
              │ FETCHING │─────────────────────────┘          │
              └────┬─────┘                                    │
                   │                                          │
     User changes  │                                          │
     viewport      │                                          │
     (again)       │                                          │
                   ▼                                          │
              ┌──────────┐      Response arrives              │
              │  STALE   │────────────────────────────────────┘
              └──────────┘      (discard, re-fetch)
                   │
                   │ User changes viewport (yet again)
                   └──────────────┐
                                  │
                                  ▼
                            (stays STALE)
```

#### 5.6.4 Debounce vs Throttle for Rapid Interactions

**Problem:** User panning continuously generates many relayoutData events.

| Strategy | Behaviour | Trade-off |
|----------|-----------|-----------|
| **No limit** | Every event triggers fetch | Request flood, wasted computation |
| **Debounce (300ms)** | Wait until user stops, then fetch | Delay before seeing data |
| **Throttle (200ms)** | Max 1 fetch per 200ms | User sees updates during pan |
| **Hybrid** | Throttle during interaction, debounce after | Best of both |

**Recommended Hybrid Strategy:**

```python
THROTTLE_INTERVAL = 0.2   # Max 5 requests/second during interaction
DEBOUNCE_DELAY = 0.3      # Wait 300ms after interaction stops

current_time = time.time()
last_request_time = metadata.get('last_request_time', 0)
last_interaction_time = metadata.get('last_interaction_time', 0)

# Update interaction timestamp
metadata['last_interaction_time'] = current_time

# Throttle: skip if too soon since last request
if current_time - last_request_time < THROTTLE_INTERVAL:
    return dash.no_update

# Debounce: if user is actively interacting, let throttle handle it
# If user stopped, wait for debounce delay
# (In practice, Dash doesn't support post-delay triggers easily;
#  implement via dcc.Interval with short period checking interaction age)

metadata['last_request_time'] = current_time
# ... proceed with fetch
```

#### 5.6.5 Follow Mode and Manual Interaction Conflict

**Scenario:** Follow mode is active. User manually pans to examine historical data.

**Design Options:**

| Option | Behaviour | UX Impact |
|--------|-----------|-----------|
| A | Auto-disable follow mode when user pans away | Clear intent; user must re-enable |
| B | Pause follow mode; resume when user returns to tail | Smart but complex |
| C | Follow mode always updates; may override user viewport | Frustrating; user loses position |

**Chosen: Option A with visual feedback**

```python
# On viewport change (relayoutData):
if follow_mode_enabled:
    is_at_tail = check_tail_threshold(viewport_bounds, data_bounds)
    
    if not is_at_tail:
        # User navigated away from tail
        follow_mode_enabled = False
        show_notification("Follow mode paused — you've navigated away from latest data")
```

**UI Design:**

| Element | Implementation |
|---------|----------------|
| Control type | Checkbox (not button) — clearer toggle state |
| Layout | Horizontal compact: `☑ Follow Mode \| Latest: 2025-12-09 10:30:07` |
| Vertical space | Single line (~30px); positioned above chart |
| State indication | Checkbox checked/unchecked + status text |
| Timestamp format | Local time: `YYYY-MM-DD HH:MM:SS` (not UTC) |
| Timestamp content | **Always shows last row timestamp**, regardless of viewport position |
| Auto-pause feedback | Status text changes: `Latest: ...` → `Paused \| Latest: ...` |

#### 5.6.6 Progressive Data Loading (Optional Enhancement)

For smoother UX during viewport changes, maintain two data layers:

| Layer | Content | Purpose |
|-------|---------|---------|
| **Full-View Cache** | LTTB of entire dataset (4,000 points) | Instant fallback; always available |
| **Viewport Cache** | LTTB of current viewport (4,000 points) | High-resolution detail |

**On viewport change:**

```text
1. Immediately render from Full-View Cache
   → User sees data instantly (lower resolution)
   
2. Start background fetch for Viewport Cache
   → Request high-res data for new viewport
   
3. When Viewport Cache ready, swap in
   → Smooth transition; no loading indicator needed
```

**Benefits:**
- No blank screen during data loading
- Perceived instant response
- Data appears to "sharpen" as zoom progresses

**Trade-off:**
- Requires maintaining full-view LTTB in memory (~128KB for 4000 points × 4 columns × 8 bytes)
- Two LTTB computations (one for full view, one for viewport)

#### 5.6.7 Viewport Persistence

**Decision:** No persistence. Every launch starts at full view.

**Rationale:**
- Simpler implementation
- Predictable behaviour — no hidden state
- Users can quickly pan/zoom to region of interest
- Avoids confusion when CSV content changes between sessions

### 5.7 Data Integrity Constraints

| Constraint | Requirement | Handling if Violated |
|------------|-------------|----------------------|
| Monotonic x-values | Timestamps/indices must be sorted ascending | Log error; refuse to load |
| Consistent column count | All rows must have same column count | Skip malformed rows; log warning |
| Consistent column types | Column dtypes should not change mid-file | Re-detect on follow; warn if changed |
| Complete rows | Final row must be complete | Skip incomplete final row |
| UTF-8 encoding | File must be valid UTF-8 | Fail with clear error message |

---

## 6. Test Coverage Summary

### 6.1 Tested Behaviours

| Module | Test File | Key Behaviours |
|--------|-----------|----------------|
| `csv_loader.py` | `test_csv_loader.py` | Valid CSV loading, malformed row handling, first column as index, dimension validation, oversized file rejection |
| `column_filter.py` | `test_column_filter.py` | Mixed-type filtering, all-numeric retention, no-numeric error, all-NaN column dropping, high NaN ratio logging, NaN ratio calculation |
| `chart_app.py` | `test_chart_app.py` | Trace-per-column generation, line mode, NaN gap handling, trace names match columns, app instance type |
| `main.py` | `test_main.py` | Port discovery, server startup parameters, window creation, CLI argument parsing, error exit codes |

### 6.2 Test Categories

| Category | Files | Description |
|----------|-------|-------------|
| Unit | `test_csv_loader.py`, `test_column_filter.py`, `test_chart_app.py`, `test_main.py` | Isolated function testing with fixtures |
| Integration | `test_error_handling_integration.py` | Cross-module error propagation, logging capture |
| Performance | `test_chart_performance.py`, `test_performance_validation.py` | Timing benchmarks, memory tracking, scaling characteristics |

### 6.3 Key Test Scenarios

**CSV Loading:**

- `test_load_csv_valid` — sample.csv yields 23 columns, Timestamp index
- `test_load_csv_malformed_rows` — malformed rows skipped silently
- ~~`test_dimension_validation_rejects_oversized`~~ **OBSOLETE** — no dimension limits

**Column Filtering:**

- `test_filter_numeric_columns_mixed` — retains only `age`, `salary`, `bonus` from mixed DataFrame
- `test_filter_drops_all_nan_columns` — all-NaN column dropped, warning logged
- `test_filter_sample_csv` — sample.csv yields exactly 23 numeric columns

**Chart Application:**

- `test_traces_use_line_mode` — `mode='lines'` property set correctly
- `test_traces_handle_nan_gaps` — all traces have `connectgaps=False`
- `test_figure_title` — figure title contains source filename

**Main Entry Point:**

- `test_find_available_port` — discovered port can be bound
- `test_exit_code_file_not_found` — exit code 1 for missing file
- `test_exit_code_unexpected_error` — exit code 2 for runtime errors

**Performance:**

- `test_app_creation_time` — app creation <1s for 100k×10
- `test_nan_handling_performance` — handles 5% NaN values across 500k rows
- `test_column_scaling` — 20 columns < 5× time of 5 columns
- ~~`test_memory_under_budget`~~ **OBSOLETE** — streaming removes memory ceiling
- ~~`test_full_pipeline_timing`~~ **NEEDS REVISION** — timing targets change with streaming

---

## 7. Build and Distribution

### 7.1 Build Process

**Prerequisites:**
1. Python 3.13+ via UV package manager
2. C compiler (MSVC recommended for Windows)
3. Nuitka build dependency: `uv add --optional nuitka`

**Execution:**
```bash
python build.py
```

**Build Script Actions:**
1. Verify Nuitka availability
2. Clean `dist/` directory
3. Invoke Nuitka compilation with bundled dependencies
4. Verify executable creation
5. Report file size (~45-60 MB)

### 7.2 Packaging Details

**Nuitka Flags:**

| Flag | Purpose |
|------|---------|
| `--standalone` | Bundle Python interpreter and all dependencies |
| `--onefile` | Single executable (not folder) |
| `--enable-plugin=no-qt` | Disable Qt auto-detection |
| `--follow-imports` | Recursively include imported modules |
| `--include-package=...` | Explicit package inclusion |
| `--include-data-dir=...` | Include templates and JSON configs |
| `--nofollow-import-to=pytest,unittest,test` | Exclude test frameworks |
| `--windows-console-mode=disable` | GUI-only (no console window) |

### 7.3 Platform Targets

| Platform | Status | Notes |
|----------|--------|-------|
| Windows 11 | Tested | Primary target; MSVC compiler recommended |
| Windows 10 | Expected to work | Not explicitly tested |
| macOS | Untested | pywebview dependencies may vary |
| Linux | Untested | pywebview dependencies may vary |

**Cross-Compilation:** Not supported. Build must occur on target platform.

---

## Appendices

### Appendix A: Sample CSV Structure

The bundled `sample.csv` demonstrates expected data format:

- **Rows:** 107 data rows (plus header)
- **Columns:** 24 total (1 timestamp + 23 numeric metrics)
- **Domain:** .NET process memory and GC statistics
- **File size:** ~20 KB

**Column Names:**
```
Timestamp, WorkingSetMB, PrivateBytesMB, PeakWorkingSetMB, PeakPrivateBytesMB,
PagedMemoryMB, NonPagedMemoryMB, Gen0SizeMB, Gen1SizeMB, Gen2SizeMB,
LOHSizeMB, POHSizeMB, GCTotalHeapMB, GCTotalCommittedMB, Gen0Collections,
Gen1Collections, Gen2Collections, Gen0FragmentedMB, Gen1FragmentedMB,
Gen2FragmentedMB, LOHFragmentedMB, ThreadCount, HandleCount, ProcessorCount
```

### Appendix B: LTTB Downsampling Algorithm

The Largest-Triangle-Three-Buckets (LTTB) algorithm preserves visual shape when reducing point density:

1. Always retain first and last point
2. Divide remaining points into equal-sized buckets
3. For each bucket, select point forming largest triangle with:
   - Previous selected point
   - Average of next bucket
4. Repeat for all buckets

**Advantages over stride sampling:**
- Preserves peaks and troughs
- Maintains visual fidelity at reduced point counts
- Computationally efficient (O(n) single pass)

**Reference Implementation:**
```python
def lttb_downsample(x: np.ndarray, y: np.ndarray, threshold: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Largest-Triangle-Three-Buckets downsampling.
    
    Args:
        x: X-axis values (timestamps or indices)
        y: Y-axis values (numeric data)
        threshold: Maximum number of points to return
        
    Returns:
        Tuple of (downsampled_x, downsampled_y)
    """
    n = len(x)
    if n <= threshold:
        return x, y
    
    # Always include first and last points
    sampled_indices = [0]
    
    # Bucket size for interior points
    bucket_size = (n - 2) / (threshold - 2)
    
    a = 0  # Previous selected point index
    
    for i in range(threshold - 2):
        # Calculate bucket boundaries
        bucket_start = int((i + 1) * bucket_size) + 1
        bucket_end = int((i + 2) * bucket_size) + 1
        bucket_end = min(bucket_end, n - 1)
        
        # Calculate average of next bucket
        next_bucket_start = bucket_end
        next_bucket_end = int((i + 3) * bucket_size) + 1
        next_bucket_end = min(next_bucket_end, n)
        
        avg_x = np.mean(x[next_bucket_start:next_bucket_end])
        avg_y = np.mean(y[next_bucket_start:next_bucket_end])
        
        # Find point in current bucket with largest triangle area
        max_area = -1
        max_area_index = bucket_start
        
        for j in range(bucket_start, bucket_end):
            # Triangle area = 0.5 * |x_a(y_j - y_avg) + x_j(y_avg - y_a) + x_avg(y_a - y_j)|
            area = abs(
                (x[a] - avg_x) * (y[j] - y[a]) -
                (x[a] - x[j]) * (avg_y - y[a])
            ) * 0.5
            
            if area > max_area:
                max_area = area
                max_area_index = j
        
        sampled_indices.append(max_area_index)
        a = max_area_index
    
    sampled_indices.append(n - 1)
    
    return x[sampled_indices], y[sampled_indices]
```

### Appendix C: Colour Palettes

**Design Principles:**
- Colorblind-safe: Based on Okabe-Ito, Paul Tol, and Kelly's maximum contrast palettes
- WCAG AA compliant: All trace colors meet ≥3:1 contrast ratio against plot backgrounds
- Perceptually distinct: Colors chosen to maximize differentiability across vision types
- Extended palette: 20 colors to support files with many columns without cycling

**Light Theme (20 colors, ordered by perceptual priority):**
```python
LIGHT_PALETTE = [
    '#E69F00',  # orange        (Okabe-Ito)      — 4.1:1 contrast vs white
    '#0072B2',  # blue          (Okabe-Ito)      — 5.4:1
    '#009E73',  # bluish green  (Okabe-Ito)      — 4.2:1
    '#D55E00',  # vermillion    (Okabe-Ito)      — 5.7:1
    '#CC6677',  # rose          (Tol muted)      — 4.8:1
    '#882255',  # wine          (Tol vibrant)    — 8.6:1
    '#44AA99',  # teal          (Tol vibrant)    — 3.4:1
    '#117733',  # green         (Tol vibrant)    — 7.9:1
    '#332288',  # indigo        (Tol vibrant)    — 10.7:1
    '#AA4499',  # purple        (Tol vibrant)    — 5.2:1
    '#CC79A7',  # reddish purple (Okabe-Ito)     — 4.5:1
    '#999933',  # olive         (Tol vibrant)    — 4.9:1
    '#BE0032',  # red           (Kelly)          — 7.0:1
    '#F3C300',  # yellow        (Kelly)          — 3.2:1
    '#875692',  # purple        (Kelly)          — 6.4:1
    '#F38400',  # orange        (Kelly)          — 4.0:1
    '#008856',  # green         (Kelly)          — 5.8:1
    '#0067A5',  # blue          (Kelly)          — 5.9:1
    '#882D17',  # brown         (Kelly)          — 9.2:1
    '#8DB600',  # lime          (Kelly)          — 3.5:1
]
```

**Dark Theme (20 colors, matched perceptual equivalents):**
```python
DARK_PALETTE = [
    '#FFA94D',  # orange        (lightened Okabe-Ito)  — 5.2:1 contrast vs #1a1a1a
    '#5BA3E8',  # blue          (lightened Okabe-Ito)  — 4.8:1
    '#2ECC94',  # bluish green  (lightened Okabe-Ito)  — 5.1:1
    '#FF7A3D',  # vermillion    (lightened Okabe-Ito)  — 5.9:1
    '#E88BA5',  # rose          (lightened Tol)        — 5.3:1
    '#C8659D',  # wine          (lightened Tol)        — 5.5:1
    '#66D4C2',  # teal          (lightened Tol)        — 6.4:1
    '#4DB870',  # green         (lightened Tol)        — 5.7:1
    '#6B7FDB',  # indigo        (lightened Tol)        — 4.2:1
    '#D67AC4',  # purple        (lightened Tol)        — 5.0:1
    '#E89CC6',  # reddish purple (lightened Okabe-Ito) — 4.9:1
    '#D4D45C',  # olive         (lightened Tol)        — 6.8:1
    '#FF5A6E',  # red           (lightened Kelly)      — 5.1:1
    '#FFD966',  # yellow        (lightened Kelly)      — 6.2:1
    '#B589C0',  # purple        (lightened Kelly)      — 4.5:1
    '#FFA94D',  # orange        (lightened Kelly)      — 5.2:1
    '#4DB88A',  # green         (lightened Kelly)      — 5.3:1
    '#4D9DD9',  # blue          (lightened Kelly)      — 4.9:1
    '#C77A5C',  # brown         (lightened Kelly)      — 4.7:1
    '#B8D966',  # lime          (lightened Kelly)      — 6.5:1
]
```

**Bad Data Color (Both Themes):**
```python
BAD_DATA_COLOR = '#DDDDDD'  # Light gray (Tol standard)
```

**Contrast Verification Notes:**
- All light theme colors tested against `#ffffff` (white plot background)
- All dark theme colors tested against `#1a1a1a` (dark plot background)
- Minimum contrast ratio: 3:1 (WCAG AA for graphics/UI components)
- Most colors exceed 4.5:1 (WCAG AA for text)
- Palette order prioritizes most distinguishable pairs first (orange/blue, green/red analogs)

**Colorblind Safety:**
- Deuteranopia (green-blind, ~5% of males): First 12 colors highly distinct; full palette distinguishable
- Protanopia (red-blind, ~2% of males): First 12 colors highly distinct; full palette distinguishable
- Tritanopia (blue-blind, <1%): 18 of 20 colors distinct (some yellow/lime/olive overlap possible)
- Verification: Use [Coblis](https://www.color-blindness.com/coblis-color-blindness-simulator/) or [Colorblindor](https://www.colorblindor.com/)
- **Note**: For files with >20 columns, colors cycle. Consider additional visual cues (line width, dash patterns) if many traces must be compared simultaneously

### Appendix D: CSS Variables Reference

```css
/* Light Theme */
:root {
    --color-base: #ffffff;
    --color-surface: #f5f5f5;
    --color-border: #c0c0c0;
    --color-text-primary: #1a1a1a;
    --color-text-secondary: #4a4a4a;
    --color-accent: #d84315;
    --color-accent-hover: #bf360c;
    --color-plot-bg: #ffffff;
    --color-grid: #e0e0e0;
    
    --font-xs: 10px;
    --font-sm: 11px;
    --font-base: 12px;
    --font-md: 13px;
    --font-lg: 14px;
    --font-xl: 16px;
    --font-2xl: 20px;
    
    --spacing-xs: 4px;
    --spacing-sm: 8px;
    --spacing-md: 12px;
    --spacing-lg: 16px;
    --spacing-xl: 24px;
}

/* Dark Theme */
[data-theme="dark"] {
    --color-base: #1a1a1a;
    --color-surface: #242424;
    --color-border: #3a3a3a;
    --color-text-primary: #e8e8e8;
    --color-text-secondary: #a0a0a0;
    --color-accent: #ff6b35;
    --color-accent-hover: #ff8a5b;
    --color-plot-bg: #1a1a1a;
    --color-grid: #3a3a3a;
}
```

### Appendix E: CLI Interface

```
usage: csv_chart_plotter [-h] [--follow] [--theme {light,dark}] [csv_file]

Interactive CSV time-series chart viewer

positional arguments:
  csv_file              (Optional) Path to CSV file to visualize

optional arguments:
  -h, --help            show this help message and exit
  --follow              Enable follow mode (auto-reload on file changes)
  --theme {light,dark}  Initial color theme (default: light); switchable via UI
```

**Examples:**

```bash
# Basic usage
csv_chart_plotter data.csv

# With follow mode
csv_chart_plotter --follow metrics.csv

# Dark theme
csv_chart_plotter --theme dark output.csv
```

---

### Appendix F: Obsolete Constraints from Original Implementation

The original implementation contained constraints that are **no longer applicable** when using a streaming/indexed architecture. This appendix documents them for historical clarity and to prevent re-introduction.

| Obsolete Constraint | Original Value | Why Obsolete |
|---------------------|----------------|--------------|
| `MAX_ROWS` | 1,000,000 | Streaming reads only viewport data; full file never in memory |
| `MAX_COLUMNS` | 40 | Display columns limited by legend readability, not memory |
| `CHUNK_SIZE` | 50,000 | Chunked loading replaced by indexed random access |
| `CSVDimensionError` | Custom exception | No dimension validation needed |
| `validate_csv_dimensions()` | Pre-flight check | No pre-validation needed |
| Memory budget (2GB) | Soft limit | Memory bounded by display buffer (~1MB), not data size |
| File size estimation | Heuristic | Exact row count from index; no estimation |

**Root Cause of Obsolescence:**

The original design loaded the entire CSV into a pandas DataFrame before downsampling for display. This created a memory ceiling proportional to data size:

```text
Memory = rows × columns × 8 bytes (float64)
1M rows × 40 columns × 8 bytes = 320 MB minimum
```

With LTTB downsampling to 4,000 points, the display buffer is constant:

```text
Display Memory = 4,000 points × columns × 16 bytes ≈ 1 MB for 40 columns
```

The architectural insight: **downsampling decouples display memory from data size**, enabling arbitrarily large files if data is streamed rather than bulk-loaded.

---

*End of specification document.*
