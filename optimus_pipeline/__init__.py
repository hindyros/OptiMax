"""
OptiMUS pipeline steps, executed in order:

  01. parameters       - Extract parameters from problem description
  02. objective        - Extract optimization objective
  03. constraints      - Extract constraints
  04. constraint_model - Formulate constraints mathematically
  05. objective_model  - Formulate objective mathematically
  06. target_code      - Generate solver code for constraints/objective
  07. generate_code    - Assemble complete solver script
  08. execute_code     - Execute and debug the generated code
"""

from optimus_pipeline.step01_parameters import get_params
from optimus_pipeline.step02_objective import get_objective
from optimus_pipeline.step03_constraints import get_constraints
from optimus_pipeline.step04_constraint_model import get_constraint_formulations
from optimus_pipeline.step05_objective_model import get_objective_formulation
from optimus_pipeline.step06_target_code import get_codes
from optimus_pipeline.step07_generate_code import generate_code
from optimus_pipeline.step08_execute_code import execute_and_debug
