"""Validates user input against the question spec from the situation pack."""
import re
from datetime import date

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_answers(questions: list, raw) -> tuple[dict, dict]:
    """Returns (values, errors). A "list" question holds rows; its errors are keyed "<id>.<row>.<field>"."""
    errors: dict = {}
    out: dict = {}
    body = raw if isinstance(raw, dict) else {}
    for q in questions:
        qid = q["id"]
        v = body.get(qid)
        if v is None or (isinstance(v, str) and v.strip() == ""):
            if q.get("required"):
                errors[qid] = "Required"
            else:
                out[qid] = q.get("default", 0) if q["type"] == "number" else ""
            continue
        t = q["type"]
        if t == "list":
            rows = v if isinstance(v, list) else []
            rows = [r for r in rows if isinstance(r, dict) and any(str(x).strip() for x in r.values() if x is not None)]
            if len(rows) < q.get("minRows", 1):
                errors[qid] = f"Add at least {q.get('minRows', 1)}"
                continue
            if len(rows) > q.get("maxRows", 10):
                errors[qid] = f"At most {q.get('maxRows', 10)}"
                continue
            vals = []
            for n, row in enumerate(rows):
                rv, re_ = validate_answers(q["fields"], row)
                errors.update({f"{qid}.{n}.{k}": m for k, m in re_.items()})
                vals.append(rv)
            if not any(k.startswith(qid + ".") for k in errors):
                out[qid] = vals
            continue
        if t == "number":
            try:
                if isinstance(v, bool):
                    raise ValueError
                n = float(str(v).replace(",", "")) if not isinstance(v, (int, float)) else float(v)
                if n != n or n in (float("inf"), float("-inf")):
                    raise ValueError
            except ValueError:
                errors[qid] = "Enter a number"
                continue
            if "min" in q and n < q["min"]:
                errors[qid] = f"Must be at least {q['min']}"
            elif "max" in q and n > q["max"]:
                errors[qid] = f"Must be at most {q['max']}"
            else:
                out[qid] = int(n) if n == int(n) else n
        elif t == "date":
            try:
                if not isinstance(v, str) or not ISO.match(v):
                    raise ValueError
                date.fromisoformat(v)
                out[qid] = v
            except ValueError:
                errors[qid] = "Enter a valid date"
        elif t == "select":
            if v not in [o["value"] for o in q["options"]]:
                errors[qid] = "Choose one of the options"
            else:
                out[qid] = v
        elif not isinstance(v, str):
            errors[qid] = "Enter text"
        elif q.get("max") and len(v) > q["max"]:
            errors[qid] = f"Max {q['max']} characters"
        else:
            out[qid] = v.strip()
    return out, errors
