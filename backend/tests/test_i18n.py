"""Languages: overlays only reference existing ids, placeholders match, packs follow the language, fallback to English."""
import re

import pytest

from app import i18n, packs
from test_api import signup

PH = re.compile(r"\{\w+\}")


def _walk_sit(sit, ov, where):
    ids = {q["id"] for q in sit["questions"]}
    assert set(ov.get("questions", {})) <= ids, where
    for qid, qo in ov.get("questions", {}).items():
        q = next(x for x in sit["questions"] if x["id"] == qid)
        assert set(qo.get("options", {})) <= {o["value"] for o in q.get("options", [])}, (where, qid)
        assert set(qo.get("fields", {})) <= {f["id"] for f in q.get("fields", [])}, (where, qid)
        if "labelTemplate" in qo:
            assert sorted(PH.findall(qo["labelTemplate"])) == sorted(PH.findall(q["labelFrom"]["template"])), (where, qid)
    assert set(ov.get("options", {})) <= set(sit["options"]), where
    for k, o in ov.get("options", {}).items():
        assert len(o["nextSteps"]) == len(sit["options"][k]["nextSteps"]), (where, k)
    assert set(ov.get("groups", {})) <= {g["id"] for g in sit.get("groups", [])}, where
    assert set(ov.get("storylines", {})) <= {s["id"] for s in sit.get("storylines", [])}, where
    assert set(ov.get("reflectionPrompts", {})) <= {p["id"] for p in sit["reflectionPrompts"]}, where
    if ov.get("pitfalls"):
        assert len(ov["pitfalls"]) == len(sit["pitfalls"]), where


@pytest.mark.parametrize("lang", ["ru"])
def test_overlay_references_only_existing_ids(lang):
    ov = i18n.overlay(lang)
    assert set(ov["situations"]) == {s["id"] for s in packs.situations}  # every situation has its translation
    for sid, o in ov["situations"].items():
        _walk_sit(packs.get_situation(sid), o, sid)
    assert set(ov["roles"]) == {r["id"] for r in packs.roles_pack["roles"]}
    assert set(ov["fears"]) == {f["id"] for f in packs.roles_pack["fears"]}
    assert set(ov["tenures"]) == {t["id"] for t in packs.roles_pack["tenures"]}


def test_localized_pack_is_cyrillic_and_english_is_untouched():
    ru = packs.public_pack(lang="ru")
    en = packs.public_pack(lang="en")
    sit_ru = next(s for s in ru["situations"] if s["id"] == "competing-priorities")
    sit_en = next(s for s in en["situations"] if s["id"] == "competing-priorities")
    assert re.search("[А-Яа-я]", sit_ru["title"]) and sit_en["title"].startswith("Several urgent asks")
    assert re.search("[А-Яа-я]", sit_ru["options"]["deadline"]["nextSteps"][0]) and re.search("[А-Яа-я]", ru["roles"][0]["label"])
    # ids, types, numbers and keys are never translated
    assert [q["id"] for q in sit_ru["questions"]] == [q["id"] for q in sit_en["questions"]] and sit_ru["engine"] == sit_en["engine"]
    assert [o["value"] for o in sit_ru["questions"][2]["fields"][4]["options"]] == [o["value"] for o in sit_en["questions"][2]["fields"][4]["options"]]
    # an unknown language falls back to English; a situation without an overlay stays as it is
    assert packs.public_pack(lang="xx")["situations"][0]["title"] == en["situations"][0]["title"]
    custom = {**sit_en, "id": "my-x", "title": "My own"}
    assert i18n.localize_situation(custom, "ru")["title"] == "My own"


def test_api_follows_language(client):
    signup(client, "lang@example.com")
    assert client.put("/api/profile", json={"roleId": "promoted-to-lead", "industry": "", "tenure": "1-3m", "fears": []}).status_code == 200
    en = client.get("/api/packs").json()
    ru = client.get("/api/packs?lang=ru").json()
    assert ru != en and re.search("[А-Яа-я]", ru["situations"][0]["title"]) and not re.search("[А-Яа-я]", en["situations"][0]["title"])
    assert re.search("[А-Яа-я]", client.get("/api/packs", headers={"x-lang": "ru"}).json()["fears"][0]["label"])
    assert client.put("/api/profile/language", json={"language": "xx"}).status_code == 400
    assert client.put("/api/profile/language", json={"language": "ru"}).json() == {"language": "ru"}
    assert client.get("/api/me").json()["profile"]["language"] == "ru"
    assert re.search("[А-Яа-я]", client.get("/api/packs").json()["situations"][0]["title"])  # the saved choice applies without a header
    assert not re.search("[А-Яа-я]", client.get("/api/packs?lang=en").json()["situations"][0]["title"])  # an explicit choice wins
    assert client.put("/api/profile/language", json={"language": None}).json() == {"language": None}
    assert i18n.resolve(None, None) == "en"


