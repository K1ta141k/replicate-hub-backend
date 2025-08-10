import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.api.deps import get_ai_service
from backend.models.ai import ChatRequest, ChatResponse
from backend.services.ai_service import AIService
from backend.ai_providers import AIProviderError
from backend.services.chat_history_service import ChatHistoryService

logger = logging.getLogger("backend")

router = APIRouter()


@router.post("/api/ai/chat", response_model=ChatResponse)
async def ai_chat(req: ChatRequest, svc: AIService = Depends(get_ai_service)):
    try:
        # Persist user message (last in the list if provided)
        history = ChatHistoryService()
        if req.messages:
            last = req.messages[-1]
            if last.get("role") == "user":
                history.append("user", last.get("content", ""), session=req.session)

        result = svc.chat(req)

        # Persist assistant reply
        assistant_text = result.get("assistant", "")
        if assistant_text:
            history.append("assistant", assistant_text, session=req.session)

        return result
    except AIProviderError as e:
        # Propagate as 400 so frontend can handle gracefully
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/ai/history")
async def ai_history(limit: int | None = None, session: str | None = None):
    history = ChatHistoryService()
    return {"messages": history.load(session=session, limit=limit)}


@router.post("/api/ai/history/clear")
async def ai_history_clear(session: str | None = None):
    history = ChatHistoryService()
    history.clear(session=session)
    return {"success": True}


@router.get("/api/ai/history/sessions")
async def ai_history_sessions():
    history = ChatHistoryService()
    return {"sessions": history.list_sessions()}


@router.post("/api/ai/history/sessions")
async def ai_history_create_session(data: dict):
    name = data.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Missing session name")
    history = ChatHistoryService()
    history.create_session(name)
    return {"success": True}


@router.delete("/api/ai/history/sessions/{name}")
async def ai_history_delete_session(name: str):
    if not name:
        raise HTTPException(status_code=400, detail="Missing session name")
    history = ChatHistoryService()
    history.delete_session(name)
    return {"success": True}


@router.get("/api/ai/models")
async def ai_models():
    svc = AIService()
    items = []
    for label, (provider, model_id) in svc.provider_map.items():
        items.append({
            "label": label,
            "provider": provider,
            "model_id": model_id,
        })
    return {"models": items}
