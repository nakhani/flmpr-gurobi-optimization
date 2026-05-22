# data.py

from dataclasses import dataclass
from typing import Dict, List, Tuple
import math
import random


Customer = int
Facility = int
PriceLevel = int
Option = Tuple[Facility, PriceLevel]


@dataclass
class FLMPrData:
    customers: List[Customer]
    facilities: List[Facility]
    price_levels: Dict[Facility, List[PriceLevel]]

    demand: Dict[Customer, float]          # d_i
    budget: Dict[Customer, float]          # b_i
    fixed_cost: Dict[Facility, float]      # f_j
    price: Dict[Option, float]             # p_jk

    access_cost: Dict[Tuple[Customer, Facility], float]  # c_ij
    theta: Dict[Tuple[Customer, Facility, PriceLevel], float]  # theta_ijk


def generate_instance(
    n_customers: int = 20,
    n_facilities: int = 10,
    n_price_levels: int = 20,
    seed: int = 1,
    fixed_cost: float = 1000.0,
    lambda_budget: float = 0.7,
    max_price: float = 20.0,
) -> FLMPrData:
    """
    Generate a random FLMPr instance.

    This follows the paper's RND dataset idea:
    - customer/facility locations are random in [0,100]^2
    - access cost = Euclidean distance / 2
    - demand is random in [0,100]
    - budget b_i = average access cost of customer i * lambda
    - prices are discrete levels up to max_price
    """

    random.seed(seed)

    customers = list(range(n_customers))
    facilities = list(range(n_facilities))

    customer_pos = {
        i: (random.uniform(0, 100), random.uniform(0, 100))
        for i in customers
    }

    facility_pos = {
        j: (random.uniform(0, 100), random.uniform(0, 100))
        for j in facilities
    }

    price_levels = {
        j: list(range(n_price_levels))
        for j in facilities
    }

    price = {}
    for j in facilities:
        for k in price_levels[j]:
            price[j, k] = max_price * (k + 1) / n_price_levels

    demand = {
        i: random.uniform(0, 100)
        for i in customers
    }

    fixed_cost_dict = {
        j: fixed_cost
        for j in facilities
    }

    access_cost = {}
    for i in customers:
        xi, yi = customer_pos[i]
        for j in facilities:
            xj, yj = facility_pos[j]
            distance = math.sqrt((xi - xj) ** 2 + (yi - yj) ** 2)
            access_cost[i, j] = distance / 2.0

    budget = {}
    for i in customers:
        avg_access = sum(access_cost[i, j] for j in facilities) / n_facilities
        budget[i] = avg_access * lambda_budget

    theta = {}
    for i in customers:
        for j in facilities:
            for k in price_levels[j]:
                theta[i, j, k] = access_cost[i, j] + price[j, k]

    return FLMPrData(
        customers=customers,
        facilities=facilities,
        price_levels=price_levels,
        demand=demand,
        budget=budget,
        fixed_cost=fixed_cost_dict,
        price=price,
        access_cost=access_cost,
        theta=theta,
    )


if __name__ == "__main__":
    data = generate_instance(
        n_customers=5,
        n_facilities=3,
        n_price_levels=4,
        seed=42,
    )

    print("Customers:", data.customers)
    print("Facilities:", data.facilities)
    print("Demand:", data.demand)
    print("Budget:", data.budget)
    print("Prices:", data.price)