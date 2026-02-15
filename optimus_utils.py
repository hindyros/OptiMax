import os
import json
import time
from dotenv import load_dotenv

load_dotenv()

# Optional providers: only load and create clients when API keys are set
groq_key = os.environ.get("GROQ_API_KEY", "###")
openai_key = os.environ.get("OPENAI_API_KEY", "###")
openai_org = os.environ.get("OPENAI_ORG_ID", "###")
anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "###")

_open_ai_client = None
_groq_client = None
_anthropic_client = None


def _get_openai_client():
    global _open_ai_client
    if _open_ai_client is None:
        if openai_key == "###":
            raise ValueError(
                "OpenAI model requested but OPENAI_API_KEY is not set. "
                "Set it with: export OPENAI_API_KEY='your-key'"
            )
        import openai
        _open_ai_client = openai.Client(
            api_key=openai_key,
            organization=openai_org if openai_org != "###" else None,
        )
    return _open_ai_client


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        if groq_key == "###":
            raise ValueError(
                "Groq model requested but GROQ_API_KEY is not set. "
                "Set it with: export GROQ_API_KEY='your-key'"
            )
        from groq import Groq
        _groq_client = Groq(api_key=groq_key)
    return _groq_client


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        if anthropic_key == "###":
            raise ValueError(
                "Anthropic model requested but ANTHROPIC_API_KEY is not set. "
                "Set it with: export ANTHROPIC_API_KEY='your-key'"
            )
        from anthropic import Anthropic
        _anthropic_client = Anthropic(api_key=anthropic_key)
    return _anthropic_client


def extract_json_from_end(text):
    
    try:
        return extract_json_from_end_backup(text)
    except:
        pass
    
    # Find the start of the JSON object
    json_start = text.find("{")
    if json_start == -1:
        raise ValueError("No JSON object found in the text.")

    # Extract text starting from the first '{'
    json_text = text[json_start:]
    
    # Remove backslashes used for escaping in LaTeX or other formats
    json_text = json_text.replace("\\", "")

    # Remove any extraneous text after the JSON end
    ind = len(json_text) - 1
    while json_text[ind] != "}":
        ind -= 1
    json_text = json_text[: ind + 1]

    # Find the opening curly brace that matches the closing brace
    ind -= 1
    cnt = 1
    while cnt > 0 and ind >= 0:
        if json_text[ind] == "}":
            cnt += 1
        elif json_text[ind] == "{":
            cnt -= 1
        ind -= 1

    # Extract the JSON portion and load it
    json_text = json_text[ind + 1:]

    # Attempt to load JSON
    try:
        jj = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to decode JSON: {e}")

    return jj

def extract_json_from_end_backup(text):

    if "```json" in text:
        text = text.split("```json")[1]
        text = text.split("```")[0]
    ind = len(text) - 1
    while text[ind] != "}":
        ind -= 1
    text = text[: ind + 1]

    ind -= 1
    cnt = 1
    while cnt > 0:
        if text[ind] == "}":
            cnt += 1
        elif text[ind] == "{":
            cnt -= 1
        ind -= 1

    # find comments in the json string (texts between "//" and "\n") and remove them
    while True:
        ind_comment = text.find("//")
        if ind_comment == -1:
            break
        ind_end = text.find("\n", ind_comment)
        text = text[:ind_comment] + text[ind_end + 1 :]

    # convert to json format
    jj = json.loads(text[ind + 1 :])
    return jj


def extract_list_from_end(text):
    ind = len(text) - 1
    while text[ind] != "]":
        ind -= 1
    text = text[: ind + 1]

    ind -= 1
    cnt = 1
    while cnt > 0:
        if text[ind] == "]":
            cnt += 1
        elif text[ind] == "[":
            cnt -= 1
        ind -= 1

    # convert to json format
    jj = json.loads(text[ind + 1 :])
    return jj


# Retry on transient API errors (500, 429, 529 overloaded, etc.).
def _retry_llm_call(callable_fn, max_attempts=4, base_delay=2.0):
    last_error = None
    for attempt in range(max_attempts):
        try:
            return callable_fn()
        except Exception as e:
            last_error = e
            err_str = type(e).__name__
            is_retryable = (
                "InternalServerError" in err_str
                or "RateLimitError" in err_str
                or "OverloadedError" in err_str
                or "APIConnectionError" in err_str
                or (hasattr(e, "status_code") and e.status_code in (500, 502, 503, 429, 529))
            )
            if not is_retryable or attempt == max_attempts - 1:
                raise
            delay = base_delay * (2**attempt)
            time.sleep(delay)
    raise last_error


