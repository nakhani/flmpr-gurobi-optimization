# summarize_scalability.py

import pandas as pd


INPUT_FILE = "scalability_results.csv"

OUTPUT_FILE = "summary_results.csv"
FAIR_OUTPUT_FILE = "fair_summary_results.csv"


def summarize_results():
    df = pd.read_csv(INPUT_FILE)

    summary = make_summary(df)
    summary.to_csv(OUTPUT_FILE, index=False)

    fair_df = make_fair_dataframe(df)
    fair_summary = make_summary(fair_df)
    fair_summary.to_csv(FAIR_OUTPUT_FILE, index=False)

    print(f"Summary saved to: {OUTPUT_FILE}")
    print(f"Fair summary saved to: {FAIR_OUTPUT_FILE}")
    print(f"Number of raw rows: {len(df)}")
    print(f"Number of summary rows: {len(summary)}")
    print(f"Number of fair raw rows: {len(fair_df)}")
    print(f"Number of fair summary rows: {len(fair_summary)}")

    print("\nFair comparison objective:")
    print(
        fair_df.groupby(
            ["model", "n_customers"],
            as_index=False
        )["objective"].mean()
    )


def make_summary(df):
    summary = (
        df.groupby(
            [
                "model",
                "n_customers",
                "n_facilities",
                "n_price_levels",
                "lambda_budget",
                "fixed_cost",
            ],
            as_index=False,
        )
        .agg(
            objective_mean=("objective", "mean"),
            objective_std=("objective", "std"),
            runtime_mean=("runtime", "mean"),
            runtime_std=("runtime", "std"),
            gap_mean=("mip_gap", "mean"),
            gap_std=("mip_gap", "std"),
            gap_percent_mean=("gap_percent", "mean"),
            gap_percent_std=("gap_percent", "std"),
            opened_facilities_mean=("opened_facilities", "mean"),
            served_customers_mean=("served_customers", "mean"),
            service_rate_mean=("service_rate", "mean"),
            served_demand_mean=("served_demand", "mean"),
            revenue_mean=("total_revenue", "mean"),
            opening_cost_mean=("total_opening_cost", "mean"),
            lazy_mean=("lazy_cuts_added", "mean"),
            lazy_std=("lazy_cuts_added", "std"),
            nodes_mean=("node_count", "mean"),
            nodes_std=("node_count", "std"),
            best_bound_mean=("best_bound", "mean"),
            num_vars_mean=("num_vars", "mean"),
            num_constraints_mean=("num_constraints", "mean"),
            base_constraints_mean=("base_constraints", "mean"),
            effective_constraints_mean=("effective_constraints", "mean"),
            optimal_cases=("solved_optimal", "sum"),
            total_cases=("solved_optimal", "count"),
        )
    )

    summary["optimal_rate"] = (
            100*summary["optimal_cases"]/summary["total_cases"]
    )

    return summary


def make_fair_dataframe(df):
    common_keys = [
        "seed",
        "lambda_budget",
        "fixed_cost",
        "n_customers",
        "n_facilities",
        "n_price_levels",
    ]

    target_models = [
        "MILP-3",
        "BBC",
        "BBC-Paper",
        "BBC-NoCuts",
    ]

    candidate_df = df[df["model"].isin(target_models)].copy()

    valid_keys = (
        candidate_df.groupby(common_keys)["model"]
        .nunique()
        .reset_index()
    )

    valid_keys = valid_keys[
        valid_keys["model"] == len(target_models)
    ]

    fair_df = candidate_df.merge(
        valid_keys[common_keys],
        on=common_keys,
        how="inner",
    )

    return fair_df


if __name__ == "__main__":
    summarize_results()