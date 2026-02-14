
import os
import numpy as np
import json 
from gurobipy import Model, GRB, quicksum


model = Model("OptimizationProblem")

with open("data.json", "r") as f:
    data = json.load(f)




### Define the parameters

NumberOfItems = data["NumberOfItems"] # shape: [], definition: Number of items

ItemValue = data["ItemValue"] # shape: ['NumberOfItems'], definition: Value of each item

ItemWeight = data["ItemWeight"] # shape: ['NumberOfItems'], definition: Weight of each item

Capacity = data["Capacity"] # shape: [], definition: Maximum total weight we can carry



### Define the variables

itemTaken = model.addVars(NumberOfItems, vtype=GRB.BINARY, name="itemTaken")



### Define the constraints

model.addConstr(sum(ItemWeight[i] * itemTaken[i] for i in range(NumberOfItems)) <= Capacity)


### Define the objective

from gurobipy import quicksum

model.setObjective(quicksum(ItemValue[i] * itemTaken[i] for i in range(NumberOfItems)), GRB.MAXIMIZE)


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
