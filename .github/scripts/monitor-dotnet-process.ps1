# Monitor .NET Process Metrics
# Waits for a target process, then collects System.Runtime metrics via dotnet-counters
# Outputs to CSV with timestamp-based filename

param(
    [Parameter(Mandatory=$true)]
    [string]$ProcessName,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "$PSScriptRoot\..\..\metrics",
    
    [Parameter(Mandatory=$false)]
    [int]$RefreshIntervalSeconds = 1
)

# Strip .exe extension if provided (Get-Process expects name without extension)
$OriginalInput = $ProcessName
$ProcessName = $ProcessName -replace '\.exe$', ''

# Helper function to find process by name (supports wildcards and partial matching)
function Find-TargetProcess {
    param([string]$Name)
    
    # Try exact match first
    $proc = Get-Process -Name $Name -ErrorAction SilentlyContinue
    if ($proc) { return $proc }
    
    # Try wildcard match (process name contains the search term)
    $proc = Get-Process -Name "*$Name*" -ErrorAction SilentlyContinue
    if ($proc) { return $proc }
    
    # Try matching by executable path using WMI (handles cases where ProcessName differs from exe name)
    $wmiProc = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | 
        Where-Object { $_.Name -like "*$Name*" -or $_.ExecutablePath -like "*$Name*" } |
        Select-Object -First 1
    if ($wmiProc) {
        return Get-Process -Id $wmiProc.ProcessId -ErrorAction SilentlyContinue
    }
    
    return $null
}

# Helper function to show similar running processes for debugging
function Show-SimilarProcesses {
    param([string]$SearchTerm)
    
    Write-Host ""
    Write-Host "=== DEBUG: Currently running processes (filtered) ===" -ForegroundColor Yellow
    
    # Get all processes and show those that might be related
    $allProcs = Get-Process -ErrorAction SilentlyContinue | 
        Select-Object -Property ProcessName, Id, Path -Unique |
        Sort-Object ProcessName
    
    # Show processes with similar names (fuzzy match)
    $similar = $allProcs | Where-Object { 
        $_.ProcessName -like "*$SearchTerm*" -or 
        ($_.Path -and $_.Path -like "*$SearchTerm*")
    }
    
    if ($similar) {
        Write-Host "Processes matching '$SearchTerm':" -ForegroundColor Green
        $similar | ForEach-Object {
            Write-Host "  - $($_.ProcessName) (PID: $($_.Id))" -ForegroundColor Cyan
            if ($_.Path) { Write-Host "    Path: $($_.Path)" -ForegroundColor Gray }
        }
    } else {
        Write-Host "No processes found matching '$SearchTerm'" -ForegroundColor Red
        Write-Host ""
        Write-Host "Showing all .NET-related processes:" -ForegroundColor Yellow
        $dotnetProcs = $allProcs | Where-Object { 
            $_.ProcessName -match 'dotnet|aspnet|blazor|maui|wpf|winforms|core' -or
            ($_.Path -and $_.Path -match '\\dotnet\\|\\\.NET\\')
        }
        if ($dotnetProcs) {
            $dotnetProcs | ForEach-Object {
                Write-Host "  - $($_.ProcessName) (PID: $($_.Id))" -ForegroundColor Cyan
            }
        } else {
            Write-Host "  (none found)" -ForegroundColor Gray
        }
    }
    
    Write-Host ""
    Write-Host "Tip: Run 'Get-Process | Select ProcessName, Id | Sort ProcessName' to see all processes" -ForegroundColor Yellow
    Write-Host "=== END DEBUG ===" -ForegroundColor Yellow
    Write-Host ""
}

# Ensure output directory exists
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    Write-Host "Created output directory: $OutputDir"
}

Write-Host "Searching for process: $ProcessName" -ForegroundColor Cyan
Write-Host "  Original input: $OriginalInput"
Write-Host "  Search method: exact match -> wildcard (*$ProcessName*) -> executable path"
Write-Host ""
Write-Host "Tip: Launch your application now if not already running"
Write-Host ""

