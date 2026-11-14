"""Roles are broad (any new position), old ids stay valid, and the catalog depends on the role."""
from app import packs
from test_api import signup

NEW = {"specialist-new-company", "promoted-to-lead", "head-of-function", "career-switch"}
LEGACY = {"it-pm", "animation-pm", "construction-pm", "eng-lead", "other"}


def visible(role_id):
    """The same rule as Home.tsx."""
    return {s["id"] for s in packs.situations if "*" in s["applies_to"] or role_id in s["applies_to"]}


def test_roles_and_fears_are_broad():
    ids = {r["id"] for r in packs.roles_pack["roles"]}
    assert NEW <= ids and LEGACY <= ids and len(ids) == len(packs.roles_pack["roles"])
    assert all({"milestone", "work", "unit"} <= set(r["terms"]) for r in packs.roles_pack["roles"])
    fears = " ".join(f["label"] for f in packs.roles_pack["fears"]).lower()
    assert "project" not in fears and "client" not in fears and "scope" not in fears
    assert {f["id"] for f in packs.roles_pack["fears"]} >= {"wrong-call", "pushback", "not-understanding", "too-many-demands"}


def test_catalog_per_role():
    every = {r["id"] for r in packs.roles_pack["roles"]}
    for s in packs.situations:  # every applies_to entry is a real role (or *)
        assert set(s["applies_to"]) <= every | {"*"}
    for role in every:
        assert "competing-priorities" in visible(role)  # nobody ends up with an empty catalog
    assert "client-change-request" not in visible("specialist-new-company") and "client-change-request" not in visible("promoted-to-lead")
    assert {"it-pm", "construction-pm", "eng-lead", "other"} <= {r for r in every if "client-change-request" in visible(r)}


def test_onboarding_accepts_new_and_legacy_roles(client):
    signup(client, "roles@example.com")
    for role in ("promoted-to-lead", "career-switch", "it-pm"):
        p = client.put("/api/profile", json={"roleId": role, "industry": "", "tenure": "lt-1m", "fears": ["not-understanding", "scope"]})
        assert p.status_code == 200 and p.json()["profile"]["roleId"] == role
        assert p.json()["profile"]["fears"] == ["not-understanding"]  # the retired "scope" worry is dropped
    # a situation not listed for the role can still be started (intake and AI-made situations are not filtered)
    client.put("/api/profile", json={"roleId": "career-switch", "industry": "", "tenure": "lt-1m", "fears": []})
    r = client.post("/api/intake", json={"text": "The client wants a new feature added before the release date."}).json()
    assert r["situationId"] == "client-change-request"
