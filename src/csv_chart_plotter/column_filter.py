"""
Column Filter - Numeric column detection and quality validation.

Filters DataFrame columns to retain only plottable numeric types,
with logging for dropped columns and data quality warnings.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)

NUMERIC_DTYPES = {'int64', 'float64', 'int32', 'float32'}


def filter_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter DataFrame to retain only numeric columns.
    
    Args:
        df: Input DataFrame (index already set)
        
    Returns:
        DataFrame with only numeric columns
        
    Raises:
        ValueError: if no numeric columns remain after filtering
        
    Requirements:
        FR-FILTER-01: Retain columns with int64, float64, int32, float32 dtypes
        FR-FILTER-02: Drop non-numeric columns with INFO log
        FR-FILTER-03: Drop all-NaN columns with WARNING log
        FR-FILTER-05: Raise ValueError when no numeric columns remain
    """
    if df.empty:
        raise ValueError("No numeric columns remain after filtering")
    
    numeric_columns = []
    dropped_non_numeric = []
    dropped_all_nan = []
    
    for col in df.columns:
        dtype_name = str(df[col].dtype)
        
        # FR-FILTER-01: Check if dtype is in allowed numeric types
        if dtype_name not in NUMERIC_DTYPES:
            dropped_non_numeric.append(col)
            continue
        
        # FR-FILTER-03: Check for all-NaN columns
        if df[col].isna().all():
            dropped_all_nan.append(col)
            continue
        
        numeric_columns.append(col)
    
    # FR-FILTER-02: Log dropped non-numeric columns
    for col in dropped_non_numeric:
        logger.info("Dropped non-numeric column: '%s' (dtype: %s)", col, df[col].dtype)
    
    # FR-FILTER-03: Log dropped all-NaN columns
    for col in dropped_all_nan:
        logger.warning("Dropped all-NaN column: '%s'", col)
    
    # FR-FILTER-05: Raise if no numeric columns remain
    if not numeric_columns:
        raise ValueError("No numeric columns remain after filtering")
    
    return df[numeric_columns]


def calculate_nan_ratio(series: pd.Series) -> float:
    """
    Calculate the ratio of NaN values in a series.
    
    Args:
        series: Input pandas Series
        
    Returns:
        Float between 0.0 and 1.0 representing NaN ratio.
        Returns 0.0 for empty series.
    """
    if len(series) == 0:
        return 0.0
    return series.isna().sum() / len(series)


def validate_data_quality(df: pd.DataFrame) -> dict[str, float]:
    """
    Analyze data quality and return NaN ratios per column.
    
    Logs INFO warnings for columns with >50% NaN values.
    
    Args:
        df: DataFrame with numeric columns
        
    Returns:
        Dictionary mapping column names to their NaN ratios
        
    Requirements:
        FR-FILTER-04: Log INFO for columns with >50% NaN ratio
    """
    nan_ratios: dict[str, float] = {}
    
    for col in df.columns:
        ratio = calculate_nan_ratio(df[col])
        nan_ratios[col] = ratio
        
        # FR-FILTER-04: Log columns with >50% NaN
        if ratio > 0.5:
            logger.info(
                "Column '%s' has %.1f%% missing values",
                col,
                ratio * 100
            )
    
    return nan_ratios
