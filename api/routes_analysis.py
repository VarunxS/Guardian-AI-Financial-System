"""
Analysis routes — statement upload, findings retrieval, and resolution.
"""

import os
import tempfile
import logging
import asyncio

from typing import Optional
from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from config import settings
from api.models import AnalyseResponse, ResolveFindingRequest, UserProfileRequest, GoalRequest, GoalAgentRequest, PurgeRequest
from ingestion.parser import StatementParser
from agents.supervisor import run_guardian
from agents.budget_goals_agent import run_budget_goals_agent
from memory.supabase_client import SupabaseMemory

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Analysis"])

_parser = StatementParser()
_memory = SupabaseMemory()


def _health_rating_to_score(rating: str) -> int:
    """Convert Financial Consultant's text rating to a numeric score."""
    mapping = {
        "Excellent": 95, "Great": 85, "Good": 75, "Decent": 65,
        "Average": 55, "Below Average": 45, "Poor": 30, "Terrible": 15,
    }
    return mapping.get(rating, 50)

@router.post("/analyse", response_model=AnalyseResponse)
async def analyse_statement(
    file: Optional[UploadFile] = File(None),
    user_id: str = Form(...),
    source: str = Form(...),
    api_key: Optional[str] = Form(None),
    statement_months: int = Form(1),
    use_sample: bool = Form(False),
    monthly_income: float = Form(0.0),
):
    """
    Upload a bank/credit card/UPI statement and run the full Guardian pipeline.
    Or use the sample PDF for demonstration.
    """
    if use_sample:
        source = "credit_card_pdf"
        statement_months = 6
        # Use relative path so it works both locally and on Render
        tmp_path = os.path.join(os.getcwd(), "sample_data", "transaction_history_6months.pdf")
    else:
        if not file:
            raise HTTPException(status_code=400, detail="No file uploaded.")
        if source not in ("bank_csv", "credit_card_pdf", "upi_pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source: '{source}'. Must be one of: bank_csv, credit_card_pdf, upi_pdf",
            )

    # NEW: Fetch stored provider config if api_key not provided in form
    provider = "google"
    model_id = "gemini-2.5-flash-lite"
    exa_api_key = settings.exa_api_key

    try:
        config = await _memory.get_provider_config(user_id)
    except Exception as e:
        logger.warning(f"Provider config lookup failed for {user_id}: {e}")
        config = None

    if config:
        if not api_key:
            api_key = config["api_key"]
        provider = config["provider"]
        model_id = config["model_id"]
        if config.get("exa_api_key"):
            exa_api_key = config["exa_api_key"]

    if monthly_income > 0:
        await asyncio.get_event_loop().run_in_executor(None, _memory.set_user_income, user_id, monthly_income)

    if not api_key:
        raise HTTPException(
            status_code=400, 
            detail="No API key provided. Please configure it in Settings or provide it in the request."
        )

    if not use_sample:
        # Save uploaded file temporarily
        suffix = ".csv" if source == "bank_csv" else ".pdf"
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")

    try:
        # Parse the statement
        logger.info(f"[Guardian] Parsing statement for user {user_id} (source={source})")
        upload = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: _parser.parse(
                file_path=tmp_path,
                source=source,
                user_id=user_id,
                api_key=api_key,
                provider=provider,
                model_id=model_id
            )
        )
        logger.info(f"[Guardian] Parsed {len(upload.transactions)} transactions for user {user_id}")

        if not upload.transactions:
            raise HTTPException(
                status_code=400,
                detail="No transactions could be parsed from the uploaded file.",
            )

        # Run the Guardian pipeline
        try:
            final_state = await asyncio.wait_for(
                run_guardian(
                    user_id=user_id,
                    transactions=upload.transactions,
                    api_key=api_key,
                    provider=provider,
                    model_id=model_id,
                    exa_api_key=exa_api_key,
                    statement_months=statement_months,
                ),
                timeout=120.0
            )
        except asyncio.TimeoutError:
            logger.error(f"[Guardian] CRITICAL: Analysis timed out for user {user_id}")
            raise HTTPException(status_code=504, detail="Analysis timed out.")

        budget_report = final_state.get("budget_goals_report", {})
        reward_findings = final_state.get("reward_findings", [])
        insight_findings = final_state.get("insight_findings", [])
        all_findings = insight_findings + reward_findings

        # Derive summary metrics from actual agent outputs
        total_missed = 0
        if reward_findings:
            for rf in reward_findings:
                total_missed += rf.get("total_missed_monthly", 0)

        # Calculate dynamic health score
        # 1. Budget Health (70% weight)
        income = budget_report.get("raw", {}).get("monthly_income") or 0
        surplus = budget_report.get("budget_summary", {}).get("forecasted_surplus") or 0
        
        budget_score = 50
        if income > 0:
            ratio = surplus / income
            budget_score = 50 + (ratio * 100)
        else:
            # If no income, score based on spending volume vs a benchmark or just neutral
            budget_score = 50

        # 2. Reward Efficiency (30% weight)
        # Higher leakage = lower score
        total_spend = budget_report.get("raw", {}).get("budget_forecast", {}).get("total", 1)
        leakage_ratio = total_missed / max(100, total_spend)
        reward_score = max(0, 100 - (leakage_ratio * 1000)) # 10% leakage = 0 score for this component

        # Composite Score
        health_score = int(max(10, min(98, (budget_score * 0.7) + (reward_score * 0.3))))
        
        verdict = budget_report.get("budget_summary", {}).get("one_line_verdict", "Analysis complete.")
        top_actions = [f.get("suggestion", "") for f in budget_report.get("behavioural_goal_impacts", [])[:3]]

        return AnalyseResponse(
            run_id=final_state["run_id"],
            user_id=user_id,
            health_score=health_score,
            total_monthly_at_risk=total_missed,
            findings_count=len(all_findings) + len(budget_report.get("behavioural_goal_impacts", [])),
            executive_summary=verdict,
            top_3_actions=top_actions,
            ranked_findings=all_findings,
            insight_findings=insight_findings,
            reward_findings=reward_findings,
            budget_goals_report=budget_report,
            financial_consultant_report=budget_report, # Fallback for old keys
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        # Clean up temp file (only if it's a real upload)
        if not use_sample:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


@router.get("/findings/{user_id}")
async def get_findings(user_id: str):
    """Get all unresolved findings for a user."""
    loop = asyncio.get_event_loop()
    findings = await loop.run_in_executor(None, _memory.get_findings, user_id, False)
    return {"user_id": user_id, "findings": findings, "count": len(findings)}


@router.get("/findings/{user_id}/history")
async def get_run_history(user_id: str):
    """Get the last 6 analysis run summaries for a user."""
    loop = asyncio.get_event_loop()
    history = await loop.run_in_executor(None, _memory.get_run_history, user_id, 6)
    return {"user_id": user_id, "runs": history, "count": len(history)}


@router.post("/findings/resolve")
async def resolve_finding(request: ResolveFindingRequest):
    """Mark a finding as resolved."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, _memory.resolve_finding,
        request.finding_id, request.rupee_saved, request.notes,
    )
    return {"status": "resolved", "finding_id": request.finding_id}


@router.get("/user/{user_id}/context")
async def get_user_context(user_id: str):
    """Get user income and active goals."""
    loop = asyncio.get_event_loop()
    income = await loop.run_in_executor(None, _memory.get_user_income, user_id)
    goals = await loop.run_in_executor(None, _memory.get_active_goals, user_id)
    return {
        "user_id": user_id,
        "monthly_income": income,
        "goals": goals
    }


@router.post("/user/profile")
async def update_profile(request: UserProfileRequest):
    """Update user's monthly income."""
    # set_user_income is synchronous
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _memory.set_user_income, request.user_id, request.monthly_income)
    return {"status": "success", "monthly_income": request.monthly_income}


