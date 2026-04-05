# HBC-Tool Project Context

## Project Overview

**HBC-Tool** (hbctool) is a command-line utility for **disassembling and assembling Hermes Bytecode (HBC)**. Hermes is an open-source JavaScript engine optimized for React Native applications on Android, created by Meta (Facebook). As more React Native apps compile to Hermes bytecode instead of standard JavaScript, reverse engineers and penetration testers need tools to analyze these binaries — hbctool fills that gap.

### Key Features
- **Disassemble** HBC files into a human-readable HASM (Hermes Assembly) format
- **Assemble** HASM files back into valid HBC binaries
- Supports **HBC versions 59 through 96** (18 different bytecode versions)
- Used primarily for static analysis, patching, and security research of React Native apps

### Architecture

The project is organized as follows:

```
hbctool/
├── __init__.py        # CLI entry point (docopt-based), main disasm/asm functions
├── hasm.py            # HASM format serialization (dump/load instructions, strings, metadata)
├── util.py            # Low-level bit I/O (BitReader, BitWriter, packing/unpacking utilities)
├── metadata.py        # Project metadata (version, name)
├── test.py            # Unit tests
└── hbc/
    ├── __init__.py    # HBC loader/dispatcher — selects version-specific handler
    └── hbc{NN}/       # Version-specific implementations (hbc59, hbc62, ..., hbc96)
        ├── __init__.py    # HBC class definition for this version
        ├── parser.py      # Bytecode parsing logic
        ├── translator.py  # Opcode translation/mapping
        ├── data/          # JSON data files (opcode.json, structure.json)
        ├── raw/           # Raw bytecode data
        └── tool/          # Version-specific tools
```

Each HBC version directory (e.g., `hbc96`) contains a class (`HBC96`) that handles the binary format specifics for that bytecode version, including header structure, string table, function table, and instruction opcodes.

## Technologies

- **Language:** Python 3.6+
- **CLI Framework:** docopt
- **Build System:** Poetry
- **Package Format:** Wheel (`.whl`)

## Building and Running

### Installation

```bash
# Install from wheel
pip install --force-reinstall hbctool-0.1.5-96-py3-none-any.whl

# Or install via pip (if published)
pip install hbctool
```

### Usage

```bash
# Disassemble an HBC file to HASM directory
hbctool disasm index.android.bundle output_hasm/

# Assemble HASM directory back to HBC
hbctool asm output_hasm/ index.android.bundle

# Show help
hbctool --help
```

> **Note:** On Android, the HBC file is typically found at `assets/index.android.bundle` within an APK.

### Development Setup

```bash
# Using Poetry
poetry install
poetry build

# Install the built wheel
pip install --force-reinstall dist/hbctool-<VERSION>-py3-none-any.whl
```

### Running Tests

```bash
cd hbctool
python test.py
```

## HASM Output Format

When disassembling, hbctool produces a directory containing:

| File | Description |
|------|-------------|
| `metadata.json` | Full HBC object serialized as JSON (header, function metadata, etc.) |
| `string.json` | String table with UTF-8/UTF-16 flags and values |
| `instruction.hasm` | Human-readable assembly instructions per function |

The HASM instruction format looks like:

```
Function<0>0(1 params, 3 registers, 5 symbols):
    MovLongLitObj         LitObjectId:3086
    ; Oper[0]: String(3086) 'Hello World'
EndFunction
```

## Development Conventions

- **Version Abstraction:** Each HBC version has its own isolated directory with a class implementing the version-specific binary format
- **Bit-level I/O:** The `util.py` module provides `BitReader`/`BitWriter` for precise bit-level parsing (important since HBC uses non-byte-aligned fields)
- **Testing:** Unit tests exist in `hbctool/test.py` and within individual `hbc{NN}/test.py` files. Run all tests before submitting pull requests
- **Pending Work:** See README's "Next Step" section — includes adding more HBC versions, class abstraction, overflow patching support, and resolving TODO/FIXME/NOTE comments in source code

## Key Files

| File | Purpose |
|------|---------|
| `hbctool/__init__.py` | Main CLI entry point with docopt argument parsing |
| `hbctool/hbc/__init__.py` | HBC version dispatcher — reads magic/version and returns appropriate handler |
| `hbctool/hasm.py` | Serializes/deserializes the HASM text format |
| `hbctool/util.py` | Core bit I/O primitives (BitReader, BitWriter, type conversions) |
| `pyproject.toml` | Poetry configuration, dependencies, and build settings |
