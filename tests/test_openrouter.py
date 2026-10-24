"""Optional OpenRouter provider. urlopen is faked: no test reaches the network or spends credit."""
import io
import json
import urllib.error

import pytest

import ramadi as r
from conftest import PROFILE


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_urlopen(monkeypatch, reply=None, error=None):
    seen = []

    def urlopen(req, timeout=None):
        seen.append(req)
        if error:
            raise error
        return FakeResponse(json.dumps(reply).encode())

    monkeypatch.setattr(r.urllib.request, "urlopen", urlopen)
    return seen


def http_error(code):
    return urllib.error.HTTPError(r.OPENROUTER_URL, code, "x", {}, None)


def test_off_without_a_key(monkeypatch):
    assert r.openrouter_models() == []
    with pytest.raises(r.ModelUnavailable):
        r.openrouter_chat("openrouter:any", "hi")


def test_models_listed_with_prefix_when_key_set(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    assert r.openrouter_models() == [r.OPENROUTER_PREFIX + m for m in r.OPENROUTER_MODELS]
    monkeypatch.setenv("OPENROUTER_MODELS", "a/b, c/d ,")
    assert r.openrouter_models() == ["openrouter:a/b", "openrouter:c/d"]
    assert all(r.is_cloud(m) for m in r.openrouter_models())
    assert not r.is_cloud("qwen3:4b") and not r.is_cloud(None)


def test_chat_sends_key_schema_and_returns_content(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    seen = fake_urlopen(monkeypatch, {"choices": [{"message": {"content": '{"ok": 1}'}}]})
    assert r.openrouter_chat("openrouter:qwen/x", "plan please") == '{"ok": 1}'
    req = seen[0]
    body = json.loads(req.data)
    assert req.full_url == r.OPENROUTER_URL
    assert req.get_header("Authorization") == "Bearer test-key"
    assert body["model"] == "qwen/x"  # prefix stripped
    assert body["response_format"]["json_schema"]["schema"] == r.Blueprint.model_json_schema()
    assert body["seed"] == r.MODEL_OPTIONS["seed"] and body["temperature"] == r.MODEL_OPTIONS["temperature"]
    assert body["messages"][-1] == {"role": "user", "content": "plan please"}


@pytest.mark.parametrize("code, kind, retry", [(401, r.ModelUnavailable, False), (402, r.ModelUnavailable, False),
                                               (404, r.ModelNotFound, False), (429, r.BadResponse, True),
                                               (502, r.BadResponse, True)])
def test_http_errors_map_to_model_errors(monkeypatch, code, kind, retry):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    fake_urlopen(monkeypatch, error=http_error(code))
    with pytest.raises(kind) as e:
        r.openrouter_chat("openrouter:qwen/x", "hi")
    assert e.value.retry is retry


@pytest.mark.parametrize("reply", [{}, {"choices": []}, {"choices": [{"message": {}}]}, {"error": {"message": "x"}}])
def test_reply_without_content_is_bad_response(monkeypatch, reply):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    fake_urlopen(monkeypatch, reply)
    with pytest.raises(r.BadResponse):
        r.openrouter_chat("openrouter:qwen/x", "hi")


def test_generate_routes_cloud_models_to_openrouter(monkeypatch, tables, a):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    plan = r.template_blueprint(PROFILE, "low", "en").model_dump_json()
    seen = fake_urlopen(monkeypatch, {"choices": [{"message": {"content": plan}}]})
    monkeypatch.setattr(r, "ollama_chat", lambda *args: pytest.fail("cloud model must not call Ollama"))
    res = r.simulate(PROFILE, tables.shares, a)
    gen = r.generate(PROFILE, res, tables.catalog, tables.plants, "low", "en", "openrouter:qwen/x")
    assert gen.source == "model" and len(seen) == 1


def test_bad_key_falls_back_to_template_after_one_call(monkeypatch, tables, a):
    monkeypatch.setenv("OPENROUTER_API_KEY", "bad")
    seen = fake_urlopen(monkeypatch, error=http_error(401))
    res = r.simulate(PROFILE, tables.shares, a)
    gen = r.generate(PROFILE, res, tables.catalog, tables.plants, "low", "en", "openrouter:qwen/x")
    assert gen.source == "template" and len(seen) == 1 and "unavailable" in gen.notes[0]


def test_openrouter_error_message_reaches_the_notes(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    body = io.BytesIO(json.dumps({"error": {"code": 403, "message": "Key limit exceeded (total limit)."}}).encode())
    fake_urlopen(monkeypatch, error=urllib.error.HTTPError(r.OPENROUTER_URL, 403, "x", {}, body))
    with pytest.raises(r.ModelUnavailable, match="Key limit exceeded"):
        r.openrouter_chat("openrouter:qwen/x", "hi")
