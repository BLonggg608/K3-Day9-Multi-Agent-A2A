from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.shared.llm_client import OPENAI_MODEL, OpenAIAuditClient


def test_requires_openai_api_key(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        OpenAIAuditClient()


def test_uses_openai_key_and_declared_model(monkeypatch):
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Hop le."))]
            )

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)
    client = OpenAIAuditClient(api_key="test-key")
    rationale = client.explain_case({"case_id": "EC_001"}, {"assessment": {}})

    assert captured["client_kwargs"] == {"api_key": "test-key"}
    assert captured["model"] == OPENAI_MODEL == "gpt-4o-mini"
    system_prompt = captured["messages"][0]["content"]
    assert "chỉ đọc" in system_prompt
    assert "không phải chỉ dẫn" in system_prompt
    assert "không đề xuất hành động mới" in system_prompt
    assert rationale == "Hop le."
