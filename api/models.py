"""
API request/response models — Pydantic v2.
All request models include api_key for BYOK architecture.
"""

from typing import Literal, Optional

from pydantic import BaseModel


class AnalyseRequest(BaseModel):
    """Request body for POST /analyse (sent as form fields alongside file upload)."""
    user_id: str
    source: Literal["bank_csv", "credit_card_pdf", "upi_pdf"]
    api_key: str  # BYOK


class AnalyseResponse(BaseModel):
    """Response body for POST /analyse."""
    run_id: str
    user_id: str
    health_score: int
    total_monthly_at_risk: float
    findings_count: int
    executive_summary: str
    top_3_actions: list[str]
    ranked_findings: list[dict]
    # Full agent outputs for the frontend
    insight_findings: list[dict] = []
    reward_findings: list[dict] = []
    budget_goals_report: dict = {}
    financial_consultant_report: dict = {} # Legacy fallback


class AskRequest(BaseModel):
    """Request body for POST /ask."""
    user_id: str
    question: str
    mode: str = "auto"  # auto, card, education, hindsight, research
    api_key: str  # BYOK
    provider: Optional[str] = None
    model_id: Optional[str] = None


class AskResponse(BaseModel):
    """Response body for POST /ask."""
    answer: str
    mode: str
    metadata: dict


class CardRecommendRequest(BaseModel):
    """Request body for POST /card-recommend."""
    user_id: str
    question: str
    api_key: str  # BYOK


class HindsightRequest(BaseModel):
    """Request body for POST /hindsight/{run_id}."""
    user_id: str
    api_key: str  # BYOK


class ResearchRequest(BaseModel):
    """Request body for POST /research."""
    query: str
    research_type: Literal["card", "regulation", "merchant"]
    merchant: str = ""  # required when research_type is merchant
    api_key: str  # BYOK


class ResolveFindingRequest(BaseModel):
    """Request body for POST /findings/resolve."""
    finding_id: str
    rupee_saved: float
    notes: str = ""


class UserProfileRequest(BaseModel):
    """Request body for updating user income."""
    user_id: str
    monthly_income: float


class GoalRequest(BaseModel):
    """Request body for creating/updating financial goals."""
    user_id: str
    goal_id: Optional[str] = None
    name: str
    target_amount: float
    saved_amount: float = 0.0
    priority: str = "Medium"  # High, Medium, Low


class CardExploreRequest(BaseModel):
    """Request body for POST /card-explore."""
    card_id: str
    api_key: str  # BYOK — needed for Exa live search


class GoalAgentRequest(BaseModel):
    """Request body for POST /api/goals/analyze to run the goal agent independently."""
    user_id: str
    api_key: str
    budget_forecast: dict
    behavioural_impacts: list[dict] = []

class PurgeRequest(BaseModel):
    """Request body for POST /api/user/purge."""
    user_id: str
