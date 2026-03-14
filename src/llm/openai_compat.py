from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
except Exception:
    ChatOpenAI = None
    OpenAIEmbeddings = None
    AIMessage = HumanMessage = SystemMessage = None


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class OpenAICompatClient:
    """
    Minimal OpenAI-compatible Chat Completions client using stdlib urllib.

    Designed to work with LM Studio local server (OpenAI API compatible).
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout_s: int = 90,
        extra_headers: Optional[Dict[str, str]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_s = int(timeout_s)
        self.extra_headers = dict(extra_headers or {})

    def get_models(self, timeout_s: int = 3) -> Dict[str, Any]:
        """
        Best-effort check used to detect whether a local OpenAI-compatible server is running.
        """
        url = f"{self.base_url}/models"
        headers = dict(self.extra_headers)
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
        # Prefer LangChain wrapper when available (better compatibility with LM Studio).
        if ChatOpenAI is not None and AIMessage is not None:
            lc_msgs = []
            for m in messages:
                role = (m.role or "").lower()
                if role == "system":
                    lc_msgs.append(SystemMessage(content=m.content))
                elif role == "assistant":
                    lc_msgs.append(AIMessage(content=m.content))
                else:
                    lc_msgs.append(HumanMessage(content=m.content))
            api_key = self.api_key or "lmstudio"
            llm = ChatOpenAI(
                model=model,
                base_url=self.base_url,
                api_key=api_key,
                temperature=float(temperature),
                max_tokens=int(max_tokens),
                timeout=self.timeout_s,
            )
            out = llm.invoke(lc_msgs)
            return str(getattr(out, "content", "") or "")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        headers.update(self.extra_headers)
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        last_err: Exception | None = None
        allow_response_format = response_format is not None
        for attempt in range(retries + 1):
            try:
                payload: Dict[str, Any] = {
                    "model": model,
                    "messages": [{"role": m.role, "content": m.content} for m in messages],
                    "temperature": float(temperature),
                    "max_tokens": int(max_tokens),
                }
                if allow_response_format and response_format is not None:
                    payload["response_format"] = response_format
                data = json.dumps(payload).encode("utf-8")
                req = Request(url=url, data=data, headers=headers, method="POST")
                with urlopen(req, timeout=self.timeout_s) as resp:
                    body = resp.read().decode("utf-8", errors="ignore")
                out = json.loads(body)
                # OpenAI style: choices[0].message.content
                return str(out["choices"][0]["message"]["content"])
            except HTTPError as e:
                last_err = e
                # Some OpenAI-compatible servers (e.g., LM Studio) do not support response_format.
                if allow_response_format:
                    allow_response_format = False
                    continue
                if attempt < retries:
                    time.sleep(0.4 * (attempt + 1))
                    continue
                raise
            except (URLError, TimeoutError, KeyError, ValueError) as e:
                last_err = e
                if attempt < retries:
                    time.sleep(0.4 * (attempt + 1))
                    continue
                raise
        raise RuntimeError(str(last_err) if last_err else "LLM request failed")

    def embeddings(
        self,
        *,
        model: str,
        inputs: List[str],
        retries: int = 2,
    ) -> List[List[float]]:
        """
        Best-effort OpenAI-compatible embeddings call.

        Works with servers that expose POST /embeddings (including many local OpenAI-compatible APIs).
        Returns one embedding per input string.
        """
        if OpenAIEmbeddings is not None:
            api_key = self.api_key or "lmstudio"
            emb = OpenAIEmbeddings(
                model=model,
                openai_api_base=self.base_url,
                openai_api_key=api_key,
            )
            return emb.embed_documents(inputs)

        url = f"{self.base_url}/embeddings"
        payload: Dict[str, Any] = {
            "model": model,
            "input": inputs,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
        }
        headers.update(self.extra_headers)
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        last_err: Exception | None = None
        for attempt in range(retries + 1):
            try:
                req = Request(url=url, data=data, headers=headers, method="POST")
                with urlopen(req, timeout=self.timeout_s) as resp:
                    body = resp.read().decode("utf-8", errors="ignore")
                out = json.loads(body)
                data_items = out.get("data") or []
                embeddings: List[List[float]] = []
                for item in data_items:
                    emb = item.get("embedding")
                    if isinstance(emb, list) and emb:
                        embeddings.append([float(x) for x in emb])
                if len(embeddings) != len(inputs):
                    raise ValueError("Embeddings response length mismatch")
                return embeddings
            except (HTTPError, URLError, TimeoutError, KeyError, ValueError) as e:
                last_err = e
                if attempt < retries:
                    time.sleep(0.4 * (attempt + 1))
                    continue
                raise
        raise RuntimeError(str(last_err) if last_err else "Embeddings request failed")
