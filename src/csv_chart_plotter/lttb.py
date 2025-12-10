"""
Downsampling - MinMaxLTTB algorithm via tsdownsample.

Reduces point density while preserving visual shape of time-series data.
Two-phase approach: min-max preselection + LTTB refinement.
Performance: 10-30× faster than pure LTTB with comparable visual fidelity.

Reference: https://arxiv.org/abs/2305.00332
"""

import numpy as np
import pandas as pd
from tsdownsample import MinMaxLTTBDownsampler

# Default ratio for min-max preselection phase
# Higher values improve speed but may miss mid-range features
# Research establishes 4 as optimal balance
DEFAULT_MINMAX_RATIO = 4


def lttb_downsample(
    x: np.ndarray,
    y: np.ndarray,
    threshold: int,
    minmax_ratio: int = DEFAULT_MINMAX_RATIO,
    parallel: bool = False
) -> tuple[np.ndarray, np.ndarray]:
    """
    MinMaxLTTB downsampling via tsdownsample library.
    
    Two-phase algorithm:
    1. Min-max preselection: Select threshold × minmax_ratio extreme points
    2. LTTB refinement: Apply Largest-Triangle-Three-Buckets to preselected points
    
    Args:
        x: X-axis values (timestamps or indices), must be 1D
        y: Y-axis values (numeric data), must be 1D
        threshold: Maximum number of points to return (must be >= 2)
        minmax_ratio: Preselection multiplier (default 4, higher = faster but less detail)
        parallel: Enable multi-threaded execution (default False)
        
    Returns:
        Tuple of (downsampled_x, downsampled_y)
        
    Raises:
        ValueError: if threshold < 2
        
    Complexity: O(n) with improved constant factors vs pure LTTB
    
    Edge cases:
        - Empty arrays return empty results
        - Arrays with n <= threshold returned unchanged
        - NaN values handled by tsdownsample NaN-aware implementation
        
    Reference: https://arxiv.org/abs/2305.00332
    """
    if threshold < 2:
        raise ValueError("threshold must be >= 2")
    
    n = len(x)
    
    # Edge case: empty arrays
    if n == 0:
        return np.array([]), np.array([])
    
    # No downsampling needed
    if n <= threshold:
        return x.copy(), y.copy()
    
    # Use tsdownsample MinMaxLTTB implementation
    downsampler = MinMaxLTTBDownsampler()
    indices = downsampler.downsample(
        x, y, 
        n_out=threshold, 
        minmax_ratio=minmax_ratio,
        parallel=parallel
    )
    
    return x[indices], y[indices]


def downsample_dataframe(
    df: pd.DataFrame,
    x_values: np.ndarray,
    threshold: int = 4000,
    minmax_ratio: int = DEFAULT_MINMAX_RATIO,
    parallel: bool = False
) -> tuple[np.ndarray, pd.DataFrame]:
    """
    Apply MinMaxLTTB to all columns of a DataFrame.
    
    Uses a unified index approach: computes representative indices
    from the first column, then applies those indices to all columns.
    This maintains alignment across traces.
    
    Args:
        df: DataFrame with numeric columns
        x_values: X-axis values (same length as df)
        threshold: Maximum points per trace (default 4000)
        minmax_ratio: Preselection multiplier (default 4)
        parallel: Enable multi-threaded execution (default False)
        
    Returns:
        Tuple of (downsampled_x, downsampled_df)
        
    Raises:
        ValueError: if threshold < 2 or x_values length mismatches df
        
    Note: 
        Each column could theoretically be downsampled independently,
        but this implementation uses a unified index from the first
        column to maintain x-axis alignment across all traces.
    """
    if threshold < 2:
        raise ValueError("threshold must be >= 2")
    
    if len(x_values) != len(df):
        raise ValueError(
            f"x_values length ({len(x_values)}) must match "
            f"DataFrame length ({len(df)})"
        )
    
    n = len(df)
    
    # Edge case: empty DataFrame
    if n == 0:
        return np.array([]), pd.DataFrame()
    
    # No downsampling needed
    if n <= threshold:
        return x_values.copy(), df.copy()
    
    # Use first column to determine sampling indices
    # This ensures all columns share the same x-coordinates
    if len(df.columns) == 0:
        return x_values.copy(), df.copy()
    
    first_col = df.iloc[:, 0].to_numpy()
    
    # Compute indices via MinMaxLTTB on first column
    sampled_indices = compute_lttb_indices(
        x_values, first_col, threshold, minmax_ratio, parallel
    )
    sampled_x = x_values[sampled_indices]
    
    # Apply indices to all columns
    downsampled_data = {}
    for col in df.columns:
        downsampled_data[col] = df[col].iloc[sampled_indices].to_numpy()
    
    downsampled_df = pd.DataFrame(downsampled_data)
    
    return sampled_x, downsampled_df


def compute_lttb_indices(
    x: np.ndarray,
    y: np.ndarray,
    threshold: int,
    minmax_ratio: int = DEFAULT_MINMAX_RATIO,
    parallel: bool = False
) -> np.ndarray:
    """
    Compute MinMaxLTTB sampling indices without returning the actual values.
    
    Public API for obtaining indices when display values differ from numeric values.
    
    Args:
        x: X-axis values
        y: Y-axis values (used for area calculation)
        threshold: Target number of points
        minmax_ratio: Preselection multiplier (default 4)
        parallel: Enable multi-threaded execution (default False)
        
    Returns:
        Array of indices selected by MinMaxLTTB algorithm
    """
    n = len(x)
    
    if n <= threshold:
        return np.arange(n)
    
    # Use tsdownsample for index computation
    downsampler = MinMaxLTTBDownsampler()
    indices = downsampler.downsample(
        x, y,
        n_out=threshold,
        minmax_ratio=minmax_ratio,
        parallel=parallel
    )
    
    return indices
