# .NET Process Monitoring Scripts

Scripts for monitoring .NET process metrics using `dotnet-counters` and exporting to CSV format compatible with CSV Chart Plotter.

## Prerequisites

Install `dotnet-counters` globally:

```bash
dotnet tool install --global dotnet-counters
```

Verify installation:

```bash
dotnet-counters --version
```

## Usage

### Windows (PowerShell)

```powershell
# Monitor process with default settings
.\monitor-dotnet-process.ps1 -ProcessName "MyApp"

# Specify custom output directory
.\monitor-dotnet-process.ps1 -ProcessName "MyApp" -OutputDir "C:\metrics"

# Custom refresh interval (default: 1 second)
.\monitor-dotnet-process.ps1 -ProcessName "MyApp" -RefreshIntervalSeconds 5
```

### Windows (Batch File)

```cmd
REM Monitor with defaults
monitor-dotnet-process.bat MyApp

REM Custom output directory
monitor-dotnet-process.bat MyApp C:\metrics

REM Custom refresh interval
monitor-dotnet-process.bat MyApp C:\metrics 5
```

## Output

**Filename Format:** `memory-metrics-YYMMDD_HHMMSS.csv`

**Default Location:** `../../metrics/` (relative to script directory)

**Collected Metrics:**

| Metric | Unit | Description |
|--------|------|-------------|
| `cpu-usage` | % | CPU utilization |
| `working-set` | bytes | Physical memory usage (≈ private bytes) |
| `gc-heap-size` | bytes | Managed heap size |
| `gen-0-gc-count` | count | Generation 0 collections |
| `gen-1-gc-count` | count | Generation 1 collections |
| `gen-2-gc-count` | count | Generation 2 collections |
| `gen-0-size` | bytes | Generation 0 size |
| `gen-1-size` | bytes | Generation 1 size |
| `gen-2-size` | bytes | Generation 2 size |
| `loh-size` | bytes | Large Object Heap size |
| `poh-size` | bytes | Pinned Object Heap size |
| `alloc-rate` | bytes/sec | Allocation rate |
| `assembly-count` | count | Loaded assemblies |
| `exception-count` | count | Exceptions thrown |
| `threadpool-thread-count` | count | Thread pool threads |
| `monitor-lock-contention-count` | count | Lock contention events |
| `threadpool-queue-length` | count | Queued work items |
| `threadpool-completed-items-count` | count | Completed work items |
| `active-timer-count` | count | Active timers |

**Note:** Memory values (working-set, gc-heap-size, etc.) are in **bytes**. To convert to MB: divide by 1,048,576.

## CSV Format

The output CSV uses standardized timestamp format optimized for CSV Chart Plotter:

```csv
Timestamp,System.Runtime[cpu-usage],System.Runtime[working-set],...
2025-12-10 10:30:00,15.2,52428800,...
2025-12-10 10:30:01,16.1,52441088,...
```

- First column: Local timestamp in `yyyy-MM-dd HH:mm:ss` format (scannable, sortable, parsable)
- Subsequent columns: Metric values

## Visualization with CSV Chart Plotter

View metrics in real-time:

```bash
# Start monitoring in background
start monitor-dotnet-process.bat MyApp

# Open CSV Chart Plotter in follow mode (from repo root)
uv run csv-chart-plotter metrics/memory-metrics-*.csv --follow
```

## Script Behavior

1. **Wait for Process:** Polls every 2 seconds until target process starts
2. **Runtime Initialization:** 2-second delay after process detection for EventPipe setup
3. **Collection:** Continuous metric collection until process exits or Ctrl+C
4. **Clean Shutdown:** Flushes buffered data to CSV on exit
5. **Auto-Reconnect:** Not supported; script exits when process terminates

## Troubleshooting

**"Process not found"**

- Provide process name **without** `.exe` extension (e.g., `MyApp`, not `MyApp.exe`)
- If you include `.exe`, the script will strip it automatically
- Verify process name matches exactly (case-insensitive on Windows)
- Check process is .NET Core 3.0+ or .NET 5+
- Ensure the process is actually running before or during script execution

**"Unable to connect to process"**

- Ensure sufficient privileges (same user or administrator)
- Verify EventPipe is enabled (default in .NET Core 3.0+)

**Empty CSV file**

- Process exited too quickly (before first sample)
- Increase `RefreshIntervalSeconds` if too much overhead

**High overhead**

- Reduce refresh frequency (increase `RefreshIntervalSeconds`)
- Typical overhead: <2% CPU with 1-second interval

## Private Bytes Note

`working-set` approximates private bytes but measures physical memory. For exact private bytes on Windows:

```powershell
(Get-Process -Name "MyApp").PrivateMemorySize64 / 1MB
```

Consider adding custom instrumentation via `EventSource` if precise private bytes logging is required.
