from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class OpenAICompatClient:
    """
    Minimal OpenAI-compatible Chat Completions client using stdlib urllib.

    Designed to work with LM Studio local server (OpenAI API compatible).
    """

    def __init__(self, base_url: str, api_key: str, timeout_s: int = 90):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_s = int(timeout_s)

    def get_models(self, timeout_s: int = 3) -> Dict[str, Any]:
        """
        Best-effort check used to detect whether a local OpenAI-compatible server is running.
        """
        url = f"{self.base_url}/models"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = Request(url=url, headers=headers, method="GET")
        with urlopen(req, timeout=int(timeout_s)) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
        return json.loads(body)

    def is_available(self, timeout_s: int = 3) -> bool:
        try:
            self.get_models(timeout_s=timeout_s)
            return True
        except Exception:
            return False

    def chat_completions(
        self,
        *,
        model: str,
        messages: List[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 900,
        response_format: Optional[Dict[str, Any]] = None,
        retries: int = 2,
    ) -> str:
        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
        }
        if response_format is not None:
            payload["response_format"] = response_format

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        last_err: Exception | None = None
        for attempt in range(retries + 1):
            try:
                req = Request(url=url, data=data, headers=headers, method="POST")
                with urlopen(req, timeout=self.timeout_s) as resp:
                    body = resp.read().decode("utf-8", errors="ignore")
                out = json.loads(body)
                # OpenAI style: choices[0].message.content
                return str(out["choices"][0]["message"]["content"])
            except (HTTPError, URLError, TimeoutError, KeyError, ValueError) as e:
                last_err = e
                if attempt < retries:
                    time.sleep(0.4 * (attempt + 1))
                    continue
                raise
        raise RuntimeError(str(last_err) if last_err else "LLM request failed")
