"""
CSV Indexer - Streaming random-access CSV reader.

Builds a byte-offset index on first open, enabling O(1) row access
without loading the entire file into memory. Memory footprint is
approximately 8 bytes per row (numpy int64 offset array).
"""

from dataclasses import dataclass
from pathlib import Path
from io import StringIO
from typing import Optional
import logging
import re

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Pattern to detect ISO 8601 UTC timestamps ending with 'Z'
_UTC_TIMESTAMP_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)


@dataclass
class CSVIndex:
    """Byte offset index for a CSV file."""

    file_path: Path
    row_offsets: np.ndarray  # int64 array of byte offsets
    header_offset: int  # byte offset where data rows begin
    columns: list[str]  # column names from header
    row_count: int  # number of data rows (excludes header)
    file_size: int  # file size at index build time


class CSVIndexer:
    """
    Streaming CSV reader with row-level random access.

    Builds a byte-offset index by scanning the file once, then provides
    efficient random access to arbitrary row ranges. Each read operation
    opens its own file handle, ensuring thread safety for concurrent reads.

    Usage:
        indexer = CSVIndexer(Path("data.csv"))
        indexer.build_index()
        df = indexer.read_range(0, 1000)  # Read first 1000 rows

    Memory:
        Index consumes ~8 bytes per row (numpy int64 offset).
        A 10 million row file requires ~80 MB for the index.
    """

    def __init__(self, file_path: Path) -> None:
        """
        Initialize the indexer for a CSV file.

        Args:
            file_path: Path to the CSV file to index.
        """
        self.file_path = Path(file_path)
        self.index: Optional[CSVIndex] = None

    def build_index(self) -> CSVIndex:
        """
        Build byte-offset index by scanning the file.

        Reads the file line by line in binary mode, recording the byte
        offset of each data row. The header row is parsed to extract
        column names but is not included in the row offsets.

        Returns:
            CSVIndex with row offsets and metadata.

        Raises:
            FileNotFoundError: If file does not exist.
            ValueError: If file is empty or has no header.
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.file_path}")

        file_size = self.file_path.stat().st_size
        if file_size == 0:
            raise ValueError(f"CSV file is empty: {self.file_path}")

        offsets: list[int] = []
        columns: list[str] = []
        header_offset = 0
        malformed_count = 0

        with self.file_path.open("rb") as f:
            # Read and parse header
            header_line = f.readline()
            if not header_line:
                raise ValueError(f"CSV file has no header: {self.file_path}")

            try:
                header_text = header_line.decode("utf-8").rstrip("\r\n")
                columns = self._parse_csv_row(header_text)
            except UnicodeDecodeError as e:
                raise ValueError(f"Header contains invalid UTF-8: {e}") from e

            if not columns:
                raise ValueError(f"CSV header is empty: {self.file_path}")

            header_offset = f.tell()
            expected_column_count = len(columns)

            # Scan data rows
            while True:
                row_offset = f.tell()
                line = f.readline()

                if not line:
                    # End of file
                    break

                # Handle trailing newline without content
                stripped = line.rstrip(b"\r\n")
                if not stripped:
                    # Empty line at end of file, skip
                    continue

                try:
                    text = stripped.decode("utf-8")
                    fields = self._parse_csv_row(text)

                    if len(fields) != expected_column_count:
                        malformed_count += 1
                        logger.warning(
                            "Row %d: expected %d columns, got %d - skipping",
                            len(offsets) + 1,
                            expected_column_count,
                            len(fields),
                        )
                        continue

                    offsets.append(row_offset)

                except UnicodeDecodeError:
                    malformed_count += 1
                    logger.warning(
                        "Row %d: invalid UTF-8 encoding - skipping",
                        len(offsets) + 1,
                    )
                    continue

        if malformed_count > 0:
            logger.info(
                "Indexing complete: %d rows indexed, %d malformed rows skipped",
                len(offsets),
                malformed_count,
            )

        self.index = CSVIndex(
            file_path=self.file_path,
            row_offsets=np.array(offsets, dtype=np.int64),
            header_offset=header_offset,
            columns=columns,
            row_count=len(offsets),
            file_size=file_size,
        )

        logger.debug(
            "Built index for %s: %d rows, %d columns",
            self.file_path.name,
            self.index.row_count,
            len(columns),
        )

        return self.index

    def read_range(self, start_row: int, end_row: int) -> pd.DataFrame:
        """
        Read a range of rows from the indexed CSV.

        Opens a fresh file handle for thread safety. Seeks directly to
        the start offset and reads only the required bytes.

        Args:
            start_row: 0-based inclusive start row index.
            end_row: 0-based exclusive end row index.

        Returns:
            DataFrame with requested rows. First column becomes the index.
            UTC timestamps (ISO 8601 with Z suffix) are converted to local time.

        Raises:
            RuntimeError: If index has not been built.
            IndexError: If row range is out of bounds.
            ValueError: If start_row >= end_row.
        """
        if self.index is None:
            raise RuntimeError("Index not built. Call build_index() first.")

        if start_row >= end_row:
            raise ValueError(
                f"Invalid range: start_row ({start_row}) must be < end_row ({end_row})"
            )

        if start_row < 0:
            raise IndexError(f"start_row ({start_row}) cannot be negative")

        if end_row > self.index.row_count:
            raise IndexError(
                f"end_row ({end_row}) exceeds row count ({self.index.row_count})"
            )

        # Calculate byte range to read
        start_offset = self.index.row_offsets[start_row]

        if end_row >= self.index.row_count:
            # Read to end of file
            end_offset = self.index.file_size
        else:
            end_offset = self.index.row_offsets[end_row]

        bytes_to_read = end_offset - start_offset

        # Read raw bytes
        with self.file_path.open("rb") as f:
            f.seek(start_offset)
            raw_bytes = f.read(bytes_to_read)

        # Decode and parse with pandas
        text = raw_bytes.decode("utf-8")

        # Prepend header for pandas parsing
        header_line = ",".join(self.index.columns)
        csv_text = header_line + "\n" + text

        df = pd.read_csv(
            StringIO(csv_text),
            index_col=0,  # First column as index
            encoding="utf-8",
        )

        # Convert UTC timestamps to local time
        df = self._convert_timestamps(df)

        return df

    def update_index(self) -> int:
        """
        Check for appended rows and extend index if file has grown.

        Useful for tail-following scenarios where data is continuously
        appended to the CSV file.

        Returns:
            Number of new rows indexed (0 if no change).

        Raises:
            RuntimeError: If index has not been built.
            ValueError: If file has shrunk (truncation detected).
        """
        if self.index is None:
            raise RuntimeError("Index not built. Call build_index() first.")

        current_size = self.file_path.stat().st_size

        if current_size == self.index.file_size:
            return 0

        if current_size < self.index.file_size:
            raise ValueError(
                f"File has shrunk from {self.index.file_size} to {current_size} bytes. "
                "Rebuild index required."
            )

        # File has grown - scan from last known position
        new_offsets: list[int] = []
        expected_column_count = len(self.index.columns)
        malformed_count = 0

        # Determine starting position
        if self.index.row_count > 0:
            last_offset = self.index.row_offsets[-1]
        else:
            last_offset = self.index.header_offset

        with self.file_path.open("rb") as f:
            f.seek(last_offset)

            # Skip the last indexed row (we already have its offset)
            if self.index.row_count > 0:
                f.readline()

            while True:
                row_offset = f.tell()
                line = f.readline()

                if not line:
                    break

                stripped = line.rstrip(b"\r\n")
                if not stripped:
                    continue

                try:
                    text = stripped.decode("utf-8")
                    fields = self._parse_csv_row(text)

                    if len(fields) != expected_column_count:
                        malformed_count += 1
                        logger.warning(
                            "Row %d: expected %d columns, got %d - skipping",
                            self.index.row_count + len(new_offsets) + 1,
                            expected_column_count,
                            len(fields),
                        )
                        continue

                    new_offsets.append(row_offset)

                except UnicodeDecodeError:
                    malformed_count += 1
                    logger.warning(
                        "Row %d: invalid UTF-8 encoding - skipping",
                        self.index.row_count + len(new_offsets) + 1,
                    )
                    continue

        if new_offsets:
            # Extend the offset array
            self.index.row_offsets = np.concatenate(
                [self.index.row_offsets, np.array(new_offsets, dtype=np.int64)]
            )
            self.index.row_count = len(self.index.row_offsets)
            self.index.file_size = current_size

            logger.debug(
                "Index updated: %d new rows, total %d rows",
                len(new_offsets),
                self.index.row_count,
            )

        if malformed_count > 0:
            logger.info(
                "Index update: %d new rows indexed, %d malformed rows skipped",
                len(new_offsets),
                malformed_count,
            )

        return len(new_offsets)

    def _convert_timestamps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert UTC timestamps (ISO 8601 with Z suffix) to local time.

        Scans all object-dtype columns and the index for string values
        matching the pattern YYYY-MM-DDTHH:MM:SS[.fff]Z. Converts these
        to timezone-aware datetime in the local timezone.

        Args:
            df: DataFrame to process.

        Returns:
            DataFrame with converted timestamps.
        """
        # Check index if it's a string type
        if df.index.dtype == object:
            df.index = self._convert_series_timestamps(df.index)

        # Check each column
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = self._convert_series_timestamps(df[col])

        return df

    def _convert_series_timestamps(
        self, series: pd.Series | pd.Index
    ) -> pd.Series | pd.Index:
        """
        Convert UTC timestamp strings in a Series or Index to local time.

        Args:
            series: Series or Index to check and convert.

        Returns:
            Converted Series/Index, or original if not timestamps.
        """
        # Sample first non-null value to check pattern
        if isinstance(series, pd.Index):
            sample_values = [v for v in series[:10] if pd.notna(v) and isinstance(v, str)]
        else:
            sample_values = [
                v for v in series.head(10).tolist() if pd.notna(v) and isinstance(v, str)
            ]

        if not sample_values:
            return series

        # Check if values match UTC timestamp pattern
        if not any(_UTC_TIMESTAMP_PATTERN.match(str(v)) for v in sample_values):
            return series

        try:
            # Parse as datetime, convert from UTC to local
            from datetime import timezone as tz
            import time
            
            # Get local timezone offset
            if time.daylight:
                local_tz_offset = time.altzone
            else:
                local_tz_offset = time.timezone
            
            if isinstance(series, pd.Index):
                parsed = pd.to_datetime(series, utc=True)
                # Convert to local timezone then strip tz info for naive local time
                local = parsed.tz_convert(tz.utc).tz_localize(None) - pd.Timedelta(seconds=local_tz_offset)
                return local
            else:
                parsed = pd.to_datetime(series, utc=True)
                # Convert to local timezone then strip tz info for naive local time
                local = parsed.dt.tz_convert(tz.utc).dt.tz_localize(None) - pd.Timedelta(seconds=local_tz_offset)
                return local
        except (ValueError, TypeError):
            # Parsing failed, return original
            return series

    @staticmethod
    def _parse_csv_row(text: str) -> list[str]:
        """
        Parse a single CSV row, handling quoted fields.

        Simple parser that handles:
        - Comma-separated values
        - Double-quoted fields containing commas
        - Escaped quotes ("") within quoted fields

        Args:
            text: Single line of CSV text (no newline).

        Returns:
            List of field values.
        """
        fields: list[str] = []
        current_field: list[str] = []
        in_quotes = False
        i = 0
        n = len(text)

        while i < n:
            char = text[i]

            if in_quotes:
                if char == '"':
                    # Check for escaped quote
                    if i + 1 < n and text[i + 1] == '"':
                        current_field.append('"')
                        i += 2
                        continue
                    else:
                        in_quotes = False
                        i += 1
                        continue
                else:
                    current_field.append(char)
                    i += 1
            else:
                if char == '"':
                    in_quotes = True
                    i += 1
                elif char == ",":
                    fields.append("".join(current_field))
                    current_field = []
                    i += 1
                else:
                    current_field.append(char)
                    i += 1

        # Don't forget the last field
        fields.append("".join(current_field))

        return fields
