"""Intake: free text -> situation + pre-filled answers. The AI is faked; what we verify is that code,
not the model, decides which values reach the form."""
from app import config, intake, llm
from app.routers import intake as intake_router
from test_api import signup

TEXT = ("My manager, the VP and a colleague all asked me for something this week and I can't do it all. "
        "The VP overview is due Friday, about 6 hours of work.")


def test_keyword_fallback_without_ai(client):
    signup(client, "k@example.com")
    r = client.post("/api/intake", json={"text": TEXT})
    assert r.status_code == 200
    out = r.json()
    assert out["situationId"] == "competing-priorities" and out["source"] == "keywords"
    assert out["answers"]["title"].startswith("My manager, the VP")
    assert out["answers"]["context"] == TEXT
    assert "Tasks" in out["missing"]
    client_text = client.post("/api/intake", json={"text": "The client wants a new feature added before the release date."}).json()
    assert client_text["situationId"] == "client-change-request"
    assert client_text["answers"]["changeTitle"].startswith("The client wants")


def test_intake_rules(client, make_client):
    assert make_client().post("/api/intake", json={"text": TEXT}).status_code == 401
    signup(client, "r@example.com")
    assert client.post("/api/intake", json={"text": "too short"}).status_code == 400
    assert client.post("/api/intake", json={"text": "x" * 4001}).status_code == 400
    r = client.post("/api/intake", json={"text": TEXT, "useAi": True})
    assert r.status_code == 400 and "privacyAck" in r.json()["fields"]
    # AI asked for but no key on this server: falls back and says so
    out = client.post("/api/intake", json={"text": TEXT, "useAi": True, "privacyAck": True}).json()
    assert out["source"] == "keywords" and "not configured" in out["notes"][0]


def test_ai_values_are_validated_by_code(client, monkeypatch):
    signup(client, "a@example.com")
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")
    seen = {}

    def fake(text, catalog, today):
        seen["ids"] = [c["id"] for c in catalog]
        return {"situationId": "competing-priorities",
                "fields": [{"id": "title", "value": "Three asks, one week"},
                           {"id": "hoursPerWeek", "value": "40 hours"},
                           {"id": "committedHours", "value": "lots"},      # not a number -> dropped
                           {"id": "unknownField", "value": "x"}],           # not in the form -> ignored
                "tasks": [{"name": "VP overview", "effortHours": "6", "deadline": "2026-11-20", "requester": "skip", "impact": "reputation", "note": ""},
                          {"name": "Report", "effortHours": "-3", "deadline": "Friday", "requester": "ceo", "impact": "", "note": ""},
                          {"name": "", "effortHours": "2", "deadline": "", "requester": "", "impact": "", "note": ""}],
                "unclear": ["How many hours does the report take?"]}
    monkeypatch.setattr(llm, "extract_situation", fake)
    out = client.post("/api/intake", json={"text": TEXT, "useAi": True, "privacyAck": True}).json()
    assert seen["ids"] == ["client-change-request", "competing-priorities", "asked-for-a-deadline"]
    assert out["source"] == "ai" and out["situationId"] == "competing-priorities"
    a = out["answers"]
    assert a["title"] == "Three asks, one week" and a["hoursPerWeek"] == 40
    assert "committedHours" not in a and "unknownField" not in a
    assert a["tasks"] == [{"name": "VP overview", "effortHours": 6, "deadline": "2026-11-20", "requester": "skip", "impact": "reputation"},
                          {"name": "Report"}]  # bad effort, bad date, unknown requester dropped; nameless row dropped
    assert any("could not be used" in n for n in out["notes"]) and "How many hours does the report take?" in out["notes"]
    assert a["context"] == TEXT  # the user's own words are kept as background


def test_ai_failure_and_daily_limit_fall_back(client, monkeypatch):
    signup(client, "f@example.com")
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")

    def broken(*a):
        raise llm.LlmError("connection")
    monkeypatch.setattr(llm, "extract_situation", broken)
    out = client.post("/api/intake", json={"text": TEXT, "useAi": True, "privacyAck": True}).json()
    assert out["source"] == "keywords" and "unavailable" in out["notes"][0]

    monkeypatch.setattr(llm, "extract_situation", lambda *a: {"situationId": "client-change-request", "fields": [], "tasks": [], "unclear": []})
    monkeypatch.setattr(intake_router, "AI_PER_DAY", 2)
    sources = [client.post("/api/intake", json={"text": TEXT, "useAi": True, "privacyAck": True}).json()["source"] for _ in range(2)]
    assert sources == ["ai", "keywords"]  # the failed call above counted too


def test_sanitize_never_passes_invalid_select_or_date():
    sit = next(s for s in intake.packs.situations if s["id"] == "client-change-request")
    a, filled, rejected = intake.sanitize(sit, {"priority": "critical", "releaseDate": "2026-02-30", "teamSize": "6 people",
                                               "dailyRate": "$600", "budgetRemaining": "40k", "clientCoversPct": "50%"})
    assert a == {"dailyRate": 600, "budgetRemaining": 40000, "clientCoversPct": 50}
    assert set(filled) == {"dailyRate", "budgetRemaining", "clientCoversPct"} and len(rejected) == 3


def test_llm_request_shape_and_refusal(monkeypatch):
    """Runs the real SDK against a fake HTTP transport: checks what we send and how the reply is read."""
    import json as _json

    import anthropic
    import httpx2 as httpx  # the SDK's own HTTP client package
    sent = {}
    reply = {"stop_reason": "end_turn", "text": _json.dumps({"situationId": "competing-priorities", "fields": [], "tasks": [], "unclear": []})}

    def handler(req):
        sent["body"] = _json.loads(req.content)
        sent["beta"] = req.headers.get("anthropic-beta", "")
        return httpx.Response(200, json={
            "id": "msg_1", "type": "message", "role": "assistant", "model": sent["body"]["model"],
            "content": [{"type": "text", "text": reply["text"]}], "stop_reason": reply["stop_reason"],
            "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1}})
    monkeypatch.setattr(llm, "_client", lambda: anthropic.Anthropic(api_key="k", http_client=httpx.Client(transport=httpx.MockTransport(handler))))
    out = llm.extract_situation("My manager and a colleague both need things by Friday.", intake.catalog(), "2026-11-16")
    assert out["situationId"] == "competing-priorities"
    b = sent["body"]
    assert b["model"] == config.LLM_MODEL and b["fallbacks"] == "default" and "server-side-fallback" in sent["beta"]
    assert b["output_config"]["format"]["schema"]["properties"]["situationId"]["enum"] == ["client-change-request", "competing-priorities", "asked-for-a-deadline"]
    assert "<description>" in b["messages"][0]["content"]
    reply.update(stop_reason="refusal", text="")
    try:
        llm.extract_situation("My manager and a colleague both need things by Friday.", intake.catalog(), "2026-11-16")
        assert False, "refusal must raise"
    except llm.LlmError as e:
        assert str(e) == "refusal"
