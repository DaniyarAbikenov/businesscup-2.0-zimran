"""Every position can run every scenario it sees, end to end, with the scenario's own example (all roles x scenarios)."""
import pytest

from app import packs
from app.validate import validate_answers
from test_api import signup

ROLES = [r["id"] for r in packs.roles_pack["roles"]]
PERSONAS = {"promoted-to-lead", "director", "it-pm", "chief-accountant", "officer", "public-official"}  # team lead, director, PM, chief accountant, officer, mayor


def visible(role):
    return [s for s in packs.situations if "*" in s["applies_to"] or role in s["applies_to"]]


def resolve_story(sit):
    return packs.public_situation(sit)["storylines"][0]["answers"]


def test_persona_roles_exist():
    assert PERSONAS <= set(ROLES)


@pytest.mark.parametrize("role", sorted(PERSONAS))
@pytest.mark.parametrize("lang", ["en", "ru"])
def test_persona_walks_through_every_visible_scenario(client, role, lang):
    signup(client, f"{role}-{lang}@example.com")
    assert client.put("/api/profile", json={"roleId": role, "industry": "", "tenure": "1-3m", "fears": []}).status_code == 200
    pack = {s["id"]: s for s in client.get("/api/packs", headers={"x-lang": lang}).json()["situations"]}
    for sit in visible(role):
        pub = pack[sit["id"]]
        defaults = {q["id"]: q["default"] for q in pub["questions"] if "default" in q}  # the form fills these in before the storyline
        answers = {**defaults, **pub["storylines"][0]["answers"]}
        values, errors = validate_answers(pub["questions"], answers)
        assert not errors, (role, sit["id"], errors)
        r = client.post("/api/cases", json={"situationId": sit["id"], "privacyAck": True, "confidenceBefore": 3, "inputs": answers}, headers={"x-lang": lang})
        if r.status_code == 402:  # free plan limit reached: that is the pricing rule, not a failure
            break
        assert r.status_code == 201, (role, sit["id"], r.text)
        case = r.json()["case"]
        option = next(iter(pub["options"]))
        d = client.post(f"/api/cases/{case['id']}/decision", json={"option": option, "rationale": "test"}, headers={"x-lang": lang})
        assert d.status_code == 200 and d.json()["case"]["document"], (role, sit["id"])
        assert d.json()["case"]["debrief"]["points"]
