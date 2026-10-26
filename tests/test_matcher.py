import asyncio
import json
from types import SimpleNamespace

from src.matcher import find_matching_series
from src.models import Series


class _FakeMessages:
    def __init__(self, response):
        self._response = response
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


def _fake_client(response):
    return SimpleNamespace(beta=SimpleNamespace(messages=_FakeMessages(response)))


def _text_response(payload: dict, stop_reason: str = "end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="text", text=json.dumps(payload))],
    )


_SERIES = [
    Series(series_id="s1", title="架空の冒険", author="山田太郎"),
    Series(series_id="s2", title="サンプル殺人事件", author="鈴木花子"),
]


def test_returns_matched_series_and_drops_unknown_ids():
    client = _fake_client(
        _text_response({"matches": ["s2", "s999"], "reasoning": "ミステリーなので"})
    )

    matches, reasoning = asyncio.run(find_matching_series(client, "推理小説", _SERIES))

    assert [s.series_id for s in matches] == ["s2"]
    assert reasoning == "ミステリーなので"


def test_sends_catalog_with_cache_control():
    client = _fake_client(_text_response({"matches": [], "reasoning": ""}))

    asyncio.run(find_matching_series(client, "何か", _SERIES))

    [call] = client.beta.messages.calls
    catalog = call["system"][1]
    assert catalog["cache_control"] == {"type": "ephemeral"}
    assert "s1\t架空の冒険\t山田太郎\t0冊" in catalog["text"]
    assert call["messages"] == [{"role": "user", "content": "何か"}]


def test_refusal_returns_no_matches():
    client = _fake_client(SimpleNamespace(stop_reason="refusal", content=[]))

    assert asyncio.run(find_matching_series(client, "何か", _SERIES)) == ([], None)


def test_empty_catalog_skips_api_call():
    client = _fake_client(None)

    assert asyncio.run(find_matching_series(client, "何か", [])) == ([], None)
    assert client.beta.messages.calls == []
