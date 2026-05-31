"""
Matplotlib visualizer for VRP solutions.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np

from src.utils.data_loader import VRPInstance
from src.solvers.ortools_cvrp import VRPSolution


def plot_solution(solution: VRPSolution, title: str = "", save_path: str | None = None):
    instance = solution.instance
    depot = instance.depot
    colors = cm.tab10(np.linspace(0, 1, max(len(solution.routes), 1)))

    fig, ax = plt.subplots(figsize=(9, 9))

    ax.scatter(depot.x, depot.y, s=200, c="black", marker="*", zorder=5, label="Depot")

    for c in instance.customers:
        ax.scatter(c.x, c.y, s=60, c="steelblue", zorder=4)
        ax.annotate(str(c.id), (c.x, c.y), textcoords="offset points",
                    xytext=(4, 4), fontsize=7)

    nodes = [depot] + instance.customers
    for route, color in zip(solution.routes, colors):
        if not route.stops:
            continue
        path = [0] + [s + 1 for s in route.stops] + [0]
        xs = [nodes[i].x for i in path]
        ys = [nodes[i].y for i in path]
        ax.plot(xs, ys, "-o", color=color, linewidth=1.5, markersize=4,
                label=f"V{route.vehicle_id} (load={route.load:.0f}, d={route.distance:.1f})")

    heading = title or f"{instance.name} — Total distance: {solution.total_distance:.2f}"
    ax.set_title(heading, fontsize=12)
    ax.legend(loc="upper right", fontsize=8)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_aspect("equal")
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"Saved to {save_path}")
    else:
        plt.show()

    plt.close(fig)