# Default model: Anthropic Claude. Also supports OpenAI (gpt-*) and Groq (llama3-70b-8192).
def get_response(prompt, model="claude-haiku-4-5-20251001"):
    if model.startswith("claude-"):
        client = _get_anthropic_client()

        def _call():
            message = client.messages.create(
                model=model,
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text

        return _retry_llm_call(_call)
    if model == "llama3-70b-8192":
        client = _get_groq_client()

        def _call():
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model,
            )
            return chat_completion.choices[0].message.content

        return _retry_llm_call(_call)
    # OpenAI (gpt-* etc.)
    client = _get_openai_client()

    def _call():
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model,
        )
        return chat_completion.choices[0].message.content

    return _retry_llm_call(_call)


def load_state(state_file):
    with open(state_file, "r") as f:
        state = json.load(f)
    return state


def save_state(state, dir):
    with open(dir, "w") as f:
        json.dump(state, f, indent=4)


def shape_string_to_list(shape_string):
    if type(shape_string) == list:
        return shape_string
    # convert a string like "[N, M, K, 19]" to a list like ['N', 'M', 'K', 19]
    shape_string = shape_string.strip()
    shape_string = shape_string[1:-1]
    shape_list = shape_string.split(",")
    shape_list = [x.strip() for x in shape_list]
    shape_list = [int(x) if x.isdigit() else x for x in shape_list]
    if len(shape_list) == 1 and shape_list[0] == "":
        shape_list = []
    return shape_list


def extract_equal_sign_closed(text):
    ind_1 = text.find("=====")
    ind_2 = text.find("=====", ind_1 + 1)
    obj = text[ind_1 + 6 : ind_2].strip()
    return obj


class Logger:
    def __init__(self, file):
        self.file = file

    def log(self, text):
        with open(self.file, "a") as f:
            f.write(text + "\n")

    def reset(self):
        with open(self.file, "w") as f:
            f.write("")


def create_state(parent_dir, run_dir):
    model_dir = os.path.join(parent_dir, "model_input")
    # read params.json
    with open(os.path.join(model_dir, "params.json"), "r") as f:
        params = json.load(f)

    data = {}
    for key in params:
        data[key] = params[key]["value"]
        del params[key]["value"]

    # save the data file in the run_dir
    with open(os.path.join(run_dir, "data.json"), "w") as f:
        json.dump(data, f, indent=4)

    # read the description
    with open(os.path.join(model_dir, "desc.txt"), "r") as f:
        desc = f.read()

    state = {"description": desc, "parameters": params}
    return state

if __name__ == "__main__":
    
    text = 'To maximize the number of successfully transmitted shows, we can introduce a new variable called "TotalTransmittedShows". This variable represents the total number of shows that are successfully transmitted.\n\nThe constraint can be formulated as follows:\n\n\\[\n\\text{{Maximize }} TotalTransmittedShows\n\\]\n\nTo model this constraint in the MILP formulation, we need to add the following to the variables list:\n\n\\{\n    "TotalTransmittedShows": \\{\n        "shape": [],\n        "type": "integer",\n        "definition": "The total number of shows transmitted"\n    \\}\n\\}\n\nAnd the following auxiliary constraint:\n\n\\[\n\\forall i \\in \\text{{NumberOfShows}}, \\sum_{j=1}^{\\text{{NumberOfStations}}} \\text{{Transmitted}}[i][j] = \\text{{TotalTransmittedShows}}\n\\]\n\nThe complete output in the requested JSON format is:\n\n\\{\n    "FORMULATION": "",\n    "NEW VARIABLES": \\{\n        "TotalTransmittedShows": \\{\n            "shape": [],\n            "type": "integer",\n            "definition": "The total number of shows transmitted"\n        \\}\n    \\},\n    "AUXILIARY CONSTRAINTS": [\n        ""\n    ]\n\\'
    
    extract_json_from_end(text)