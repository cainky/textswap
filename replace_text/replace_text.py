"""Replace text in files based on dictionary mappings."""

from __future__ import annotations

import difflib
import json
import os
from pathlib import Path

import click

from replace_text.core import (
    Config,
    FileOperator,
    LocalFileOperator,
)


def load_config(config_path: Path, file_operator: FileOperator) -> Config:
    """Load and validate the configuration file.

    Args:
        config_path: Path to the JSON config file.
        file_operator: File operator for reading files.

    Returns:
        Parsed configuration object.

    Raises:
        SystemExit: If config file is invalid or missing required fields.
    """
    try:
        content = file_operator.read_text(config_path)
        cfg_dict = json.loads(content)
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON in config file: {e}", err=True)
        raise SystemExit(1)
    except OSError as e:
        click.echo(f"Error: Could not read config file: {e}", err=True)
        raise SystemExit(1)

    if not isinstance(cfg_dict.get("dictionaries"), dict):
        click.echo("Error: Config must contain a 'dictionaries' object", err=True)
        raise SystemExit(1)

    version = cfg_dict.get("version", "1.0")

    return Config(
        dictionaries=cfg_dict["dictionaries"],
        ignore_extensions=cfg_dict.get("ignore_extensions", []),
        ignore_directories=cfg_dict.get("ignore_directories", []),
        ignore_file_prefixes=cfg_dict.get("ignore_file_prefixes", []),
        version=version,
    )


def get_replacement_dict(
    dictionaries: dict[str, dict[str, str]],
    dict_name: str | None,
    direction: int,
) -> tuple[str, dict[str, str]]:
    """Get the replacement dictionary based on name and direction.

    Args:
        dictionaries: All available dictionaries from config.
        dict_name: Name of dictionary to use, or None to auto-select/prompt.
        direction: 1 for keys-to-values, 2 for values-to-keys.

    Returns:
        Tuple of (dictionary_name, replacement_dict).

    Raises:
        SystemExit: If no dictionaries found or specified dict doesn't exist.
    """
    if not dictionaries:
        click.echo("Error: No dictionaries found in config", err=True)
        raise SystemExit(1)

    if dict_name is None:
        if len(dictionaries) == 1:
            dict_name = next(iter(dictionaries))
            click.echo(f"Using dictionary: {dict_name}")
        else:
            dict_name = click.prompt(
                "Dictionary name", type=click.Choice(list(dictionaries.keys()))
            )

    if dict_name not in dictionaries:
        click.echo(f"Error: Dictionary '{dict_name}' not found", err=True)
        raise SystemExit(1)

    replacement_dict: dict[str, str] = dictionaries[dict_name]

    if direction == 2:
        replacement_dict = {v: k for k, v in replacement_dict.items()}

    return dict_name, replacement_dict


def should_skip_file(
    file_path: Path,
    ignore_extensions: list[str],
    ignore_file_prefixes: list[str],
) -> bool:
    """Check if a file should be skipped based on ignore rules.

    Args:
        file_path: Path to the file.
        ignore_extensions: List of extensions to skip.
        ignore_file_prefixes: List of filename prefixes to skip.

    Returns:
        True if file should be skipped.
    """
    filename = file_path.name

    if any(filename.endswith(ext) for ext in ignore_extensions):
        return True

    if any(filename.startswith(prefix) for prefix in ignore_file_prefixes):
        return True

    return False


def generate_diff(file_path: Path, old_content: str, new_content: str) -> str:
    """Generate a unified diff between old and new content.

    Args:
        file_path: Path to the file (for diff header).
        old_content: Original content.
        new_content: Modified content.

    Returns:
        Unified diff string.
    """
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="",
    )
    return "".join(diff)


def process_file(
    file_path: Path,
    replacement_dict: dict[str, str],
    dry_run: bool,
) -> tuple[bool, str | None]:
    """Process a single file and apply replacements.

    Args:
        file_path: Path to the file to process.
        replacement_dict: Dictionary of replacements to apply.
        dry_run: If True, don't modify the file.

    Returns:
        Tuple of (was_modified, error_message).
        error_message is None if successful, otherwise contains the error.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False, f"Skipped (not UTF-8 encoded): {file_path}"
    except PermissionError:
        return False, f"Skipped (permission denied): {file_path}"
    except OSError as e:
        return False, f"Skipped (read error): {file_path} - {e}"

    new_content = content
    for key, value in replacement_dict.items():
        new_content = new_content.replace(key, value)

    if new_content != content:
        if dry_run:
            click.echo(f"\nWould modify: {file_path}")
            diff = generate_diff(file_path, content, new_content)
            if diff:
                click.echo(click.style(diff, fg="yellow"))
        else:
            try:
                file_path.write_text(new_content, encoding="utf-8")
                click.echo(f"Modified: {file_path}")
            except PermissionError:
                return False, f"Skipped (write permission denied): {file_path}"
            except OSError as e:
                return False, f"Skipped (write error): {file_path} - {e}"
        return True, None

    return False, None


@click.command(name="textswap")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default="config.json",
    help="Path to config file (default: config.json in current directory)",
)
@click.option(
    "--direction",
    "-d",
    type=click.IntRange(1, 2),
    prompt="Direction (1 for keys-to-values, 2 for values-to-keys)",
    help="1 for keys-to-values, 2 for values-to-keys",
)
@click.option(
    "--folder",
    "-f",
    type=click.Path(exists=True),
    prompt="Folder path",
    help="Path to folder containing files to process",
)
@click.option(
    "--dict-name",
    "-n",
    default=None,
    help="Dictionary name from config (auto-selects if only one)",
)
@click.option(
    "--backup-dir",
    "-b",
    type=click.Path(file_okay=False, dir_okay=True),
    help="Directory to store backups before writing files",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be replaced without making changes",
)
def replace_text(
    config: str,
    direction: int,
    folder: str,
    dict_name: str | None,
    dry_run: bool,
    backup_dir: str,
) -> None:
    """Replace text in files based on dictionary mappings.

    Define replacement dictionaries in a JSON config file, then run this tool
    to bulk replace text across all files in a folder.
    """
    config_path = Path(config)
    folder_path = Path(folder)

    file_operator = LocalFileOperator()
    cfg = load_config(config_path, file_operator)

    dictionaries = getattr(cfg, "dictionaries", {})
    ignore_extensions = getattr(cfg, "ignore_extensions", [])
    ignore_directories = getattr(cfg, "ignore_directories", [])
    ignore_file_prefixes = getattr(cfg, "ignore_file_prefixes", [])

    dict_name, replacement_dict = get_replacement_dict(dictionaries, dict_name, direction)

    if dry_run:
        click.echo("Dry run mode - no files will be modified\n")

    files_processed = 0
    files_modified = 0
    files_skipped = 0
    skipped_reasons: list[str] = []

    for root, dirs, files in os.walk(folder_path):
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_directories]

        for filename in files:
            file_path = Path(root) / filename

            if should_skip_file(file_path, ignore_extensions, ignore_file_prefixes):
                continue

            modified, error = process_file(file_path, replacement_dict, dry_run)

            if error:
                files_skipped += 1
                skipped_reasons.append(error)
            else:
                files_processed += 1
                if modified:
                    files_modified += 1

    # Summary
    click.echo(f"\nProcessed {files_processed} files, {files_modified} modified")

    if files_skipped > 0:
        click.echo(click.style(f"\nSkipped {files_skipped} files:", fg="yellow"))
        for reason in skipped_reasons:
            click.echo(click.style(f"  {reason}", fg="yellow"))


def main() -> None:
    """Entry point."""
    replace_text()


if __name__ == "__main__":
    main()
