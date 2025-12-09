# Building Standalone Executable

Detailed instructions for compiling CSV Chart Plotter to a standalone Windows executable using Nuitka.

## Prerequisites

### Required Software

1. **Python 3.13+** (installed via UV)
2. **C Compiler** (one of the following):
   - **Microsoft Visual C++ (MSVC)** - Recommended for Windows
     - Install via [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022)
     - Select "Desktop development with C++" workload
   - **MinGW-w64** - Alternative open-source compiler
     - Download from [WinLibs](https://winlibs.com/)
     - Add `bin/` directory to PATH
   - **Clang** - LLVM-based compiler
     - Install via [LLVM releases](https://releases.llvm.org/)

3. **Nuitka** (installed via UV):
   ```powershell
   uv add --optional nuitka
   ```

### Verify Installation

Check compiler availability:

```powershell
# For MSVC
cl.exe

# For MinGW
gcc --version

# For Clang
clang --version
```

Check Nuitka:

```powershell
python -m nuitka --version
```

Expected output: `Commercial: None | Python: 3.13.x | Flavor: CPython | Executable: ...`

## Build Process

### Standard Build

Execute build script:

```powershell
python build.py
```

**Expected Output:**
```
=== CSV Chart Plotter Build Script ===
Nuitka version: 2.8.9
Cleaning previous build artifacts...
Starting Nuitka compilation...
Nuitka command: python -m nuitka --standalone --onefile ...
[Nuitka progress output...]
Executable created: dist\csv-chart-plotter.exe
Size: 45-60 MB (approximate)
=== Build completed successfully ===
Run: dist\csv-chart-plotter.exe sample.csv
```

**Duration:**
- First build: 5-15 minutes (depends on CPU, disk speed)
- Subsequent builds: 2-5 minutes (Nuitka caches compiled modules)

### Manual Compilation

If `build.py` fails, compile manually:

```powershell
python -m nuitka `
  --standalone `
  --onefile `
  --enable-plugin=no-qt `
  --follow-imports `
  --include-package=pandas `
  --include-package=plotly `
  --include-package=dash `
  --include-package=flask `
  --include-package=werkzeug `
  --include-package=dash_html_components `
  --include-package=dash_core_components `
  --include-package-data=plotly `
  --include-package-data=dash `
  --nofollow-import-to=pytest `
  --nofollow-import-to=unittest `
  --nofollow-import-to=test `
  --windows-console-mode=disable `
  --output-dir=dist `
  --output-filename=csv-chart-plotter.exe `
  src/csv_chart_plotter/main.py
```

## Build Flags Explained

| Flag | Purpose |
|------|---------|
| `--standalone` | Bundle all dependencies (Python interpreter + libraries) |
| `--onefile` | Package as single executable (not folder) |
| `--enable-plugin=no-qt` | Disable Qt auto-detection (not used in this project) |
| `--follow-imports` | Recursively include all imported modules |
| `--include-package=<name>` | Explicitly include package (ensures pandas/plotly/dash included) |
| `--include-package-data=<name>` | Include non-Python files (templates, JSON configs) |
| `--nofollow-import-to=<name>` | Exclude module from compilation (reduces size) |
| `--windows-console-mode=disable` | No console window on Windows (GUI-only) |
| `--output-dir=dist` | Output directory for compiled executable |
| `--output-filename=<name>.exe` | Executable filename |

## Verification

### Test Standalone Execution

1. **On development machine** (with Python installed):
   ```powershell
   .\dist\csv-chart-plotter.exe sample.csv
   ```

2. **On clean machine** (without Python):
   - Copy `csv-chart-plotter.exe` to system without Python
   - Copy test CSV file
   - Execute: `csv-chart-plotter.exe <csv_file>`
   - Verify window opens and chart renders

### Expected Behavior

- No console window appears (GUI-only mode)
- Native window opens within 2-5 seconds
- Chart renders with all numeric columns
- No Python installation required on target system

## Troubleshooting

### Compilation Errors

#### Error: "No C compiler found"

**Cause:** MSVC/MinGW/Clang not installed or not in PATH.

**Solution:**
1. Install Visual Studio Build Tools with C++ workload
2. Verify with: `cl.exe` (MSVC) or `gcc --version` (MinGW)
3. Restart terminal to refresh PATH

#### Error: "Module X not found during compilation"

**Cause:** Missing `--include-package` flag for implicit dependency.

**Solution:**
Add flag to `build.py`:
```python
'--include-package=<missing_module>',
```

#### Error: "Out of memory during linking"

**Cause:** Insufficient RAM for large executable linking.

**Solution:**
1. Close other applications to free memory
2. Use `--standalone` without `--onefile` (creates folder instead)
3. Increase system pagefile size

### Runtime Errors

#### Error: "Failed to execute script"

**Cause:** Missing data files or incorrect package includes.

**Solution:**
Ensure `--include-package-data` flags present for plotly and dash:
```python
'--include-package-data=plotly',
'--include-package-data=dash',
```

#### Error: "Port already in use"

**Cause:** Previous Flask server instance still running.

**Solution:**
1. Open Task Manager
2. End any `csv-chart-plotter.exe` processes
3. Retry execution

#### Chart does not render

**Cause:** Missing WebGL support on target system.

**Solution:**
1. Update graphics drivers
2. Verify browser supports WebGL: visit https://get.webgl.org/
3. Check Windows display settings (hardware acceleration enabled)

## Optimisation Strategies

### Reduce Executable Size

Current size: ~45-60 MB. To reduce:

1. **Exclude unused packages:**
   ```python
   '--nofollow-import-to=matplotlib',  # If not used
   '--nofollow-import-to=scipy',       # If not used
   ```

2. **Use UPX compression** (optional):
   ```python
   '--upx-binary=<path_to_upx.exe>',
   ```
   Download UPX: https://upx.github.io/

3. **Disable debug symbols:**
   ```python
   '--remove-output',  # Remove intermediate files
   ```

### Faster Compilation

1. **Use SSD for build directory** (3-5x faster than HDD)
2. **Enable module caching** (automatic in Nuitka 2.8+)
3. **Exclude test code:**
   ```python
   '--nofollow-import-to=tests',
   ```

## Platform-Specific Considerations

### Windows

- **Recommended compiler:** MSVC (best compatibility)
- **Antivirus:** Temporarily disable during build (false positives common)
- **Windows Defender:** Add `dist/` to exclusions

### Cross-Compilation (Not Recommended)

Nuitka does not support cross-compilation. To build for Linux/macOS:
1. Use virtual machine or Docker container with target OS
2. Install Python + dependencies in target environment
3. Run build script on target OS

## Continuous Integration

### GitHub Actions Example

```yaml
name: Build Executable

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      
      - name: Install UV
        run: pip install uv
      
      - name: Install dependencies
        run: uv sync
      
      - name: Build executable
        run: python build.py
      
      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: csv-chart-plotter-windows
          path: dist/csv-chart-plotter.exe
```

## License Compliance

Nuitka-compiled executables must comply with:
- Python Software Foundation License (Python interpreter)
- Licenses of all bundled libraries (pandas, plotly, dash, etc.)

Ensure `LICENSE` file includes all dependency licenses for distribution.

## Support

For Nuitka-specific issues:
- Nuitka GitHub: https://github.com/Nuitka/Nuitka
- Nuitka documentation: https://nuitka.net/doc/

For project-specific build issues:
- Report at: https://github.com/yourusername/CsvChartPlotter/issues
