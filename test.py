# test.py

from data import generate_instance
from model_milp import solve_milp3, print_solution


def main():

    # Generate a small test instance
    # data = generate_instance(
    #      n_customers=5,
    #      n_facilities=3,
    #      n_price_levels=20,
    #      seed=42,
    # )
    data = generate_instance(
        n_customers=10,
        n_facilities=4,
        n_price_levels=20,
        seed=42,
        fixed_cost=100,
        lambda_budget=1.5,
    )

    # Solve MILP-3
    result = solve_milp3(
        data=data,
        time_limit=60,
        mip_gap=1e-4,
        verbose=True,
    )

    # Print results
    print_solution(result)


if __name__ == "__main__":
    main()