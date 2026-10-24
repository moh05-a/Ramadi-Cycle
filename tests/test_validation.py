import http.server
import json
import logging
import threading

import pytest
from hypothesis import given, settings
from hypothesis import strategies as hs

import ramadi as r
from conftest import PROFILE


@pytest.fixture
def cat(tables):
    return tables.catalog


@pytest.fixture
def pl(tables):
    return tables.plants


def plan(lang="en", budget="low", **overrides):
    p = r.template_blueprint(PROFILE, budget, lang).model_dump()
    p.update(overrides)
    return p


def check(raw, tables, budget="low", lang="en", cap=None):
    if not isinstance(raw, str):
        raw = json.dumps(raw, ensure_ascii=False)
    return r.validate(raw, tables.catalog, tables.plants, budget, lang, cap)


def code(raw, tables, **kw):
    bp, why = check(raw, tables, **kw)
    assert bp is None, "expected a rejection"
    return why.code


# ---------------------------------------------------------------- one test per rejection code

@pytest.mark.parametrize("raw", ["", "   ", "<think>I will answer in JSON.</think>", "```json\n```"])
def test_empty_response(raw, tables):
    assert code(raw, tables) == r.EMPTY_RESPONSE


@pytest.mark.parametrize("raw", ["Sure! Here is your plan: buy a tank.", "{'language': 'en'}", '{"language": "en"'])
def test_not_json(raw, tables):
    assert code(raw, tables) == r.NOT_JSON


@pytest.mark.parametrize("bad", [
    {"summary": None}, {"greywater_steps": []}, {"rainwater_steps": "one step"}, {"language": "fr"},
    {"warnings": ["extra field"]}, {"plants": [{"plant_id": "olive", "reason": "x", "dose": 1}]},
    {"materials": [{"item_id": "drip_kit", "quantity": 1, "reason": "x" * 201}]},
])
def test_schema_mismatch(bad, tables):
    assert code(plan(**bad), tables) == r.SCHEMA


def test_extra_top_level_field_rejected(tables):
    assert code({**plan(), "price_total": 5}, tables) == r.SCHEMA


@pytest.mark.parametrize("qty", [0, 51, -1, 2.5, 3.0, "3", True, None])
def test_bad_quantity(qty, tables):
    assert code(plan(materials=[{"item_id": "drip_kit", "quantity": qty, "reason": "x"}]), tables) == r.BAD_QUANTITY


@pytest.mark.parametrize("qty", [1, 50])
def test_quantity_bounds_accepted(qty, tables):
    bp, why = check(plan(materials=[{"item_id": "gutter_pvc", "quantity": qty, "reason": "x"}]), tables)
    assert bp and why is None


def test_wrong_language(tables):
    assert code(plan(lang="ar"), tables, lang="en") == r.WRONG_LANGUAGE


def test_unknown_item(tables):
    assert code(plan(materials=[{"item_id": "gold_tap", "quantity": 1, "reason": "x"}]), tables) == r.UNKNOWN_ITEM


@pytest.mark.parametrize("item", ["transfer_pump", "float_switch", "tank_2m3"])
def test_item_over_budget(item, tables):
    assert code(plan(materials=[{"item_id": item, "quantity": 1, "reason": "x"}]), tables) == r.ITEM_OVER_BUDGET


def test_bom_over_budget(tables):
    raw = plan(materials=[{"item_id": "tank_1m3", "quantity": 3, "reason": "x"}])
    assert code(raw, tables, cap=100) == r.BOM_OVER_BUDGET
    bp, _ = check(raw, tables, cap=1000)
    assert bp is not None


def test_bom_cap_counts_required_items(tables, a):
    raw = plan(materials=[{"item_id": "tank_1m3", "quantity": 1, "reason": "x"}])  # 90 + 15 + 3 added
    assert code(raw, tables, cap=100) == r.BOM_OVER_BUDGET
    assert r.budget_cap(a, "low") is None  # no cap configured in assumptions.csv yet


def test_unknown_plant(tables):
    assert code(plan(plants=[{"plant_id": "baobab", "reason": "x"}]), tables) == r.UNKNOWN_PLANT


def test_every_raw_eaten_plant_rejected(tables):
    unsafe = tables.plants.loc[~tables.plants["greywater_ok"], "plant_id"].tolist()
    assert unsafe
    for pid in unsafe:
        assert code(plan(plants=[{"plant_id": pid, "reason": "x"}]), tables) == r.PLANT_NOT_GREYWATER_SAFE


