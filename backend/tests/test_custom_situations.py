"""AI-made situations: the AI only fills a preset on an existing engine; code validates everything.
The AI is faked. What we verify: invalid ids/keys/values are dropped, text is capped, a user cannot see or use
another user's situation, limits hold, and a saved situation works end to end like a built-in one."""
import json as _json

from app import config, llm, presets
from test_api import signup

TEXT = "My manager and the product owner both want me to take on extra work while two reports are due this week. I need to pick an order."
LONG = "x" * 900


def preset(**over):
    base = {
        "engine": "priorities", "title": "Two bosses, one week", "summary": "Two people with authority ask for work at once.", "category": "ignored",
        "labels": [{"id": "title", "label": "What did they ask for?", "help": "One line."},
                   {"id": "nope", "label": "unknown id, dropped", "help": ""},
                   {"id": "name", "label": "Request", "help": ""},                      # a row field: allowed
                   {"id": "context", "label": LONG, "help": LONG}],
        "options": [{"key": "deadline", "label": "By due date", "nextSteps": ["Tell both of them the date.", "", "Block time."]},
                    {"key": "hack", "label": "unknown key, dropped", "nextSteps": ["x"]},
                    {"key": "custom", "label": "My own order", "nextSteps": [LONG] + ["s"] * 10}],
        "pitfalls": ["Saying yes to both."] + [LONG] * 20,
        "reflectionPrompts": [{"id": "learned", "label": "What did you learn?"}, {"id": "other", "label": "dropped"}],
        "storyline": {"title": "Two asks", "story": "A short example.",
                      "fields": [{"id": "title", "value": "Two asks this week"}, {"id": "hoursPerWeek", "value": "40"},
                                 {"id": "committedHours", "value": "lots"}, {"id": "bogus", "value": "1"}],
                      "tasks": [{"name": "Report A", "effortHours": "6", "deadline": "+3", "requester": "manager", "impact": "money", "note": ""},
                                {"name": "Report B", "effortHours": "-2", "deadline": "+5", "requester": "ceo", "impact": "", "note": ""},
                                {"name": "Extra", "effortHours": "4", "deadline": "+6", "requester": "peer", "impact": "minor", "note": ""}]},
    }
    return {**base, **over}


def ai_on(monkeypatch, proposal=None):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")
    calls = []
    monkeypatch.setattr(llm, "generate_preset", lambda text, specs: (calls.append((text, specs)), proposal if proposal is not None else preset())[1])
    return calls


def draft(client, **kw):
    return client.post("/api/situations/draft", json={"text": TEXT, "privacyAck": True, **kw})


def test_validation_drops_invalid_parts_and_caps_text():
    p = presets.normalize(preset())
    assert [x["id"] for x in p["labels"]] == ["title", "name", "context"]
    assert len(p["labels"][2]["label"]) <= presets.CAPS["label"] and len(p["labels"][2]["help"]) <= presets.CAPS["help"]
    assert [o["key"] for o in p["options"]] == ["deadline", "custom"]
    assert p["options"][0]["nextSteps"] == ["Tell both of them the date.", "Block time."]
    assert len(p["options"][1]["nextSteps"]) == presets.MAX_STEPS and len(p["options"][1]["nextSteps"][0]) <= presets.CAPS["step"]
    assert len(p["pitfalls"]) == presets.MAX_PITFALLS and all(len(x) <= presets.CAPS["pitfall"] for x in p["pitfalls"])
    assert [x["id"] for x in p["reflectionPrompts"]] == ["learned"]
    st = p["storyline"]
    assert [f["id"] for f in st["fields"]] == ["title", "hoursPerWeek"]          # "lots" and "bogus" dropped
    assert [t["name"] for t in st["tasks"]] == ["Report A", "Extra"]             # the invalid row is dropped
    assert presets.normalize(p) == p                                              # idempotent
    sit = presets.build(p, "two-bosses")
    assert sit["id"] == "my-two-bosses" and sit["category"] == "My situations" and sit["aiMade"] is True and sit["engine"] == "priorities"
    assert sit["options"]["deadline"]["label"] == "By due date" and sit["options"]["stakeholder"]["label"] == "Most senior requester first"
    assert set(sit["options"]) == {"deadline", "stakeholder", "impact", "custom"}
    a = sit["storylines"][0]["answers"]
    assert a["tasks"][0]["deadline"] == {"daysFromNow": 3} and a["hoursPerWeek"] == 40 and "committedHours" not in a


