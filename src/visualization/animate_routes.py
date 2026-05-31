"""
Animated GIF / video for LinkedIn — OR-Tools only.

  Act 1 — Problem: 100 customer dots on a dark map
  Act 2 — Routes build up one by one with neon glow
  Act 3 — Stats card (distance, vehicles, time)
"""

from __future__ import annotations

import io
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
from PIL import Image

from src.utils.data_loader import load_solomon
from src.solvers.ortools_cvrp import solve as ortools_solve, VRPSolution

OUTPUT_PATH = Path(__file__).parent.parent.parent / "outputs" / "linkedin_routes.gif"

BG       = "#0D1117"
GRID     = "#161B22"
NODE_DIM = "#2A3A4A"

NEON = [
    "#00F5FF", "#FF2079", "#FFB700", "#39FF14",
    "#BF5AF2", "#FF6B35", "#00D4AA", "#FF4DC4",
    "#5CE1E6", "#FFD166",
]

FIG_W, FIG_H = 9, 9
DPI = 120


def _fig_to_pil(fig: plt.Figure) -> Image.Image:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, facecolor=fig.get_facecolor())
    buf.seek(0)
    return Image.open(buf).copy()


def _base_axes(fig: plt.Figure, instance) -> plt.Axes:
    # Leave top 14% of figure as a clear header band for text
    ax = fig.add_axes([0.05, 0.04, 0.90, 0.82])
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)
    ax.set_aspect("equal")
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID)
    xs = [c.x for c in instance.customers]
    ys = [c.y for c in instance.customers]
    ax.scatter(xs, ys, s=18, c=NODE_DIM, zorder=3, linewidths=0)
    ax.scatter(instance.depot.x, instance.depot.y,
               s=260, c="white", marker="*", zorder=6)
    return ax


def _glow_line(ax, xs, ys, color, lw=2.0):
    ax.plot(xs, ys, "-", color=color, linewidth=lw + 4, alpha=0.15, zorder=4, solid_capstyle="round")
    ax.plot(xs, ys, "-", color=color, linewidth=lw + 1.5, alpha=0.35, zorder=4, solid_capstyle="round")
    ax.plot(xs, ys, "-", color=color, linewidth=lw, alpha=0.95, zorder=5, solid_capstyle="round")


def _glow_scatter(ax, xs, ys, color, s=40):
    ax.scatter(xs, ys, s=s + 40, c=color, alpha=0.22, zorder=5, linewidths=0)
    ax.scatter(xs, ys, s=s, c=color, zorder=6, linewidths=0)


def _title(fig, line1, line2=""):
    # Place text in the header band above the axes (figure coords: axes ends at 0.86)
    fig.text(0.5, 0.955, line1, ha="center", va="center",
             fontsize=13, fontweight="bold", color="white",
             path_effects=[pe.withStroke(linewidth=3, foreground=BG)])
    if line2:
        fig.text(0.5, 0.915, line2, ha="center", va="center",
                 fontsize=9, color="#8B949E")


# ── Act 1: problem statement ──────────────────────────────────────────────────

def act1_frames(instance) -> list[Image.Image]:
    frames = []
    for _ in range(10):
        fig = plt.figure(figsize=(FIG_W, FIG_H))
        ax = _base_axes(fig, instance)
        _title(fig,
               "Fleet Routing Optimisation",
               f"{instance.num_customers} delivery stops  ·  {instance.num_vehicles} vehicles  ·  where do you even start?")
        frames.append(_fig_to_pil(fig))
        plt.close(fig)
    return frames


# ── Act 2: routes build up ────────────────────────────────────────────────────

def act2_frames(instance, sol: VRPSolution) -> list[Image.Image]:
    frames = []
    nodes = [instance.depot] + instance.customers
    active = [r for r in sol.routes if r.stops]

    revealed: list[int] = []
    for idx, route in enumerate(active):
        revealed.append(idx)
        for _ in range(2):
            fig = plt.figure(figsize=(FIG_W, FIG_H))
            ax = _base_axes(fig, instance)
            for ridx in revealed:
                r = active[ridx]
                color = NEON[ridx % len(NEON)]
                path = [0] + [s + 1 for s in r.stops] + [0]
                rx = [nodes[i].x for i in path]
                ry = [nodes[i].y for i in path]
                _glow_line(ax, rx, ry, color)
                _glow_scatter(ax,
                               [nodes[i].x for i in path[1:-1]],
                               [nodes[i].y for i in path[1:-1]],
                               color)
            dist_so_far = sum(active[i].distance for i in revealed)
            _title(fig,
                   f"OR-Tools  ·  route {idx + 1} / {len(active)}",
                   f"distance so far: {dist_so_far:,.0f}")
            frames.append(_fig_to_pil(fig))
            plt.close(fig)

    # Hold on completed map
    for _ in range(12):
        fig = plt.figure(figsize=(FIG_W, FIG_H))
        ax = _base_axes(fig, instance)
        for idx, r in enumerate(active):
            color = NEON[idx % len(NEON)]
            path = [0] + [s + 1 for s in r.stops] + [0]
            _glow_line(ax, [nodes[i].x for i in path], [nodes[i].y for i in path], color)
            _glow_scatter(ax,
                           [nodes[i].x for i in path[1:-1]],
                           [nodes[i].y for i in path[1:-1]],
                           color)
        _title(fig,
               "OR-Tools  ·  done ✓",
               f"Total distance: {sol.total_distance:,.0f}  ·  {sol.num_routes_used} routes")
        frames.append(_fig_to_pil(fig))
        plt.close(fig)

    return frames


