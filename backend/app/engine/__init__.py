"""Engine registry: a situation pack names its engine; each engine has compute(inputs) and optional check(inputs)."""
from . import change_request, decision, estimate, priorities

ENGINES = {"change_request": change_request, "priorities": priorities, "estimate": estimate, "decision": decision}


def run(sit: dict, inputs: dict) -> dict:
    from .. import levers, msg
    result = ENGINES[sit["engine"]].compute(inputs)
    lv = levers.compute(sit, inputs, result)  # time, money and quality: ways to fix lateness, only when optional data was entered
    if lv:
        result["levers"] = lv
    return msg.localize_dates_deep(result)  # dates inside sentences follow the language


def check(sit: dict, inputs: dict) -> dict:
    fn = getattr(ENGINES[sit["engine"]], "check", None)
    return fn(inputs) if fn else {}
