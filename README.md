# textswap

**Bulk text replacement in files using dictionary mappings.**

[![PyPI version](https://badge.fury.io/py/textswap.svg)](https://badge.fury.io/py/textswap)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

Replace text across multiple files using find/replace dictionaries.

- **Reversible**: apply a dictionary forward (keys-to-values) or backward (values-to-keys) — encode/decode, rename/undo
- **Swap-safe**: all replacements happen in a single pass, so `{"foo": "bar", "bar": "foo"}` swaps cleanly and chains never cascade
- **Whole-word mode**: `-w` keeps a key like `cat` from matching inside `category` — built for renaming identifiers
- **Safe by default**: dry-run diffs before you commit, automatic backups with `-b`

## Installation

```bash
pip install textswap
```

## Quick Start

1. Create a config file (`config.json`):

```json
{
  "dictionaries": {
    "example": {
      "old_text": "new_text",
      "foo": "bar"
    }
  },
  "ignore_extensions": [".exe", ".bin"],
  "ignore_directories": ["node_modules", ".git"],
  "ignore_file_prefixes": [".", "_"]
}
```

2. Run:

```bash
textswap -f ./my_folder -d 1
```

## Usage

```bash
# Interactive mode
textswap

# With options
textswap --folder ./src --direction 1 --config my_config.json

# Dry run (preview changes with diff output)
textswap -f ./src -d 1 --dry-run

# Back up originals before modifying
textswap -f ./src -d 1 -b ./backups

# Only match whole words (won't touch "category" when renaming "cat")
textswap -f ./src -d 1 -w

# Reverse direction (values-to-keys)
textswap -f ./src -d 2
```

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--folder` | `-f` | Folder to process |
| `--direction` | `-d` | 1 = keys-to-values, 2 = values-to-keys |
| `--config` | `-c` | Path to config file (default: config.json) |
| `--dict-name` | `-n` | Dictionary name (auto-selects if only one) |
| `--backup-dir` | `-b` | Copy originals here (mirroring folder structure) before modifying |
| `--whole-words` | `-w` | Only match keys as whole words (not inside identifiers) |
| `--dry-run` | | Preview changes without modifying files |

## Config Format

```json
{
  "dictionaries": {
    "my_replacements": {
      "find_this": "replace_with_this",
      "old": "new"
    }
  },
  "ignore_extensions": [".exe", ".dll"],
  "ignore_directories": ["node_modules", "venv"],
  "ignore_file_prefixes": [".", "_"]
}
```

## How It Works

1. **Load config**: Reads your JSON config file containing replacement dictionaries
2. **Walk directory**: Recursively traverses the target folder
3. **Filter files**: Skips files matching ignore rules (extensions, prefixes, directories)
4. **Read & replace**: For each file, applies every mapping in a single pass — longest key wins on overlaps, and replaced text is never re-replaced
5. **Write back**: Backs up originals (if `--backup-dir` is set), then saves modified files (or shows diff in dry-run mode)

All files are processed as UTF-8. Non-UTF-8 files are automatically skipped with a warning.

## Dry Run Output

The `--dry-run` flag shows exactly what would change without modifying files:

```bash
$ textswap -f ./src -d 1 --dry-run
Dry run mode - no files will be modified

Would modify: ./src/example.txt
--- a/./src/example.txt
+++ b/./src/example.txt
@@ -1 +1 @@
-Hello world
+Goodbye world

Processed 5 files, 1 modified
```

## Multiple Dictionaries

You can define multiple dictionaries in your config for different replacement scenarios:

```json
{
  "dictionaries": {
    "encode": {
      "secret": "s3cr3t",
      "password": "p4ssw0rd"
    },
    "localize_fr": {
      "Hello": "Bonjour",
      "Goodbye": "Au revoir"
    }
  }
}
```

Select which dictionary to use with `--dict-name`:

```bash
textswap -f ./src -d 1 -n encode
textswap -f ./src -d 1 -n localize_fr
```

## Troubleshooting

### "Invalid JSON in config file"

Your config file has a syntax error. Common issues:
- Missing commas between items
- Trailing commas (not allowed in JSON)
- Unquoted strings

Use a JSON validator to check your config.

### "Config must contain a 'dictionaries' object"

Your config file is missing the required `dictionaries` key:

```json
{
  "dictionaries": {
    "my_dict": {"find": "replace"}
  }
}
```

### Files being skipped

Files are skipped for these reasons (shown in output):
- **Not UTF-8 encoded**: Binary files or files with different encoding
- **Permission denied**: No read/write access to the file

### No files modified

Check that:
1. Your search terms exactly match the file content (case-sensitive)
2. Files aren't being filtered by ignore rules
3. The target folder contains text files

### Overlapping or swapped replacements

All replacements happen in a single pass, longest key first:

- Overlapping keys (e.g., "hello" and "hello world"): the longest key wins wherever it matches.
- Replaced text is never re-replaced, so `{"cat": "dog", "dog": "wolf"}` turns "cat" into "dog" (not "wolf").
- Two names can be swapped safely: `{"foo": "bar", "bar": "foo"}` exchanges them in one run.

When renaming identifiers, add `--whole-words` so a key like `cat` doesn't match inside `category` or `concat`.

### Reverse direction with duplicate values

Direction 2 inverts the dictionary (values become keys). If two keys map to the same value, only the last mapping survives the inversion — a warning is printed when this happens.

## Use Cases

- **Encoding/decoding**: Obfuscate or de-obfuscate text in files
- **Localization**: Batch replace text for different languages
- **Refactoring**: Rename variables, functions, or classes across a codebase (use `--whole-words`)
- **Template substitution**: Replace placeholders with actual values
- **Migration**: Update deprecated API calls or import paths

## Encoding

All files are read and written as **UTF-8**. Files that cannot be decoded as UTF-8 (binary files, files with other encodings) are automatically skipped and reported in the output.

## License

GPL v3
