import os
import numpy as np
import json 
from gurobipy import Model, GRB, quicksum


model = Model("OptimizationProblem")

with open("data.json", "r") as f:
    data = json.load(f)


### Define the parameters

TotalSpace = data["TotalSpace"]
RentPercentage = data["RentPercentage"]
AreaJewelry = data["AreaJewelry"]
AreaShoesHats = data["AreaShoesHats"]
AreaGeneralMerch = data["AreaGeneralMerch"]
AreaBookstore = data["AreaBookstore"]
AreaCatering = data["AreaCatering"]
MinJewelry = data["MinJewelry"]
MinShoesHats = data["MinShoesHats"]
MinGeneralMerch = data["MinGeneralMerch"]
MinBookstore = data["MinBookstore"]
MinCatering = data["MinCatering"]
MaxJewelry = data["MaxJewelry"]
MaxShoesHats = data["MaxShoesHats"]
MaxGeneralMerch = data["MaxGeneralMerch"]
MaxBookstore = data["MaxBookstore"]
MaxCatering = data["MaxCatering"]
ProfitJewelry1 = data["ProfitJewelry1"]
ProfitJewelry2 = data["ProfitJewelry2"]
ProfitJewelry3 = data["ProfitJewelry3"]
ProfitShoesHats1 = data["ProfitShoesHats1"]
ProfitShoesHats2 = data["ProfitShoesHats2"]
ProfitGeneralMerch1 = data["ProfitGeneralMerch1"]
ProfitGeneralMerch2 = data["ProfitGeneralMerch2"]
ProfitGeneralMerch3 = data["ProfitGeneralMerch3"]
ProfitBookstore1 = data["ProfitBookstore1"]
ProfitBookstore2 = data["ProfitBookstore2"]
ProfitCatering1 = data["ProfitCatering1"]
ProfitCatering2 = data["ProfitCatering2"]
ProfitCatering3 = data["ProfitCatering3"]


### Define the variables

# Binary variables for each store type and count combination
jewelry_vars = {}
shoeshats_vars = {}
generalmerch_vars = {}
bookstore_vars = {}
catering_vars = {}

for i in range(MinJewelry, MaxJewelry + 1):
    jewelry_vars[i] = model.addVar(vtype=GRB.BINARY, name=f"jewelry_{i}")

for i in range(MinShoesHats, MaxShoesHats + 1):
    shoeshats_vars[i] = model.addVar(vtype=GRB.BINARY, name=f"shoeshats_{i}")

for i in range(MinGeneralMerch, MaxGeneralMerch + 1):
    generalmerch_vars[i] = model.addVar(vtype=GRB.BINARY, name=f"generalmerch_{i}")

for i in range(MinBookstore, MaxBookstore + 1):
    bookstore_vars[i] = model.addVar(vtype=GRB.BINARY, name=f"bookstore_{i}")

for i in range(MinCatering, MaxCatering + 1):
    catering_vars[i] = model.addVar(vtype=GRB.BINARY, name=f"catering_{i}")


### Define the constraints

# Exactly one option must be chosen for each store type
model.addConstr(quicksum(jewelry_vars[i] for i in range(MinJewelry, MaxJewelry + 1)) == 1)
model.addConstr(quicksum(shoeshats_vars[i] for i in range(MinShoesHats, MaxShoesHats + 1)) == 1)
model.addConstr(quicksum(generalmerch_vars[i] for i in range(MinGeneralMerch, MaxGeneralMerch + 1)) == 1)
model.addConstr(quicksum(bookstore_vars[i] for i in range(MinBookstore, MaxBookstore + 1)) == 1)
model.addConstr(quicksum(catering_vars[i] for i in range(MinCatering, MaxCatering + 1)) == 1)

# Space constraint
total_area = (
    quicksum(i * AreaJewelry * jewelry_vars[i] for i in range(MinJewelry, MaxJewelry + 1)) +
    quicksum(i * AreaShoesHats * shoeshats_vars[i] for i in range(MinShoesHats, MaxShoesHats + 1)) +
    quicksum(i * AreaGeneralMerch * generalmerch_vars[i] for i in range(MinGeneralMerch, MaxGeneralMerch + 1)) +
    quicksum(i * AreaBookstore * bookstore_vars[i] for i in range(MinBookstore, MaxBookstore + 1)) +
    quicksum(i * AreaCatering * catering_vars[i] for i in range(MinCatering, MaxCatering + 1))
)
model.addConstr(total_area <= TotalSpace)


### Define the objective

# Define profit dictionaries with 0 profit for 0 stores
jewelry_profits = {0: 0, 1: ProfitJewelry1, 2: ProfitJewelry2, 3: ProfitJewelry3}
shoeshats_profits = {0: 0, 1: ProfitShoesHats1, 2: ProfitShoesHats2}
generalmerch_profits = {0: 0, 1: ProfitGeneralMerch1, 2: ProfitGeneralMerch2, 3: ProfitGeneralMerch3}
bookstore_profits = {0: 0, 1: ProfitBookstore1, 2: ProfitBookstore2}
catering_profits = {0: 0, 1: ProfitCatering1, 2: ProfitCatering2, 3: ProfitCatering3}

total_profit = (
    quicksum(i * jewelry_profits[i] * jewelry_vars[i] for i in range(MinJewelry, MaxJewelry + 1)) +
    quicksum(i * shoeshats_profits[i] * shoeshats_vars[i] for i in range(MinShoesHats, MaxShoesHats + 1)) +
    quicksum(i * generalmerch_profits[i] * generalmerch_vars[i] for i in range(MinGeneralMerch, MaxGeneralMerch + 1)) +
    quicksum(i * bookstore_profits[i] * bookstore_vars[i] for i in range(MinBookstore, MaxBookstore + 1)) +
    quicksum(i * catering_profits[i] * catering_vars[i] for i in range(MinCatering, MaxCatering + 1))
)

model.setObjective(RentPercentage * total_profit, GRB.MAXIMIZE)


### Optimize the model

model.optimize()


### Output optimal objective value

if model.status == GRB.OPTIMAL:
    print("Optimal Objective Value: ", model.objVal)
    with open("output_solution.txt", "w") as f:
        f.write(str(model.objVal))
else:
    print("Optimization failed with status: ", model.status)
    with open("output_solution.txt", "w") as f:
        f.write(str(model.status))