# ---------------------------------------------------------------- banned terms

def put(text, field):
    """A plan with text placed in one free-text field."""
    if field == "summary":
        return plan(summary=text)
    if field in ("greywater_steps", "rainwater_steps"):
        return plan(**{field: [text]})
    if field == "material_reason":
        return plan(materials=[{"item_id": "drip_kit", "quantity": 1, "reason": text}])
    return plan(plants=[{"plant_id": "olive", "reason": text}])


FIELDS = ["summary", "greywater_steps", "rainwater_steps", "material_reason", "plant_reason"]


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("term", r.BANNED_TERMS)
def test_every_banned_term_in_every_field(term, field, tables):
    assert code(put(f"Then {term} here.", field), tables) == r.BANNED_TERM


@pytest.mark.parametrize("text", [
    "Add bleach weekly to keep it clean.", "Safe for DRINKING after filtering.", "It is undrinkable.",
    "Use non-potable water.", "Do not use toilet-water.", "Route the kitchen sink here.", "Pipe the TOILET\nwater in",
    "dr​ink it", "Send toilet and shower water to trees.", "Add Chlorinated tablets.",
    "يمكن استخدامها للشرب", "يمكن استخدامها لِلشُّرْبِ", "لـلـشـرب", "صالحة للشُرب", "اشرب منها",
    "لا تضف الكلور", "ﻛﻠﻮﺭ", "مياه المِرْحاض", "صِل مَجْلَى المطبخ", "المياه السوداء", "أضف مُبيّض",
    "مواد كيميائية", "مواد كيميأئية", "مياه المراحيض",
])
def test_banned_variants_rejected(text, tables):
    assert code(plan(summary=text), tables) == r.BANNED_TERM


@pytest.mark.parametrize("text", ["Connect the tank outlet to the toilet cisterns.", "Use rain for toilet flushing.",
                                  "صِل الخزان بصناديق طرد المراحيض.", "إكليل الجبل والزيتون"])
def test_allowed_phrases_not_rejected(text, tables):
    bp, why = check(plan(summary=text), tables)
    assert bp and why is None, why


@pytest.mark.parametrize("a_form", ["أ", "إ", "آ", "ٱ", "ا"])
def test_alef_forms_normalise(a_form):
    assert r.normalise(f"{a_form}لكلور") == "الكلور"
    assert r.normalise("مياهُ الشُّرْبِ") == r.normalise("مياه الشرب")
    assert r.normalise("مدرسة") == r.normalise("مدرسه")
    assert r.normalise("مجلى") == r.normalise("مجلي")


def test_banned_list_includes_prd_terms():
    norm = {r.normalise(t) for t in r.BANNED_TERMS}
    for t in ["bleach", "chlorine", "chemical", "drink", "potable", "kitchen", "toilet", "sewage", "شرب", "كلور"]:
        assert r.normalise(t) in norm


# ---------------------------------------------------------------- cleaning model text

def test_think_and_fence_stripped(tables):
    body = json.dumps(plan())
    for raw in [f"<think>\nPlan: drink bleach? no.\n</think>\n{body}", f"```json\n{body}\n```",
                f"<THINK>x</THINK>```\n{body}\n```"]:
        bp, why = check(raw, tables)
        assert bp and why is None, why


def test_unclosed_think_rejected(tables):
    assert code("<think> still thinking " + json.dumps(plan()), tables) == r.NOT_JSON


# ---------------------------------------------------------------- required items (M8)

@pytest.mark.parametrize("lang", ["en", "ar"])
def test_required_items_added_once_in_plan_language(lang, tables):
    bp, _ = check(plan(lang, materials=[{"item_id": "drip_kit", "quantity": 1, "reason": "x"}]), tables, lang=lang)
    ids = [m.item_id for m in bp.materials]
    assert ids.count("first_flush") == ids.count("label_kit") == 1
    assert all(m.reason == r.REQUIRED_REASON[lang] for m in bp.materials if m.item_id in r.REQUIRED_ITEMS)


def test_required_items_not_duplicated(tables):
    mats = [{"item_id": "first_flush", "quantity": 2, "reason": "x"}, {"item_id": "label_kit", "quantity": 1,
                                                                       "reason": "y"}]
    bp, _ = check(plan(materials=mats), tables)
    assert [m.item_id for m in bp.materials] == ["first_flush", "label_kit"]
    assert bp.materials[0].quantity == 2


