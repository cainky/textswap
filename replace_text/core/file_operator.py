"""File operator interface and implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class FileOperator(ABC):
    """Abstract interface for file operations."""

    @abstractmethod
    def read_text(self, path: Path) -> str:
        """Read text from a file."""
        pass

    @abstractmethod
    def write_text(self, path: Path, content: str) -> None:
        """Write text to a file."""
        pass

    @abstractmethod
    def list_files(self, directory: Path, pattern: str = "*") -> list[Path]:
        """List files matching a pattern in a directory."""
        pass

    @abstractmethod
    def is_binary(self, path: Path) -> bool:
        """Check if a file is binary."""
        pass

    @abstractmethod
    def create_backup(self, path: Path, backup_dir: Path) -> Path:
        """Create a backup of a file."""
        pass


class LocalFileOperator(FileOperator):
    """Local file system implementation of FileOperator."""

    def read_text(self, path: Path) -> str:
        """Read text from a file with UTF-8 encoding."""
        try:
            with open(path, encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            raise ValueError(f"File is not UTF-8 encoded: {path}")
        except PermissionError:
            raise PermissionError(f"Permission denied reading: {path}")

    def write_text(self, path: Path, content: str) -> None:
        """Write text to a file with UTF-8 encoding."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except PermissionError:
            raise PermissionError(f"Permission denied writing: {path}")
        except OSError as e:
            raise OSError(f"Error writing to {path}: {e}")

    def list_files(self, directory: Path, pattern: str = "*") -> list[Path]:
        """List files matching a pattern in a directory recursively."""
        if not directory.exists():
            return []
        return sorted(directory.rglob(pattern))

    def is_binary(self, path: Path) -> bool:
        """Check if a file is binary by examining its content."""
        try:
            with open(path, "rb") as f:
                chunk = f.read(8192)
                if not chunk:
                    return False
                return b"\0" in chunk
        except (OSError, PermissionError):
            return True

    def create_backup(self, path: Path, backup_dir: Path) -> Path:
        """Create a backup of a file in the backup directory."""
        import shutil

        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / path.name
        if backup_path.exists():
            stem = path.stem
            suffix = path.suffix
            counter = 1
            while backup_path.exists():
                backup_path = backup_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        shutil.copy2(path, backup_path)
        return backup_path
