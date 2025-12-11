# Building Standalone Executable

Instructions for compiling CSV Chart Plotter to a standalone executable using Nuitka.

## Prerequisites

### Required Software

1. **Python 3.13+** (via UV)
2. **C Compiler:**
   - **macOS:** Xcode Command Line Tools (`xcode-select --install`)
   - **Windows:** [Visual Studio Build Tools 2026](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2026) with:
     - "Desktop development with C++" workload
     - Windows XX SDK (from Individual Components)
   - **Linux:** GCC (`sudo apt install build-essential`)
   
   > **Windows Installation:** Download Build Tools from the link above, run the installer, select "Desktop development with C++" workload, then go to Individual Components tab and check the latest Windows SDK (e.g., Windows 11 SDK 10.0.22621).

3. **Nuitka:**

   ```bash
   uv add --dev nuitka
   ```

### Verify Installation

```bash
# Check Nuitka
uv run python -m nuitka --version

# Check compiler (macOS/Linux)
gcc --version
clang --version

# Check compiler (Windows) - must run from Developer Command Prompt
cl.exe
```

**Critical for Windows:**

- Python 3.13 requires MSVC (MinGW not supported due to internal layout changes)
- Windows SDK must be installed alongside MSVC
- Standard `cmd.exe` or PowerShell will not have MSVC in PATH
- Always use "Developer Command Prompt for VS 2026" from Start Menu

## Build Process

### Standard Build

```bash
python build.py
```

**Expected Output:**

```text
=== CSV Chart Plotter Build Script ===
Nuitka version: 2.x.x
Cleaning previous build artifacts...
Starting Nuitka compilation...
[Nuitka progress output...]
Executable created: dist/csv-chart-plotter
=== Build completed successfully ===
```

**Duration:**

- First build: 5-15 minutes
- Subsequent builds: 2-5 minutes (cached modules)

### Run Executable

```bash
# macOS/Linux
./dist/csv-chart-plotter sample.csv

# Windows
.\dist\csv-chart-plotter.exe sample.csv
```

## Build Flags

| Flag | Purpose |
|------|---------|
| `--standalone` | Bundle Python interpreter and dependencies |
| `--onefile` | Single executable (not folder) |
| `--follow-imports` | Include all imported modules |
| `--include-package=X` | Explicitly include package |
| `--include-package-data=X` | Include non-Python assets |
| `--nofollow-import-to=X` | Exclude module (reduces size) |

## Troubleshooting

### Windows SDK Not Installed (Windows)

**Symptom:** `Nuitka-Scons:WARNING: Windows SDK must be installed in Visual Studio for it to be usable with Nuitka`

**Solution:**

1. Open "Visual Studio Installer" (from Start Menu)
2. Click "Modify" on "Build Tools for Visual Studio 2026"
3. Go to "Individual components" tab
4. Search for "Windows SDK"
5. Check latest "Windows XX SDK" (e.g., Windows 11 SDK 10.0.22621)
6. Click "Modify" to install (~1-2 GB download)

**If Build Tools not installed:** Download from [visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2026](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2026)

### "The system cannot find the path specified" (Windows)

**Symptom:** Nuitka compilation fails during SCons backend setup with `OSError: The system cannot find the path specified`.

**Root Cause:** Either MSVC not in PATH, or SCons worker threads cannot inherit MSVC environment during parallel compilation.

**Solution:**

1. **Verify Windows SDK is installed** (see above)

2. **Use Developer Command Prompt:**
   - Start Menu → search "Developer Command Prompt for VS 2026"
   - Navigate to project: `cd C:\path\to\csv-chart-plotter`
   - Run build: `uv run build.py`

3. **Verify MSVC availability:**

   ```cmd
   cl.exe
   # Should output: Microsoft (R) C/C++ Optimizing Compiler Version...
   ```

**The build script automatically applies workarounds:**

- `--msvc=latest` forces SCons to use the latest MSVC version
- `--jobs=1` disables parallel compilation (prevents environment inheritance issues)

This makes compilation slower (~5-15min first build) but more reliable.

### Module Import Errors

**Symptom:** Executable fails with `ModuleNotFoundError` despite package being installed.

**Solution:** Add explicit package inclusion to `build.py`:

```python
'--include-package=missing_module',
```

### Executable does not start

Ensure package data is included:

```python
'--include-package-data=plotly',
'--include-package-data=dash',
```

### "No C compiler found" (macOS/Linux)

Install compiler for your platform:

```bash
# macOS
xcode-select --install

# Ubuntu/Debian
sudo apt install build-essential
```

## Platform Notes

### macOS

- Uses Clang from Xcode
- App bundle creation not currently supported (bare executable only)
- May require Gatekeeper exception on first run

### Windows

- **MSVC required** (Python 3.13 requirement)
- Must include Windows SDK with Visual Studio installation
- Run build from Developer Command Prompt
- Disable antivirus during build (false positives common)
- Use `--windows-console-mode=disable` for GUI-only

### Linux

- Requires GTK or Qt for pywebview
- Install: `sudo apt install python3-gi gir1.2-webkit2-4.0`

## Reducing Executable Size

Current size: ~50-70 MB. To reduce:

```python
# Exclude unused packages
'--nofollow-import-to=matplotlib',
'--nofollow-import-to=scipy',
'--nofollow-import-to=tests',

# Use UPX compression (optional)
'--upx-binary=/path/to/upx',
```

## CI/CD Example

GitHub Actions workflow:

```yaml
name: Build

on:
  push:
    tags: ['v*']

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]

    steps:
      - uses: actions/checkout@v4

      - name: Install UV
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: uv sync

      - name: Build executable
        run: uv run python build.py

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: csv-chart-plotter-${{ matrix.os }}
          path: dist/csv-chart-plotter*
```

## Support

- Nuitka documentation: <https://nuitka.net/doc/>
- Project issues: <https://github.com/yourusername/csv-chart-plotter/issues>
