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

from pipeline.step01_parameters import get_params
from pipeline.step02_objective import get_objective
from pipeline.step03_constraints import get_constraints
from pipeline.step04_constraint_model import get_constraint_formulations
from pipeline.step05_objective_model import get_objective_formulation
from pipeline.step06_target_code import get_codes
from pipeline.step07_generate_code import generate_code
from pipeline.step08_execute_code import execute_and_debug
