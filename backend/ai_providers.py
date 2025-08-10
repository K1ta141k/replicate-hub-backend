from typing import List, Dict, Any
import os
import httpx

class AIProviderError(Exception):
    pass


def call_openai(messages: List[Dict[str, str]], functions: List[Dict[str, Any]] | None, model: str) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise AIProviderError("OPENAI_API_KEY not set in environment")
    headers = {"Authorization": f"Bearer {api_key}"}
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }
    if functions:
        payload["tools"] = [{"type": "function", "function": f} for f in functions]
        payload["tool_choice"] = "auto"
    try:
        resp = httpx.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        body = e.response.text if e.response is not None else ""
        raise AIProviderError(f"openai {e.response.status_code if e.response else ''}: {body[:500]}")


def call_groq(messages: List[Dict[str, str]], functions: List[Dict[str, Any]] | None, model: str) -> Dict[str, Any]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise AIProviderError("GROQ_API_KEY not set in environment")
    headers = {"Authorization": f"Bearer {api_key}"}
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }
    if functions:
        # Groq's OpenAI-compatible API expects `tools`
        payload["tools"] = [{"type": "function", "function": f} for f in functions]
        payload["tool_choice"] = "auto"
    try:
        resp = httpx.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        body = e.response.text if e.response is not None else ""
        raise AIProviderError(f"groq {e.response.status_code if e.response else ''}: {body[:500]}")


def call_anthropic(messages: List[Dict[str, str]], tools: List[Dict[str, Any]] | None, model: str) -> Dict[str, Any]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise AIProviderError("ANTHROPIC_API_KEY not set in environment")
    headers = {"x-api-key": api_key}
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 1024,
    }
    if tools:
        payload["tools"] = tools
    try:
        resp = httpx.post("https://api.anthropic.com/v1/complete", headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        body = e.response.text if e.response is not None else ""
        raise AIProviderError(f"anthropic {e.response.status_code if e.response else ''}: {body[:500]}")


def call_llm(provider: str, model: str, messages: List[Dict[str, str]], functions: List[Dict[str, Any]] | None = None):
    if provider == "openai":
        return call_openai(messages, functions, model)
    if provider == "groq":
        return call_groq(messages, functions, model)
    if provider == "anthropic":
        return call_anthropic(messages, functions, model)
    raise AIProviderError(f"Unknown provider {provider}")
