from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from backend.ai_providers import call_llm, AIProviderError
from backend.tools import TOOLS_REGISTRY, build_function_schemas
from backend.sandbox import manager as sandbox_manager
from backend.models.ai import ChatRequest


class AIService:
    def __init__(self, provider_map: Dict[str, Tuple[str, str]] | None = None) -> None:
        self.provider_map = provider_map or {
            "kimi2": ("groq", "llama3-70b-8192"),
            "gpt5": ("openai", "gpt-5"),
            "claude": ("anthropic", "claude-3-opus-20240229"),
        }

    def chat(self, req: ChatRequest) -> Dict[str, Any]:
        messages = list(req.messages)
        model_choice = req.model or "kimi2"
        project = req.project or "scratch"

        provider, model_id = self.provider_map.get(model_choice, self.provider_map["kimi2"])

        # ensure workspace exists for project
        sandbox_manager.init(project_name=project)

        function_schemas = build_function_schemas()

        resp = call_llm(provider, model_id, messages, function_schemas)

        iterations = 0
        while True:
            iterations += 1
            if iterations > 5:
                break
            choice = resp["choices"][0]
            if choice.get("finish_reason") == "stop":
                break
            if "message" in choice and choice["message"].get("function_call"):
                fn_call = choice["message"]["function_call"]
                fn_name = fn_call["name"]
                try:
                    args = json.loads(fn_call.get("arguments", "{}"))
                except Exception:
                    args = {}
                tool_fn = TOOLS_REGISTRY.get(fn_name)
                if not tool_fn:
                    tool_result = {"error": f"unknown tool {fn_name}"}
                else:
                    try:
                        tool_result = tool_fn(**args)
                    except Exception as exc:
                        tool_result = {"error": str(exc)}

                messages.append(choice["message"])  # assistant invoking tool
                messages.append({"role": "function", "name": fn_name, "content": json.dumps(tool_result)})
                resp = call_llm(provider, model_id, messages)
                continue
            else:
                break

        assistant_msg = resp["choices"][0]["message"]["content"]
        return {"assistant": assistant_msg, "messages": messages}
