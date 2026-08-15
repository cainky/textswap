"""Core domain models for text replacement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    """Configuration for text replacement."""

    dictionaries: dict[str, dict[str, str]]
    ignore_extensions: list[str] = field(default_factory=list)
    ignore_directories: list[str] = field(default_factory=list)
    ignore_file_prefixes: list[str] = field(default_factory=list)
    version: str = "1.0"


class FileOperator(ABC):
    """Abstract interface for file operations."""

    @abstractmethod
    def read_text(self, path: Path) -> str:
        """Read text from a file."""


class LocalFileOperator(FileOperator):
    """Local filesystem file operator."""

    def read_text(self, path: Path) -> str:
        with open(path, encoding="utf-8") as f:
            return f.read()