# Wait for process to start
$retryCount = 0
$showDebugEvery = 5  # Show debug info every N retries
while ($true) {
    $process = Find-TargetProcess -Name $ProcessName
    if ($process) {
        # Handle multiple instances (take first)
        if ($process -is [array]) {
            $foundProcess = $process[0]
            Write-Host "Multiple instances found. Monitoring first match." -ForegroundColor Yellow
        } else {
            $foundProcess = $process
        }
        $targetPid = $foundProcess.Id
        $actualName = $foundProcess.ProcessName
        Write-Host ""
        Write-Host "Process found!" -ForegroundColor Green
        Write-Host "  Name: $actualName"
        Write-Host "  PID: $targetPid"
        if ($foundProcess.Path) {
            Write-Host "  Path: $($foundProcess.Path)"
        }
        
        # Generate timestamp NOW (when monitoring actually begins)
        $timestamp = Get-Date -Format "yyMMdd_HHmmss"
        $tempFile = Join-Path $env:TEMP "dotnet-counters-temp-$timestamp.csv"
        $outputFile = Join-Path $OutputDir "memory-metrics-$timestamp.csv"
        Write-Host "  Output: $outputFile"
        
        break
    }
    $retryCount++
    Write-Host "[$retryCount] Process '$ProcessName' not found. Retrying in 2 seconds..."
    
    # Show debug info periodically to help user identify the correct process name
    if ($retryCount % $showDebugEvery -eq 0) {
        Show-SimilarProcesses -SearchTerm $ProcessName
    }
    
    Start-Sleep -Seconds 2
}

# Wait brief moment for .NET runtime initialization
Start-Sleep -Seconds 2

# Define counters to collect (System.Runtime metrics, no web metrics)
$counters = @(
    "cpu-usage",
    "working-set",
    "gc-heap-size",
    "gen-0-gc-count",
    "gen-1-gc-count", 
    "gen-2-gc-count",
    "gen-0-size",
    "gen-1-size",
    "gen-2-size",
    "loh-size",
    "poh-size",
    "alloc-rate",
    "assembly-count",
    "exception-count",
    "threadpool-thread-count",
    "monitor-lock-contention-count",
    "threadpool-queue-length",
    "threadpool-completed-items-count",
    "active-timer-count"
)

$counterSpec = "System.Runtime[$($counters -join ',')]"

Write-Host ""
Write-Host "Starting dotnet-counters collection..."
Write-Host "Counters: System.Runtime (all metrics)"
Write-Host "Refresh interval: $RefreshIntervalSeconds second(s)"
Write-Host "Press Ctrl+C to stop or wait for process to exit"
Write-Host ""

# Run dotnet-counters (write to temp file)
& dotnet-counters collect `
    --process-id $targetPid `
    --format csv `
    --output $tempFile `
    --refresh-interval $RefreshIntervalSeconds `
    --counters $counterSpec

# Post-process CSV to normalize timestamp format to yyyy-MM-dd HH:mm:ss
if (Test-Path $tempFile) {
    Write-Host ""
    Write-Host "Converting timestamp format to yyyy-MM-dd HH:mm:ss..."
    
    $lines = Get-Content $tempFile
    $outputLines = @()
    
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($i -eq 0) {
            # Keep header as-is
            $outputLines += $lines[$i]
        } else {
            $parts = $lines[$i] -split ',', 2
            if ($parts.Count -eq 2) {
                try {
                    # Parse timestamp and reformat to yyyy-MM-dd HH:mm:ss
                    $dt = [DateTime]::Parse($parts[0])
                    $newTimestamp = $dt.ToString("yyyy-MM-dd HH:mm:ss")
                    $outputLines += "$newTimestamp,$($parts[1])"
                } catch {
                    # If parsing fails, keep original line
                    $outputLines += $lines[$i]
                }
            } else {
                # Keep malformed lines as-is
                $outputLines += $lines[$i]
            }
        }
    }
    
    # Write normalized CSV
    $outputLines | Out-File -FilePath $outputFile -Encoding UTF8
    
    # Clean up temp file
    Remove-Item $tempFile -ErrorAction SilentlyContinue
}

# Post-collection summary
if (Test-Path $outputFile) {
    $fileSize = (Get-Item $outputFile).Length
    $fileSizeMB = [math]::Round($fileSize / 1MB, 2)
    Write-Host ""
    Write-Host "Collection complete."
    Write-Host "Output file: $outputFile"
    Write-Host "File size: $fileSizeMB MB"
    
    # Display first few lines as preview
    Write-Host ""
    Write-Host "Preview (first 3 data rows):"
    Get-Content $outputFile -TotalCount 4
} else {
    Write-Host ""
    Write-Host "Warning: Output file not created. Process may have exited immediately."
}

Write-Host ""
Write-Host "Note: Memory values (working-set, gc-heap-size, etc.) are in bytes."
Write-Host "To convert to MB: divide by 1048576"
