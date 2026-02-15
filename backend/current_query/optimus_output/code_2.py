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
TransferTimes = model.addVars(140, vtype=GRB.CONTINUOUS, name="TransferTimes", lb=0, ub=PlanningHorizonLength)

# Binary variable indicating if patient i is transferred
HasTransfer = model.addVars(140, vtype=GRB.BINARY, name="HasTransfer")

# Auxiliary variables for time-of-day calculation (hour within 24-hour cycle)
TimeOfDay = model.addVars(140, vtype=GRB.CONTINUOUS, name="TimeOfDay", lb=0, ub=24)
DayNumber = model.addVars(140, vtype=GRB.INTEGER, name="DayNumber", lb=0)

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

# Constraint 4: Link transfer time to time of day
for i in range(140):
    model.addConstr(
        TransferTimes[i] == 24 * DayNumber[i] + TimeOfDay[i],
        name=f"TimeOfDayLink_{i}"
    )

# Constraint 5: Capacity constraint - simplified hourly capacity
# We'll use a simplified approach that limits transfers in each hour
time_slots = range(int(PlanningHorizonLength))
for t in time_slots:
    transfers_in_hour = []
    for i in range(140):
        # Binary variable indicating if transfer happens in this hour
        transfer_in_hour = model.addVar(vtype=GRB.BINARY, name=f"TransferInHour_{i}_{t}")
        
        # If transfer happens in hour t, then t <= TransferTime < t+1
        model.addConstr(
            transfer_in_hour * t <= TransferTimes[i],
            name=f"LowerBound_{i}_{t}"
        )
        model.addConstr(
            TransferTimes[i] <= t + 1 - (1 - transfer_in_hour) * PlanningHorizonLength,
            name=f"UpperBound_{i}_{t}"
        )
        
        # Can only transfer in one hour
        transfers_in_hour.append(transfer_in_hour)
    
    # Capacity constraint for this hour
    model.addConstr(
        quicksum(transfers_in_hour) <= MaxTransfersPerHour,
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

bed_hours_used = quicksum(HasTransfer[i] * (TransferTimes[i] - ICUInTimes[i]) for i in range(140))

# For timing penalty, use absolute deviation from preferred time
timing_deviation = model.addVars(140, vtype=GRB.CONTINUOUS, name="TimingDeviation", lb=0)
for i in range(140):
    model.addConstr(timing_deviation[i] >= TimeOfDay[i] - PreferredTransferTime, name=f"DeviationPos_{i}")
    model.addConstr(timing_deviation[i] >= PreferredTransferTime - TimeOfDay[i], name=f"DeviationNeg_{i}")

transfer_timing_penalty = quicksum(HasTransfer[i] * timing_deviation[i] for i in range(140))

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
    total_transfers = sum(HasTransfer[i].x for i in range(140) if HasTransfer[i].x > 0.5)
    if total_transfers > 0:
        avg_transfer_time = sum(TransferTimes[i].x * HasTransfer[i].x for i in range(140)) / total_transfers
        print(f"Total transfers scheduled: {total_transfers}")
        print(f"Average transfer time: {avg_transfer_time:.2f} hours")
    else:
        print("No transfers scheduled")
    
elif model.status == GRB.INFEASIBLE:
    print("Model is infeasible")
    with open("output_solution.txt", "w") as f:
        f.write("INFEASIBLE")
else:
    print(f"Optimization status: {model.status}")
    with open("output_solution.txt", "w") as f:
        f.write(str(model.status))