# model_milp.py (MILP1, MILP2, MILP3 formulations)

from typing import Dict, Tuple, Any, List, Literal
import time

import gurobipy as gp
from gurobipy import GRB

from data import FLMPrData


SolutionDict = Dict[str, Any]
FormulationName = Literal["milp1", "milp2", "milp3"]


# Solver functions
def solve_milp1(
    data: FLMPrData,
    time_limit: float | None = None,
    mip_gap: float | None = None,
    verbose: bool = True,
) -> SolutionDict:
    return _solve_milp(
        data=data,
        formulation="milp1",
        time_limit=time_limit,
        mip_gap=mip_gap,
        verbose=verbose,
    )


def solve_milp2(
    data: FLMPrData,
    time_limit: float | None = None,
    mip_gap: float | None = None,
    verbose: bool = True,
) -> SolutionDict:
    return _solve_milp(
        data=data,
        formulation="milp2",
        time_limit=time_limit,
        mip_gap=mip_gap,
        verbose=verbose,
    )


def solve_milp3(
    data: FLMPrData,
    time_limit: float | None = None,
    mip_gap: float | None = None,
    verbose: bool = True,
) -> SolutionDict:
    return _solve_milp(
        data=data,
        formulation="milp3",
        time_limit=time_limit,
        mip_gap=mip_gap,
        verbose=verbose,
    )


# Main MILP Solver
def _solve_milp(
    data: FLMPrData,
    formulation: FormulationName,
    time_limit: float | None = None,
    mip_gap: float | None = None,
    verbose: bool = True,
) -> SolutionDict:

    if formulation not in {"milp1", "milp2", "milp3"}:
        raise ValueError(f"Unknown formulation: {formulation}")

    model = gp.Model(f"FLMPr_{formulation.upper()}")
    model.Params.OutputFlag = 1 if verbose else 0

    if time_limit is not None:
        model.Params.TimeLimit = time_limit

    if mip_gap is not None:
        model.Params.MIPGap = mip_gap

    I = data.customers
    J = data.facilities
    K = data.price_levels

    # Gamma = all facility-price options: (j, k)
    options: List[Tuple[int, int]] = [(j, k) for j in J for k in K[j]]

    # Decision variables
    w = model.addVars(J, vtype=GRB.BINARY, name="w")
    x = model.addVars(options, vtype=GRB.BINARY, name="x")
    y = model.addVars(
        [(i, j, k) for i in I for (j, k) in options],
        vtype=GRB.BINARY,
        name="y",
    )

    # Objective: revenue - opening cost
    revenue = gp.quicksum(
        data.demand[i] * data.price[j, k] * y[i, j, k]
        for i in I
        for (j, k) in options
    )

    opening_cost = gp.quicksum(
        data.fixed_cost[j] * w[j]
        for j in J
    )

    model.setObjective(revenue - opening_cost, GRB.MAXIMIZE)

    # Constraint 1: exactly one price if facility is open
    for j in J:
        model.addConstr(
            gp.quicksum(x[j, k] for k in K[j]) == w[j],
            name=f"one_price_if_open[{j}]",
        )

    # Constraint 2: each customer chooses at most one option
    for i in I:
        model.addConstr(
            gp.quicksum(y[i, j, k] for (j, k) in options) <= 1,
            name=f"at_most_one_option[{i}]",
        )

    # Constraint 3: customer can choose only open option
    for i in I:
        for (j, k) in options:
            model.addConstr(
                y[i, j, k] <= x[j, k],
                name=f"choose_only_if_open[{i},{j},{k}]",
            )

    # Constraint 4: budget feasibility
    for i in I:
        for (j, k) in options:
            if data.theta[i, j, k] > data.budget[i]:
                model.addConstr(
                    y[i, j, k] == 0,
                    name=f"budget_cut[{i},{j},{k}]",
                )

    # Formulation-specific CAC constraints
    if formulation == "milp1":
        _add_milp1_constraints(model, data, I, options, x, y)
    elif formulation == "milp2":
        _add_milp2_constraints(model, data, I, options, x, y)
    elif formulation == "milp3":
        _add_milp3_constraints(model, data, I, options, x, y)

    # Optimize
    start_time = time.time()
    model.optimize()
    runtime = time.time() - start_time

    return _extract_solution(
        data=data,
        model=model,
        formulation=formulation,
        w=w,
        x=x,
        y=y,
        runtime=runtime,
    )


# MILP-1 constraints
def _add_milp1_constraints(model, data: FLMPrData, I, options, x, y) -> None:
    for i in I:
        for (j, k) in options:
            model.addConstr(
                gp.quicksum(
                    data.theta[i, m, n] * y[i, m, n]
                    for (m, n) in options
                )
                <= data.theta[i, j, k] * x[j, k]
                + data.budget[i] * (1 - x[j, k]),
                name=f"milp1_cac[{i},{j},{k}]",
            )


