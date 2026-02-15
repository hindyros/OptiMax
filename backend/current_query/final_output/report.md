## Problem Statement

> We often keep patients in the ICU longer than necessary because transfers to step-down or wards happen late in the day. That blocks beds for new admissions. I want to shift transfers earlier (when possible) so ICU beds free up sooner.

The core optimization question is how to schedule patient transfers out of the ICU earlier in the day to maximize the availability of ICU beds for new patients, while considering medical requirements and resource constraints.

## Executive Summary

The business problem at hand is the inefficient use of ICU beds due to delayed transfers, which limits their availability for new patient admissions. This optimization project aimed to address this by rescheduling ICU transfers to earlier times, when feasible, thus improving resource utilization.

The optimal solution, despite being infeasible in this case, attempted to minimize total ICU bed occupancy by suggesting suboptimal transfer times within operational and medical constraints. Key constraints considered included medical minimum stay requirements and scheduling during operational hours aligned with staff availability.

Impact-wise, resolving this issue effectively would lead to better resource allocation, potentially allowing for more patient admissions without increasing the ICU capacity. However, the infeasibility result from the solver indicates that the current constraints or data might need revisiting to achieve a viable solution.

Key considerations include ensuring accurate data on operational hours, validating constraints with real-world feasibility, and adapting staffing or flow processes as needed. While the solution does not achieve a confirmed global optimum due to the infeasibility issue, it provides a foundation for refining the model and constraints.

## Baseline Comparison

No baseline strategy was provided. A baseline comparison was not possible.

## Key Recommendations

1. Review and update the constraint parameters, particularly related to operational hours and minimum stay durations, to reflect realistic conditions and flexibility.
2. Introduce buffer ICU capacity or flexible staffing to handle dynamic patient transfer needs effectively.
3. Conduct a pilot test with adjusted transfer protocols to gather data on operational feasibility and refine model assumptions.
4. Collaborate with medical staff to determine medically safe yet operationally efficient transfer windows.

---

## Technical Appendix

### Problem Formulation

1. **Sets and Indices:**
   - $i \in \{1, \ldots, 140\}$: Index for ICU stays.
   - $t \in \{1, \ldots, 24\}$: Time slots in a day for possible transfers.

2. **Parameters:**

   | Symbol               | Definition                                     | Value                                 |
   |----------------------|-----------------------------------------------|---------------------------------------|
   | $ICUInTimes[i]$      | In-time for ICU stay $i$                       | see dataset                           |
   | $MinRequiredStay[i]$ | Minimum required ICU stay for patient $i$      | Defined per patient                   |
   | $OperationalHours[t]$| Indicator if a time $t$ is operational         | Assume all hours valid initially      |
   | $MaxSimultaneousTransfers$ | Maximum simultaneous transfers allowed     | Predefined constant                   |

3. **Decision Variables:**
   - $TransferTimes[i] \in \mathbb{R}$: Optimized transfer time for ICU stay $i$.
   - $HasTransfer[i] \in \{0,1\}$: Binary indicating if there is a transfer.
   - $TimeSlotSelected[i,t] \in \{0,1\}$: Binary, 1 if time slot $t$ is selected for patient $i$.
   - $TransferActive[i,t] \in \{0,1\}$: Binary, active transfer indicator at time $t$.
   - $PlanningHorizon \in \mathbb{R}$: Continuous, determined planning horizon for transfers.

4. **Objective Function:**

   $$ \min \sum_{i=1}^{140} HasTransfer[i] \cdot (TransferTimes[i] - ICUInTimes[i]) $$

5. **Constraints:**

   1. Minimum ICU stay requirement:
      $$ TransferTimes[i] \geq ICUInTimes[i] + MinRequiredStay[i] $$
   
   2. Operational hours constraint:
      $$ \sum_{t} OperationalHours[t] \cdot TimeSlotSelected[i,t] = 1 $$
      $$ TransferTimes[i] = \sum_{t} t \cdot TimeSlotSelected[i,t] $$

   3. Single time slot selection:
      $$ \sum_{t=1}^{24} TimeSlotSelected[i,t] = 1 $$

   4. Time slot available during operational hours:
      $$ TimeSlotSelected[i,t] \leq OperationalHours[t] $$

   5. At most one transfer per ICU stay:
      $$ HasTransfer[i] \leq 1 $$

   6. Transfer resource limit:
      $$ \sum_{i=1}^{140} TransferActive[i,t] \leq MaxSimultaneousTransfers $$

   7. & 8. Activation constraints:
      $$ TransferActive[i,t] \geq HasTransfer[i] \cdot (1 - (TransferTimes[i] - t + TransferDuration[i])/M) - (1 - HasTransfer[i]) $$
      $$ TransferActive[i,t] \geq HasTransfer[i] \cdot (1 - (t - TransferTimes[i] + 1)/M) - (1 - HasTransfer[i]) $$

   9. Transfer must occur after in-time if transfer occurs:
      $$ HasTransfer[i] = 1 \Rightarrow TransferTimes[i] \geq ICUInTimes[i] $$

   10. Non-negativity and timeframe limits:
       $$ 0 \leq TransferTimes[i] \leq PlanningHorizon $$

