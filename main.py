"""
Entry point: solve a CVRP/VRPTW instance from real benchmark data.

Uses:
  - Solomon VRPTW benchmarks (100 customers, SINTEF 1987)
  - Augerat CVRP benchmarks (TSPLIB format)

Solves with Google OR-Tools routing solver (CP + Guided Local Search).

Usage:
    python main.py --solomon C101
    python main.py --solomon R201 --time-limit 60 --plot
    python main.py --augerat A-n32-k5
    python main.py --list-solomon
"""

import argparse
import time

from src.utils.data_loader import load_solomon, load_augerat
from src.utils.download_data import SOLOMON_INSTANCES
from src.solvers.ortools_cvrp import solve as ortools_solve
from src.visualization.plot_routes import plot_solution


def main():
    parser = argparse.ArgumentParser(
        description="Fleet routing on real VRP benchmark data (OR-Tools)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--solomon", metavar="NAME",
                       help="Solomon VRPTW instance name, e.g. C101, R201, RC101")
    group.add_argument("--augerat", metavar="NAME",
                       help="Augerat CVRP instance name, e.g. A-n32-k5, B-n31-k5")
    group.add_argument("--list-solomon", action="store_true",
                       help="Print all available Solomon instance names and exit")

    parser.add_argument("--time-limit", type=int, default=30,
                        help="OR-Tools search time limit in seconds (default: 30)")
    parser.add_argument("--plot", action="store_true",
                        help="Show matplotlib route plots after solving")
    args = parser.parse_args()

    if args.list_solomon:
        print("Available Solomon instances:")
        for i, name in enumerate(SOLOMON_INSTANCES):
            end = "\n" if (i + 1) % 9 == 0 else "  "
            print(name, end=end)
        print()
        return

    if args.solomon:
        instance = load_solomon(args.solomon)
    else:
        instance = load_augerat(args.augerat)

    print(f"\nInstance   : {instance.name}")
    print(f"Customers  : {instance.num_customers}")
    print(f"Vehicles   : {instance.num_vehicles}")
    print(f"Capacity   : {instance.vehicle_capacity}\n")

    t0 = time.perf_counter()
    solution = ortools_solve(instance, time_limit_seconds=args.time_limit)
    elapsed = time.perf_counter() - t0

    print(f"=== OR-Tools routing solver (time limit: {args.time_limit}s) ===")
    print(solution.summary())
    print(f"Time: {elapsed:.2f} s")

    if args.plot:
        plot_solution(solution, title=f"OR-Tools — {instance.name}")


if __name__ == "__main__":
    main()
