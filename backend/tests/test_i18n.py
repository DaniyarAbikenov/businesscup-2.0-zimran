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