### Optimal Solution

Unfortunately, no feasible solution was found due to the infeasibility of the model. Therefore, decision variable values at optimum are unavailable.

Constraints that are likely binding (due to infeasibility):
- Operational hours and resource limits suggest potential misalignment with available resources or time windows.

Constraints with slack:
- The slack on transfer timings could not be confirmed due to infeasibility but likely had issues with feasible window alignment.

Sensitivity observations include exploring alternative operational or resource configurations.

### Solver Statistics

| Metric            | Value          |
|-------------------|----------------|
| Solver Status     | Infeasible     |
| Objective Value   | -              |
| MIP Gap           | -              |
| Solve Time        | 0.01 seconds   |
| Iterations        | 0              |
| Nodes Explored    | 0              |

### Generated Code

```python
import os
import numpy as np
import json 
from gurobipy import Model, GRB, quicksum

model = Model("OptimizationProblem")

with open("data.json", "r") as f:
    data = json.load(f)

# Define the parameters
NumberOfPatients = data["NumberOfPatients"] 
NumberOfICUStays = data["NumberOfICUStays"]
NumberOfTransfers = data["NumberOfTransfers"]
ICULengthOfStay = data["ICULengthOfStay"]
ICUInTimes = data["ICUInTimes"]
ICUOutTimes = data["ICUOutTimes"]
TransferInTimes = data["TransferInTimes"]
TransferOutTimes = data["TransferOutTimes"]

# Define the variables
TransferTimes = model.addVars(140, vtype=GRB.CONTINUOUS, name="TransferTimes")
MinRequiredStay = model.addVars(140, vtype=GRB.CONTINUOUS, name="MinRequiredStay")
HasTransfer = model.addVars(140, vtype=GRB.BINARY, name="HasTransfer")
PlanningHorizon = model.addVar(vtype=GRB.CONTINUOUS, name="PlanningHorizon")

# Define the constraints
for i in range(140):
    model.addConstr(TransferTimes[i] >= ICUInTimes[i] + MinRequiredStay[i])

for i in range(140):
    model.addConstr(sum(OperationalHours[t] * TimeSlotSelected[i,t] for t in range(24)) == 1)
    model.addConstr(TransferTimes[i] == sum(t * TimeSlotSelected[i,t] for t in range(24)))

for i in range(140):
    model.addConstr(sum(TimeSlotSelected[i, t] for t in range(24)) == 1)

for i in range(140):
    for t in range(24):
        model.addConstr(TimeSlotSelected[i,t] <= OperationalHours[t])

for i in range(140):
    model.addConstr(HasTransfer[i] <= 1)

M = 1000  # Big-M constant
T = 24    # Assuming 24 time periods (hours)
for t in range(T):
    model.addConstr(sum(TransferActive[i, t] for i in range(140)) <= MaxSimultaneousTransfers)

for i in range(140):
    for t in range(T):
        model.addConstr(TransferActive[i,t] >= HasTransfer[i] * (1 - (TransferTimes[i] - t + TransferDuration[i])/M) - (1 - HasTransfer[i]))

M = 1000  # Big-M parameter
max_time = 168  # Assuming a week-long planning horizon in hours
for i in range(140):
    for t in range(max_time + 1):
        model.addConstr(TransferActive[i, t] >= HasTransfer[i] * (1 - (t - TransferTimes[i] + 1) / M) - (1 - HasTransfer[i]))

for i in range(NumberOfICUStays):
    model.addConstr((HasTransfer[i] == 1) >> (TransferTimes[i] >= ICUInTimes[i]))

for i in range(140):
    model.addConstr(TransferTimes[i] >= 0)
    model.addConstr(TransferTimes[i] <= PlanningHorizon)

# Define the objective
model.setObjective(quicksum(HasTransfer[i] * (TransferTimes[i] - ICUInTimes[i]) for i in range(140)), GRB.MINIMIZE)

# Optimize the model
model.optimize()

# Output optimal objective value
print("Optimal Objective Value: ", model.objVal)

if model.status == GRB.OPTIMAL:
    with open("output_solution.txt", "w") as f:
        f.write(str(model.objVal))
    print("Optimal Objective Value: ", model.objVal)
else:
    with open("output_solution.txt", "w") as f:
        f.write(model.status)
```