def test_rejects_missing_title_summary_or_engine():
    for bad in ({"title": ""}, {"summary": "  "}, {"engine": "rocket"}):
        try:
            presets.normalize(preset(**bad))
            assert False, bad
        except Exception as e:
            assert getattr(e, "status", None) == 422


def test_disabled_without_key_and_rules(client, make_client, monkeypatch):
    assert make_client().post("/api/situations/draft", json={"text": TEXT, "privacyAck": True}).status_code == 401
    signup(client, "d@example.com")
    assert draft(client).status_code == 404  # no key on this server
    ai_on(monkeypatch)
    assert client.post("/api/situations/draft", json={"text": "short", "privacyAck": True}).status_code == 400
    r = client.post("/api/situations/draft", json={"text": TEXT, "privacyAck": False})
    assert r.status_code == 400 and "privacyAck" in r.json()["fields"]


def test_daily_limit(client, monkeypatch):
    signup(client, "lim@example.com")
    ai_on(monkeypatch)
    for _ in range(10):
        assert draft(client).status_code == 200
    r = draft(client)
    assert r.status_code == 429 and "10 AI drafts" in r.json()["error"]


def test_ai_failure_is_a_friendly_502(client, monkeypatch):
    signup(client, "f@example.com")
    ai_on(monkeypatch)

    def boom(text, specs):
        raise llm.LlmError("connection")
    monkeypatch.setattr(llm, "generate_preset", boom)
    r = draft(client)
    assert r.status_code == 502 and "unavailable" in r.json()["error"]


def test_full_flow_draft_save_case_decide_document(client, make_client, monkeypatch):
    signup(client, "flow@example.com")
    calls = ai_on(monkeypatch)
    d = draft(client).json()
    assert [s["engine"] for s in calls[0][1]] == ["change_request", "priorities", "estimate", "decision"]  # the AI only sees the supported engines
    assert d["situation"]["aiMade"] is True and d["situation"]["title"] == "Two bosses, one week"
    assert d["situation"]["storylines"][0]["answers"]["tasks"][0]["deadline"] > "2000"  # dates resolved for the browser
    assert "my-two-bosses-one-week" not in [s["id"] for s in client.get("/api/packs").json()["situations"]]  # a draft is not saved
    saved = client.post("/api/situations", json={"preset": d["preset"]})
    assert saved.status_code == 201 and saved.json()["situation"]["id"] == "my-two-bosses-one-week"
    pack = {s["id"]: s for s in client.get("/api/packs").json()["situations"]}
    assert pack["my-two-bosses-one-week"]["category"] == "My situations" and pack["my-two-bosses-one-week"]["aiMade"] is True

    inputs = {"title": "Two asks", "hoursPerWeek": 40, "committedHours": 15,
              "tasks": [{"name": "Report A", "effortHours": 6, "deadline": "2030-01-15", "requester": "manager", "impact": "money"},
                        {"name": "Extra", "effortHours": 4, "deadline": "2030-01-16", "requester": "peer", "impact": "minor"}]}
    case = client.post("/api/cases", json={"situationId": "my-two-bosses-one-week", "privacyAck": True, "confidenceBefore": 2, "inputs": inputs}).json()["case"]
    assert case["title"] == "Two asks" and len(case["result"]["options"]) == 4
    decided = client.post(f"/api/cases/{case['id']}/decision", json={"option": "deadline", "rationale": "Due dates first"}).json()["case"]
    assert decided["document"].startswith("# Priority proposal: Two asks") and "By due date" in decided["document"]
    assert decided["debrief"]["nextSteps"] == ["Tell both of them the date.", "Block time."]
    assert client.get("/api/documents").json()["documents"][0]["label"] == "Priority proposal"
    assert client.request("DELETE", "/api/situations/two-bosses-one-week", json={}).status_code == 409  # a case uses it

    # another user can neither see nor use it, nor delete it
    other = make_client()
    signup(other, "other@example.com")
    assert "my-two-bosses-one-week" not in [s["id"] for s in other.get("/api/packs").json()["situations"]]
    r = other.post("/api/cases", json={"situationId": "my-two-bosses-one-week", "privacyAck": True, "confidenceBefore": 2, "inputs": inputs})
    assert r.status_code == 400 and r.json()["error"] == "Unknown situation"
    assert other.request("DELETE", "/api/situations/two-bosses-one-week", json={}).status_code == 404
    assert other.get(f"/api/cases/{case['id']}").status_code == 404


