"""Unit tests for main entry point module."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import socket

from csv_chart_plotter.main import find_available_port, validate_file


class TestFindAvailablePort:
    """Tests for find_available_port()."""

    def test_find_available_port(self):
        """Find and return an available port."""
        port = find_available_port(start=9000)

        assert isinstance(port, int)
        assert port >= 9000

        # Verify port is actually available
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", port))  # Should not raise

    def test_find_available_port_skips_occupied(self):
        """Skip occupied ports and find next available."""
        # Occupy a port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied_sock:
            occupied_sock.bind(("127.0.0.1", 0))
            occupied_port = occupied_sock.getsockname()[1]

            # Should find a different port
            port = find_available_port(start=occupied_port, max_attempts=10)

            assert port != occupied_port

    def test_find_available_port_max_attempts_exceeded(self):
        """Raise RuntimeError when no port found within max_attempts."""
        # Mock socket to always raise OSError (all ports occupied)
        with patch("socket.socket") as mock_socket:
            mock_sock_instance = MagicMock()
            mock_sock_instance.__enter__ = MagicMock(return_value=mock_sock_instance)
            mock_sock_instance.__exit__ = MagicMock(return_value=False)
            mock_sock_instance.bind.side_effect = OSError("Port in use")
            mock_socket.return_value = mock_sock_instance

            with pytest.raises(RuntimeError, match="No available port found"):
                find_available_port(start=8050, max_attempts=5)


class TestValidateFile:
    """Tests for validate_file()."""

    def test_validate_file_not_found(self, tmp_path):
        """Raise FileNotFoundError for non-existent file."""
        nonexistent = tmp_path / "does_not_exist.csv"

        with pytest.raises(FileNotFoundError, match="not found"):
            validate_file(nonexistent)

    def test_validate_file_is_directory(self, tmp_path):
        """Raise FileNotFoundError when path is a directory."""
        directory = tmp_path / "subdir"
        directory.mkdir()

        with pytest.raises(FileNotFoundError, match="not a file"):
            validate_file(directory)

    def test_validate_file_exists(self, temp_csv_file):
        """No exception for valid file."""
        # Should not raise
        validate_file(temp_csv_file)


class TestMainIntegration:
    """Integration tests for main() function."""

    def test_main_file_not_found_returns_exit_code_1(self, tmp_path):
        """Return exit code 1 for non-existent file."""
        from csv_chart_plotter.main import main

        nonexistent = tmp_path / "missing.csv"

        with patch("sys.argv", ["csv_chart_plotter", str(nonexistent)]):
            exit_code = main()

        assert exit_code == 1

    def test_main_no_numeric_columns_returns_exit_code_1(self, tmp_path):
        """Return exit code 1 when CSV has no numeric columns."""
        from csv_chart_plotter.main import main

        # Create CSV with only string columns
        csv_file = tmp_path / "strings_only.csv"
        csv_file.write_text("Col1,Col2\na,x\nb,y\nc,z\n")

        with patch("sys.argv", ["csv_chart_plotter", str(csv_file)]):
            exit_code = main()

        assert exit_code == 1
