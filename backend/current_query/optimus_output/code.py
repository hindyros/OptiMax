
import os
import numpy as np
import json 
from gurobipy import Model, GRB, quicksum


model = Model("OptimizationProblem")

with open("data.json", "r") as f:
    data = json.load(f)




### Define the parameters

NumberOfPatients = data["NumberOfPatients"] # shape: [], definition: Total number of rows in admissions dataset

NumberOfICUStays = data["NumberOfICUStays"] # shape: [], definition: Total number of rows in icustays dataset

NumberOfTransfers = data["NumberOfTransfers"] # shape: [], definition: Total number of rows in transfers dataset

ICULengthOfStay = data["ICULengthOfStay"] # shape: [140], definition: Length of stay in ICU for each admission

ICUInTimes = data["ICUInTimes"] # shape: [140], definition: In-time for each ICU stay

ICUOutTimes = data["ICUOutTimes"] # shape: [140], definition: Out-time for each ICU stay

TransferInTimes = data["TransferInTimes"] # shape: [1190], definition: In-time for each transfer event

TransferOutTimes = data["TransferOutTimes"] # shape: [1190], definition: Out-time for each transfer event



### Define the variables

TransferTimes = model.addVars(140, vtype=GRB.CONTINUOUS, name="TransferTimes")

MinRequiredStay = model.addVars(140, vtype=GRB.CONTINUOUS, name="MinRequiredStay")

HasTransfer = model.addVars(140, vtype=GRB.BINARY, name="HasTransfer")

PlanningHorizon = model.addVar(vtype=GRB.CONTINUOUS, name="PlanningHorizon")



### Define the constraints

for i in range(140):
    model.addConstr(TransferTimes[i] >= ICUInTimes[i] + MinRequiredStay[i])
# Assuming we have time slots from 0 to some max time T, and OperationalHours and TimeSlotSelected are defined
# We need to determine the range of t - assuming it covers the planning horizon discretized into time slots
# For this example, I'll assume time slots go from 0 to 23 (24 hours) but this should be adjusted based on actual problem setup

for i in range(140):
    # Each patient must be transferred during exactly one operational time slot
    model.addConstr(sum(OperationalHours[t] * TimeSlotSelected[i,t] for t in range(24)) == 1)
    
    # Transfer time is defined by the selected time slot
    model.addConstr(TransferTimes[i] == sum(t * TimeSlotSelected[i,t] for t in range(24)))
for i in range(140):
    model.addConstr(sum(TimeSlotSelected[i, t] for t in range(24)) == 1)
for i in range(140):
    for t in range(24):
        model.addConstr(TimeSlotSelected[i,t] <= OperationalHours[t])
for i in range(140):
    model.addConstr(HasTransfer[i] <= 1)
# Assuming TransferActive is a 2D variable [140, T] and MaxSimultaneousTransfers is defined
# Also assuming T represents the number of time periods in the planning horizon
for t in range(T):
    model.addConstr(sum(TransferActive[i, t] for i in range(140)) <= MaxSimultaneousTransfers)
# Assuming TransferActive is defined as a binary variable with appropriate dimensions
# Assuming TransferDuration is available as a parameter
# Assuming M is a large constant and time horizon T is defined
M = 1000  # Big-M constant
T = 24    # Assuming 24 time periods (hours)

for i in range(140):
    for t in range(T):
        model.addConstr(TransferActive[i,t] >= HasTransfer[i] * (1 - (TransferTimes[i] - t + TransferDuration[i])/M) - (1 - HasTransfer[i]))
M = 1000  # Big-M parameter
max_time = 168  # Assuming a week-long planning horizon in hours

for i in range(140):  # NumberOfICUStays is 140 based on the variable shapes
    for t in range(max_time + 1):
        model.addConstr(TransferActive[i, t] >= HasTransfer[i] * (1 - (t - TransferTimes[i] + 1) / M) - (1 - HasTransfer[i]))
for i in range(NumberOfICUStays):
    model.addConstr((HasTransfer[i] == 1) >> (TransferTimes[i] >= ICUInTimes[i]))
for i in range(140):
    model.addConstr(TransferTimes[i] >= 0)
    model.addConstr(TransferTimes[i] <= PlanningHorizon)


### Define the objective

model.setObjective(quicksum(HasTransfer[i] * (TransferTimes[i] - ICUInTimes[i]) for i in range(140)), GRB.MINIMIZE)


### Optimize the model

model.optimize()



### Output optimal objective value

print("Optimal Objective Value: ", model.objVal)


if model.status == GRB.OPTIMAL:
    with open("output_solution.txt", "w") as f:
        f.write(str(model.objVal))
    print("Optimal Objective Value: ", model.objVal)
else:
    with open("output_solution.txt", "w") as f:
        f.write(model.status)
