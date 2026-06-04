# Fleet Routing Optimisation

Solving the **Capacitated Vehicle Routing Problem (CVRP)** on real benchmark data using Google OR-Tools.

> Tested on Python 3.10+. Compatible with Python 3.11 and 3.12 as well.

Given one depot, N customers, and K vehicles — assign every customer to a vehicle and sequence each vehicle's stops to minimise total travel distance, subject to capacity constraints.

---

## The Problem

Fleet routing is NP-hard. The search space grows factorially with the number of customers — brute force is infeasible beyond ~15 stops. Real solvers exploit problem structure through constraint programming and metaheuristics.

### Problem variants

| Variant | Constraint |
|---|---|
| CVRP | Each vehicle has a weight/volume capacity |
| VRPTW | Each customer has a time window `[ready, due]` |
| MDVRP | Multiple depots |
| PDP | Paired pickup + delivery stops |

---

## Solver

**Google OR-Tools routing solver** (`src/solvers/ortools_cvrp.py`)

- Uses **Constraint Programming (CP)** for feasibility + **Guided Local Search (GLS)** metaheuristic for optimisation
- Starts from a `PATH_CHEAPEST_ARC` seed, then iteratively improves by exploring neighbour solutions
- Finds near-optimal solutions in seconds for 100-customer instances
- Chosen over MILP (PuLP/CBC): MILP proves global optimality but scales poorly — OR-Tools exploits routing structure directly and is orders of magnitude faster in practice

The solver decides both **assignment** (which customers go to which vehicle) and **sequencing** (the exact visitation order per vehicle) simultaneously. Both matter — `A→B→C` and `A→C→B` have different total distances.

---

## Datasets

Both datasets auto-download on first use and are cached in `data/raw/`.

### Solomon VRPTW benchmarks

The gold-standard dataset for VRP algorithm comparison — every routing paper benchmarks against it.

- Published by Marius Solomon (1987)
- **56 instances**, each with exactly **100 customers**
- Three spatial layouts: `C` (clustered), `R` (random), `RC` (mixed)
- Two time-window tightness levels: `x1xx` (tight), `x2xx` (wide)
- Source: [SINTEF TOP](https://www.sintef.no/projectweb/top/vrptw/solomon-benchmark/)

> Coordinates are dimensionless (not lat/lon) — a normalised 2D plane with Euclidean distances.

### Augerat CVRP benchmarks

Pure capacity-constrained VRP without time windows.

- Published by Augerat et al. (1995)
- Classes A, B, E, F, M, P — 13 to 200 customers
- TSPLIB-style `.vrp` format
- Source: [vrp.gdb.tools](https://vrp.gdb.tools/)

---

## Project structure

```
.
├── data/
│   └── raw/
│       ├── solomon/          # .txt files (auto-downloaded)
│       └── augerat/          # .vrp files (auto-downloaded)
├── src/
│   ├── utils/
│   │   ├── data_loader.py    # parse Solomon & Augerat formats; build VRPInstance
│   │   └── download_data.py  # CLI bulk downloader
│   ├── solvers/
│   │   └── ortools_cvrp.py   # OR-Tools routing solver + Route/VRPSolution dataclasses
│   └── visualization/
│       ├── plot_routes.py    # static matplotlib route plots
│       └── animate_routes.py # animated GIF/video generator
├── outputs/                  # generated media (gitignored)
├── main.py                   # CLI entry point
└── requirements.txt
```

---

## Quick start

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Solve a Solomon instance (auto-downloads on first run)
python main.py --solomon C101

# 4. Show route plots
python main.py --solomon C101 --plot

# 5. Try different instance layouts
python main.py --solomon R101    # random customer layout
python main.py --solomon RC201   # mixed layout, wide time windows

# 6. Solve an Augerat CVRP instance (no time windows)
python main.py --augerat A-n32-k5

# 7. Pre-download all 56 Solomon instances
python -m src.utils.download_data --all-solomon

# 8. List all available Solomon instance names
python main.py --list-solomon

# 9. Generate animated visualisation
python -m src.visualization.animate_routes
```

---

## Example output

```
Instance   : C101
Customers  : 100
Vehicles   : 25
Capacity   : 200.0

=== OR-Tools routing solver (time limit: 30s) ===
Instance  : C101
Feasible  : True
Vehicles  : 10/25
Total dist: 873.30
  V0: depot -> [32, 33, 31, 35, 37, 38, 39, 36, 34] -> depot  (load=200, dist=168.42)
  V1: depot -> [57, 55, 54, 56, 58, 60, 59] -> depot          (load=190, dist=127.85)
  ...
Time: 0.10 s
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `ortools` | Google OR-Tools — routing solver (CP + GLS) |
| `networkx` | Graph algorithms for future graph-theoretic extensions |
| `osmnx` | Real road networks from OpenStreetMap (planned) |
| `pulp` | MILP modelling — planned exact two-index VRP formulation |
| `geopandas` | Geospatial data handling |
| `folium` | Interactive map visualisation (planned) |
| `matplotlib` | Static route plots |
| `Pillow` | GIF export for animated visualisations |

---

## References

- Solomon, M.M. (1987). *Algorithms for the Vehicle Routing and Scheduling Problems with Time Window Constraints.* Operations Research 35(2).
- Augerat, P. et al. (1995). *Computational Results with a Branch-and-Cut Code for the Capacitated Vehicle Routing Problem.*
- [Google OR-Tools VRP documentation](https://developers.google.com/optimization/routing/vrp)
- [SINTEF TOP — best known VRP solutions](https://www.sintef.no/projectweb/top/)
- [vrp.gdb.tools — Augerat instances](https://vrp.gdb.tools/)
