# Aligning the pipeline with client input and expert formulation

This note reflects on whether our current approach (natural language + one data file → params → OptiMUS) matches how **clients** provide input and how **experts** formulate optimization models.

---

## How clients typically provide input

- **Problem description**: Natural language: goals (“reduce stockouts”, “minimize cost”), context (“120 stores, 3 warehouses”), constraints (“capacity limits”, “unreliable deliveries”), and questions (“how much to reorder?”, “where to allocate?”). They rarely specify decision variables, parameters, or equations.
- **Data**: Spreadsheets, CSVs, exports from systems. Often:
  - Multiple tables (inventory, stores, orders) rather than one flat file.
  - Mixed content: IDs, dates, counts, percentages, text.
  - Business column names (“Stock Levels”, “Reorder Point”), not math symbols.
  - Not pre-shaped as “parameters” with types and dimensions; experts infer that.

So **client input** is: narrative + one or more data sources, messy and multi-table, without a formal split of “parameters” vs “variables.”

---

## How experts formulate optimization problems

1. **Understand the business**: Interpret the description, clarify goals and constraints.
2. **Decide what we’re choosing**: Reorder quantities, allocations, prices, etc. → **decision variables** (often indexed: e.g. \(x_{ij}\) = units to send from warehouse \(i\) to store \(j\)).
3. **Decide what we treat as given**: Current inventory, capacities, demands, costs, lead times → **parameters** (indexed to match the model: e.g. demand per product-store, capacity per warehouse).
4. **Reshape and derive from raw data**: Aggregate (e.g. demand per product from transactions), join tables, define index sets (products, stores, periods), and derive scalars (e.g. “number of products” = \(N\)).
5. **Write constraints and objective**: In terms of variables and parameters, with clear indexing (e.g. “for each product \(i\), inventory balance …”).
6. **Choose model class**: LP, MIP, etc., and possibly simplify (e.g. deterministic first, then uncertainty).

So **expert formulation** is: index sets + indexed parameters and variables + constraints/objective in math, with data mapped into that structure.

---

## Where we align well

| Aspect | Our approach | Client / expert analogue |
|--------|----------------|---------------------------|
| **Input** | Natural language + one CSV/Excel | Client gives narrative + data; we approximate with one file. |
| **Parameters vs variables** | Expert extraction: “given” = params, “to be decided” = left to OptiMUS | Expert separates data (params) from decisions (variables). |
| **Structured output** | params.json (symbol, shape, type, value) + desc.txt | Expert produces a structured model (symbols, dimensions, equations). |
| **Code** | Generated Gurobi from formulation | Expert implements model in a solver. |

So at a high level we **do** emulate: client-like input (description + data) and expert-like output (parameters, then formulation and code).

---

## Gaps and risks

### 1. **Single table, one param per column**

- **Reality**: Clients often have several tables; experts join/aggregate and define parameters with clear **indexing** (e.g. demand\(_{i,j}\), capacity\(_j\)).
- **Us**: One file → one param per column; shape is scalar or “[N]” from row count. We don’t infer **index sets** (e.g. “products”, “stores”) or 2D structure when the table is a long list of (product, store, …) rows.
- **Risk**: Params are flat (e.g. one long vector) while the formulation expects indexed structure (e.g. demand by product and store). The formulation step may still work, but the mapping from “client data” to “expert-style indexed params” is weak.

### 2. **IDs and dimensions**

- **Reality**: Experts use “number of products”, “number of stores” as dimensions and often treat ProductId / StoreId as **indices**, not as numeric parameters in the objective.
- **Us**: We treat every column as a parameter; ProductId/StoreId become scalars (e.g. first row) or vectors. So we don’t explicitly model “index sets” or “\(N\), \(M\)” the way an expert would.
- **Risk**: Model might use IDs as numbers or miss the right dimensions; formulation can be awkward or wrong.

### 3. **Derived parameters**

- **Reality**: Experts define things like “\(N\) = number of products” from the data, or “total capacity” = sum of a column.
- **Us**: We only pass through columns as-is (plus date→ordinal). We don’t derive \(N\), \(M\), or aggregates unless the LLM invents a column name for them (and we have no such column).
- **Risk**: Formulation may assume “\(N\)” or “number of warehouses” that doesn’t exist in params, so code gen can fail or guess.

### 4. **Semantics of non-numeric columns**

