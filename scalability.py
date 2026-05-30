# scalability.py

import csv
from pathlib import Path

from gurobipy import GurobiError

from data import generate_instance
from model_milp import solve_milp1, solve_milp3
from model_bbc import solve_bbc


RESULTS_FILE = Path("scalability_results.csv")


def run_scalability_analysis():

    instance_sizes = [
        # n_customers, n_facilities, n_price_levels
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

        data = generate_instance(
            n_customers=n_customers,
            n_facilities=n_facilities,
            n_price_levels=n_price_levels,
            seed=42,
            fixed_cost=100,
            lambda_budget=1.5,
        )

        n_options = n_facilities * n_price_levels

        models = []

        # MILP-1 is included only for smaller instances
        if n_options <= 50:
            models.append(("MILP-1", solve_milp1))

        # MILP-3 and BBC are tested for all instance sizes
        models.append(("MILP-3", solve_milp3))
        models.append(("BBC", solve_bbc))

        for model_name, solver in models:
            print(f"\nRunning {model_name}...")

            try:
                result = solver(
                    data=data,
                    time_limit=120,
                    mip_gap=1e-4,
                    verbose=False,
                )

                row = {
                    "model": model_name,
                    "n_customers": n_customers,
                    "n_facilities": n_facilities,
                    "n_price_levels": n_price_levels,
                    "n_options": n_options,
                    "status": result["status"],
                    "objective": result["objective"],
                    "runtime": result["runtime"],
                    "mip_gap": result["mip_gap"],
                    "opened_facilities": len(result["opened_facilities"]),
                    "served_demand": result["served_demand"],
                    "total_revenue": result["total_revenue"],
                    "total_opening_cost": result["total_opening_cost"],
                    "lazy_cuts_added": result.get("lazy_cuts_added", ""),
                }

                results.append(row)

                print(
                    f"{model_name}: objective={row['objective']}, "
                    f"runtime={row['runtime']:.4f}s, "
                    f"gap={row['mip_gap']}, "
                    f"opened={row['opened_facilities']}, "
                    f"lazy cuts={row['lazy_cuts_added']}"
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

    fieldnames = list(results[0].keys())

    with RESULTS_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


if __name__ == "__main__":
    run_scalability_analysis()