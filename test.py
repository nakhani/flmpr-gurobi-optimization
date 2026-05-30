# test.py

from data import generate_instance
from model_milp import solve_milp1, solve_milp2, solve_milp3, print_solution
from model_bbc import solve_bbc


def run_small_test():

    data = generate_instance(
        n_customers=3,
        n_facilities=2,
        n_price_levels=5,
        seed=42,
        fixed_cost=50,
        lambda_budget=1.5,
    )

    n_options = len(data.facilities) * len(data.price_levels[0])

    models = []

    # MILP-1 is used only for small/medium instances
    if n_options <= 50:
        models.append(("MILP-1", solve_milp1))

    # MILP-2 is used only for very small instances
    if n_options <= 15:
        models.append(("MILP-2", solve_milp2))

    # MILP-3 and BBC are more practical for larger instances
    models.append(("MILP-3", solve_milp3))
    models.append(("BBC", solve_bbc))

    results = []

    for name, solver in models:
        print("\n" + "=" * 60)
        print(f"Running {name}")
        print("=" * 60)

        result = solver(
            data=data,
            time_limit=60,
            mip_gap=1e-4,
            verbose=True,
        )

        print_solution(result)
        results.append(result)

    print("\n" + "=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)

    for result in results:
        print(
            f"{result['formulation'].upper()} | "
            f"Objective: {result['objective']} | "
            f"Runtime: {result['runtime']:.4f}s | "
            f"Gap: {result['mip_gap']}"
        )


if __name__ == "__main__":
    run_small_test()