def test_accept_language_for_public_resolution():
    class R:
        query_params = {}
        headers = {"accept-language": "ru-RU,ru;q=0.9,en;q=0.8"}
    assert i18n.resolve(R()) == "ru"
    R.headers = {"accept-language": "de-DE,fr;q=0.8,kk;q=0.5"}
    assert i18n.resolve(R()) == "kk"


def _server_keys():
    import ast
    import glob
    keys = set()
    for f in glob.glob("app/**/*.py", recursive=True):
        for n in ast.walk(ast.parse(open(f).read())):
            if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "tr" and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
                keys.add(n.args[0].value)
    return keys


def test_server_texts_have_russian_with_matching_placeholders():
    from app import msg
    table = msg.table("ru")
    skip = {"options.{r}.s{v}"}  # a field key, not a text
    missing = [k for k in _server_keys() if k not in table and k not in skip and re.search(r"[A-Za-z]{4}", k) and "user=%s" not in k]
    assert not missing, missing[:10]
    for en, ru in table.items():
        assert set(PH.findall(ru)) <= set(PH.findall(en)) | {"{sfx}", "{s}"}, (en, ru)  # a translation may drop {sfx} but never invent a placeholder
        assert set(PH.findall(en)) - set(PH.findall(ru)) <= {"{sfx}", "{s}"}, (en, ru)


def test_engine_outputs_and_documents_follow_the_language(client):
    signup(client, "ru-doc@example.com")
    client.put("/api/profile", json={"roleId": "promoted-to-lead", "industry": "", "tenure": "1-3m", "fears": []})
    body = {"situationId": "competing-priorities", "privacyAck": True, "confidenceBefore": 3, "inputs": {
        "title": "Три просьбы", "context": "", "hoursPerWeek": 40, "committedHours": 15,
        "tasks": [{"name": "Отчёт", "effortHours": 14, "deadline": "2030-01-23", "requester": "manager", "impact": "reputation", "note": ""},
                  {"name": "Данные", "effortHours": 6, "deadline": "2030-01-18", "requester": "peer", "impact": "money", "note": ""}]}}
    en = client.post("/api/cases", json=body).json()["case"]
    ru = client.post("/api/cases", json=body, headers={"x-lang": "ru"}).json()["case"]
    assert not re.search("[А-Яа-я]", en["result"]["assumptions"]) and re.search("[А-Яа-я]", ru["result"]["assumptions"])
    assert re.search("[А-Яа-я]", ru["result"]["options"][0]["label"]) and ru["result"]["options"][0]["key"] == "deadline"
    done = client.post(f"/api/cases/{ru['id']}/decision", json={"option": "deadline", "rationale": "x"}, headers={"x-lang": "ru"}).json()["case"]
    assert done["document"].startswith("# Предложение по приоритетам: Три просьбы") and "Почему этот порядок" in done["document"]
    assert "Earliest deadline first" not in done["document"] and re.search("[А-Яа-я]", done["debrief"]["points"][0])
    # errors and field messages are localized too, with the same status and field ids
    bad = client.post("/api/cases", json={**body, "inputs": {**body["inputs"], "hoursPerWeek": "abc"}}, headers={"x-lang": "ru"})
    assert bad.status_code == 400 and bad.json()["error"] == "Проверьте выделенные поля" and bad.json()["fields"]["hoursPerWeek"] == "Введите число"


def test_emails_follow_the_profile_language(client):
    import json
    from sqlalchemy import text as sql

    from app import emails
    from app.cache import get_redis
    from app.db import SessionLocal, engine
    signup(client, "ru-mail@example.com")
    client.put("/api/profile", json={"roleId": "director", "industry": "", "tenure": "1-3m", "fears": []})
    client.put("/api/profile/language", json={"language": "ru"})
    client.post("/api/progress/reminders", json={"enabled": True})
    body = {"situationId": "competing-priorities", "privacyAck": True, "confidenceBefore": 3, "inputs": {
        "title": "Заявки", "context": "СЕКРЕТ", "hoursPerWeek": 40, "committedHours": 15,
        "tasks": [{"name": "А", "effortHours": 14, "deadline": "2030-01-23", "requester": "manager", "impact": "reputation", "note": ""},
                  {"name": "Б", "effortHours": 6, "deadline": "2030-01-18", "requester": "peer", "impact": "money", "note": ""}]}}
    cid = client.post("/api/cases", json=body).json()["case"]["id"]
    client.post(f"/api/cases/{cid}/decision", json={"option": "deadline", "rationale": "x"})
    with engine.begin() as conn:
        conn.execute(sql("UPDATE decisions SET followup_due = CURRENT_DATE - 1"))
    with SessionLocal() as db:
        assert emails.send_due_followups(db, get_redis()) == 1
    mail = json.loads(get_redis().lrange("outbox", 0, 0)[0])
    assert "Как всё прошло" in mail["subject"] and "Сработало" in mail["body"] and f"/case/{cid}" in mail["body"] and "СЕКРЕТ" not in mail["body"]
