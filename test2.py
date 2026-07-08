import pandas as pd

df = pd.read_csv("scalability_results.csv")

print("Optimal instances:", df["solved_optimal"].sum())
print("Total instances:", len(df))
print("Optimality rate:", 100*df["solved_optimal"].mean(), "%")