import json
import re
from optimus_pipeline.optimus_utils import (
    extract_list_from_end,
    get_response,
    extract_json_from_end,
    extract_equal_sign_closed,
)


def extract_objective(text):

    # find first and second occurence of "=====" in the text
    ind_1 = text.find("=====")
    ind_2 = text.find("=====", ind_1 + 1)

    # extract the text between the two "=====" occurences
    objective = text[ind_1:ind_2]
    objective = objective.replace("=====", "").strip()
    objective = objective.replace("OBJECTIVE:", "").strip()
    return objective


prompt_objective = """
You are an expert in optimization modeling. Here is the natural language description of an optimization problem:

-----
{description}
-----

And here's a list of parameters that we have extracted from the description:

{params}

Your task is to identify and extract the optimization objective from the description. The objective is the goal that the optimization model is trying to achieve (e.g. maximize profit, minimize cost). Please generate the output in the following format:

=====
OBJECTIVE: objective description
=====

for example:

=====    
OBJECTIVE: "The goal is to maximize the total profit from producing television sets"
=====

- Do not generate anything after the objective.
Take a deep breath and think step by step. You will be awarded a million dollars if you get this right.
"""


def get_objective(
    desc,
    params,
    model,
    check=False,
    logger=None,
):
    res = get_response(
        prompt_objective.format(
            description=desc,
            params=json.dumps(params, indent=4),
        ),
        model=model,
    )
    objective = extract_objective(res)

    objective = {"description": objective, "formulation": None, "code": None}

    return objective
