#!/usr/bin/env python3
"""Benchmark hbctool roundtrip speed and output-size safety.

Supports comparing pure-Python mode vs C++-accelerated util mode (if available).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import shutil
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import hbctool
import hbctool.util as util


@dataclass
class RunMetrics:
    label: str
    disasm_seconds: float
    asm_seconds: float
    total_seconds: float
    input_size_bytes: int
    output_size_bytes: int
    size_ratio_vs_input: float
    sha256_input: str
    sha256_output: str


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def set_fastutil_mode(enable_cpp: bool) -> bool:
    """Enable/disable C++ fast util bindings at runtime.

    Returns True if C++ mode is active after the call.
    """
    if not enable_cpp:
        util._fastutil = None
        return False

    if util._fastutil is not None:
        return True

    spec = importlib.util.find_spec("hbctool._fastutil")
    if spec is None:
        util._fastutil = None
        return False

    module = importlib.import_module("hbctool._fastutil")
    util._fastutil = module
    return True


def run_roundtrip(input_file: Path, out_dir: Path, label: str, enable_cpp: bool, force_clean: bool = True) -> RunMetrics:
    hasm_dir = out_dir / f"{label}_hasm"
    output_bundle = out_dir / f"{label}.bundle"

    if force_clean:
        shutil.rmtree(hasm_dir, ignore_errors=True)
        if output_bundle.exists():
            output_bundle.unlink()

    set_fastutil_mode(enable_cpp)

    t0 = time.perf_counter()
    hbctool.disasm(str(input_file), str(hasm_dir))
    t1 = time.perf_counter()
    hbctool.asm(str(hasm_dir), str(output_bundle))
    t2 = time.perf_counter()

    input_size = input_file.stat().st_size
    output_size = output_bundle.stat().st_size

    return RunMetrics(
        label=label,
        disasm_seconds=t1 - t0,
        asm_seconds=t2 - t1,
        total_seconds=t2 - t0,
        input_size_bytes=input_size,
        output_size_bytes=output_size,
        size_ratio_vs_input=(output_size / input_size) if input_size else 0.0,
        sha256_input=sha256_file(input_file),
        sha256_output=sha256_file(output_bundle),
    )


def summarize(label: str, runs: list[RunMetrics]) -> dict:
    disasm = [r.disasm_seconds for r in runs]
    asm = [r.asm_seconds for r in runs]
    total = [r.total_seconds for r in runs]

    return {
        "label": label,
        "runs": [asdict(r) for r in runs],
        "mean_disasm_seconds": statistics.mean(disasm),
        "mean_asm_seconds": statistics.mean(asm),
        "mean_total_seconds": statistics.mean(total),
        "stdev_total_seconds": statistics.pstdev(total),
        "last_size_ratio_vs_input": runs[-1].size_ratio_vs_input,
        "last_output_size_bytes": runs[-1].output_size_bytes,
        "last_sha256_equal": runs[-1].sha256_input == runs[-1].sha256_output,
    }


def benchmark_mode(mode_name: str, input_file: Path, out_dir: Path, iterations: int, enable_cpp: bool) -> dict:
    runs: list[RunMetrics] = []
    for i in range(iterations):
        runs.append(
            run_roundtrip(
                input_file,
                out_dir,
                label=f"{mode_name}_{i}",
                enable_cpp=enable_cpp,
            )
        )
    return summarize(mode_name, runs)


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark hbctool and enforce output-size guardrails.")
    parser.add_argument("input", type=Path, help="Path to source Hermes bytecode bundle")
    parser.add_argument("--out-dir", type=Path, default=Path("output/bench"), help="Output directory for artifacts")
    parser.add_argument("--iterations", type=int, default=2, help="Number of runs per mode")
    parser.add_argument("--max-size-ratio", type=float, default=1.10, help="Fail if output/input ratio exceeds this")
    parser.add_argument("--json", type=Path, default=None, help="Optional JSON output path")
    args = parser.parse_args()

    if args.iterations < 1:
        raise SystemExit("--iterations must be >= 1")
    if not args.input.is_file():
        raise SystemExit(f"Input file does not exist: {args.input}")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    py_summary = benchmark_mode("python", args.input, args.out_dir, args.iterations, enable_cpp=False)

    cpp_available = set_fastutil_mode(enable_cpp=True)
    cpp_summary = None
    if cpp_available:
        cpp_summary = benchmark_mode("cpp", args.input, args.out_dir, args.iterations, enable_cpp=True)

    comparisons = {
        "cpp_available": cpp_available,
        "speedup_vs_python": None,
        "python_size_ratio": py_summary["last_size_ratio_vs_input"],
        "cpp_size_ratio": cpp_summary["last_size_ratio_vs_input"] if cpp_summary else None,
    }

    if cpp_summary:
        comparisons["speedup_vs_python"] = py_summary["mean_total_seconds"] / cpp_summary["mean_total_seconds"]

    report = {
        "input": str(args.input),
        "iterations": args.iterations,
        "max_size_ratio": args.max_size_ratio,
        "python": py_summary,
        "cpp": cpp_summary,
        "comparisons": comparisons,
    }

    print("\n=== hbctool benchmark report ===")
    print(f"input: {args.input}")
    print(f"iterations per mode: {args.iterations}")
    print(f"python mean total: {py_summary['mean_total_seconds']:.3f}s")
    print(f"python size ratio: {py_summary['last_size_ratio_vs_input']:.4f}")

    if cpp_summary:
        print(f"cpp mean total: {cpp_summary['mean_total_seconds']:.3f}s")
        print(f"cpp size ratio: {cpp_summary['last_size_ratio_vs_input']:.4f}")
        print(f"speedup (python/cpp): {comparisons['speedup_vs_python']:.3f}x")
    else:
        print("cpp fastutil extension not available; only python mode measured.")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"json report: {args.json}")

    failing_ratios = [py_summary["last_size_ratio_vs_input"]]
    if cpp_summary:
        failing_ratios.append(cpp_summary["last_size_ratio_vs_input"])

    if any(r > args.max_size_ratio for r in failing_ratios):
        print(f"ERROR: one or more modes exceeded max size ratio {args.max_size_ratio:.4f}")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
