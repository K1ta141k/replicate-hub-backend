from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple
import re
import logging

from backend.ai_providers import call_llm, AIProviderError
from backend.tools import TOOLS_REGISTRY, build_function_schemas
from backend.sandbox import manager as sandbox_manager
from backend.models.ai import ChatRequest


class AIService:
    def __init__(self, provider_map: Dict[str, Tuple[str, str]] | None = None) -> None:
        self.provider_map = provider_map or {
            # Groq (OpenAI-compatible endpoint)
            "kimi2": ("groq", "llama3-70b-8192"),
            "llama3-8b": ("groq", "llama3-8b-8192"),
            "mixtral": ("groq", "mixtral-8x7b-32768"),

            # OpenAI
            "gpt5": ("openai", "gpt-5-2025-08-07"),
            "gpt4o": ("openai", "gpt-4o"),
            "gpt4o-mini": ("openai", "gpt-4o-mini"),
            "gpt41-mini": ("openai", "gpt-4.1-mini"),

            # Anthropic (kept for compatibility; API adapter is basic)
            "claude": ("anthropic", "claude-3-opus-20240229"),
        }

    def chat(self, req: ChatRequest) -> Dict[str, Any]:
        logger = logging.getLogger("backend")
        messages = list(req.messages)
        model_choice = req.model or "kimi2"
        project = req.project or "scratch"

        provider, model_id = self.provider_map.get(model_choice, self.provider_map["kimi2"])

        # ensure workspace exists for project
        sandbox_manager.init(project_name=project)

        function_schemas = build_function_schemas()

        # Decide mode
        user_text = " ".join([m.get("content", "") for m in messages if m.get("role") == "user"]) or ""
        last_user = None
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = m.get("content", "")
                break
        is_frontend = bool(last_user and isinstance(last_user, str) and last_user.strip().lower().startswith("frontend:"))
        is_large = len(user_text) > 300 or any(k in user_text.lower() for k in [
            "build", "implement", "refactor", "scaffold", "migrate", "architecture", "fix bug", "add feature",
        ])
        if is_frontend:
            policy = (
                "You are a frontend code generator.\n"
                "When the user prompt starts with 'frontend:', interpret the rest as a UI description.\n"
                "- Generate a Vite + React + TypeScript app structure using batched tool_calls.\n"
                "- Create/overwrite these files at project root unless otherwise specified:\n"
                "  index.html (loads /src/main.tsx)\n"
                "  package.json (react, react-dom; devDependencies: vite, typescript, @types/react, @types/react-dom)\n"
                "  tsconfig.json\n"
                "  vite.config.ts\n"
                "  src/main.tsx\n"
                "  src/App.tsx\n"
                "- You MUST use tool_calls to: make_dir('src') then write_file for each file.\n"
                "- Do not attempt to run shell commands; the server will start the dev process itself.\n"
                "- Do not wrap file content in markdown fences.\n"
                "- Return a concise message explaining where the app runs.\n"
                "Return your answer as JSON: {\n  \"tool_calls\": [ ... ],\n  \"message\": \"...\"\n}"
            )
            messages = [{"role": "system", "content": policy}] + messages
            is_large = True
        elif is_large:
            policy = (
                "You are an autonomous coding assistant.\n"
                "- Batch multiple tool calls in a single response using tool_calls to reduce round trips.\n"
                "- Prefer sequence per task: list_files → read_file (as needed) → make_dir (if needed) → write_file/append_file → update todo.md.\n"
                "- Use concise messages; avoid unnecessary chit-chat.\n"
                "- If a tool call fails, adjust and retry once, then proceed.\n"
                "- Do not include markdown fences in file contents when writing files.\n"
                "Return your answer as JSON with optional tool_calls and a human message: {\n"
                "  \"tool_calls\": [{ \"name\": \"function\", \"parameters\": { ... } }],\n"
                "  \"message\": \"...\"\n}"
            )
            messages = [{"role": "system", "content": policy}] + messages

        # Initial call with tools; on provider 400 fallback to no-tools
        try:
            resp = call_llm(provider, model_id, messages, function_schemas)
        except AIProviderError as e:
            # Fallback: call without tools to at least produce a textual response
            resp = call_llm(provider, model_id, messages, None)
        try:
            logger.info("LLM initial response:\n%s", json.dumps(resp, indent=2)[:2000])
        except Exception:
            pass

        iterations = 0
        max_iterations = 8 if is_large else 4
        started_dev = False
        while True:
            iterations += 1
            if iterations > max_iterations:
                break
            choice = resp["choices"][0]
            if choice.get("finish_reason") == "stop":
                break

            # Legacy function_call
            if "message" in choice and choice["message"].get("function_call"):
                fn_call = choice["message"]["function_call"]
                fn_name = fn_call.get("name")
                try:
                    args = json.loads(fn_call.get("arguments", "{}"))
                except Exception:
                    args = {}
                tool_result = self._execute_tool(fn_name, args)
                messages.append(choice["message"])  # assistant invoking tool
                messages.append({"role": "function", "name": fn_name, "content": json.dumps(tool_result)})
                resp = call_llm(provider, model_id, messages, function_schemas)
                try:
                    logger.info("LLM response (function_call loop):\n%s", json.dumps(resp, indent=2)[:2000])
                except Exception:
                    pass
                continue

            # OpenAI tool_calls (batch supported)
            if "message" in choice and (choice["message"].get("tool_calls") or choice["message"].get("tool calls")):
                tool_calls = choice["message"].get("tool_calls") or choice["message"].get("tool calls") or []
                messages.append(choice["message"])  # keep assistant msg
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    fn_name = fn.get("name") or tc.get("name")
                    raw_args = fn.get("arguments", tc.get("arguments", "{}"))
                    try:
                        args = json.loads(raw_args or "{}") if isinstance(raw_args, str) else (raw_args or {})
                    except Exception:
                        args = self._coerce_args(fn_name, raw_args)
                    tool_result = self._execute_tool(fn_name, args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id"),
                        "content": json.dumps(tool_result),
                    })
                # Auto-start dev server for frontend mode (once)
                if is_frontend and not started_dev:
                    try:
                        sandbox_manager.start_dev()
                        started_dev = True
                    except Exception:
                        pass
                # Follow-up without tools to avoid provider complaints
                resp = call_llm(provider, model_id, messages, None)
                try:
                    logger.info("LLM response (tool_calls loop):\n%s", json.dumps(resp, indent=2)[:2000])
                except Exception:
                    pass
                continue

            # Fallback: <tool-use>{...}</tool-use>
            if "message" in choice and choice["message"].get("content"):
                content = choice["message"].get("content", "") or ""
                m = re.search(r"<tool-use>\s*(\{[\s\S]*?\})\s*</tool-use>", content)
                if m:
                    try:
                        tool_spec = json.loads(m.group(1))
                        fn_info = tool_spec.get("function", {})
                        fn_name = fn_info.get("name")
                        params = tool_spec.get("parameters", {}) or fn_info.get("parameters", {}) or {}
                        tool_result = self._execute_tool(fn_name, params)
                        messages.append({"role": "assistant", "content": content})
                        messages.append({"role": "function", "name": fn_name, "content": json.dumps(tool_result)})
                        resp = call_llm(provider, model_id, messages, function_schemas)
                        try:
                            logger.info("LLM response (plain <tool-use> loop):\n%s", json.dumps(resp, indent=2)[:2000])
                        except Exception:
                            pass
                        continue
                    except Exception:
                        pass
                # Fallback: pure JSON envelope { tool_calls: [...], message? }
                try:
                    obj = json.loads(content)
                except Exception:
                    obj = None
                alt_calls = None
                if isinstance(obj, dict):
                    alt_calls = obj.get("tool_calls") or obj.get("tool calls")
                if isinstance(obj, dict) and isinstance(alt_calls, list):
                    if obj.get("message"):
                        messages.append({"role": "assistant", "content": str(obj.get("message"))})
                    for tc in alt_calls or []:
                        fn_name = (tc.get("function", {}) or {}).get("name") or tc.get("name")
                        params = tc.get("parameters") or (tc.get("function", {}) or {}).get("parameters") or {}
                        if not params and tc.get("arguments"):
                            raw_args = tc.get("arguments")
                            try:
                                params = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                            except Exception:
                                params = self._coerce_args(fn_name, raw_args)
                        tool_result = self._execute_tool(fn_name, params)
                        messages.append({"role": "function", "name": fn_name, "content": json.dumps(tool_result)})
                    # Auto-start dev server for frontend mode (once)
                    if is_frontend and not started_dev:
                        try:
                            sandbox_manager.start_dev()
                            started_dev = True
                        except Exception:
                            pass
                    resp = call_llm(provider, model_id, messages, None)
                    try:
                        logger.info("LLM response (JSON tool_calls loop):\n%s", json.dumps(resp, indent=2)[:2000])
                    except Exception:
                        pass
                    continue

            # Nothing actionable
            break

        assistant_msg = resp["choices"][0]["message"].get("content", "")
        # If the model returned a JSON envelope, return only the 'message' field
        try:
            obj = json.loads(assistant_msg)
            if isinstance(obj, dict) and obj.get("message") is not None:
                assistant_msg = str(obj.get("message"))
        except Exception:
            pass
        if is_frontend:
            url = sandbox_manager.meta.get("url") or "http://localhost:5173"
            if not assistant_msg:
                assistant_msg = f"App is running at {url}."
            else:
                try:
                    # Replace any localhost:PORT with the actual sandbox URL and avoid 3000/8000 in output
                    assistant_msg = re.sub(r"https?://localhost:\d+", url, assistant_msg)
                    if "http" not in assistant_msg:
                        assistant_msg = assistant_msg.rstrip() + f" App is running at {url}."
                except Exception:
                    pass
        return {"assistant": assistant_msg, "messages": messages}

    @staticmethod
    def _coerce_args(fn_name: str | None, raw_args: Any) -> Dict[str, Any]:
        if isinstance(raw_args, str):
            if fn_name in ("read_file", "delete_file", "make_dir", "create_dir", "mkdir"):
                return {"path": raw_args}
            if fn_name == "list_files":
                return {"dir": raw_args}
            return {"value": raw_args}
        return {}

    @staticmethod
    def _execute_tool(fn_name: str | None, args: Dict[str, Any]) -> Dict[str, Any]:
        tool_fn = TOOLS_REGISTRY.get(fn_name or "")
        if not tool_fn:
            return {"error": f"unknown tool {fn_name}"}
        try:
            return tool_fn(**args)
        except Exception as exc:
            return {"error": str(exc)}
