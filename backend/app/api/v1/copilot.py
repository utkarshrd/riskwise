from backend.app.agents.copilot import CopilotMessageResponse, RiskCopilotService
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/copilot", tags=["Agentic Risk Copilot"])


class CopilotRequest(BaseModel):
    message: str = Field(..., min_length=2, description="User query or risk analysis prompt")
    session_id: str | None = Field(default=None, description="Optional conversation session ID")
    conversation_id: str | None = Field(default=None, description="Optional conversation session ID alias")


@router.post("/message", response_model=CopilotMessageResponse)
def handle_copilot_message(request: CopilotRequest):
    """Route user message through bounded state machine, tools, or RAG retriever."""
    copilot_service = RiskCopilotService()
    sess_id = request.session_id or request.conversation_id
    return copilot_service.route_and_execute(request.message, session_id=sess_id)
