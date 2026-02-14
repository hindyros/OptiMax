import os
import numpy as np
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, value

# Define the data directly (or load from JSON if available)
NumberOfItems = 4
ItemValue = [10, 20, 15, 25]
ItemWeight = [2, 4, 3, 5]
Capacity = 8

# Create the optimization model
model = LpProblem("OptimizationProblem", LpMaximize)

# Define the variables
itemTaken = [LpVariable(f"itemTaken_{i}", cat='Binary') for i in range(NumberOfItems)]

# Define the constraints
model += lpSum(ItemWeight[i] * itemTaken[i] for i in range(NumberOfItems)) <= Capacity, "WeightCapacity"

# Define the objective
model += lpSum(ItemValue[i] * itemTaken[i] for i in range(NumberOfItems)), "TotalValue"

# Optimize the model
model.solve()

# Output optimal objective value
optimal_value = value(model.objective)
print("Optimal Objective Value: ", optimal_value)

if model.status == 1:  # Status 1 means optimal solution found
    with open("output_solution.txt", "w") as f:
        f.write(str(optimal_value))
    print("Optimal Objective Value: ", optimal_value)
else:
    with open("output_solution.txt", "w") as f:
        f.write(str(model.status))