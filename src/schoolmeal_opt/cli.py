"""CLI entrypoint for schoolmeal-opt."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .planner import optimize_school_meal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="schoolmeal-opt",
        description="Optimize Home-Grown School Feeding least-cost meals meeting FAO/WFP RDA minimums.",
    )
    parser.add_argument("--students", type=int, default=650, help="Enrolled students fed daily.")
    parser.add_argument("--days", type=int, default=65, help="School feeding days in term.")
    args = parser.parse_args(argv)

    plan = optimize_school_meal(students=args.students, school_days=args.days)
    print(json.dumps(asdict(plan), indent=2))
    return 0 if plan.feasible else 1


if __name__ == "__main__":
    raise SystemExit(main())