# ── Act 3: stats card ─────────────────────────────────────────────────────────

def act3_frames(instance, sol: VRPSolution, elapsed_s: float) -> list[Image.Image]:
    frames = []
    for _ in range(22):
        fig = plt.figure(figsize=(FIG_W, FIG_H))
        fig.patch.set_facecolor(BG)
        ax = fig.add_subplot(111)
        ax.set_facecolor(BG)
        ax.axis("off")

        cx = 0.5
        ax.text(cx, 0.88, "Fleet Routing Optimisation  ·  Solomon C101",
                ha="center", va="center", fontsize=15, fontweight="bold",
                color="white", transform=ax.transAxes)
        ax.text(cx, 0.80, f"{instance.num_customers} customers  ·  {instance.num_vehicles} vehicles  ·  Google OR-Tools",
                ha="center", va="center", fontsize=10, color="#8B949E",
                transform=ax.transAxes)

        ax.plot([0.15, 0.85], [0.74, 0.74], color="#30363D", linewidth=1,
                transform=ax.transAxes)

        stats = [
            ("DISTANCE",  f"{sol.total_distance:,.0f}", "#00F5FF"),
            ("VEHICLES",  str(sol.num_routes_used),      "#FFB700"),
            ("SOLVE TIME", f"{elapsed_s:.1f} s",         "#39FF14"),
        ]
        x_positions = [0.22, 0.5, 0.78]
        for x_pos, (label, value, color) in zip(x_positions, stats):
            ax.text(x_pos, 0.64, label, ha="center", va="center",
                    fontsize=10, color=color, fontweight="bold",
                    transform=ax.transAxes)
            ax.text(x_pos, 0.50, value, ha="center", va="center",
                    fontsize=26, color=color, fontweight="bold",
                    transform=ax.transAxes)

        ax.plot([0.15, 0.85], [0.38, 0.38], color="#30363D", linewidth=1,
                transform=ax.transAxes)

        ax.text(cx, 0.28, "CP  +  Guided Local Search",
                ha="center", va="center", fontsize=14, fontweight="bold",
                color="white", transform=ax.transAxes,
                path_effects=[pe.withStroke(linewidth=3, foreground=BG)])
        ax.text(cx, 0.19, "same stops  ·  same vehicles  ·  optimal sequencing",
                ha="center", va="center", fontsize=10, color="#8B949E",
                transform=ax.transAxes)

        ax.text(cx, 0.07, "VRP benchmark: Solomon 1987  ·  Solver: Google OR-Tools  ·  github.com/mohithvarma",
                ha="center", va="center", fontsize=8, color="#444D56",
                transform=ax.transAxes)

        frames.append(_fig_to_pil(fig))
        plt.close(fig)

    return frames


# ── main ──────────────────────────────────────────────────────────────────────

def generate(save_path: Path = OUTPUT_PATH) -> None:
    save_path.parent.mkdir(parents=True, exist_ok=True)

    print("Loading Solomon C101 ...")
    instance = load_solomon("C101")

    print("Running OR-Tools solver (30s limit) ...")
    t0 = time.perf_counter()
    sol = ortools_solve(instance, time_limit_seconds=30)
    elapsed = time.perf_counter() - t0

    print("Rendering frames ...")
    frames: list[Image.Image] = []
    frames += act1_frames(instance)
    frames += act2_frames(instance, sol)
    frames += act3_frames(instance, sol, elapsed)

    n_intro   = 10
    n_reveal  = len([r for r in sol.routes if r.stops]) * 2
    n_hold    = 12
    n_stats   = 22

    durations = (
        [700]  * n_intro  +
        [200]  * n_reveal +
        [500]  * n_hold   +
        [160]  * (n_stats - 1) +
        [3500]
    )

    print(f"Converting {len(frames)} frames ...")
    pal = [f.convert("P", palette=Image.ADAPTIVE, colors=256) for f in frames]

    print(f"Saving → {save_path}")
    pal[0].save(
        save_path,
        save_all=True,
        append_images=pal[1:],
        duration=durations,
        loop=0,
        optimize=False,
        disposal=2,
    )
    print(f"Done  ({save_path.stat().st_size / 1024:.0f} KB)")
    print(f"  Distance : {sol.total_distance:,.2f}")
    print(f"  Vehicles : {sol.num_routes_used}")
    print(f"  Time     : {elapsed:.2f} s")


if __name__ == "__main__":
    generate()
