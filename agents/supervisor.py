import json
import logging
import os
from typing import Annotated, TypedDict, Any
from uuid import uuid4

import operator
import asyncio
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from ingestion.schema import Transaction
from agents.insights_agent import run_insights_agent
from agents.reward_optimiser import run_reward_optimiser
from agents.financial_consultant import run_financial_consultant
from agents.utils import deserialise_transactions
from memory.supabase_client import SupabaseMemory

logger = logging.getLogger(__name__)


class GuardianState(TypedDict):
    user_id: str
    transactions_json: str
    api_key: str
    provider: str
    model_id: str
    exa_api_key: str
    monthly_income: float
    goals: list[dict]
    insight_findings: list[dict]
    reward_findings: list[dict]
    budget_goals_report: dict
    errors: Annotated[list[str], operator.add]
    run_id: str
    statement_months: int


_memory = SupabaseMemory()
_vectorstore = None


def _is_low_memory_mode() -> bool:
    """
    Render free tier has very limited RAM, so default to the lighter execution
    path there unless explicitly overridden.
    """
    raw = os.getenv("GUARDIAN_LOW_MEMORY_MODE")
    if raw is not None:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return bool(os.getenv("RENDER"))


def _should_store_hindsight() -> bool:
    """
    Hindsight embeddings are useful, but they are one of the heaviest parts of
    the pipeline. Keep them opt-in on low-memory hosts.
    """
    raw = os.getenv("GUARDIAN_ENABLE_HINDSIGHT")
    if raw is not None:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return not _is_low_memory_mode()


def _get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        from rag.vectorstore import GuardianVectorStore
        _vectorstore = GuardianVectorStore()
    return _vectorstore


def _store_hindsight_docs(user_id: str, transactions, findings: list[dict]):
    """
    Build spending summary documents from actual transactions and store
    them in ChromaDB's hindsight collection so the chatbot can answer
    questions about the user's spending.
    """
    from collections import defaultdict
    from langchain_core.documents import Document

    # Build category summaries
    cat_totals = defaultdict(lambda: {"total": 0, "count": 0, "merchants": defaultdict(float)})
    for txn in transactions:
        if txn.amount > 0:  # debits only
            cat = txn.category
            cat_totals[cat]["total"] += txn.amount
            cat_totals[cat]["count"] += 1
            cat_totals[cat]["merchants"][txn.merchant_name] += txn.amount

    docs = []

    # Document 1: Overall spending summary
    sorted_cats = sorted(cat_totals.items(), key=lambda x: x[1]["total"], reverse=True)
    lines = [f"User {user_id} spending analysis:"]
    total_spend = sum(c["total"] for _, c in sorted_cats)
    lines.append(f"Total spending: ₹{total_spend:,.0f}")
    lines.append(f"Total transactions: {sum(c['count'] for _, c in sorted_cats)}")
    lines.append("")
    lines.append("Top spending categories:")
    for cat, data in sorted_cats[:8]:
        pct = (data["total"] / total_spend * 100) if total_spend > 0 else 0
        lines.append(f"- {cat}: ₹{data['total']:,.0f} ({pct:.1f}%) across {data['count']} transactions")
    docs.append(Document(page_content="\n".join(lines), metadata={"user_id": user_id, "type": "spending_summary"}))

    # Document 2: Top merchants
    all_merchants = defaultdict(float)
    for _, data in cat_totals.items():
        for m, amt in data["merchants"].items():
            all_merchants[m] += amt
    top_merchants = sorted(all_merchants.items(), key=lambda x: x[1], reverse=True)[:15]
    
    merchant_lines = [f"User {user_id} top merchants by spending:"]
    for m, amt in top_merchants:
        merchant_lines.append(f"- {m}: ₹{amt:,.0f}")
    docs.append(Document(page_content="\n".join(merchant_lines), metadata={"user_id": user_id, "type": "merchant_summary"}))

    # Document 3: Per-category detail with top merchants
    for cat, data in sorted_cats[:6]:
        sorted_merchants = sorted(data["merchants"].items(), key=lambda x: x[1], reverse=True)[:5]
        cat_lines = [
            f"User {user_id} {cat} spending breakdown:",
            f"Total {cat} spend: ₹{data['total']:,.0f} across {data['count']} transactions",
            "Top merchants in this category:"
        ]
        for m, amt in sorted_merchants:
            cat_lines.append(f"- {m}: ₹{amt:,.0f}")
    docs.append(Document(page_content="\n".join(cat_lines), metadata={"user_id": user_id, "type": f"category_{cat}"}))

    # Store in ChromaDB
    _get_vectorstore().add_hindsight_docs(user_id, docs)

