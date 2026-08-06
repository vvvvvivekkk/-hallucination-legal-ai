from __future__ import annotations

import asyncio
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable

import httpx

from ..core.exceptions import LegalAIError
from ..core.logger import get_logger

PROVIDERS = {"claude", "openai", "gemini", "llama", "mock"}


class LLMError(LegalAIError):
    status_code = 502
    code = "llm_error"


@dataclass
class LLMConfig:
    provider: str = "mock"
    model: str = "gpt-4o-mini"
    base_url: str | None = None
    api_key: str | None = None
    temperature: float = 0.2
    max_tokens: int = 1024
    timeout_seconds: int = 120
    max_retries: int = 3
    mock_response: str = ""
    json_instruction: bool = True


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    raw: Any = None


def extract_json(text: str | None) -> dict[str, Any] | None:
    """Extract the first balanced JSON object from free-form LLM output."""
    if not text:
        return None
    candidate = text.strip()
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    fenced = re.search(r"```(?:json)?\s*(.*?)```", candidate, re.DOTALL)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1).strip())
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    start = candidate.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(candidate)):
            char = candidate[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
            elif char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    try:
                        parsed = json.loads(candidate[start : index + 1])
                        if isinstance(parsed, dict):
                            return parsed
                    except (json.JSONDecodeError, TypeError):
                        pass
                    break
        start = candidate.find("{", start + 1)
    return None


class SSEParser:
    """Line-based SSE parser for streaming LLM responses."""

    def __init__(self) -> None:
        self._event = "message"
        self._data: list[str] = []

    def push_line(self, line: str) -> list[tuple[str, str]]:
        if line == "":
            if self._data:
                events = [(self._event, "\n".join(self._data))]
                self._event = "message"
                self._data = []
                return events
            return []
        if line.startswith(":"):
            return []
        if line.startswith("event:"):
            self._event = line[len("event:") :].strip()
        elif line.startswith("data:"):
            self._data.append(line[len("data:") :].lstrip())
        return []

    def flush(self) -> list[tuple[str, str]]:
        if self._data:
            events = [(self._event, "\n".join(self._data))]
            self._event = "message"
            self._data = []
            return events
        return []


class LLMAdapter(ABC):
    def __init__(self, config: LLMConfig, logger: object | None = None) -> None:
        self._config = config
        self._logger = logger or get_logger(self.__class__.__name__)

    @property
    def provider(self) -> str:
        return self._config.provider

    @property
    def model(self) -> str:
        return self._config.model

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
        **kwargs: Any,
    ) -> LLMResponse: ...

    @abstractmethod
    def stream(
        self,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
        **kwargs: Any,
    ) -> AsyncIterator[str]: ...