def test_save_revalidates_on_the_server_and_limits(client, monkeypatch):
    signup(client, "s@example.com")
    assert client.post("/api/situations", json={"preset": {"engine": "priorities", "title": "", "summary": ""}}).status_code == 422
    forged = preset(options=[{"key": "deadline", "label": "<b>x</b>", "nextSteps": ["ok"]}, {"key": "evil", "label": "y", "nextSteps": []}])
    s = client.post("/api/situations", json={"preset": forged}).json()["situation"]
    assert set(s["options"]) == {"deadline", "stakeholder", "impact", "custom"}  # keys are the engine's, whatever was sent
    for n in range(2, 21):
        assert client.post("/api/situations", json={"preset": preset(title=f"Case {n}")}).status_code == 201
    r = client.post("/api/situations", json={"preset": preset(title="One too many")})
    assert r.status_code == 400 and "up to 20" in r.json()["error"]
    assert client.request("DELETE", "/api/situations/case-2", json={}).status_code == 200
    assert client.post("/api/situations", json={"preset": preset(title="One too many")}).status_code == 201
    assert client.request("DELETE", "/api/situations/case-3", json={}).status_code == 200
    assert client.post("/api/situations", json={"preset": preset(title="Two bosses, one week")}).json()["situation"]["id"] == "my-two-bosses-one-week-2"


def test_intake_hints_when_nothing_matches(client):
    signup(client, "h@example.com")
    out = client.post("/api/intake", json={"text": "I accidentally deleted a shared folder and I am not sure what to do about it now."}).json()
    assert out["noMatch"] is True
    out = client.post("/api/intake", json={"text": "The client wants a new feature added before the release date."}).json()
    assert out["noMatch"] is False


def test_llm_request_shape(monkeypatch):
    """The real SDK against a fake HTTP transport: what we send for a preset and how a refusal is read."""
    import anthropic
    import httpx2 as httpx
    sent, reply = {}, {"stop_reason": "end_turn", "text": _json.dumps(preset())}

    def handler(req):
        sent["body"] = _json.loads(req.content)
        sent["beta"] = req.headers.get("anthropic-beta", "")
        return httpx.Response(200, json={
            "id": "msg_1", "type": "message", "role": "assistant", "model": sent["body"]["model"],
            "content": [{"type": "text", "text": reply["text"]}], "stop_reason": reply["stop_reason"],
            "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1}})
    monkeypatch.setattr(llm, "_client", lambda: anthropic.Anthropic(api_key="k", http_client=httpx.Client(transport=httpx.MockTransport(handler))))
    out = llm.generate_preset(TEXT, presets.engine_specs())
    assert out["engine"] == "priorities"
    b = sent["body"]
    assert b["model"] == config.LLM_MODEL and b["fallbacks"] == "default" and "server-side-fallback" in sent["beta"]
    props = b["output_config"]["format"]["schema"]["properties"]
    assert props["engine"]["enum"] == ["change_request", "priorities", "estimate", "decision"] and {"labels", "options", "storyline", "pitfalls", "reflectionPrompts"} <= set(props)
    content = b["messages"][0]["content"]
    assert "<description>" in content and "client-change-request" not in content and '"engine": "priorities"' in content
    reply.update(stop_reason="refusal", text="")
    try:
        llm.generate_preset(TEXT, presets.engine_specs())
        assert False, "refusal must raise"
    except llm.LlmError as e:
        assert str(e) == "refusal"


def test_ai_preset_on_the_estimate_engine():
    p = presets.normalize(preset(engine="estimate", title="Quote a date for a report", summary="Someone wants a date.",
                                 labels=[{"id": "optimisticHours", "label": "Best case (hours)", "help": ""}, {"id": "tasks", "label": "not a question here", "help": ""}],
                                 options=[{"key": "safe", "label": "Safe date", "nextSteps": ["Explain the buffer."]}, {"key": "deadline", "label": "x", "nextSteps": []}],
                                 reflectionPrompts=[],
                                 storyline={"title": "A report", "story": "Example.", "fields": [
                                     {"id": "title", "value": "Report"}, {"id": "optimisticHours", "value": "8"}, {"id": "likelyHours", "value": "16"},
                                     {"id": "pessimisticHours", "value": "30"}, {"id": "askedDeadline", "value": "+7"}, {"id": "requester", "value": "ceo"}], "tasks": []}))
    assert [x["id"] for x in p["labels"]] == ["optimisticHours"] and [o["key"] for o in p["options"]] == ["safe"]
    sit = presets.build(p, "quote-a-date")
    assert sit["engine"] == "estimate" and set(sit["options"]) == {"optimistic", "likely", "safe", "range"}
    a = sit["storylines"][0]["answers"]
    assert a["askedDeadline"] == {"daysFromNow": 7} and a["likelyHours"] == 16 and "requester" not in a