- **Reality**: Dates might be used for “don’t use stock that expires before …” or “lead time in days”; experts translate that into constraints and possibly derived params (e.g. “usable inventory”).
- **Us**: We convert date columns to ordinal numbers so the code doesn’t crash. That keeps things numeric but doesn’t guarantee the **meaning** (e.g. “days until expiry”) matches what the formulation assumes.
- **Risk**: Model runs but interpretation is off (e.g. ordinal used where “days until expiry” was intended).

### 5. **What “one data file” means**

- **Reality**: Client might give “inventory snapshot”, “store list”, “capacity by warehouse” as separate files or sheets.
- **Us**: One CSV/Excel only. Multi-table or multi-sheet is not first-class.
- **Risk**: User has to merge everything into one table; that’s not how they naturally think or how experts always receive data.

---

## Recommendations (to better emulate client + expert)

1. **Index sets and structure (medium term)**  
   - In expert extraction, add: “Identify index sets (e.g. products, stores, periods) from the description and column names.”  
   - Output not only a list of params but **indexing** (e.g. “StockLevels is indexed by product” or “by (product, store)” from row structure).  
   - Use that in the formulation/code step so we generate indexed params (e.g. 2D arrays where appropriate) instead of one flat vector.

2. **Derived parameters (short term)**  
   - Allow the LLM to emit “derived” params whose value is computed from the data (e.g. “NumberOfProducts”: row count or distinct ProductId, “NumberOfStores”: distinct StoreId).  
   - In the script: if `data_column` is missing or a special token like `"__row_count__"` or `"__distinct(ProductId)__"`, compute the value instead of reading a column.

3. **Parameter roles in the prompt (short term)**  
   - In the expert prompt, say explicitly: “Parameters are quantities that appear in the math (coefficients, RHS, capacities, demands). ID columns (ProductId, StoreId) are often used only for indexing; you may omit them as numeric parameters or use them to define dimensions (e.g. N = number of distinct products).”  
   - That pushes the model toward expert-like separation of “data for the math” vs “indices/dimensions.”

4. **Multiple files (later)**  
   - Support multiple CSVs/sheets (e.g. “inventory”, “stores”, “capacities”) and a small schema or narrative: “Sheet ‘inventory’ has one row per product-store; sheet ‘stores’ has one row per store.”  
   - Expert extraction then maps tables to index sets and params (e.g. capacity from “stores” table, demand from “inventory” or a third table).

5. **Client-facing summary**  
   - Optional: one short “model summary” or “assumptions” (from the LLM) in natural language, e.g. “We are modeling reorder quantities per product and allocation from warehouses to stores; we assume deterministic demand for this formulation.”  
   - That mirrors what experts write when handing off a model and helps the client (or you) sanity-check.

---

## Summary

- **Client input**: We approximate it well with “natural language + one data file,” which is a common and reasonable simplification.
- **Expert formulation**: We emulate the overall flow (params from data, variables and formulation by OptiMUS), but we under-specify **index sets**, **derived dimensions**, and **multi-table structure**, and we overload “parameter” (e.g. IDs vs true RHS/coefficients).

Improving index-set awareness, derived parameters, and parameter roles in the prompt will make the pipeline closer to how experts actually go from client input to a formulated optimization model.

---

## Implemented (real-life alignment)

The following are now in place in `scripts/data_to_optimus.py`:

1. **Expert prompt rewritten**  
   - Framed as “client has described their problem and provided a dataset”; you act as consultant.  
   - Parameters = quantities that appear in the math (coefficients, RHS, capacities, demands); ID columns are for indexing/dimensions, not as numeric parameters unless needed.  
   - Explicit guidance to prefer derived dimensions (NumberOfProducts, NumberOfStores) over using ID columns as parameters.

2. **Derived parameters**  
   - `data_column` can be `__n_rows__` (total rows) or `__n_distinct__:ColumnName` (number of distinct values in that column).  
   - The script computes these from the dataframe and writes scalar integer params (e.g. NumberOfProducts, NumberOfStores) so the formulation has proper dimensions.

3. **Richer data summary for the LLM**  
   - Per-column: dtype, distinct count (when small), sample values.  
   - Listed derived tokens: `__n_rows__` and `__n_distinct__:<col>` for each column with a reasonable distinct count, so the LLM can suggest dimension parameters.

4. **Optional model summary (assumptions)**  
   - The LLM may output a `model_summary` string (what we are modeling and key assumptions).  
   - When present, it is written to `assumptions.txt` in the output folder for the client, similar to an expert handoff note.
