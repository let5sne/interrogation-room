import json
import httpx

from settings import (
    MODELSPACE_API_KEY,
    MODELSPACE_BASE_URL,
    MODELSPACE_MODEL,
)


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key if api_key is not None else MODELSPACE_API_KEY
        self.base_url = base_url if base_url is not None else MODELSPACE_BASE_URL
        self.model = model if model is not None else MODELSPACE_MODEL

    def stream(self, messages, temperature: float = 0.8, timeout: float = 60.0):
        """流式对话。yield 增量文本片段。失败重试 1 次。"""
        url = self.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        last_err = None
        for attempt in range(2):
            try:
                with httpx.Client(timeout=timeout) as c:
                    with c.stream("POST", url, headers=headers, json=payload) as resp:
                        resp.raise_for_status()
                        for line in resp.iter_lines():
                            if not line or not line.startswith("data:"):
                                continue
                            data = line[len("data:"):].strip()
                            if data == "[DONE]":
                                break
                            try:
                                obj = json.loads(data)
                                delta = obj["choices"][0]["delta"].get("content")
                                if delta:
                                    yield delta
                            except (json.JSONDecodeError, KeyError, IndexError):
                                continue
                return
            except Exception as e:  # noqa: BLE001
                last_err = e
                continue
        raise LLMError(f"LLM request failed after retries: {last_err}")