# ---------------------------------------------------------------- template plan

@settings(max_examples=60, deadline=None)
@given(roof=hs.floats(0, 2000), people=hs.integers(0, 30), budget=hs.sampled_from(r.BUDGETS),
       lang=hs.sampled_from(["en", "ar"]))
def test_template_passes_validator(roof, people, budget, lang, tables):
    profile = {**PROFILE, "roof_m2": roof, "people": people}
    tpl = r.template_blueprint(profile, budget, lang)
    bp, why = r.validate(tpl.model_dump_json(), tables.catalog, tables.plants, budget, lang)
    assert bp and why is None, why
    assert all(ok for _, ok in r.safety_checks(bp))
    assert [m.item_id for m in bp.materials] == [m.item_id for m in tpl.materials]  # nothing had to be added


# ---------------------------------------------------------------- generate(): retries and fallback (M7, M12)

class Fake:
    def __init__(self, *replies):
        self.replies, self.calls = list(replies), 0

    def __call__(self, model, prompt):
        self.calls += 1
        reply = self.replies[min(self.calls, len(self.replies)) - 1]
        if isinstance(reply, BaseException):
            raise reply
        return reply


def run(fake, tables, a, lang="en", budget="low", model="fake", cap=None):
    res = r.simulate(PROFILE, tables.shares, a)
    return r.generate(PROFILE, res, tables.catalog, tables.plants, budget, lang, model, chat=fake, max_total_jod=cap)


@pytest.mark.parametrize("reply,calls", [
    ("Sure! Here is your plan.", r.MAX_ATTEMPTS),
    ("", r.MAX_ATTEMPTS),
    (None, r.MAX_ATTEMPTS),
    (json.dumps(plan(materials=[{"item_id": "gold_tap", "quantity": 1, "reason": "x"}])), r.MAX_ATTEMPTS),
    (json.dumps(plan(summary="Safe for drinking.")), r.MAX_ATTEMPTS),
    (r.BadResponse("HTTP 500"), r.MAX_ATTEMPTS),
    (ValueError("odd client bug"), r.MAX_ATTEMPTS),
    (ConnectionRefusedError(111, "refused"), 1),
    (TimeoutError("timed out"), 1),
    (r.ModelUnavailable("down"), 1),
    (r.ModelNotFound("not pulled"), 1),
    (r.ModelTimeout("slow"), 1),
])
def test_failures_fall_back_to_template(reply, calls, tables, a):
    fake = Fake(reply)
    gen = run(fake, tables, a)
    assert gen.source == "template" and fake.calls == calls and len(gen.notes) == calls
    assert gen.blueprint == r.template_blueprint(PROFILE, "low", "en")
    notice = r.fallback_notice(gen, "fake")
    assert notice.startswith("Showing the built-in template plan") and "fake" in notice


def test_over_budget_total_falls_back(tables, a):
    fake = Fake(json.dumps(plan()))
    gen = run(fake, tables, a, cap=10)
    assert gen.source == "template" and fake.calls == r.MAX_ATTEMPTS
    assert all(r.BOM_OVER_BUDGET in n for n in gen.notes)


def test_retry_constant_is_three_attempts():
    assert r.MAX_ATTEMPTS == 3


def test_recovers_on_second_attempt(tables, a):
    fake = Fake("prose", "<think>ok</think>" + json.dumps(plan()))
    gen = run(fake, tables, a)
    assert gen.source == "model" and fake.calls == 2 and len(gen.notes) == 1
    assert r.fallback_notice(gen, "fake") is None


def test_no_model_means_no_call(tables, a):
    fake = Fake(json.dumps(plan()))
    gen = run(fake, tables, a, model=None)
    assert gen.source == "template" and fake.calls == 0 and gen.notes == []
    assert "No local model" in r.fallback_notice(gen, None)


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_valid_model_output_used(lang, tables, a):
    gen = run(Fake(json.dumps(plan(lang), ensure_ascii=False)), tables, a, lang=lang)
    assert gen.source == "model" and gen.blueprint.language == lang


def test_rejections_logged_without_user_data(tables, a, caplog):
    caplog.set_level(logging.INFO, logger="ramadi")
    run(Fake(json.dumps(plan(summary="drink it")), ConnectionRefusedError()), tables, a)
    text = caplog.text
    assert r.BANNED_TERM in text and "unavailable" in text
    for private in (PROFILE["governorate"], "drink it", str(PROFILE["roof_m2"])):
        assert private not in text


