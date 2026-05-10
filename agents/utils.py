import json
import logging
from typing import Optional
from collections import defaultdict
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ingestion.schema import Transaction

from agents.llm_factory import create_llm

logger = logging.getLogger(__name__)

def get_llm(api_key: str, provider: str = "google", model_id: str = "gemini-2.5-flash-lite"):
    """
    Returns an LLM instance based on the chosen provider.
    Proxies to llm_factory.create_llm for consistency.
    """
    return create_llm(api_key=api_key, provider=provider, model_id=model_id)


def enrich_findings(raw_findings: list[dict], system_prompt: str, api_key: str, provider: str = "google", model_id: str = "gemini-2.5-flash-lite") -> list[dict]:
    """
    Single LLM call that adds 'explanation' and 'action' fields to every finding.
    Falls back to template strings if LLM fails.
    """
    if not raw_findings:
        return []

    fallback = [
        {**f, "explanation": f.get("title", "Finding detected."), "action": "Review this item."}
        for f in raw_findings
    ]

    try:
        llm = get_llm(api_key, provider, model_id)
        human = (
            f"Here are the findings as JSON:\n{json.dumps(raw_findings, indent=2)}\n\n"
            "Return the exact same JSON list with 'explanation' and 'action' added to each item. "
            "No other changes. Return only valid JSON, no markdown, no commentary."
        )
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human)
        ])
        import re
        text = response.content.strip()
        
        # Extract JSON block
        match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
        if match:
            text = match.group(0)
            
        # Fix trailing commas
        text = re.sub(r',\s*([\]}])', r'\1', text)
        
        return json.loads(text)
    except Exception as e:
        logger.warning(f"LLM enrichment failed: {e}")
        return fallback


def months_of_data(transactions: list[Transaction]) -> float:
    """Compute how many months the transaction data spans."""
    if not transactions:
        return 1.0
    dates = [t.date for t in transactions]
    delta = (max(dates) - min(dates)).days
    return max(delta / 30, 1.0)


def build_merchant_spend_summary(transactions: list[Transaction]) -> dict:
    """
    Builds a summary of spend per merchant.
    Returns dict keyed by original merchant_name.
    """
    summary = defaultdict(lambda: {"total_spent": 0.0, "last_30_days": 0.0, "transaction_count": 0})
    
    if not transactions:
        return dict(summary)
        
    dates = [t.date for t in transactions]
    max_date = max(dates) if dates else None
    
    for t in transactions:
        if t.amount > 0:  # Debits only
            m = summary[t.merchant_name]
            m["total_spent"] += t.amount
            m["transaction_count"] += 1
            if max_date and (max_date - t.date).days <= 30:
                m["last_30_days"] += t.amount
                
    for m in summary.values():
        if m["transaction_count"] > 0:
            m["average_transaction"] = m["total_spent"] / m["transaction_count"]
            
    return dict(summary)


def deserialise_transactions(json_str: str) -> list[Transaction]:
    """Converts a JSON string back to a list of Transaction objects."""
    import json
    from datetime import datetime
    raw = json.loads(json_str)
    txns = []
    for t in raw:
        # Pydantic v2 requires date strings to be parsed or handled nicely, 
        # but passing dict to model_validate works best.
        txns.append(Transaction.model_validate(t))
    return txns
