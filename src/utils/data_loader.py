"""
Loaders for standard VRP benchmark datasets.

Supports:
  - Solomon VRPTW instances (100-customer, .txt format from SINTEF)
  - Augerat CVRP instances (TSPLIB-style .vrp format)
"""

import re
import ssl
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw"

SOLOMON_BASE_URL = "https://raw.githubusercontent.com/iRB-Lab/py-ga-VRPTW/master/data/text/"
AUGERAT_BASE_URL = "https://vrp.gdb.tools/datasets/"

# macOS ships without default CA certs for Python; unverified context is acceptable
# for downloading well-known public benchmark files.
_ssl_ctx = ssl._create_unverified_context()


@dataclass
class Customer:
    id: int
    x: float
    y: float
    demand: float
    ready_time: float = 0.0
    due_time: float = float("inf")
    service_time: float = 0.0


@dataclass
class VRPInstance:
    name: str
    depot: Customer
    customers: list[Customer]
    num_vehicles: int
    vehicle_capacity: float
    distance_matrix: Optional[np.ndarray] = field(default=None, repr=False)

    def __post_init__(self):
        if self.distance_matrix is None:
            self.distance_matrix = self._compute_euclidean_matrix()

    def _compute_euclidean_matrix(self) -> np.ndarray:
        coords = np.array([[n.x, n.y] for n in [self.depot] + self.customers])
        diff = coords[:, None, :] - coords[None, :, :]
        return np.sqrt((diff ** 2).sum(axis=-1))

    @property
    def num_customers(self) -> int:
        return len(self.customers)

    def to_dataframe(self) -> pd.DataFrame:
        rows = [
            {"id": c.id, "x": c.x, "y": c.y, "demand": c.demand,
             "ready_time": c.ready_time, "due_time": c.due_time,
             "service_time": c.service_time, "is_depot": is_depot}
            for c, is_depot in [(self.depot, True)] + [(c, False) for c in self.customers]
        ]
        return pd.DataFrame(rows)


def _fetch(url: str, dest: Path) -> None:
    """Download url to dest, raising RuntimeError on failure."""
    try:
        with urllib.request.urlopen(url, context=_ssl_ctx) as resp:
            dest.write_bytes(resp.read())
    except Exception as e:
        raise RuntimeError(f"Download failed for {url}") from e


def load_solomon(instance_name: str, download: bool = True) -> VRPInstance:
    """
    Load a Solomon VRPTW benchmark instance by name (e.g. 'C101', 'R201').

    File format (whitespace-separated):
        CUST_NO  XCOORD  YCOORD  DEMAND  READY_TIME  DUE_DATE  SERVICE_TIME
    """
    path = DATA_DIR / "solomon" / f"{instance_name}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        if not download:
            raise FileNotFoundError(f"Instance file not found: {path}")
        url = f"{SOLOMON_BASE_URL}{instance_name}.txt"
        print(f"Downloading {instance_name} from {url} ...")
        try:
            _fetch(url, path)
        except RuntimeError:
            raise RuntimeError(
                f"Could not download {instance_name}. "
                f"Download manually from https://www.sintef.no/projectweb/top/vrptw/solomon-benchmark/ "
                f"and place in {path.parent}"
            )

    return _parse_solomon(path, instance_name)


def load_augerat(instance_name: str, download: bool = True) -> VRPInstance:
    """
    Load an Augerat CVRP benchmark instance (TSPLIB-style .vrp format).
    Example names: 'A-n32-k5', 'B-n31-k5', 'P-n16-k8'
    """
    path = DATA_DIR / "augerat" / f"{instance_name}.vrp"
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        if not download:
            raise FileNotFoundError(f"Instance file not found: {path}")
        url = f"{AUGERAT_BASE_URL}{instance_name}.vrp"
        print(f"Downloading {instance_name} from {url} ...")
        try:
            _fetch(url, path)
        except RuntimeError:
            raise RuntimeError(
                f"Could not download {instance_name}. "
                f"Browse instances at https://vrp.gdb.tools/ and place in {path.parent}"
            )

    return _parse_tsplib_vrp(path, instance_name)


def _parse_solomon(path: Path, name: str) -> VRPInstance:
    lines = [l.strip() for l in path.read_text().splitlines() if l.strip()]

    num_vehicles = capacity = None
    customers: list[Customer] = []
    depot: Optional[Customer] = None
    in_customer_section = False

    for line in lines:
        if num_vehicles is None and re.match(r"^\d+\s+\d+", line):
            parts = line.split()
            num_vehicles, capacity = int(parts[0]), float(parts[1])
            continue
        if re.match(r"^CUST", line, re.IGNORECASE):
            in_customer_section = True
            continue
        if in_customer_section:
            parts = line.split()
            if len(parts) < 7 or not parts[0].isdigit():
                continue
            cid, x, y, demand, ready, due, service = (
                int(parts[0]), float(parts[1]), float(parts[2]),
                float(parts[3]), float(parts[4]), float(parts[5]), float(parts[6])
            )
            c = Customer(cid, x, y, demand, ready, due, service)
            if depot is None:
                depot = c
            else:
                customers.append(c)

    if depot is None or num_vehicles is None:
        raise ValueError(f"Failed to parse Solomon instance at {path}")

    return VRPInstance(name=name, depot=depot, customers=customers,
                       num_vehicles=num_vehicles, vehicle_capacity=capacity)


def _parse_tsplib_vrp(path: Path, name: str) -> VRPInstance:
    lines = path.read_text().splitlines()

    capacity = num_vehicles = depot_id = None
    coords: dict[int, tuple[float, float]] = {}
    demands: dict[int, float] = {}
    section = None

    for line in lines:
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("CAPACITY"):
            capacity = float(line.split(":")[1].strip())
        elif "NO_OF_TRUCKS" in line or "VEHICLES" in line:
            m = re.search(r"\d+", line.split(":")[-1])
            if m:
                num_vehicles = int(m.group())
        elif line == "NODE_COORD_SECTION":
            section = "coords"
        elif line == "DEMAND_SECTION":
            section = "demands"
        elif line == "DEPOT_SECTION":
            section = "depot"
        elif line in ("EOF", ""):
            section = None
        elif section == "coords":
            parts = line.split()
            if len(parts) >= 3:
                coords[int(parts[0])] = (float(parts[1]), float(parts[2]))
        elif section == "demands":
            parts = line.split()
            if len(parts) >= 2:
                demands[int(parts[0])] = float(parts[1])
        elif section == "depot":
            if line.lstrip("-").isdigit() and int(line) > 0:
                depot_id = int(line)

    if depot_id is None:
        depot_id = 1
    if num_vehicles is None:
        m = re.search(r"-k(\d+)", name)
        num_vehicles = int(m.group(1)) if m else 10

    depot_coord = coords[depot_id]
    depot = Customer(depot_id, depot_coord[0], depot_coord[1], demands.get(depot_id, 0))
    customers = [
        Customer(nid, x, y, demands.get(nid, 0))
        for nid, (x, y) in sorted(coords.items())
        if nid != depot_id
    ]

    return VRPInstance(name=name, depot=depot, customers=customers,
                       num_vehicles=num_vehicles, vehicle_capacity=capacity or 0)
