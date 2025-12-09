"""Pytest fixtures for CSV Chart Plotter tests."""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile


@pytest.fixture
def sample_csv_path():
    """Path to the sample CSV file in the project root."""
    return Path(__file__).parent.parent / "sample.csv"


@pytest.fixture
def temp_csv_file():
    """Create a temporary CSV file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("Timestamp,Value1,Value2,Label\n")
        f.write("2025-01-01T10:00:00Z,1.0,10.0,A\n")
        f.write("2025-01-01T10:01:00Z,2.0,20.0,B\n")
        f.write("2025-01-01T10:02:00Z,3.0,30.0,C\n")
        f.flush()
        temp_path = Path(f.name)
    yield temp_path
    # Cleanup
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def numeric_dataframe():
    """DataFrame with all numeric columns."""
    return pd.DataFrame({
        "col1": [1.0, 2.0, 3.0, 4.0, 5.0],
        "col2": [10, 20, 30, 40, 50],
        "col3": [0.1, 0.2, 0.3, 0.4, 0.5],
    })


@pytest.fixture
def mixed_dataframe():
    """DataFrame with mixed numeric and non-numeric columns."""
    return pd.DataFrame({
        "numeric1": [1.0, 2.0, 3.0],
        "numeric2": [10, 20, 30],
        "string_col": ["a", "b", "c"],
        "date_col": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]),
    })


@pytest.fixture
def dataframe_with_nans():
    """DataFrame with various NaN patterns."""
    return pd.DataFrame({
        "no_nan": [1.0, 2.0, 3.0, 4.0],
        "some_nan": [1.0, np.nan, 3.0, np.nan],
        "all_nan": [np.nan, np.nan, np.nan, np.nan],
        "high_nan": [1.0, np.nan, np.nan, np.nan],  # 75% NaN
    })


@pytest.fixture
def temp_csv_with_utc_timestamps():
    """Temporary CSV with UTC timestamps (Z suffix) for conversion testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("Timestamp,Value\n")
        f.write("2025-06-15T12:00:00Z,100.0\n")
        f.write("2025-06-15T12:01:00Z,200.0\n")
        f.write("2025-06-15T12:02:00Z,300.0\n")
        f.flush()
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def empty_csv_file():
    """Create an empty CSV file for error testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        # Write nothing - completely empty
        pass
        yield Path(f.name)
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def large_numeric_arrays():
    """Generate large arrays for LTTB downsampling tests."""
    n = 10000
    x = np.arange(n, dtype=np.float64)
    y = np.sin(x / 100) + np.random.normal(0, 0.1, n)
    return x, y
