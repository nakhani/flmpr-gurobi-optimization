# model_bbc.py (BBC formulation)


from typing import Dict, Tuple, Any, List
import time

import gurobipy as gp
from gurobipy import GRB

from data import FLMPrData


SolutionDict = Dict[str, Any]


# Solver function
def solve_bbc(
    data: FLMPrData,
    time_limit: float | None = None,
    mip_gap: float | None = None,
    verbose: bool = True,
) -> SolutionDict:

    model = gp.Model("FLMPr_BBC")
    model.Params.OutputFlag = 1 if verbose else 0
    model.Params.LazyConstraints = 1

    if time_limit is not None:
        model.Params.TimeLimit = time_limit

    if mip_gap is not None:
        model.Params.MIPGap = mip_gap

    I = data.customers
    J = data.facilities
    K = data.price_levels

    # Gamma = all facility-price options: (j, k)
    options: List[Tuple[int, int]] = [(j, k) for j in J for k in K[j]]

    # Surplus values used in BBC cuts: pi_ijk = budget_i - theta_ijk
    surplus = {
        (i, j, k): data.budget[i] - data.theta[i, j, k]
        for i in I
        for (j, k) in options
    }


    # Decision variables
    # w[j] = 1 if facility j is opened, 0 otherwise
    w = model.addVars(J, vtype=GRB.BINARY, name="w")
    # x[j,k] = 1 if facility j is opened with price level k, 0 otherwise
    x = model.addVars(options, vtype=GRB.BINARY, name="x")
    # y[i,j,k] = customer assignment variable; relaxed in BBC
    y = model.addVars(
        [(i, j, k) for i in I for (j, k) in options],
        vtype=GRB.CONTINUOUS,
        lb=0.0,
        ub=1.0,
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


    # Constraint 1:
    # If facility j is open, exactly one price level is selected.
    # If facility j is closed, no price level is selected.
    for j in J:
        model.addConstr(
            gp.quicksum(x[j, k] for k in K[j]) == w[j],
            name=f"one_price_if_open[{j}]",
        )


    # Constraint 2:
    # Each customer chooses at most one facility-price option.
    for i in I:
        model.addConstr(
            gp.quicksum(y[i, j, k] for (j, k) in options) <= 1,
            name=f"at_most_one_option[{i}]",
        )


    # Constraint 3:
    # A customer can choose option (j,k) only if option (j,k) is open.
    for i in I:
        for (j, k) in options:
            model.addConstr(
                y[i, j, k] <= x[j, k],
                name=f"choose_only_if_open[{i},{j},{k}]",
            )


    # Constraint 4:
    # If theta_ijk > budget_i, customer i cannot choose option (j,k).
    for i in I:
        for (j, k) in options:
            if data.theta[i, j, k] > data.budget[i]:
                model.addConstr(
                    y[i, j, k] == 0,
                    name=f"budget_cut[{i},{j},{k}]",
                )


    # BBC preprocessing:
    # At least one facility is opened to avoid an empty open-option set.
    model.addConstr(
        gp.quicksum(w[j] for j in J) >= 1,
        name="at_least_one_facility",
    )


    # Data needed inside the callback
    model._data = data
    model._I = I
    model._options = options
    model._x = x
    model._y = y
    model._surplus = surplus
    model._lazy_cuts_added = 0


    # Optimize with BBC callback
    start_time = time.time()
    model.optimize(_bbc_callback)
    runtime = time.time() - start_time

    return _extract_solution(
        data=data,
        model=model,
        w=w,
        x=x,
        y=y,
        runtime=runtime,
    )



# BBC callback
def _bbc_callback(model: gp.Model, where: int) -> None:

    if where != GRB.Callback.MIPSOL:
        return

    data = model._data
    I = model._I
    options = model._options
    x = model._x
    y = model._y
    surplus = model._surplus

    x_val = model.cbGetSolution(x)
    y_val = model.cbGetSolution(y)

    # Find currently opened facility-price options
    open_options = [
        (j, k)
        for (j, k) in options
        if x_val[j, k] > 0.5
    ]

    if not open_options:
        return

    tolerance = 1e-6

    for i in I:
        best_option = _find_best_customer_option(data, i, open_options)

        # If no open option is affordable, the customer chooses nothing.
        if best_option is None:
            best_surplus = 0.0
            rhs_expr = 0.0
        else:
            best_j, best_k = best_option
            best_surplus = surplus[i, best_j, best_k]
            rhs_expr = best_surplus * x[best_j, best_k]

        current_surplus = sum(
            surplus[i, j, k] * y_val[i, j, k]
            for (j, k) in options
        )

        # Add lazy cut if the current customer choice is not bilevel feasible.
        if current_surplus + tolerance < best_surplus:
            lhs_expr = gp.quicksum(
                surplus[i, j, k] * y[i, j, k]
                for (j, k) in options
            )

            model.cbLazy(lhs_expr >= rhs_expr)
            model._lazy_cuts_added += 1



# Customer choice in lower-level problem
def _find_best_customer_option(
    data: FLMPrData,
    customer: int,
    open_options: List[Tuple[int, int]],
) -> Tuple[int, int] | None:

    affordable_options = [
        (j, k)
        for (j, k) in open_options
        if data.theta[customer, j, k] <= data.budget[customer]
    ]

    if not affordable_options:
        return None

    return min(
        affordable_options,
        key=lambda option: (
            data.theta[customer, option[0], option[1]],
            -data.price[option[0], option[1]],
        ),
    )



# Extract solution
def _extract_solution(
    data: FLMPrData,
    model: gp.Model,
    w,
    x,
    y,
    runtime: float,
) -> SolutionDict:

    result: SolutionDict = {
        "formulation": "bbc",
        "status": model.Status,
        "runtime": runtime,
        "objective": None,
        "mip_gap": None,
        "lazy_cuts_added": getattr(model, "_lazy_cuts_added", 0),
        "opened_facilities": [],
        "selected_prices": {},
        "assignments": {},
        "served_demand": 0.0,
        "total_revenue": 0.0,
        "total_opening_cost": 0.0,
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
                if y[i, j, k].X > 1e-5:
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
    print(f"Lazy cuts added: {result['lazy_cuts_added']}")

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