# MILP-2 constraints
def _add_milp2_constraints(model, data: FLMPrData, I, options, x, y) -> None:
    for i in I:
        for (m, n) in options:
            for (j, k) in options:
                if data.theta[i, m, n] > data.theta[i, j, k]:
                    model.addConstr(
                        y[i, m, n] <= 1 - x[j, k],
                        name=f"milp2_cac[{i},{m},{n},{j},{k}]",
                    )


# MILP-3 constraints
def _add_milp3_constraints(model, data: FLMPrData, I, options, x, y) -> None:
    for i in I:
        for (j, k) in options:
            more_expensive_options = [
                (m, n)
                for (m, n) in options
                if data.theta[i, m, n] > data.theta[i, j, k]
            ]

            if more_expensive_options:
                model.addConstr(
                    gp.quicksum(
                        y[i, m, n]
                        for (m, n) in more_expensive_options
                    )
                    <= 1 - x[j, k],
                    name=f"milp3_cac[{i},{j},{k}]",
                )


# Extract solution
def _extract_solution(
    data: FLMPrData,
    model: gp.Model,
    formulation: str,
    w,
    x,
    y,
    runtime: float,
) -> SolutionDict:

    result: SolutionDict = {
        "formulation": formulation,
        "status": model.Status,
        "runtime": runtime,
        "objective": None,
        "mip_gap": None,
        "opened_facilities": [],
        "selected_prices": {},
        "assignments": {},
        "served_demand": 0.0,
        "served_customers": 0,
        "total_revenue": 0.0,
        "total_opening_cost": 0.0,
        "node_count": model.NodeCount,
        "best_bound": model.ObjBound,
        "num_vars": model.NumVars,
        "num_constraints": model.NumConstrs,
        "base_constraints": model.NumConstrs,
        "effective_constraints": model.NumConstrs,
    }

    if model.SolCount == 0:
        return result

    result["objective"] = model.ObjVal

    try:
        result["mip_gap"] = model.MIPGap
    except gp.GurobiError:
        result["mip_gap"] = None

    for j in data.facilities:
        if w[j].X > 0.5:
            result["opened_facilities"].append(j)
            result["total_opening_cost"] += data.fixed_cost[j]

    for j in data.facilities:
        for k in data.price_levels[j]:
            if x[j, k].X > 0.5:
                result["selected_prices"][j] = {
                    "price_level": k,
                    "price": data.price[j, k],
                }

    for i in data.customers:
        for j in data.facilities:
            for k in data.price_levels[j]:
                if y[i, j, k].X > 0.5:
                    revenue = data.demand[i] * data.price[j, k]
                    result["assignments"][i] = {
                        "facility": j,
                        "price_level": k,
                        "price": data.price[j, k],
                        "access_cost": data.access_cost[i, j],
                        "theta": data.theta[i, j, k],
                        "budget": data.budget[i],
                        "demand": data.demand[i],
                        "revenue": revenue,
                    }
                    result["served_demand"] += data.demand[i]
                    result["total_revenue"] += revenue

    result["served_customers"] = sum(
        any(
            y[i, j, k].X > 0.5
            for j in data.facilities
            for k in data.price_levels[j]
        )
        for i in data.customers
    )

    return result


# Print solution
def print_solution(result: SolutionDict) -> None:
    """Print a readable solution summary."""

    print("\n========== SOLUTION SUMMARY ==========")
    print(f"Formulation: {result['formulation']}")
    print(f"Status: {result['status']}")
    print(f"Objective: {result['objective']}")
    print(f"Runtime: {result['runtime']:.4f} seconds")
    print(f"MIP gap: {result['mip_gap']}")
    print(f"Node count: {result['node_count']}")
    print(f"Best bound: {result['best_bound']}")
    print(f"Variables: {result['num_vars']}")
    print(f"Constraints: {result['num_constraints']}")

    print("\nOpened facilities:")
    print(result["opened_facilities"])

    print("\nSelected prices:")
    if not result["selected_prices"]:
        print("  No facility opened.")
    else:
        for j, info in result["selected_prices"].items():
            print(
                f"  Facility {j}: level {info['price_level']} "
                f"with price {info['price']:.2f}"
            )

    print("\nAssignments:")
    if not result["assignments"]:
        print("  No customers served.")
    else:
        for i, info in result["assignments"].items():
            print(
                f"  Customer {i} -> Facility {info['facility']} "
                f"(level {info['price_level']}, price={info['price']:.2f}, "
                f"access={info['access_cost']:.2f}, theta={info['theta']:.2f}, "
                f"budget={info['budget']:.2f}, demand={info['demand']:.2f})"
            )

    print("\nFinancial summary:")
    print(f"  Total revenue: {result['total_revenue']:.2f}")
    print(f"  Total opening cost: {result['total_opening_cost']:.2f}")
    print(f"  Served demand: {result['served_demand']:.2f}")
    print(f"  Served customers: {result['served_customers']}")