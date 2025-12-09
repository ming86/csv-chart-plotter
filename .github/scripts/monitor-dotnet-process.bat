@echo off
REM Monitor .NET Process Metrics - Windows Batch Wrapper
REM Calls PowerShell script to handle actual monitoring

setlocal

if "%~1"=="" (
    echo Usage: monitor-dotnet-process.bat ^<ProcessName^> [OutputDir] [RefreshIntervalSeconds]
    echo.
    echo Example: monitor-dotnet-process.bat MyApp
    echo Example: monitor-dotnet-process.bat MyApp C:\metrics 1
    exit /b 1
)

set PROCESS_NAME=%~1
set OUTPUT_DIR=%~2
set REFRESH_INTERVAL=%~3

REM Build PowerShell command
set PS_SCRIPT=%~dp0monitor-dotnet-process.ps1

if "%OUTPUT_DIR%"=="" (
    powershell.exe -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -ProcessName "%PROCESS_NAME%"
) else if "%REFRESH_INTERVAL%"=="" (
    powershell.exe -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -ProcessName "%PROCESS_NAME%" -OutputDir "%OUTPUT_DIR%"
) else (
    powershell.exe -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -ProcessName "%PROCESS_NAME%" -OutputDir "%OUTPUT_DIR%" -RefreshIntervalSeconds %REFRESH_INTERVAL%
)

endlocal
