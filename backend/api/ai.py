import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.api.deps import get_ai_service
from backend.models.ai import ChatRequest, ChatResponse
from backend.services.ai_service import AIService
from backend.ai_providers import AIProviderError

logger = logging.getLogger("backend")

router = APIRouter()


@router.post("/api/ai/chat", response_model=ChatResponse)
async def ai_chat(req: ChatRequest, svc: AIService = Depends(get_ai_service)):
    try:
        return svc.chat(req)
    except AIProviderError as e:
        # Propagate as 400 so frontend can handle gracefully
        raise HTTPException(status_code=400, detail=str(e))
