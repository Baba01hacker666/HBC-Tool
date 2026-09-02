"""
A command-line interface for disassembling and assembling
the Hermes Bytecode.
"""

import argparse
import os
import sys

from hbctool import hasm, hbc, metadata

DEFAULT_HASM_PATH = "hasm"
DEFAULT_HBC_FILE = "index.android.bundle"


def _confirm_overwrite(path):
    if not os.path.exists(path):
        return False

    abs_path = os.path.abspath(os.path.normpath(path))
    if abs_path in ("/", os.path.expanduser("~"), os.getcwd()):
        raise hasm.HASMError(f"Refusing to remove unsafe output directory: {path}")

    if os.path.islink(path):
        raise hasm.HASMError(f"Refusing to remove symbolic link: {path}")

    c = input(f"'{path}' exists. Do you want to remove it ? (y/n): ").lower().strip()
    if c[:1] != "y":
        raise FileExistsError(f"Output directory already exists: {path}")

    return True


def disasm(hbcfile, hasmpath):
    if not os.path.isfile(hbcfile):
        raise FileNotFoundError(f"HBC file not found: {hbcfile}")

    print(f"[*] Disassemble '{hbcfile}' to '{hasmpath}' path")
    with open(hbcfile, "rb") as f:
        hbco = hbc.load(f)

    header = hbco.getHeader()
    sourceHash = bytes(header["sourceHash"]).hex()
    version = header["version"]
    print(f"[*] Hermes Bytecode [ Source Hash: {sourceHash}, HBC Version: {version} ]")

    overwrite = _confirm_overwrite(hasmpath)
    hasm.dump(hbco, hasmpath, force=overwrite)
    print("[*] Done")


def asm(hasmpath, hbcfile):
    print(f"[*] Assemble '{hasmpath}' to '{hbcfile}' path")
    hbco = hasm.load(hasmpath)

    header = hbco.getHeader()
    sourceHash = bytes(header["sourceHash"]).hex()
    version = header["version"]
    print(f"[*] Hermes Bytecode [ Source Hash: {sourceHash}, HBC Version: {version} ]")

    with open(hbcfile, "wb") as f:
        hbc.dump(hbco, f)
    print("[*] Done")


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="hbctool",
        description="A command-line interface for disassembling and assembling the Hermes Bytecode.",
    )
    parser.add_argument(
        "--version", action="version", version=f"{metadata.project} {metadata.version}"
    )

    subparsers = parser.add_subparsers(dest="operation")
    subparsers.required = True

    disasm_parser = subparsers.add_parser(
        "disasm", aliases=["d"], help="Disassemble Hermes Bytecode"
    )
    disasm_parser.add_argument("hbc_file", metavar="HBC_FILE", help="Target HBC file")
    disasm_parser.add_argument(
        "hasm_path",
        metavar="HASM_PATH",
        nargs="?",
        default=DEFAULT_HASM_PATH,
        help="Target HASM directory path",
    )

    asm_parser = subparsers.add_parser(
        "asm", aliases=["a"], help="Assemble Hermes Bytecode"
    )
    asm_parser.add_argument(
        "hasm_path",
        metavar="HASM_PATH",
        nargs="?",
        default=DEFAULT_HASM_PATH,
        help="Target HASM directory path",
    )
    asm_parser.add_argument(
        "hbc_file",
        metavar="HBC_FILE",
        nargs="?",
        default=DEFAULT_HBC_FILE,
        help="Target HBC file",
    )

    return parser


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.operation in ("disasm", "d"):
            disasm(args.hbc_file, args.hasm_path)
        elif args.operation in ("asm", "a"):
            asm(args.hasm_path, args.hbc_file)
    except (FileNotFoundError, FileExistsError, hasm.HASMError, ValueError) as exc:
        print(f"[!] {exc}", file=sys.stderr)
        raise SystemExit(1)


def entry_point():
    """Zero-argument entry point for use with setuptools/distribute."""
    main()


if __name__ == "__main__":
    main()
