# Facility Location and Pricing Problem (FLMPr)

This project implements several exact optimization approaches for the
Facility Location and Pricing Problem (FLMPr) using Python and Gurobi.

The implementation is based on the paper:

> Facility location and pricing problem:
> Discretized mill pricing model and exact solution approaches
> (European Journal of Operational Research, 2023)

---

# Problem Description

The problem combines:

- Facility location decisions
- Pricing decisions
- Customer assignment decisions

The company must decide:

1. Which facilities to open
2. Which pricing level to choose for each facility
3. How customers react to these decisions

Customers select the available option with the minimum total cost:

```math
\theta_{ijk} = p_{jk} + c_{ij}
```

where:

- \( p_{jk} \) = price at facility \( j \) with pricing level \( k \)
- \( c_{ij} \) = access/transportation cost
- \( \theta_{ijk} \) = total customer cost

Customers also have budget constraints.

---

# Implemented Models

## MILP-1

Mixed-integer linear reformulation using customer-choice inequalities.

---

## MILP-2

Alternative reformulation with pairwise customer-choice constraints.

This formulation becomes very large for medium-size instances.

---

## MILP-3

Compact reformulation reducing the number of customer-choice constraints.

---

## BBC (Branch-and-Cut)

Bilevel branch-and-cut implementation using lazy constraints in Gurobi.

The algorithm:

1. Starts from a relaxed master problem
2. Checks customer optimality inside a callback
3. Dynamically adds violated feasibility cuts

This reduces the initial formulation size and improves scalability.

---

# Project Structure

```text
.
├── data.py
├── model_milp.py
├── model_bbc.py
├── test.py
├── scalability.py
├── scalability_results.csv
├── requirements.txt
└── README.md
```

---

# Installation

## Clone repository

```bash
git clone https://github.com/nakhani/flmpr-gurobi-optimization.git
cd flmpr-gurobi-optimization
```

---

## Install dependencies

```bash
pip install -r requirements.txt
```

---

# Gurobi

This project requires:

- Python 3.10+
- Gurobi Optimizer
- Active Gurobi license

Official website:

https://www.gurobi.com/

---

# Running Small Tests

```bash
python test.py
```

This script compares:

- MILP-1
- MILP-2
- MILP-3
- BBC

on small problem instances.

---

# Scalability Analysis

```bash
python scalability.py
```

This script evaluates runtime and scalability behavior for larger instances.

Results are stored in:

```text
scalability_results.csv
```

---

# Experimental Notes

- MILP-2 grows very quickly because it contains
  pairwise customer-choice constraints.

- MILP-3 is significantly more scalable than MILP-1 and MILP-2.

- BBC dynamically adds lazy constraints and can solve larger instances
  more efficiently.

---

# Technologies

- Python
- Gurobi
- MILP
- Branch-and-Cut

---

# Author

Najmeh Khani

---

# License

This project is intended for academic and research purposes.