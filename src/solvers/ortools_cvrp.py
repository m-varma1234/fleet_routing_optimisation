"""
CVRP solver using Google OR-Tools (routing solver).

OR-Tools uses constraint programming + guided local search to find
optimal or near-optimal solutions far faster than pure MILP for large instances.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from src.utils.data_loader import VRPInstance


@dataclass
class Route:
    vehicle_id: int
    stops: list[int] = field(default_factory=list)  # 0-based customer indices
    load: float = 0.0
    distance: float = 0.0


@dataclass
class VRPSolution:
    instance: VRPInstance
    routes: list[Route]

    @property
    def total_distance(self) -> float:
        return sum(r.distance for r in self.routes)

    @property
    def num_routes_used(self) -> int:
        return sum(1 for r in self.routes if r.stops)

    def is_feasible(self) -> bool:
        served = [stop for r in self.routes for stop in r.stops]
        all_served = sorted(served) == list(range(len(self.instance.customers)))
        capacity_ok = all(r.load <= self.instance.vehicle_capacity for r in self.routes)
        return all_served and capacity_ok

    def summary(self) -> str:
        lines = [
            f"Instance : {self.instance.name}",
            f"Feasible : {self.is_feasible()}",
            f"Vehicles : {self.num_routes_used}/{self.instance.num_vehicles}",
            f"Total dist: {self.total_distance:.2f}",
        ]
        for r in self.routes:
            if r.stops:
                stop_ids = [self.instance.customers[s].id for s in r.stops]
                lines.append(f"  V{r.vehicle_id}: depot -> {stop_ids} -> depot  "
                              f"(load={r.load:.0f}, dist={r.distance:.2f})")
        return "\n".join(lines)


def solve(
    instance: VRPInstance,
    time_limit_seconds: int = 30,
    first_solution_strategy: str = "PATH_CHEAPEST_ARC",
) -> VRPSolution:
    """
    Solve a CVRP instance with OR-Tools routing solver.

    Args:
        instance: VRPInstance to solve.
        time_limit_seconds: Wall-clock limit for the search.
        first_solution_strategy: OR-Tools strategy name for the initial solution.
            Options: PATH_CHEAPEST_ARC, SAVINGS, CHRISTOFIDES, ...

    Returns:
        VRPSolution with the best routes found within the time limit.
    """
    N = instance.num_customers
    num_nodes = N + 1  # index 0 = depot

    dist_matrix = instance.distance_matrix
    # OR-Tools works with integers; scale to avoid precision loss
    scale = 1000
    int_dist = (dist_matrix * scale).astype(int).tolist()

    manager = pywrapcp.RoutingIndexManager(num_nodes, instance.num_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        return int_dist[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    transit_cb_idx = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_cb_idx)

    def demand_callback(from_index):
        node = manager.IndexToNode(from_index)
        if node == 0:
            return 0
        return int(instance.customers[node - 1].demand)

    demand_cb_idx = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_cb_idx,
        0,
        [int(instance.vehicle_capacity)] * instance.num_vehicles,
        True,
        "Capacity",
    )

    strategy = getattr(routing_enums_pb2.FirstSolutionStrategy, first_solution_strategy)
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = strategy
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = time_limit_seconds

    assignment = routing.SolveWithParameters(params)

    if assignment is None:
        raise RuntimeError("OR-Tools found no solution within the time limit.")

    return _extract_solution(instance, routing, manager, assignment)


def _extract_solution(
    instance: VRPInstance,
    routing: pywrapcp.RoutingModel,
    manager: pywrapcp.RoutingIndexManager,
    assignment,
) -> VRPSolution:
    routes = []
    dist_matrix = instance.distance_matrix

    for vehicle_id in range(instance.num_vehicles):
        index = routing.Start(vehicle_id)
        stops, load, dist = [], 0.0, 0.0
        prev_node = 0

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            if node != 0:
                stops.append(node - 1)  # 0-based customer index
                load += instance.customers[node - 1].demand
                dist += dist_matrix[prev_node, node]
                prev_node = node
            index = assignment.Value(routing.NextVar(index))

        dist += dist_matrix[prev_node, 0]  # return to depot
        routes.append(Route(vehicle_id=vehicle_id, stops=stops, load=load, distance=dist))

    return VRPSolution(instance=instance, routes=routes)
