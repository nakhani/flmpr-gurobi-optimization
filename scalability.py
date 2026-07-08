# scalability.py

from pathlib import Path

import pandas as pd
from gurobipy import GurobiError

from data import generate_instance
from model_milp import solve_milp1, solve_milp2, solve_milp3
from model_bbc import solve_bbc


RESULTS_FILE = Path("scalability_results.csv")


def run_scalability_analysis():

    seeds = [1, 2, 3, 4, 5]
    lambda_values = [0.5, 1.0, 1.5]
    fixed_cost_values = [50, 100, 200]

    instance_sizes = [
        (3, 2, 5),
        (5, 3, 10),
        (10, 4, 10),
        (15, 5, 10),
        (20, 6, 10),
    ]

    results = []

    for n_customers, n_facilities, n_price_levels in instance_sizes:
        print("\n" + "=" * 70)
        print(
            f"Instance: customers={n_customers}, "
            f"facilities={n_facilities}, price_levels={n_price_levels}"
        )
        print("=" * 70)

        n_options = n_facilities * n_price_levels

        models = []

        if n_options <= 15:
            models.append(("MILP-2", solve_milp2))

        if n_options <= 50:
            models.append(("MILP-1", solve_milp1))

        models.append(("MILP-3", solve_milp3))

        models.append((
            "BBC-NoCuts",
            lambda **kwargs: solve_bbc(
                **kwargs,
                use_cuts=False,
                force_open=False,
            )
        ))

        models.append((
            "BBC",
            lambda **kwargs: solve_bbc(
                **kwargs,
                use_cuts=True,
                force_open=False,
            )
        ))

        models.append((
            "BBC-Paper",
            lambda **kwargs: solve_bbc(
                **kwargs,
                use_cuts=True,
                force_open=True,
            )
        ))

        for seed in seeds:
            for lam in lambda_values:
                for fixed_cost in fixed_cost_values:

                    print(
                        f"\nSeed: {seed}, "
                        f"lambda={lam}, "
                        f"fixed_cost={fixed_cost}"
                    )

                    data = generate_instance(
                        n_customers=n_customers,
                        n_facilities=n_facilities,
                        n_price_levels=n_price_levels,
                        seed=seed,
                        fixed_cost=fixed_cost,
                        lambda_budget=lam,
                    )

                    for model_name, solver in models:
                        print(f"\nRunning {model_name}...")

                        try:
                            result = solver(
                                data=data,
                                time_limit=120,
                                mip_gap=1e-4,
                                verbose=False,
                            )

                            served_customers = result.get("served_customers", 0)
                            mip_gap = result.get("mip_gap", None)

                            row = {
                                "model": model_name,
                                "formulation": result.get("formulation", model_name),
                                "seed": seed,
                                "lambda_budget": lam,
                                "fixed_cost": fixed_cost,
                                "n_customers": n_customers,
                                "n_facilities": n_facilities,
                                "n_price_levels": n_price_levels,
                                "n_options": n_options,
                                "status": result["status"],
                                "objective": result["objective"],
                                "runtime": result["runtime"],
                                "mip_gap": mip_gap,
                                "gap_percent": (
                                    100 * mip_gap
                                    if mip_gap is not None
                                    else None
                                ),
                                "solved_optimal": (
                                    mip_gap is not None
                                    and mip_gap < 1e-4
                                ),
                                "opened_facilities": len(result["opened_facilities"]),
                                "served_customers": served_customers,
                                "service_rate": served_customers / n_customers,
                                "served_demand": result["served_demand"],
                                "total_revenue": result["total_revenue"],
                                "total_opening_cost": result["total_opening_cost"],
                                "lazy_cuts_added": result.get("lazy_cuts_added", 0),
                                "node_count": result.get("node_count", ""),
                                "best_bound": result.get("best_bound", ""),
                                "num_vars": result.get("num_vars", ""),
                                "num_constraints": result.get("num_constraints", ""),
                                "base_constraints": result.get(
                                    "base_constraints",
                                    result.get("num_constraints", ""),
                                ),
                                "effective_constraints": result.get(
                                    "effective_constraints",
                                    result.get("num_constraints", ""),
                                ),
                                "use_cuts": result.get("use_cuts", ""),
                                "force_open": result.get("force_open", ""),
                            }

                            results.append(row)

                            print(
                                f"{model_name} | "
                                f"seed={row['seed']} | "
                                f"lambda={row['lambda_budget']} | "
                                f"fixed_cost={row['fixed_cost']} | "
                                f"obj={row['objective']} | "
                                f"time={row['runtime']:.4f}s | "
                                f"gap={row['mip_gap']} | "
                                f"gap%={row['gap_percent']} | "
                                f"solved={row['solved_optimal']} | "
                                f"opened={row['opened_facilities']} | "
                                f"served={row['served_customers']} | "
                                f"service={row['service_rate']:.2%} | "
                                f"cuts={row['lazy_cuts_added']} | "
                                f"nodes={row['node_count']} | "
                                f"vars={row['num_vars']} | "
                                f"base_cons={row['base_constraints']} | "
                                f"eff_cons={row['effective_constraints']}"
                            )

                        except GurobiError as error:
                            print(f"{model_name} failed.")
                            print(f"Reason: {error}")

    save_results(results)
    print(f"\nResults saved to: {RESULTS_FILE}")


def save_results(results):
    if not results:
        print("No results to save.")
        return

    df = pd.DataFrame(results)
    df.to_csv(RESULTS_FILE, index=False)
    print(f"Number of saved rows: {len(df)}")


if __name__ == "__main__":
    run_scalability_analysis()