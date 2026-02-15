import gurobipy as gp
from gurobipy import GRB

# Data
TeamSize = 10
ShiftDuration = 8
RelayRunnerCount = 1
ZonePickerPackageRate = 60
RestockSpecialistPackageRate = 30
NonRelayWorkers = 9

# Create model
m = gp.Model("FlashSaleTeam")

# Decision variable: number of Zone Pickers among the 9 non‑relay workers
Z = m.addVar(vtype=GRB.INTEGER, name="ZonePickers", lb=0, ub=NonRelayWorkers)

# Objective: maximize total packages
m.setObjective(60 * Z + 30 * (NonRelayWorkers - Z), GRB.MAXIMIZE)

# No additional constraints are needed (the fatigue constraint is automatically satisfied)

# Optimize
m.optimize()

# Print results
if m.status == GRB.OPTIMAL:
    zone = int(Z.X)
    restock = NonRelayWorkers - zone
    total_packages = zone * ZonePickerPackageRate + restock * RestockSpecialistPackageRate
    print(f"Optimal strategy:")
    print(f"  Relay Runners: {RelayRunnerCount}")
    print(f"  Zone Pickers: {zone}")
    print(f"  Restock Specialists: {restock}")
    print(f"  Total packages produced: {total_packages}")
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
