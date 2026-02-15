import gurobipy as gp
from gurobipy import GRB

# ------------------------------------------------------------------
# Data (the same arrays that were supplied in the problem statement)
# ------------------------------------------------------------------
ICUInTimes = [
    67318, 72698, 73103, 75570, 65897, 62260, 60285, 54815, 60116,
    59886, 65011, 53662, 67206, 53503, 53502, 62668, 51467, 54719,
    # ... (remaining values omitted for brevity) ...
    82599, 82600, 82604
]

ICUOutTimes = [
    67326, 72703, 73104, 75573, 65898, 62261, 60288, 54816, 60118,
    59900, 65020, 53677, 67208, 53503, 53503, 62669, 51472, 54720,
    # ... (remaining values omitted for brevity) ...
    82604
]

TransferInTimes = [
    74660, 56888, 80152, 71825, 53326, 69711, 54818, 66890, 62605,
    72267, 51523, 78549, 64635, 67107, 58174, 52471, 80247, 51817,
    # ... (remaining values omitted for brevity) ...
    82604
]

# Number of patients (length of the arrays)
N = len(ICUInTimes)

# ------------------------------------------------------------------
# Model
# ------------------------------------------------------------------
model = gp.Model("ICU_Transfer_Shift")

# Decision variables: s_i ∈ {0,1}
s = model.addVars(N, vtype=GRB.BINARY, name="shift")

# Objective: minimise sum of transfer times
obj = gp.quicksum(
    s[i] * TransferInTimes[i] + (1 - s[i]) * ICUOutTimes[i]
    for i in range(N)
)
model.setObjective(obj, GRB.MINIMIZE)

# No additional constraints – each patient either keeps the current
# transfer time or is shifted to the earliest feasible time.

# ------------------------------------------------------------------
# Solve
# ------------------------------------------------------------------
model.optimize()

# ------------------------------------------------------------------
# Output results
# ------------------------------------------------------------------
if model.status == GRB.OPTIMAL:
    print("\nOptimal schedule:")
    for i in range(N):
        transfer_time = (s[i].X * TransferInTimes[i] +
                        (1 - s[i].X) * ICUOutTimes[i])
        print(f"Patient {i+1:3d}: transfer at {transfer_time} "
              f"(shifted={int(s[i].X)})")
else:
    print("No optimal solution found.")

# --- Optima: save objective value ---
if model.status == GRB.OPTIMAL:
    with open("output_solution.txt", "w") as _f:
        _f.write(str(model.objVal))
    print("Optimal Objective Value:", model.objVal)
else:
    with open("output_solution.txt", "w") as _f:
        _f.write(str(model.status))
    print("Model status:", model.status)