def test_default_chat_resolved_at_call_time(tables, a, monkeypatch):
    fake = Fake(json.dumps(plan()))
    monkeypatch.setattr(r, "ollama_chat", fake)
    res = r.simulate(PROFILE, tables.shares, a)
    assert r.generate(PROFILE, res, tables.catalog, tables.plants, "low", "en", "m").source == "model"


# ---------------------------------------------------------------- real HTTP client against a local fake Ollama

class FakeOllama(http.server.BaseHTTPRequestHandler):
    status, body, delay, seen = 200, b"", 0.0, []

    def do_POST(self):
        FakeOllama.seen.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
        if FakeOllama.delay:
            threading.Event().wait(FakeOllama.delay)
        self.send_response(FakeOllama.status)
        self.end_headers()
        self.wfile.write(FakeOllama.body)

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"models": [{"name": "fake:1b"}]}).encode())

    def log_message(self, *args):
        pass


@pytest.fixture
def ollama(monkeypatch):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(r, "OLLAMA_URL", f"http://127.0.0.1:{server.server_address[1]}")
    FakeOllama.status, FakeOllama.body, FakeOllama.delay, FakeOllama.seen = 200, b"", 0.0, []
    yield FakeOllama
    server.shutdown()
    server.server_close()


def test_chat_sends_schema_seed_and_returns_content(ollama):
    ollama.body = json.dumps({"message": {"role": "assistant", "content": "hello"}}).encode()
    assert r.ollama_chat("fake:1b", "hi") == "hello"
    sent = ollama.seen[0]
    assert sent["format"] == r.Blueprint.model_json_schema()
    assert sent["format"]["additionalProperties"] is False
    assert sent["options"] == r.MODEL_OPTIONS and "seed" in sent["options"] and "temperature" in sent["options"]
    assert sent["stream"] is False


def test_list_models_reads_local_tags(ollama):
    assert r.list_models() == ["fake:1b"]


@pytest.mark.parametrize("status,body,err", [
    (404, b'{"error":"model not found"}', r.ModelNotFound),
    (500, b"boom", r.BadResponse),
    (200, b"not json", r.BadResponse),
    (200, b'{"done": true}', r.BadResponse),
    (200, b'{"message": {"content": null}}', r.BadResponse),
])
def test_chat_error_types(ollama, status, body, err):
    ollama.status, ollama.body = status, body
    with pytest.raises(err):
        r.ollama_chat("fake:1b", "hi")


def test_chat_timeout(ollama, monkeypatch):
    monkeypatch.setattr(r, "CHAT_TIMEOUT_S", 0.3)
    ollama.delay = 2
    with pytest.raises(r.ModelTimeout):
        r.ollama_chat("fake:1b", "hi")


def test_chat_when_ollama_not_running():
    with pytest.raises(r.ModelUnavailable):
        r.ollama_chat("fake:1b", "hi")  # conftest points OLLAMA_URL at a closed port
    assert r.list_models() == []


def test_generate_end_to_end_over_http(ollama, tables, a):
    ollama.body = json.dumps({"message": {"content": "```json\n" + json.dumps(plan()) + "\n```"}}).encode()
    gen = run(None, tables, a)
    assert gen.source == "model" and len(ollama.seen) == 1


# ---------------------------------------------------------------- Markdown download (M9, M10)

@pytest.mark.parametrize("lang", ["en", "ar"])
def test_markdown_has_warnings_disclaimer_and_direction(lang, tables, a):
    bp = r.template_blueprint(PROFILE, "full", lang)
    md = r.to_markdown(bp, r.price(bp, tables.catalog), PROFILE, r.simulate(PROFILE, tables.shares, a))
    assert r.DISCLAIMER[lang] in md and all(w in md for w in r.WARNINGS[lang])
    other = "ar" if lang == "en" else "en"
    assert r.DISCLAIMER[other] not in md
    assert ('dir="rtl"' in md) == (lang == "ar")
    if lang == "ar":
        assert md.startswith('<div dir="rtl" lang="ar">\n\n') and md.rstrip().endswith("</div>")


def test_price_empty_plan(tables):
    bp = r.Blueprint.model_validate({**plan(), "materials": []})
    bom = r.price(bp, tables.catalog)
    assert list(bom.columns) == r.BOM_COLUMNS and r.plan_cost(bom) == 0
