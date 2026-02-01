import pytest
import time as time_module

from app.services.nlu import NLU, NLUCache, _FALLBACK


class StubLLM:
    """Minimal stand-in for LLMClient.  Set .response before each call."""

    def __init__(self, response: str = ""):
        self.response = response
        self.call_count = 0

    async def call(self, prompt: str, **kwargs) -> str:
        self.call_count += 1
        return self.response


class TestNLUCache:
    def test_get_returns_none_on_miss(self):
        cache = NLUCache(ttl=5)
        assert cache.get("unknown") is None

    def test_set_then_get(self):
        cache = NLUCache(ttl=5)
        cache.set("hello", {"intent": "chit_chat"})
        assert cache.get("hello") == {"intent": "chit_chat"}

    def test_normalises_key(self):
        cache = NLUCache(ttl=5)
        cache.set("  Hello  ", {"intent": "chit_chat"})
        assert cache.get("hello") == {"intent": "chit_chat"}

    def test_expired_entry_returns_none(self):
        cache = NLUCache(ttl=0)  # TTL = 0 → expires immediately
        cache.set("hi", {"intent": "chit_chat"})
        time_module.sleep(0.05)
        assert cache.get("hi") is None


@pytest.mark.asyncio
class TestNLU:
    async def test_valid_json_response(self):
        llm = StubLLM(
            '{"intent":"set_reminder","medication":"Аспирин","times":"09:00"}'
        )
        nlu = NLU(llm=llm, cache=NLUCache(ttl=0))
        result = await nlu.understand("напоминай аспирин в 9 утра")
        assert result["intent"] == "set_reminder"
        assert "Аспирин" in result["medication"]
        assert "09:00" in result["times"]

    async def test_fallback_on_invalid_json(self):
        llm = StubLLM("this is not json at all")
        nlu = NLU(llm=llm, cache=NLUCache(ttl=0))
        result = await nlu.understand("что-то непонятное")
        assert result == _FALLBACK

    async def test_fallback_when_intent_missing(self):
        llm = StubLLM('{"medication":"test"}')
        nlu = NLU(llm=llm, cache=NLUCache(ttl=0))
        result = await nlu.understand("без интента")
        assert result["intent"] == "chit_chat"

    async def test_strips_json_code_fence(self):
        llm = StubLLM('```json\n{"intent":"summarize","medication":"","times":""}\n```')
        nlu = NLU(llm=llm, cache=NLUCache(ttl=0))
        result = await nlu.understand("дай отчёт")
        assert result["intent"] == "summarize"

    async def test_cache_prevents_second_llm_call(self):
        llm = StubLLM('{"intent":"chit_chat","medication":"","times":""}')
        cache = NLUCache(ttl=60)
        nlu = NLU(llm=llm, cache=cache)

        await nlu.understand("привет")
        assert llm.call_count == 1

        await nlu.understand("привет")
        assert llm.call_count == 1

    async def test_llm_exception_returns_fallback(self):
        class BrokenLLM:
            async def call(self, *a, **kw):
                raise RuntimeError("network error")

        nlu = NLU(llm=BrokenLLM(), cache=NLUCache(ttl=0))
        result = await nlu.understand("anything")
        assert result == _FALLBACK
