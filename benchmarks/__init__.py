"""
benchmarks — Standardized ML experiment harness for ml-decision-boundary

Usage:
    python3 -m benchmarks          # run all benchmarks
    python3 -m benchmarks --quick  # fast smoke test (single model/dataset)
    python3 -m benchmarks --report # generate report to benchmarks/reports/

Outputs:
    benchmarks/reports/YYYY-MM-DD.json  — structured results
    benchmarks/reports/YYYY-MM-DD.md    — human-readable summary
"""

from .run import run_benchmarks, main

__all__ = ["run_benchmarks", "main"]