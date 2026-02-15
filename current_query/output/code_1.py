import os
import numpy as np
import json 
from gurobipy import Model, GRB, quicksum


model = Model("OptimizationProblem")

with open("data.json", "r") as f:
    data = json.load(f)

### Define the parameters

NumberOfProducts = data["NumberOfProducts"]  # shape: [], definition: Number of products
NumberOfStores = data["NumberOfStores"]  # shape: [], definition: Number of stores
StockLevels = data["StockLevels"]  # shape: [31], definition: Current stock for each product at each store
SupplierLeadTime = data["SupplierLeadTime"]  # shape: [31], definition: Lead time for suppliers in days
StockoutFrequency = data["StockoutFrequency"]  # shape: [31], definition: Frequency of stockouts for each product
ReorderPoint = data["ReorderPoint"]  # shape: [31], definition: Reorder point for each product
WarehouseCapacity = data["WarehouseCapacity"]  # shape: [31], definition: Capacity of each warehouse
OrderFulfillmentTime = data["OrderFulfillmentTime"]  # shape: [31], definition: Order fulfillment time in days

### Define the variables

stockAllocated = model.addVars(NumberOfProducts, NumberOfStores, vtype=GRB.CONTINUOUS, name="stockAllocated")
acceptableStockoutFrequency = model.addVars(NumberOfProducts, vtype=GRB.INTEGER, name="acceptableStockoutFrequency")
c = model.addVars(NumberOfProducts, vtype=GRB.CONTINUOUS, name="c")
B = model.addVar(vtype=GRB.CONTINUOUS, name="B")
demand = model.addVars(NumberOfProducts, NumberOfStores, vtype=GRB.CONTINUOUS, name="demand")

### Define the constraints

for i in range(NumberOfProducts):
    for j in range(NumberOfStores):
        model.addConstr(stockAllocated[i, j] >= 0)
for p in range(NumberOfProducts):
    model.addConstr(sum(stockAllocated[p, s] for s in range(NumberOfStores)) <= WarehouseCapacity[p])
for p in range(NumberOfProducts):
    for s in range(NumberOfStores):
        model.addConstr(StockLevels[p][s] + stockAllocated[p, s] >= ReorderPoint[p])
for p in range(NumberOfProducts):
    for s in range(NumberOfStores):
        model.addConstr(
            sum(stockAllocated[p, s] for t in range(SupplierLeadTime[p])) <= 
            StockLevels[p][s] + ReorderPoint[p]
        )
model.addConstr(sum(stockAllocated[p, s] for p in range(NumberOfProducts) for s in range(NumberOfStores)) <= sum(WarehouseCapacity[w] for w in range(3)))
for i in range(NumberOfProducts):
    model.addConstr(StockoutFrequency[i] <= acceptableStockoutFrequency[i])
model.addConstr(sum(c[i] * stockAllocated[i, j] for i in range(NumberOfProducts) for j in range(NumberOfStores)) <= B)
for i in range(NumberOfProducts):
    model.addConstr(sum(demand[i, j] for j in range(NumberOfStores)) - c[i] * sum(stockAllocated[i, j] for j in range(NumberOfStores)) >= 0)
for i in range(NumberOfProducts):
    for j in range(NumberOfStores):
        model.addConstr(stockAllocated[i, j] >= demand[i, j] * OrderFulfillmentTime[i])

### Define the objective

model.setObjective(
    quicksum(StockoutFrequency[p] + c[p] * quicksum(stockAllocated[p, s] for s in range(NumberOfStores))
              for p in range(NumberOfProducts)), 
    GRB.MINIMIZE
)

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
        f.write(str(model.status))