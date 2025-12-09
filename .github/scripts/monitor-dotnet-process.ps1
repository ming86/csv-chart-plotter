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

# Ensure output directory exists
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    Write-Host "Created output directory: $OutputDir"
}

# Generate filename with timestamp
$timestamp = Get-Date -Format "yyMMdd_HHmmss"
$tempFile = Join-Path $env:TEMP "dotnet-counters-temp-$timestamp.csv"
$outputFile = Join-Path $OutputDir "memory-metrics-$timestamp.csv"

Write-Host "Waiting for process: $ProcessName"
Write-Host "Output file: $outputFile"
Write-Host ""

# Wait for process to start
while ($true) {
    $process = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue
    if ($process) {
        $pid = $process.Id
        Write-Host "Process found: $ProcessName (PID: $pid)"
        break
    }
    Write-Host "Process not found. Retrying in 2 seconds..."
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
    --process-id $pid `
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
