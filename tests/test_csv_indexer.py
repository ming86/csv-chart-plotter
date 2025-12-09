"""Unit tests for CSV indexer module."""

import pytest
import tempfile
from pathlib import Path

from csv_chart_plotter.csv_indexer import CSVIndexer, CSVIndex


class TestBuildIndex:
    """Tests for CSVIndexer.build_index()."""

    def test_build_index_valid_file(self, temp_csv_file):
        """Build index successfully from valid CSV file."""
        indexer = CSVIndexer(temp_csv_file)
        index = indexer.build_index()

        assert isinstance(index, CSVIndex)
        assert index.row_count == 3
        assert index.columns == ["Timestamp", "Value1", "Value2", "Label"]
        assert len(index.row_offsets) == 3

    def test_build_index_file_not_found(self, tmp_path):
        """Raise FileNotFoundError for non-existent file."""
        nonexistent = tmp_path / "does_not_exist.csv"
        indexer = CSVIndexer(nonexistent)

        with pytest.raises(FileNotFoundError, match="CSV file not found"):
            indexer.build_index()

    def test_build_index_empty_file(self, empty_csv_file):
        """Raise ValueError for empty CSV file."""
        indexer = CSVIndexer(empty_csv_file)

        with pytest.raises(ValueError, match="empty"):
            indexer.build_index()


class TestReadRange:
    """Tests for CSVIndexer.read_range()."""

    def test_read_range_basic(self, temp_csv_file):
        """Read a basic range of rows from indexed CSV."""
        indexer = CSVIndexer(temp_csv_file)
        indexer.build_index()

        df = indexer.read_range(0, 2)

        assert len(df) == 2
        assert "Value1" in df.columns
        assert "Value2" in df.columns

    def test_read_range_out_of_bounds(self, temp_csv_file):
        """Raise IndexError when end_row exceeds row count."""
        indexer = CSVIndexer(temp_csv_file)
        indexer.build_index()

        with pytest.raises(IndexError, match="exceeds row count"):
            indexer.read_range(0, 100)

    def test_read_range_without_index(self, temp_csv_file):
        """Raise RuntimeError when index not built."""
        indexer = CSVIndexer(temp_csv_file)

        with pytest.raises(RuntimeError, match="Index not built"):
            indexer.read_range(0, 1)

    def test_read_range_invalid_range(self, temp_csv_file):
        """Raise ValueError when start_row >= end_row."""
        indexer = CSVIndexer(temp_csv_file)
        indexer.build_index()

        with pytest.raises(ValueError, match="Invalid range"):
            indexer.read_range(2, 1)


class TestUpdateIndex:
    """Tests for CSVIndexer.update_index()."""

    def test_update_index_no_change(self, temp_csv_file):
        """Return 0 when file size unchanged."""
        indexer = CSVIndexer(temp_csv_file)
        indexer.build_index()

        new_rows = indexer.update_index()

        assert new_rows == 0

    def test_update_index_file_grown(self, tmp_path):
        """Detect and index new rows when file has grown."""
        csv_file = tmp_path / "growing.csv"
        csv_file.write_text("Timestamp,Value\n2025-01-01T10:00:00Z,1.0\n")

        indexer = CSVIndexer(csv_file)
        indexer.build_index()
        assert indexer.index.row_count == 1

        # Append new row
        with csv_file.open("a") as f:
            f.write("2025-01-01T10:01:00Z,2.0\n")

        new_rows = indexer.update_index()

        assert new_rows == 1
        assert indexer.index.row_count == 2

    def test_update_index_without_build(self, temp_csv_file):
        """Raise RuntimeError when called without build_index."""
        indexer = CSVIndexer(temp_csv_file)

        with pytest.raises(RuntimeError, match="Index not built"):
            indexer.update_index()


class TestUTCTimestampConversion:
    """Tests for UTC timestamp conversion."""

    def test_utc_timestamp_conversion(self, temp_csv_with_utc_timestamps):
        """Convert UTC timestamps (Z suffix) to local time."""
        indexer = CSVIndexer(temp_csv_with_utc_timestamps)
        indexer.build_index()

        df = indexer.read_range(0, 3)

        # Index should be converted from UTC string to datetime
        # The exact values depend on local timezone, but should be datetime type
        import pandas as pd
        assert pd.api.types.is_datetime64_any_dtype(df.index)

    def test_non_utc_timestamps_unchanged(self, tmp_path):
        """Non-UTC timestamp strings should remain as strings."""
        csv_file = tmp_path / "non_utc.csv"
        csv_file.write_text("Label,Value\nRow1,100\nRow2,200\n")

        indexer = CSVIndexer(csv_file)
        indexer.build_index()

        df = indexer.read_range(0, 2)

        # Index should remain as string type (Label column)
        assert df.index.dtype == object
