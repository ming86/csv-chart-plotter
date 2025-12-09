"""
LTTB Downsampling - Largest-Triangle-Three-Buckets algorithm.

Reduces point density while preserving visual shape of time-series data.
Single-pass O(n) complexity.
"""

import numpy as np
import pandas as pd


def lttb_downsample(
    x: np.ndarray,
    y: np.ndarray,
    threshold: int
) -> tuple[np.ndarray, np.ndarray]:
    """
    Largest-Triangle-Three-Buckets downsampling.
    
    Args:
        x: X-axis values (timestamps or indices), must be 1D
        y: Y-axis values (numeric data), must be 1D
        threshold: Maximum number of points to return (must be >= 2)
        
    Returns:
        Tuple of (downsampled_x, downsampled_y)
        
    Raises:
        ValueError: if threshold < 2
        
    Reference algorithm:
        1. Always retain first and last point
        2. Divide remaining points into equal-sized buckets
        3. For each bucket, select point forming largest triangle with:
           - Previous selected point
           - Average of next bucket
        4. Repeat for all buckets
        
    Complexity: O(n) single pass
    
    Edge cases:
        - Empty arrays return empty results
        - Arrays with n <= threshold returned unchanged
        - NaN values in y are handled via masked comparison
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
    
    # Convert to float for NaN handling
    y_float = y.astype(np.float64, copy=True)
    
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
        
        # Calculate average of next bucket (for triangle area calculation)
        next_bucket_start = bucket_end
        next_bucket_end = int((i + 3) * bucket_size) + 1
        next_bucket_end = min(next_bucket_end, n)
        
        # Handle NaN in next bucket average calculation
        next_x_slice = x[next_bucket_start:next_bucket_end]
        next_y_slice = y_float[next_bucket_start:next_bucket_end]
        
        # Use nanmean to handle NaN values
        if len(next_x_slice) > 0:
            avg_x = np.nanmean(next_x_slice)
            avg_y = np.nanmean(next_y_slice)
            # If all values are NaN, default to 0
            if np.isnan(avg_x):
                avg_x = 0.0
            if np.isnan(avg_y):
                avg_y = 0.0
        else:
            # Last bucket edge case
            avg_x = float(x[-1])
            avg_y = float(y_float[-1]) if not np.isnan(y_float[-1]) else 0.0
        
        # Find point in current bucket with largest triangle area
        max_area = -1.0
        max_area_index = bucket_start
        
        # Get values at anchor point, handling NaN
        x_a = float(x[a])
        y_a = float(y_float[a]) if not np.isnan(y_float[a]) else 0.0
        
        for j in range(bucket_start, bucket_end):
            y_j = y_float[j]
            
            # Skip NaN points in area calculation (treat as area = 0)
            if np.isnan(y_j):
                continue
            
            # Triangle area formula (2x area, sign irrelevant)
            area = abs(
                (x_a - avg_x) * (y_j - y_a) -
                (x_a - x[j]) * (avg_y - y_a)
            ) * 0.5
            
            if area > max_area:
                max_area = area
                max_area_index = j
        
        sampled_indices.append(max_area_index)
        a = max_area_index
    
    sampled_indices.append(n - 1)
    
    return x[sampled_indices], y[sampled_indices]


def downsample_dataframe(
    df: pd.DataFrame,
    x_values: np.ndarray,
    threshold: int = 4000
) -> tuple[np.ndarray, pd.DataFrame]:
    """
    Apply LTTB to all columns of a DataFrame.
    
    Uses a unified index approach: computes representative indices
    from the first column, then applies those indices to all columns.
    This maintains alignment across traces.
    
    Args:
        df: DataFrame with numeric columns
        x_values: X-axis values (same length as df)
        threshold: Maximum points per trace (default 4000)
        
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
    
    # Compute indices via LTTB on first column
    sampled_x, _ = lttb_downsample(x_values, first_col, threshold)
    
    # Find the indices that were selected
    # Build indices by rerunning the selection logic
    sampled_indices = compute_lttb_indices(x_values, first_col, threshold)
    
    # Apply indices to all columns
    downsampled_data = {}
    for col in df.columns:
        downsampled_data[col] = df[col].iloc[sampled_indices].to_numpy()
    
    downsampled_df = pd.DataFrame(downsampled_data)
    
    return sampled_x, downsampled_df


def compute_lttb_indices(
    x: np.ndarray,
    y: np.ndarray,
    threshold: int
) -> list[int]:
    """
    Compute LTTB sampling indices without returning the actual values.
    
    Public API for obtaining LTTB indices when display values differ from numeric values.
    
    Args:
        x: X-axis values
        y: Y-axis values (used for triangle area calculation)
        threshold: Target number of points
        
    Returns:
        List of indices selected by LTTB algorithm
    """
    n = len(x)
    
    if n <= threshold:
        return list(range(n))
    
    y_float = y.astype(np.float64, copy=True)
    
    sampled_indices = [0]
    bucket_size = (n - 2) / (threshold - 2)
    a = 0
    
    for i in range(threshold - 2):
        bucket_start = int((i + 1) * bucket_size) + 1
        bucket_end = int((i + 2) * bucket_size) + 1
        bucket_end = min(bucket_end, n - 1)
        
        next_bucket_start = bucket_end
        next_bucket_end = int((i + 3) * bucket_size) + 1
        next_bucket_end = min(next_bucket_end, n)
        
        next_x_slice = x[next_bucket_start:next_bucket_end]
        next_y_slice = y_float[next_bucket_start:next_bucket_end]
        
        if len(next_x_slice) > 0:
            avg_x = np.nanmean(next_x_slice)
            avg_y = np.nanmean(next_y_slice)
            if np.isnan(avg_x):
                avg_x = 0.0
            if np.isnan(avg_y):
                avg_y = 0.0
        else:
            avg_x = float(x[-1])
            avg_y = float(y_float[-1]) if not np.isnan(y_float[-1]) else 0.0
        
        max_area = -1.0
        max_area_index = bucket_start
        
        x_a = float(x[a])
        y_a = float(y_float[a]) if not np.isnan(y_float[a]) else 0.0
        
        for j in range(bucket_start, bucket_end):
            y_j = y_float[j]
            if np.isnan(y_j):
                continue
            
            area = abs(
                (x_a - avg_x) * (y_j - y_a) -
                (x_a - x[j]) * (avg_y - y_a)
            ) * 0.5
            
            if area > max_area:
                max_area = area
                max_area_index = j
        
        sampled_indices.append(max_area_index)
        a = max_area_index
    
    sampled_indices.append(n - 1)
    
    return sampled_indices