@router.post("/user/purge")
async def purge_user_data(request: PurgeRequest):
    """Purge user data (income and goals) from DB."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _memory.purge_user_data, request.user_id)
    return {"status": "success", "message": "User data purged."}


@router.post("/goals")
async def upsert_goal(request: GoalRequest):
    """Create or update a financial goal."""
    loop = asyncio.get_event_loop()
    goal_id = await loop.run_in_executor(
        None,
        _memory.upsert_goal,
        request.user_id,
        request.name,
        request.target_amount,
        request.saved_amount,
        request.priority,
        request.goal_id
    )
    return {"status": "success", "goal_id": goal_id}


@router.delete("/goals/{goal_id}")
async def delete_goal(goal_id: str):
    """Delete (deactivate) a financial goal."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _memory.delete_goal, goal_id)
    return {"status": "deleted", "goal_id": goal_id}


@router.post("/goals/analyze")
async def analyze_goals(request: GoalAgentRequest):
    """Run the Goal Agent independently using cached forecast and behavioural impacts."""
    loop = asyncio.get_event_loop()
    income = await loop.run_in_executor(None, _memory.get_user_income, request.user_id)
    goals = await loop.run_in_executor(None, _memory.get_active_goals, request.user_id)

    try:
        report = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                run_budget_goals_agent,
                [],  # transactions (not needed when forecast & impacts provided)
                income,
                goals,
                request.api_key,
                "openai",  # default provider
                1,  # statement_months (not needed here)
                request.budget_forecast,
                request.behavioural_impacts
            ),
            timeout=60.0
        )
        return report
    except asyncio.TimeoutError:
        logger.error(f"[Guardian] CRITICAL: Goal Agent Analysis timed out for user {request.user_id}")
        raise HTTPException(status_code=504, detail="Analysis timed out.")
    except Exception as e:
        logger.error(f"Goal Agent Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Goal Agent Analysis failed: {str(e)}")
