
import os
import numpy as np
import json 
from gurobipy import Model, GRB, quicksum


model = Model("OptimizationProblem")

with open("data.json", "r") as f:
    data = json.load(f)




### Define the parameters

TeamSize = data["TeamSize"] # shape: [], definition: Total number of workers in the team

ShiftDuration = data["ShiftDuration"] # shape: [], definition: Duration of the flash sale shift in hours

MaxAverageTravelFatigue = data["MaxAverageTravelFatigue"] # shape: [], definition: Maximum allowed average travel fatigue in miles per day

RelayRunnerCount = data["RelayRunnerCount"] # shape: [], definition: Mandatory number of Relay Runners

RelayRunnerSpeed = data["RelayRunnerSpeed"] # shape: [], definition: Speed of Relay Runner in miles per hour

RelayRunnerPackageRate = data["RelayRunnerPackageRate"] # shape: [], definition: Package processing rate for Relay Runner in packages per hour

ZonePickerSpeed = data["ZonePickerSpeed"] # shape: [], definition: Speed of Zone Picker in miles per hour

ZonePickerPackageRate = data["ZonePickerPackageRate"] # shape: [], definition: Package processing rate for Zone Picker in packages per hour

RestockSpecialistSpeed = data["RestockSpecialistSpeed"] # shape: [], definition: Speed of Restock Specialist in miles per hour

RestockSpecialistPackageRate = data["RestockSpecialistPackageRate"] # shape: [], definition: Package processing rate for Restock Specialist in packages per hour

NonRelayWorkers = data["NonRelayWorkers"] # shape: [], definition: Number of workers to be assigned as Zone Pickers or Restock Specialists



### Define the variables

NumZonePickers = model.addVar(vtype=GRB.INTEGER, name="NumZonePickers")

NumRestockSpecialists = model.addVar(vtype=GRB.INTEGER, name="NumRestockSpecialists")



### Define the constraints

model.addConstr(RelayRunners == RelayRunnerCount)
model.addConstr(RelayRunnerCount + NumZonePickers + NumRestockSpecialists == TeamSize)
model.addConstr(NumZonePickers + NumRestockSpecialists == NonRelayWorkers)
model.addConstr(NumZonePickers + NumRestockSpecialists == NonRelayWorkers)
model.addConstr(RelayRunnerCount * RelayRunnerSpeed * ShiftDuration + 
                NumZonePickers * ZonePickerSpeed * ShiftDuration + 
                NumRestockSpecialists * RestockSpecialistSpeed * ShiftDuration <= 
                MaxAverageTravelFatigue * TeamSize)
model.addConstr(NumZonePickers >= 0)
model.addConstr(NumRestockSpecialists >= 0)


### Define the objective

model.setObjective((RelayRunnerCount * RelayRunnerPackageRate + NumZonePickers * ZonePickerPackageRate + NumRestockSpecialists * RestockSpecialistPackageRate) * ShiftDuration, GRB.MAXIMIZE)


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
