"""Core domain models for text replacement."""

from __future__ import annotations

import os
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from shutil import copy2


@dataclass
class Config:
    """Configuration for text replacement."""

    dictionaries: dict[str, dict[str, str]]
    ignore_extensions: list[str] = field(default_factory=list)
    ignore_directories: list[str] = field(default_factory=list)
    ignore_file_prefixes: list[str] = field(default_factory=list)
    version: str = "1.0"

    def get_dictionary(self, name: str, direction: int) -> dict[str, str]:
        """Get replacement dictionary for a direction."""
        raw = self.dictionaries.get(name, {})
        if direction == 2:
            raw = {v: k for k, v in raw.items()}
        return raw


class FileOperator(ABC):
    """Abstract interface for file operations."""

    @abstractmethod
    def read_text(self, path: Path) -> str:
        """Read text from a file."""

    @abstractmethod
    def write_text(self, path: Path, content: str) -> None:
        """Write text to a file."""

    @abstractmethod
    def file_exists(self, path: Path) -> bool:
        """Check if a file exists."""

    @abstractmethod
    def walk(self, directory: Path):
        """Walk directory tree."""

    @abstractmethod
    def ensure_dir_exists(self, path: Path) -> None:
        """Ensure directory exists."""

    @abstractmethod
    def make_backup(self, path: Path, backup_dir: Path) -> Path:
        """Create a backup of a file."""

    @abstractmethod
    def list_files(self, directory: Path, pattern: str = "*") -> list[Path]:
        """List files matching pattern."""

    @abstractmethod
    def is_binary(self, path: Path) -> bool:
        """Check if file is binary."""

    @abstractmethod
    def create_backup(self, path: Path, backup_dir: Path) -> Path:
        """Create a backup of a file."""


class LocalFileOperator(FileOperator):
    """Local filesystem file operator with backup support."""

    def __init__(self, backup_dir: Path | None = None):
        self.backup_dir = backup_dir

    def read_text(self, path: Path) -> str:
        with open(path, encoding="utf-8") as f:
            return f.read()

    def write_text(self, path: Path, content: str) -> None:
        parent = path.parent
        if parent:
            parent.mkdir(parents=True, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(dir=parent, prefix=path.name + ".", text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def file_exists(self, path: Path) -> bool:
        return path.exists()

    def ensure_dir_exists(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def make_backup(self, path: Path, backup_dir: Path) -> Path:
        if not self.backup_dir:
            raise ValueError("No backup directory configured")
        self.ensure_dir_exists(self.backup_dir)
        rel_path = path.relative_to(os.getcwd())
        backup_path = self.backup_dir / rel_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        copy2(path, backup_path)
        return backup_path

    def walk(self, directory: Path):
        yield from os.walk(directory)

    def list_files(self, directory: Path, pattern: str = "*") -> list[Path]:
        return list(Path(directory).glob(pattern))

    def is_binary(self, path: Path) -> bool:
        try:
            path.read_text(encoding="utf-8")
            return False
        except UnicodeDecodeError:
            return True

    def create_backup(self, path: Path, backup_dir: Path) -> Path:
        if not self.backup_dir:
            raise ValueError("No backup directory configured")
        return self.make_backup(path, backup_dir)