class MockLLM(LLMAdapter):
    def __init__(self, config: LLMConfig, logger: object | None = None) -> None:
        super().__init__(config, logger)
        self._handler: Callable[[str, str | None, bool], str] | None = None
        self._seen_prompts: list[str] = []

    def set_handler(
        self,
        handler: Callable[[str, str | None, bool], str] | None,
    ) -> None:
        self._handler = handler

    @property
    def seen_prompts(self) -> list[str]:
        return list(self._seen_prompts)

    def _answer(self, prompt: str, system: str | None, json_mode: bool) -> str:
        if self._handler is not None:
            return self._handler(prompt, system, json_mode)
        return self._config.mock_response

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        self._seen_prompts.append(prompt)
        text = self._answer(prompt, system, json_mode)
        return LLMResponse(text=text, provider="mock", model=self._config.model)

    async def stream(
        self,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        self._seen_prompts.append(prompt)
        text = self._answer(prompt, system, json_mode)
        for index in range(0, len(text), 5):
            yield text[index : index + 5]
            await asyncio.sleep(0)


class OpenAICompatibleAdapter(LLMAdapter):
    """OpenAI Chat Completions protocol, also used by local Llama servers
    (llama.cpp, Ollama, vLLM) that expose a compatible endpoint."""

    def __init__(self, config: LLMConfig, logger: object | None = None) -> None:
        super().__init__(config, logger)
        self._base_url = (config.base_url or "https://api.openai.com/v1").rstrip("/")

    def _endpoint(self) -> str:
        return f"{self._base_url}/chat/completions"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        return headers

    def _payload(
        self,
        prompt: str,
        system: str | None,
        json_mode: bool,
        stream: bool,
    ) -> dict[str, Any]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body: dict[str, Any] = {
            "model": self._config.model,
            "messages": messages,
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
            "stream": stream,
        }
        if json_mode and self._config.json_instruction:
            body["response_format"] = {"type": "json_object"}
        return body

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        payload = self._payload(prompt, system, json_mode, stream=False)
        async with httpx.AsyncClient(timeout=self._config.timeout_seconds) as client:
            response = await self._post(client, payload)
            response.raise_for_status()
            data = response.json()
        choices = data.get("choices") or []
        text = (choices[0].get("message") or {}).get("content") or "" if choices else ""
        return LLMResponse(text=text, provider=self.provider, model=self.model, raw=data)

    async def stream(
        self,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        payload = self._payload(prompt, system, json_mode, stream=True)
        async with httpx.AsyncClient(timeout=self._config.timeout_seconds) as client:
            async with client.stream(
                "POST", self._endpoint(), json=payload, headers=self._headers()
            ) as response:
                if response.status_code >= 400:
                    body = await response.aread()
                    raise LLMError(
                        f"LLM request failed with status {response.status_code}",
                        details=body.decode("utf-8", errors="replace")[:2000],
                    )
                parser = SSEParser()
                async for line in response.aiter_lines():
                    for event, data in parser.push_line(line):
                        if data == "[DONE]":
                            return
                        obj = _parse_sse_json(event, data)
                        delta = (
                            (obj.get("choices") or [{}])[0].get("delta") or {}
                        ).get("content")
                        if delta:
                            yield delta
                for event, data in parser.flush():
                    if data == "[DONE]":
                        return
                    obj = _parse_sse_json(event, data)
                    delta = (
                        (obj.get("choices") or [{}])[0].get("delta") or {}
                    ).get("content")
                    if delta:
                        yield delta

    async def _post(self, client: httpx.AsyncClient, payload: dict[str, Any]) -> httpx.Response:
        try:
            return await client.post(
                self._endpoint(), json=payload, headers=self._headers()
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM request failed: {exc}", cause=exc)


class ClaudeAdapter(LLMAdapter):
    """Anthropic Messages API."""

    def __init__(self, config: LLMConfig, logger: object | None = None) -> None:
        super().__init__(config, logger)
        self._base_url = (config.base_url or "https://api.anthropic.com").rstrip("/")

    def _endpoint(self) -> str:
        return f"{self._base_url}/v1/messages"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if self._config.api_key:
            headers["x-api-key"] = self._config.api_key
        return headers

    def _payload(
        self,
        prompt: str,
        system: str | None,
        stream: bool,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self._config.model,
            "max_tokens": self._config.max_tokens,
            "temperature": self._config.temperature,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream,
        }
        if system:
            body["system"] = system
        return body

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        payload = self._payload(prompt, system, stream=False)
        async with httpx.AsyncClient(timeout=self._config.timeout_seconds) as client:
            response = await client.post(
                self._endpoint(), json=payload, headers=self._headers()
            )
            if response.status_code >= 400:
                raise LLMError(
                    f"LLM request failed with status {response.status_code}",
                    details=response.text[:2000],
                )
            data = response.json()
        content = data.get("content") or []
        text = "".join(block.get("text", "") for block in content if block.get("type") == "text")
        return LLMResponse(text=text, provider=self.provider, model=self.model, raw=data)

    async def stream(
        self,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        payload = self._payload(prompt, system, stream=True)
        async with httpx.AsyncClient(timeout=self._config.timeout_seconds) as client:
            async with client.stream(
                "POST", self._endpoint(), json=payload, headers=self._headers()
            ) as response:
                if response.status_code >= 400:
                    body = await response.aread()
                    raise LLMError(
                        f"LLM request failed with status {response.status_code}",
                        details=body.decode("utf-8", errors="replace")[:2000],
                    )
                parser = SSEParser()
                async for line in response.aiter_lines():
                    for event, data in parser.push_line(line):
                        obj = _parse_sse_json(event, data)
                        if obj.get("type") == "content_block_delta":
                            delta = (obj.get("delta") or {}).get("text")
                            if delta:
                                yield delta
                for event, data in parser.flush():
                    obj = _parse_sse_json(event, data)
                    if obj.get("type") == "content_block_delta":
                        delta = (obj.get("delta") or {}).get("text")
                        if delta:
                            yield delta


class GeminiAdapter(LLMAdapter):
    """Google Gemini generateContent / streamGenerateContent API."""

    def __init__(self, config: LLMConfig, logger: object | None = None) -> None:
        super().__init__(config, logger)
        self._base_url = (
            config.base_url or "https://generativelanguage.googleapis.com"
        ).rstrip("/")

    def _endpoint(self, stream: bool) -> str:
        action = "streamGenerateContent" if stream else "generateContent"
        return f"{self._base_url}/v1beta/models/{self._config.model}:{action}"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._config.api_key:
            headers["x-goog-api-key"] = self._config.api_key
        return headers

    def _payload(self, prompt: str, system: str | None, json_mode: bool) -> dict[str, Any]:
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        body: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": self._config.temperature,
                "maxOutputTokens": self._config.max_tokens,
            },
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if json_mode and self._config.json_instruction:
            body["generationConfig"]["responseMimeType"] = "application/json"
        return body

    def _extract_text(self, data: dict[str, Any]) -> str:
        candidates = data.get("candidates") or []
        if not candidates:
            return ""
        parts = ((candidates[0].get("content") or {}).get("parts")) or []
        return "".join(part.get("text", "") for part in parts)

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        payload = self._payload(prompt, system, json_mode)
        async with httpx.AsyncClient(timeout=self._config.timeout_seconds) as client:
            response = await client.post(
                self._endpoint(stream=False), json=payload, headers=self._headers()
            )
            if response.status_code >= 400:
                raise LLMError(
                    f"LLM request failed with status {response.status_code}",
                    details=response.text[:2000],
                )
            data = response.json()
        return LLMResponse(
            text=self._extract_text(data), provider=self.provider, model=self.model, raw=data
        )

    async def stream(
        self,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        payload = self._payload(prompt, system, json_mode)
        url = f"{self._endpoint(stream=True)}?alt=sse"
        async with httpx.AsyncClient(timeout=self._config.timeout_seconds) as client:
            async with client.stream("POST", url, json=payload, headers=self._headers()) as response:
                if response.status_code >= 400:
                    body = await response.aread()
                    raise LLMError(
                        f"LLM request failed with status {response.status_code}",
                        details=body.decode("utf-8", errors="replace")[:2000],
                    )
                parser = SSEParser()
                async for line in response.aiter_lines():
                    for event, data in parser.push_line(line):
                        text = self._extract_text(_parse_sse_json(event, data))
                        if text:
                            yield text
                for event, data in parser.flush():
                    text = self._extract_text(_parse_sse_json(event, data))
                    if text:
                        yield text


def _parse_sse_json(event: str, data: str) -> dict[str, Any]:
    if not data or data == "[DONE]":
        return {}
    try:
        obj = json.loads(data)
        return obj if isinstance(obj, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def build_llm(config: LLMConfig, logger: object | None = None) -> LLMAdapter:
    provider = (config.provider or "mock").lower()
    if provider not in PROVIDERS:
        raise LLMError(f"Unsupported LLM provider: {config.provider}")
    if provider == "mock":
        return MockLLM(config, logger)
    if provider in {"openai", "llama"}:
        return OpenAICompatibleAdapter(config, logger)
    if provider == "claude":
        return ClaudeAdapter(config, logger)
    return GeminiAdapter(config, logger)
