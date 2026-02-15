import os
import numpy as np
import json 
from gurobipy import Model, GRB, quicksum

model = Model("ICU_Transfer_Optimization")

with open("data.json", "r") as f:
    data = json.load(f)

### Define the parameters
NumberOfPatients = data["NumberOfPatients"]
NumberOfICUStays = data["NumberOfICUStays"] 
NumberOfTransfers = data["NumberOfTransfers"]
ICULengthOfStay = data["ICULengthOfStay"]
ICUInTimes = data["ICUInTimes"]
ICUOutTimes = data["ICUOutTimes"]
TransferInTimes = data["TransferInTimes"]
TransferOutTimes = data["TransferOutTimes"]

# Define planning horizon and operational parameters
PlanningHorizonLength = 168  # One week in hours
MinStayHours = 24  # Minimum required stay in ICU (hours)
PreferredTransferTime = 10  # Preferred transfer time (10 AM)
MaxTransfersPerHour = 5  # Maximum simultaneous transfers per hour

### Define the variables
# Transfer time for each ICU stay (continuous variable in hours from start of planning period)
TransferTimes = model.addVars(140, vtype=GRB.CONTINUOUS, name="TransferTimes", lb=0)

# Binary variable indicating if patient i is transferred
HasTransfer = model.addVars(140, vtype=GRB.BINARY, name="HasTransfer")

# Planning horizon end time
PlanningHorizon = model.addVar(vtype=GRB.CONTINUOUS, name="PlanningHorizon", lb=0, ub=PlanningHorizonLength)

### Define the constraints

# Constraint 1: Transfer must happen after minimum required stay
for i in range(140):
    model.addConstr(
        TransferTimes[i] >= ICUInTimes[i] + MinStayHours * HasTransfer[i],
        name=f"MinStay_{i}"
    )

# Constraint 2: Transfer must happen within planning horizon
for i in range(140):
    model.addConstr(
        TransferTimes[i] <= PlanningHorizon + (1 - HasTransfer[i]) * PlanningHorizonLength,
        name=f"WithinHorizon_{i}"
    )

# Constraint 3: Transfer should happen before original ICU out time (when beneficial)
for i in range(140):
    model.addConstr(
        TransferTimes[i] <= ICUOutTimes[i] + (1 - HasTransfer[i]) * PlanningHorizonLength,
        name=f"BeforeOriginalOut_{i}"
    )

# Constraint 4: Capacity constraint - limit transfers per time period
# Discretize time into hourly slots for capacity checking
time_slots = range(int(PlanningHorizonLength))
TransferInSlot = model.addVars(140, time_slots, vtype=GRB.BINARY, name="TransferInSlot")

# Link transfer time to time slots
for i in range(140):
    model.addConstr(
        quicksum(TransferInSlot[i, t] for t in time_slots) == HasTransfer[i],
        name=f"OneSlotPerTransfer_{i}"
    )
    
    # Transfer time consistency
    model.addConstr(
        TransferTimes[i] == quicksum(t * TransferInSlot[i, t] for t in time_slots),
        name=f"TransferTimeConsistency_{i}"
    )

# Capacity constraint per time slot
for t in time_slots:
    model.addConstr(
        quicksum(TransferInSlot[i, t] for i in range(140)) <= MaxTransfersPerHour,
        name=f"Capacity_{t}"
    )

# Set planning horizon to cover all necessary transfers
model.addConstr(
    PlanningHorizon >= quicksum((ICUInTimes[i] + MinStayHours) * HasTransfer[i] for i in range(140)) / 140,
    name="AdequateHorizon"
)

### Define the objective
# Minimize total time patients spend in ICU while encouraging earlier transfers
# Primary objective: minimize bed-hours used
# Secondary objective: prefer transfers closer to preferred time

bed_hours_used = quicksum(HasTransfer[i] * TransferTimes[i] - ICUInTimes[i] * HasTransfer[i] for i in range(140))
transfer_timing_penalty = quicksum(HasTransfer[i] * ((TransferTimes[i] % 24 - PreferredTransferTime) ** 2) for i in range(140))

# Multi-objective: primarily minimize bed usage, secondarily optimize timing
model.setObjective(
    bed_hours_used + 0.01 * transfer_timing_penalty, 
    GRB.MINIMIZE
)

### Optimize the model
model.optimize()

### Output results
if model.status == GRB.OPTIMAL:
    print("Optimal Objective Value: ", model.objVal)
    with open("output_solution.txt", "w") as f:
        f.write(str(model.objVal))
        
    # Output detailed solution
    total_transfers = sum(HasTransfer[i].x for i in range(140))
    avg_transfer_time = sum(TransferTimes[i].x * HasTransfer[i].x for i in range(140)) / max(total_transfers, 1)
    
    print(f"Total transfers scheduled: {total_transfers}")
    print(f"Average transfer time: {avg_transfer_time:.2f} hours")
    
elif model.status == GRB.INFEASIBLE:
    print("Model is infeasible")
    with open("output_solution.txt", "w") as f:
        f.write("INFEASIBLE")
else:
    print(f"Optimization status: {model.status}")
    with open("output_solution.txt", "w") as f:
        f.write(str(model.status))