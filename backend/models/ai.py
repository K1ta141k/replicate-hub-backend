from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    model: str = Field(default="kimi2")
    project: Optional[str] = Field(default=None)


class ChatResponse(BaseModel):
    assistant: str
    messages: List[Dict[str, Any]]
