<p align="center">
  <img src="https://raw.githubusercontent.com/Baba01hacker666/HBC-Tool/main/image/hbctool-logo.svg" alt="hbctool logo" width="900">
</p>

<p align="center">
  <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.x-yellow.svg" alt="Python 3.x"></a>
  <a href="https://badge.fury.io/py/hbctool-cli"><img src="https://badge.fury.io/py/hbctool-cli.svg" alt="PyPI version"></a>
  <a href="/LICENSE"><img src="https://img.shields.io/badge/license-MIT-brightgreen.svg" alt="MIT License"></a>
</p>

<p align="center">
  <strong>A Hermes bytecode disassembler and assembler for React Native bundles.</strong>
  <br>
  Originally created by <code>baba01hacker</code> and continued by <code>Doraemon cyber team</code>.
</p>

## Why hbctool

React Native apps can ship JavaScript through the Hermes engine, which compiles application code into Hermes bytecode. That makes reverse engineering, inspection, and patching harder than working with plain JavaScript bundles.

`hbctool` helps with that workflow by letting you:

- disassemble a Hermes bundle into a readable HASM representation
- modify metadata, strings, and instructions
- rebuild a valid Hermes bytecode bundle from the edited output
- use either the pure-Python path or the optional native C++ acceleration path

## Features

- Disassemble Hermes bytecode bundles into a directory with metadata, strings, and instructions.
- Assemble edited HASM output back into a Hermes bundle.
- Optional C++ acceleration for faster low-level operations.
- Test coverage for pure-Python and native execution paths.
- Support for Hermes bytecode versions `59`, `62`, `74`, `76`, `83`, `84`, `85`, `86`, `87`, `88`, `89`, `90`, `91`, `92`, `93`, `94`, `95`, and `96`.

## Installation

### Quick install

```bash
python3 -m pip install hbctool-cli
```

### Local development install

```bash
python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install -e .
```

### Build the optional native extension

```bash
python3 setup.py build_ext --inplace
```

Enable the accelerated path at runtime:

```bash
export HBCTOOL_FASTUTIL=1
```

Verify that the native modules are available:

```bash
python3 -c "import hbctool._fastutil, hbctool._bitcodec; print('native extensions ok')"
```

If the extensions are not present, `hbctool` still works in pure-Python mode.

## Usage

Show help:

```bash
hbctool --help
```

CLI syntax:

```text
Usage:
    hbctool disasm <HBC_FILE> [<HASM_PATH>]
    hbctool asm [<HASM_PATH>] [<HBC_FILE>]
    hbctool --help
    hbctool --version
```

Examples:

```bash
hbctool disasm index.android.bundle test_hasm
hbctool asm test_hasm index.android.bundle
hbctool disasm index.android.bundle
hbctool asm
```

By default:

- `disasm` writes to `hasm/`
- `asm` reads from `hasm/` and writes `index.android.bundle`

For Android targets, the Hermes bundle is commonly found under the app `assets/` directory as `index.android.bundle`.

## Output Layout

A disassembly writes three files:

- `metadata.json`
- `string.json`
- `instruction.hasm`

This makes it practical to inspect strings, metadata, and instructions separately before rebuilding.

## Benchmarking

You can benchmark the round-trip path and compare pure Python against the native path with the helper script:

```bash
python3 scripts/benchmark_roundtrip.py Testfiles/index.android.bundle --iterations 2 --max-size-ratio 1.10 --min-core-speedup 2.0 --json output/bench/report.json
```

The report includes:

- timing for both execution modes
- computed speedup
- output-to-input size ratio checks
- a low-level memcpy speedup check

The script exits non-zero when configured safety or performance thresholds are not met, which makes it suitable for CI gating.

## Development

Run the test suite:

```bash
python3 -m pytest -q
```

Run the test suite with the native path enabled:

```bash
HBCTOOL_FASTUTIL=1 python3 -m pytest -q
```

Build distributable artifacts:

```bash
python3 -m pip install --upgrade build
python3 -m build
```

If the built wheel includes the compiled extension, it will be platform-tagged rather than `py3-none-any`.

## Credits

- Original work: `baba01hacker`
- Ongoing maintenance and remastering: `Doraemon cyber team`

## License

This project is released under the MIT License. See [LICENSE](/LICENSE).