async def insights_node(state: GuardianState) -> dict:
    try:
        txns = deserialise_transactions(state["transactions_json"])
        loop = asyncio.get_event_loop()
        # Run synchronous hunter in executor
        print("[Guardian] Insights Agent: Scanning for anomalies and recurring patterns...", flush=True)
        findings = await loop.run_in_executor(
            None, 
            run_insights_agent, 
            txns, state["api_key"], state["provider"], state["model_id"]
        )
        return {"insight_findings": findings}
    except Exception as e:
        logger.error(f"insights_node error: {e}")
        return {"insight_findings": [], "errors": [f"insights_agent: {e}"]}


async def reward_node(state: GuardianState) -> dict:
    try:
        txns = deserialise_transactions(state["transactions_json"])
        # IMPORTANT: run_reward_optimiser is ASYNC now
        print("[Guardian] Reward Optimiser: Starting research...", flush=True)
        findings = await run_reward_optimiser(
            transactions=txns,
            api_key=state["api_key"],
            provider=state["provider"],
            model_id=state["model_id"],
            vectorstore=None,
            exa_api_key=state.get("exa_api_key", "")
        )
        print("[Guardian] Reward Optimiser: Analysis complete.", flush=True)
        return {"reward_findings": findings}
    except Exception as e:
        logger.error(f"reward_node error: {e}")
        return {"reward_findings": [], "errors": [f"reward_optimiser: {e}"]}


async def budget_goals_node(state: GuardianState) -> dict:
    try:
        from agents.budget_goals_agent import run_budget_goals_agent
        txns = deserialise_transactions(state["transactions_json"])
        loop = asyncio.get_event_loop()
        print("[Guardian] Budget & Goals Agent: Calculating timelines...", flush=True)
        report = await loop.run_in_executor(
            None,
            run_budget_goals_agent,
            txns, state["monthly_income"], state["goals"], state["api_key"], state["provider"], state["model_id"], state["statement_months"]
        )
        print("[Guardian] Budget & Goals Agent: Forecast generated.", flush=True)
        return {"budget_goals_report": report}
    except Exception as e:
        logger.error(f"budget_goals_node error: {e}")
        return {"budget_goals_report": {"budget_summary": {"one_line_verdict": "Calculation failed."}, "errors": str(e)}, "errors": [f"budget_goals: {e}"]}


async def persist_node(state: GuardianState) -> dict:
    try:
        run_id = state["run_id"]
        user_id = state["user_id"]
        
        report = state.get("budget_goals_report", {})
        
        all_findings = (state.get("insight_findings", [])
                       + state.get("reward_findings", []))
        
        # Save all findings
        print(f"[Guardian] Persisting results for run {run_id}...")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _memory.save_findings, run_id, user_id, all_findings)
        
        # update run summary
        summary = report.get("budget_summary", {}).get("one_line_verdict", "")
        await loop.run_in_executor(None, _memory.update_run_summary, run_id, 100, 0, summary)
        
        # save goal snapshots if available
        if "raw" in report and "scenarios_per_goal" in report["raw"]:
            await loop.run_in_executor(None, _memory.save_goal_snapshots, run_id, report["raw"]["scenarios_per_goal"])
        
        # ── Store hindsight documents in ChromaDB for chatbot ──
        if _should_store_hindsight():
            try:
                txns = deserialise_transactions(state["transactions_json"])
                if txns:
                    await loop.run_in_executor(
                        None, _store_hindsight_docs, user_id, txns, all_findings
                    )
                    print(f"[Guardian] Hindsight docs stored in ChromaDB for {user_id}")
            except Exception as e:
                logger.warning(f"Hindsight doc storage failed (non-fatal): {e}")
        else:
            print("[Guardian] Hindsight storage skipped in low-memory mode.", flush=True)
        
        print(f"[Guardian] Persistence complete for run {run_id}.")
        return {}
    except Exception as e:
        logger.error(f"persist_node error: {e}")
        return {"errors": [f"persist: {e}"]}


