# test.py

from data import generate_instance
from model_milp import solve_milp1, solve_milp2, solve_milp3, print_solution


def run_small_test():

    # data = generate_instance(
    #     n_customers=10,
    #     n_facilities=4,
    #     n_price_levels=20,
    #     seed=42,
    #     fixed_cost=100,
    #     lambda_budget=1.5,
    # ) 4 * 20 = 80 options
    """
    Model too large for size-limited license and
    MILP-2 contains up to O(|I|·|Γ|·|Γ|) constraints.

    """

    data = generate_instance(
        n_customers=5,
        n_facilities=3,
        n_price_levels=10,
        seed=42,
        fixed_cost=100,
        lambda_budget=1.5,
   ) # 3 * 10 = 30 options

    models = [
        ("MILP-1", solve_milp1),
        ("MILP-3", solve_milp3),
    ]

    # MILP-2 is only added if the total number of options is small enough to avoid excessive constraints 
    if len(data.facilities) * len(data.price_levels[0]) <= 15:
        models.insert(1, ("MILP-2", solve_milp2))

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