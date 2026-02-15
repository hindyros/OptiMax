import gurobipy as gp
from gurobipy import GRB

# Data
area = {
    'J': 250,
    'S': 350,
    'G': 800,
    'C': 500,
    'B': 400
}
profit = {
    'J': {1: 9, 2: 16, 3: 21},
    'S': {1: 10, 2: 18},
    'G': {1: 27, 2: 42, 3: 60},
    'C': {1: 17, 2: 30, 3: 36},
    'B': {0: 0, 1: 16, 2: 20}
}
# Allowed numbers of stores for each type
allowed = {
    'J': [1, 2, 3],
    'S': [1, 2],
    'G': [1, 2, 3],
    'C': [1, 2, 3],
    'B': [0, 1, 2]
}
rent_perc = 0.2
total_area = 5000

# Create model
m = gp.Model('MallLease')

# Decision variables: y[t,k] binary
y = {}
for t in allowed:
    for k in allowed[t]:
        y[t, k] = m.addVar(vtype=GRB.BINARY, name=f'y_{t}_{k}')

# Exactly one bundle per type
for t in allowed:
    m.addConstr(gp.quicksum(y[t, k] for k in allowed[t]) == 1,
                name=f'one_bundle_{t}')

# Area constraint
area_expr = gp.quicksum(area[t] * gp.quicksum(k * y[t, k] for k in allowed[t])
                      for t in allowed)
m.addConstr(area_expr <= total_area, name='area_limit')

# Objective: maximize rental income
obj = gp.quicksum(profit[t][k] * y[t, k]
                   for t in allowed for k in allowed[t])
m.setObjective(rent_perc * obj, GRB.MAXIMIZE)

# Optimize
m.optimize()

# Print results
if m.status == GRB.OPTIMAL:
    print("\nOptimal solution:")
    for t in allowed:
        for k in allowed[t]:
            if y[t, k].X > 0.5:
                print(f"{t}: {k} stores")
    total_profit = sum(profit[t][k] * y[t, k].X
                       for t in allowed for k in allowed[t])
    total_rent = rent_perc * total_profit
    print(f"\nTotal profit (before rent): {total_profit}")
    print(f"Total rental income: {total_rent:.2f}")
else:
    print("No optimal solution found.")

# --- Optima: save objective value ---
if m.status == GRB.OPTIMAL:
    with open("output_solution.txt", "w") as _f:
        _f.write(str(m.objVal))
    print("Optimal Objective Value:", m.objVal)
else:
    with open("output_solution.txt", "w") as _f:
        _f.write(str(m.status))
    print("Model status:", m.status)