def _build_graph() -> StateGraph:
    builder = StateGraph(GuardianState)
    
    builder.add_node("insights_node", insights_node)
    builder.add_node("reward_node", reward_node)
    builder.add_node("budget_goals_node", budget_goals_node)
    builder.add_node("persist_node", persist_node)
    
    # Fan out from START
    builder.add_edge(START, "insights_node")
    builder.add_edge(START, "reward_node")
    builder.add_edge(START, "budget_goals_node")
    
    # Fan in to Persist
    builder.add_edge("insights_node", "persist_node")
    builder.add_edge("reward_node", "persist_node")
    builder.add_edge("budget_goals_node", "persist_node")
    
    builder.add_edge("persist_node", END)
    
    return builder


_checkpointer = MemorySaver()
graph = _build_graph().compile(checkpointer=_checkpointer)


def _merge_state(state: GuardianState, updates: dict) -> GuardianState:
    if not updates:
        return state
    if updates.get("errors"):
        state["errors"].extend(updates["errors"])
    for key, value in updates.items():
        if key != "errors":
            state[key] = value
    return state


async def run_guardian(user_id: str, transactions: list[Transaction], api_key: str, provider: str = "google", model_id: str = "gemini-2.5-flash-lite", exa_api_key: str = None, statement_months: int = 1) -> GuardianState:
    run_id = str(uuid4())
    loop = asyncio.get_event_loop()
    
    print(f"\n[Guardian] Starting analysis run {run_id}", flush=True)
    
    # Initialise records
    await loop.run_in_executor(None, _memory.upsert_user, user_id)
    await loop.run_in_executor(None, _memory.create_run, run_id, user_id)
    
    # NEW: Fetch income and goals from DB before starting
    print("[Guardian] Loading user goals and income context...", flush=True)
    monthly_income = await loop.run_in_executor(None, _memory.get_user_income, user_id)
    goals = await loop.run_in_executor(None, _memory.get_active_goals, user_id)
    
    print("[Guardian] Preparing transaction data...", flush=True)
    transactions_json = json.dumps([t.model_dump(mode="json") for t in transactions])
    
    initial_state: GuardianState = {
        "user_id": user_id,
        "transactions_json": transactions_json,
        "api_key": api_key,
        "provider": provider,
        "model_id": model_id,
        "exa_api_key": exa_api_key or "",
        "monthly_income": monthly_income or 0.0,
        "goals": goals or [],
        "insight_findings": [],
        "reward_findings": [],
        "budget_goals_report": {},
        "errors": [],
        "run_id": run_id,
        "statement_months": statement_months,
    }
    
    config = {"configurable": {"thread_id": run_id}}
    
    if _is_low_memory_mode():
        print("[Guardian] Low-memory mode enabled. Running agents sequentially.", flush=True)
        final_state = dict(initial_state)
        final_state = _merge_state(final_state, await insights_node(final_state))
        final_state = _merge_state(final_state, await reward_node(final_state))
        final_state = _merge_state(final_state, await budget_goals_node(final_state))
        final_state = _merge_state(final_state, await persist_node(final_state))
    else:
        print(f"[Guardian] Invoking 3 AI Agents in parallel (Provider: {provider})...")
        final_state = await graph.ainvoke(initial_state, config=config)
    
    if final_state.get("errors"):
        print(f"[Guardian] Run completed with errors: {final_state['errors']}")
    else:
        print("[Guardian] Analysis successful. Returning results.")
        
    return final_state
