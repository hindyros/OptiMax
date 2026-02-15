# Sample Data Files for Optima Testing

This directory contains sample CSV files that can be used to test the Optima optimization tool.

## Files Overview

### 1. healthcare_resources.csv
**Use Case**: Hospital resource allocation optimization

**Problem Description Example**:
"I need to optimize hospital bed allocation across multiple departments to maximize patient care while minimizing costs. Each department has different staffing levels, costs, and patient demands."

**Data Includes**:
- Department names
- Available beds per department
- Staff counts
- Daily costs per bed
- Patient demand
- Priority levels

**Sample Optimization Goals**:
- Minimize total daily costs
- Maximize patient coverage
- Balance staff workload

---

### 2. production_planning.csv
**Use Case**: Manufacturing production optimization

**Problem Description Example**:
"I want to optimize our production schedule to maximize profit while staying within our resource constraints for materials, labor, and storage space."

**Data Includes**:
- Product names
- Production costs and selling prices
- Material requirements
- Labor hours needed
- Storage space requirements
- Maximum demand per product
- Minimum production quantities

**Sample Optimization Goals**:
- Maximize total profit
- Meet all minimum production requirements
- Stay within material/labor/storage constraints

---

### 3. transportation.csv
**Use Case**: Logistics and transportation optimization

**Problem Description Example**:
"I need to optimize delivery routes from multiple warehouses to customers to minimize transportation costs while meeting delivery time requirements."

**Data Includes**:
- Route identifiers
- Source and destination locations
- Distance in kilometers
- Transport costs per route
- Vehicle capacity
- Delivery time in hours

**Sample Optimization Goals**:
- Minimize total transportation cost
- Meet all delivery time constraints
- Optimize vehicle capacity utilization

---

### 4. resource_allocation.csv
**Use Case**: Knapsack-style resource allocation

**Problem Description Example**:
"I want to select the best combination of items to maximize value while staying within weight and volume constraints."

**Data Includes**:
- Item identifiers
- Value per item
- Weight per item
- Volume per item
- Quantity available

**Sample Optimization Goals**:
- Maximize total value
- Stay within weight limit
- Stay within volume limit

---

## How to Use

1. Navigate to the Optima app at `/refine`
2. Enter a problem description (see examples above)
3. Upload one or more of these CSV files
4. Answer baseline questions about your current approach
5. Submit for optimization

## Testing Tips

- **Single File**: Test with one CSV file for simple problems
- **Multiple Files**: Upload multiple CSVs together (e.g., production_planning.csv + resource_allocation.csv) for complex multi-constraint problems
- **Baseline Questions**: When asked about your current approach, describe manual methods, spreadsheets, or rule-of-thumb decisions
- **Expected Results**: The system should generate:
  - Mathematical formulation
  - Optimal solution values
  - Baseline comparison showing improvements
  - Executive summary report

## Sample Problem Statement

**Healthcare Example**:

```
Problem: I need to optimize hospital bed allocation across 7 departments

Current Approach: We currently allocate beds based on last year's average demand,
resulting in some departments being overloaded while others have excess capacity.
We spend approximately $500,000 per day on bed operations.

Goal: Minimize costs while ensuring we can handle at least 90% of patient demand
in each department, with higher priority for Emergency, ICU, and Surgery departments.
```

---

**Production Example**:

```
Problem: I want to optimize production of 5 different products to maximize profit

Current Approach: We produce equal quantities of each product based on a fixed schedule.
Last quarter we achieved $150,000 in profit. We often run out of high-margin products
while having excess inventory of low-margin ones.

Goal: Maximize profit while staying within our material budget of 2000 units,
labor budget of 1500 hours, and storage space of 800 square feet.
```

---

For more realistic testing, modify these CSV files with your own data or create new ones matching your specific use case.
