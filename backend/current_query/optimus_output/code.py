
import os
import numpy as np
import json 
from gurobipy import Model, GRB, quicksum


model = Model("OptimizationProblem")

with open("data.json", "r") as f:
    data = json.load(f)




### Define the parameters

TotalSpace = data["TotalSpace"] # shape: [], definition: Total available space for lease in the mall

RentPercentage = data["RentPercentage"] # shape: [], definition: Percentage of annual profit paid as rent

AreaJewelry = data["AreaJewelry"] # shape: [], definition: Area occupied by one jewelry shop

AreaShoesHats = data["AreaShoesHats"] # shape: [], definition: Area occupied by one shoes & hats shop

AreaGeneralMerch = data["AreaGeneralMerch"] # shape: [], definition: Area occupied by one general merchandise shop

AreaBookstore = data["AreaBookstore"] # shape: [], definition: Area occupied by one bookstore

AreaCatering = data["AreaCatering"] # shape: [], definition: Area occupied by one catering shop

MinJewelry = data["MinJewelry"] # shape: [], definition: Minimum number of jewelry shops

MinShoesHats = data["MinShoesHats"] # shape: [], definition: Minimum number of shoes & hats shops

MinGeneralMerch = data["MinGeneralMerch"] # shape: [], definition: Minimum number of general merchandise shops

MinBookstore = data["MinBookstore"] # shape: [], definition: Minimum number of bookstores

MinCatering = data["MinCatering"] # shape: [], definition: Minimum number of catering shops

MaxJewelry = data["MaxJewelry"] # shape: [], definition: Maximum number of jewelry shops

MaxShoesHats = data["MaxShoesHats"] # shape: [], definition: Maximum number of shoes & hats shops

MaxGeneralMerch = data["MaxGeneralMerch"] # shape: [], definition: Maximum number of general merchandise shops

MaxBookstore = data["MaxBookstore"] # shape: [], definition: Maximum number of bookstores

MaxCatering = data["MaxCatering"] # shape: [], definition: Maximum number of catering shops

ProfitJewelry1 = data["ProfitJewelry1"] # shape: [], definition: Annual profit for jewelry shop when 1 store

ProfitJewelry2 = data["ProfitJewelry2"] # shape: [], definition: Annual profit for jewelry shop when 2 stores

ProfitJewelry3 = data["ProfitJewelry3"] # shape: [], definition: Annual profit for jewelry shop when 3 stores

ProfitShoesHats1 = data["ProfitShoesHats1"] # shape: [], definition: Annual profit for shoes & hats shop when 1 store

ProfitShoesHats2 = data["ProfitShoesHats2"] # shape: [], definition: Annual profit for shoes & hats shop when 2 stores

ProfitGeneralMerch1 = data["ProfitGeneralMerch1"] # shape: [], definition: Annual profit for general merchandise shop when 1 store

ProfitGeneralMerch2 = data["ProfitGeneralMerch2"] # shape: [], definition: Annual profit for general merchandise shop when 2 stores

ProfitGeneralMerch3 = data["ProfitGeneralMerch3"] # shape: [], definition: Annual profit for general merchandise shop when 3 stores

ProfitBookstore1 = data["ProfitBookstore1"] # shape: [], definition: Annual profit for bookstore when 1 store

ProfitBookstore2 = data["ProfitBookstore2"] # shape: [], definition: Annual profit for bookstore when 2 stores

ProfitCatering1 = data["ProfitCatering1"] # shape: [], definition: Annual profit for catering shop when 1 store

ProfitCatering2 = data["ProfitCatering2"] # shape: [], definition: Annual profit for catering shop when 2 stores

ProfitCatering3 = data["ProfitCatering3"] # shape: [], definition: Annual profit for catering shop when 3 stores



### Define the variables

NumJewelry = model.addVar(vtype=GRB.INTEGER, name="NumJewelry")

NumShoesHats = model.addVar(vtype=GRB.INTEGER, name="NumShoesHats")

NumGeneralMerch = model.addVar(vtype=GRB.INTEGER, name="NumGeneralMerch")

NumBookstore = model.addVar(vtype=GRB.INTEGER, name="NumBookstore")

NumCatering = model.addVar(vtype=GRB.INTEGER, name="NumCatering")



### Define the constraints

model.addConstr(NumJewelry * AreaJewelry + NumShoesHats * AreaShoesHats + NumGeneralMerch * AreaGeneralMerch + NumBookstore * AreaBookstore + NumCatering * AreaCatering <= TotalSpace)
model.addConstr(NumJewelry >= MinJewelry)
model.addConstr(NumShoesHats >= MinShoesHats)
model.addConstr(NumGeneralMerch >= MinGeneralMerch)
model.addConstr(NumBookstore >= MinBookstore)
model.addConstr(NumCatering >= MinCatering)
model.addConstr(NumJewelry <= MaxJewelry)
model.addConstr(NumShoesHats <= MaxShoesHats)
model.addConstr(NumGeneralMerch <= MaxGeneralMerch)
model.addConstr(NumBookstore <= MaxBookstore)
model.addConstr(NumCatering <= MaxCatering)


### Define the objective

model.setObjective(
    RentPercentage * (
        (NumJewelry * ProfitJewelry1) * (NumJewelry == 1) +
        (NumJewelry * ProfitJewelry2) * (NumJewelry == 2) +
        (NumJewelry * ProfitJewelry3) * (NumJewelry == 3) +
        
        (NumShoesHats * ProfitShoesHats1) * (NumShoesHats == 1) +
        (NumShoesHats * ProfitShoesHats2) * (NumShoesHats == 2) +
        
        (NumGeneralMerch * ProfitGeneralMerch1) * (NumGeneralMerch == 1) +
        (NumGeneralMerch * ProfitGeneralMerch2) * (NumGeneralMerch == 2) +
        (NumGeneralMerch * ProfitGeneralMerch3) * (NumGeneralMerch == 3) +
        
        (NumBookstore * ProfitBookstore1) * (NumBookstore == 1) +
        (NumBookstore * ProfitBookstore2) * (NumBookstore == 2) +
        
        (NumCatering * ProfitCatering1) * (NumCatering == 1) +
        (NumCatering * ProfitCatering2) * (NumCatering == 2) +
        (NumCatering * ProfitCatering3) * (NumCatering == 3)
    ), 
    GRB.MAXIMIZE
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
        f.write(model.status)
