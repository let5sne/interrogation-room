import llm_client as lc


class _FakeStream:
    """模拟 httpx 的 stream() 上下文管理器。"""
    def __init__(self, lines):
        self._lines = lines

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        pass

    def iter_lines(self):
        for ln in self._lines:
            yield ln


def test_stream_parses_sse(monkeypatch):
    # 模拟 OpenAI 兼容的 SSE 流
    sse = [
        'data: {"choices":[{"delta":{"content":"你"}}]}',
        'data: {"choices":[{"delta":{"content":"说"}}]}',
        'data: {"choices":[{"delta":{"content":"什么"}}]}',
        'data: [DONE]',
    ]

    # 注意：llm_client 使用 httpx.Client(...).stream("POST", ...)，故 mock stream 而非 post
    def fake_stream(self, method, url, **kwargs):
        return _FakeStream(sse)

    monkeypatch.setattr(lc.httpx.Client, "stream", fake_stream)
    client = lc.LLMClient(api_key="x", base_url="http://test", model="m")
    out = "".join(client.stream([{"role": "user", "content": "hi"}]))
    assert out == "你说什么"