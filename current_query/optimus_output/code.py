
import os
import numpy as np
import json 
from gurobipy import Model, GRB, quicksum


model = Model("OptimizationProblem")

with open("data.json", "r") as f:
    data = json.load(f)




### Define the parameters

ProfitA = data["ProfitA"] # shape: [], definition: Profit per unit of product A

ProfitB = data["ProfitB"] # shape: [], definition: Profit per unit of product B

LaborPerA = data["LaborPerA"] # shape: [], definition: Labor hours required per unit of A

MaterialPerA = data["MaterialPerA"] # shape: [], definition: Raw material required per unit of A

LaborPerB = data["LaborPerB"] # shape: [], definition: Labor hours required per unit of B

MaterialPerB = data["MaterialPerB"] # shape: [], definition: Raw material required per unit of B

TotalLabor = data["TotalLabor"] # shape: [], definition: Total available labor hours

TotalMaterial = data["TotalMaterial"] # shape: [], definition: Total available raw material



### Define the variables

unitsA = model.addVar(vtype=GRB.CONTINUOUS, name="unitsA")

unitsB = model.addVar(vtype=GRB.CONTINUOUS, name="unitsB")



### Define the constraints

model.addConstr(2 * unitsA + 1 * unitsB <= TotalLabor)
model.addConstr(unitsA * MaterialPerA + unitsB * MaterialPerB <= TotalMaterial)
model.addConstr(unitsA >= 0)
model.addConstr(unitsB >= 0)


### Define the objective

model.setObjective(5 * unitsA + 4 * unitsB, GRB.MAXIMIZE)


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
