"""Engine registry: a situation pack names its engine; each engine has compute(inputs) and optional check(inputs)."""
from . import change_request, decision, estimate, priorities

ENGINES = {"change_request": change_request, "priorities": priorities, "estimate": estimate, "decision": decision}


def run(sit: dict, inputs: dict) -> dict:
    return ENGINES[sit["engine"]].compute(inputs)


def check(sit: dict, inputs: dict) -> dict:
    fn = getattr(ENGINES[sit["engine"]], "check", None)
    return fn(inputs) if fn else {}
