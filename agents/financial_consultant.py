import json
import logging
from collections import defaultdict
from datetime import timedelta
from langchain_core.messages import SystemMessage, HumanMessage
from ingestion.schema import Transaction
from agents.utils import get_llm, build_merchant_spend_summary

logger = logging.getLogger(__name__)

FINANCIAL_CONSULTANT_SYSTEM = """
You are the user's Financial Consultant — a professional, direct, and insightful financial
advisor who has studied every rupee this person spent.

You have been given a detailed behavioural analysis of their transactions
including any unusual category spikes and new high-value merchants.

Write a personal financial report as a JSON object with these fields:

{
  "headline": str,
  "behavioural_findings": [
    {
      "title": str,
      "observation": str,      // 2-3 sentences, specific rupee amounts
      "what_it_means": str,    // 1 sentence on financial impact
      "suggestion": str        // 1 sentence, actionable, never preachy
    }
  ],
  "anomaly_flags": [
    {
      "title": str,
      "observation": str,      // what changed vs their own history
      "possible_reason": str,  // give a charitable explanation first
                               // e.g. "this could be a one-off event"
      "suggestion": str        // what to watch next month
    }
  ],
  "top_merchant_summary": str,
  "missed_savings": [
    {
      "opportunity": str,
      "estimated_saving": float,
      "explanation": str
    }
  ],
  "monthly_verdict": str,
  "health_rating": str         // "Strong" | "Decent" | "Needs attention" | "Concerning"
}

Rules for anomaly_flags:
- Only populate if category_anomalies or new_high_value_merchants exist in the data
- For category spikes: mention the specific category, this month's spend,
  and their own average — "you usually spend ₹X here, this month was ₹Y"
- For new high-value merchants: frame it as a heads-up, not a warning —
  "we noticed a new ₹X payment to [merchant] — if this was intentional, great"
- Never use the word "suspicious" or "fraud"
- Maximum 3 anomaly flags — prioritise highest rupee impact

Rules for all fields:
- Always use rupee amounts from the data. Never invent numbers.
- Lead with empathy, land with honesty.
- Never use the word "should" — say "consider", "try", "next time"
- Maximum 4 behavioural_findings — prioritise most impactful
- Tone: smart professional consultant who knows finance, not a bank chatbot
- Return only valid JSON. No markdown. No commentary outside the JSON.
"""

def analyse_behaviour(transactions: list[Transaction]) -> dict:
    """Phase 1: Python detection for behavioural analysis."""
    debits = [t for t in transactions if t.amount > 0]
    
    analysis = {
        "time_patterns": {},
        "category_concentration": {},
        "food_delivery_analysis": {},
        "impulse_purchase_signals": {},
        "merchant_spend_summary": {},
        "missed_savings": {},
        "monthly_trend": {},
        "category_anomalies": [],
        "new_high_value_merchants": []
    }
    
    if not debits:
        return analysis

    # --- Time Patterns ---
    late_night = [t for t in debits if t.date.hour >= 23 or t.date.hour < 2]
    weekends = [t for t in debits if t.date.weekday() >= 5]
    weekdays = [t for t in debits if t.date.weekday() < 5]
    
    weekend_spend = sum(t.amount for t in weekends)
    weekday_spend = sum(t.amount for t in weekdays)
    
    weekend_per_day = weekend_spend / max(len({t.date.date() for t in weekends}), 1)
    weekday_per_day = weekday_spend / max(len({t.date.date() for t in weekdays}), 1)
    
    analysis["time_patterns"] = {
        "late_night_spend": sum(t.amount for t in late_night),
        "late_night_count": len(late_night),
        "weekend_spend": weekend_spend,
        "weekday_spend": weekday_spend,
        "weekend_multiplier": weekend_per_day / weekday_per_day if weekday_per_day > 0 else 0
    }

    # --- Category Concentration ---
    cat_totals = defaultdict(float)
    for t in debits:
        cat_totals[t.category] += t.amount
        
    total_debit = sum(cat_totals.values())
    sorted_cats = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
    
    analysis["category_concentration"] = {
        "top_category": sorted_cats[0][0] if sorted_cats else None,
        "top_category_pct": (sorted_cats[0][1] / total_debit * 100) if sorted_cats and total_debit > 0 else 0,
        "top_3_categories": [{"category": k, "monthly_spend": v, "pct_of_total": (v / total_debit * 100)} 
                             for k, v in sorted_cats[:3]]
    }

    # --- Food Delivery Analysis ---
    food_merchants = {"zomato", "swiggy", "foodpanda", "eats"}
    food_orders = [t for t in debits if any(m in t.merchant_name.lower() for m in food_merchants)]
    
    if food_orders:
        avg_order = sum(t.amount for t in food_orders) / len(food_orders)
        analysis["food_delivery_analysis"] = {
            "total_food_delivery_spend": sum(t.amount for t in food_orders),
            "order_count": len(food_orders),
            "average_order_value": avg_order,
            "estimated_cooking_savings": max(0, (avg_order - 80) * len(food_orders))
        }

    # --- Impulse Purchase Signals ---
    large_txns = [t for t in debits if t.amount > 2000 and t.category not in {"emi_loan", "transfer", "investment", "utilities"}]
    late_night_large = [t for t in large_txns if t in late_night]
    
    merchants_count = defaultdict(int)
    for t in debits:
        merchants_count[t.merchant_name] += 1
    frequent_merchants = [m for m, count in merchants_count.items() if count > 8]
    
    analysis["impulse_purchase_signals"] = {
        "large_single_transactions": [{"merchant": t.merchant_name, "amount": t.amount} for t in large_txns],
        "late_night_large_count": len(late_night_large),
        "late_night_large_spend": sum(t.amount for t in late_night_large),
        "same_merchant_frequency": frequent_merchants
    }

    # --- Merchant Spend Summary ---
    spend_summary = build_merchant_spend_summary(transactions)
    sorted_merchants = sorted(spend_summary.items(), key=lambda x: x[1]["total_spent"], reverse=True)
    
    analysis["merchant_spend_summary"] = {
        "top_10_merchants": [{"merchant": k, "total_spent": v["total_spent"], "transaction_count": v["transaction_count"]} 
                             for k, v in sorted_merchants[:10]]
    }

    # --- Missed Savings ---
    emi_merchants = {"amazon", "flipkart", "croma", "reliance digital", "apple", "samsung"}
    emi_misses = [t for t in debits if t.amount > 5000 and any(m in t.merchant_name.lower() for m in emi_merchants) and "emi" not in t.description.lower()]
    
    round_numbers = [t for t in debits if t.amount in {500, 1000, 2000, 5000}]
    
    analysis["missed_savings"] = {
        "emi_without_nocost": [{"merchant": t.merchant_name, "amount": t.amount} for t in emi_misses],
        "round_number_transactions_count": len(round_numbers)
    }

    # --- Monthly Trend ---
    monthly = defaultdict(float)
    for t in debits:
        month_key = t.date.strftime("%Y-%m")
        monthly[month_key] += t.amount
        
    sorted_months = sorted(monthly.keys())
    trend = "stable"
    if len(sorted_months) >= 2:
        last_month = monthly[sorted_months[-1]]
        prior_months_avg = sum(monthly[m] for m in sorted_months[:-1]) / (len(sorted_months) - 1)
        if last_month > prior_months_avg * 1.1:
            trend = "increasing"
        elif last_month < prior_months_avg * 0.9:
            trend = "decreasing"
            
    analysis["monthly_trend"] = {
        "spend_by_month": dict(monthly),
        "trend": trend
    }

    # --- Category Anomalies ---
    if len(sorted_months) >= 2:
        recent_month_key = sorted_months[-1]
        prior_months = sorted_months[:-1]
        
        # Spend per category for recent month
        recent_cat_spend = defaultdict(float)
        for t in debits:
            if t.date.strftime("%Y-%m") == recent_month_key:
                recent_cat_spend[t.category] += t.amount
                
        # Average spend per category for prior months
        prior_cat_spend = defaultdict(float)
        for t in debits:
            if t.date.strftime("%Y-%m") in prior_months:
                prior_cat_spend[t.category] += t.amount
                
        num_prior_months = len(prior_months)
        category_anomalies = []
        
        for cat, recent_spend in recent_cat_spend.items():
            avg_prior_spend = prior_cat_spend[cat] / num_prior_months
            if avg_prior_spend > 0:
                spike = recent_spend / avg_prior_spend
                if spike >= 2.0:
                    category_anomalies.append({
                        "category": cat,
                        "this_month_spend": recent_spend,
                        "average_prior_spend": avg_prior_spend,
                        "spike_multiplier": spike,
                        "delta_rupees": recent_spend - avg_prior_spend
                    })
                    
        category_anomalies.sort(key=lambda x: x["delta_rupees"], reverse=True)
        analysis["category_anomalies"] = category_anomalies

    # --- New High-Value Merchants ---
    recent_cutoff = max(t.date for t in debits) - timedelta(days=30) if debits else None
    if recent_cutoff:
        prior_merchants = {t.merchant_name.lower() for t in debits if t.date < recent_cutoff}
        recent_txns = [t for t in debits if t.date >= recent_cutoff]
        
        new_merchants = []
        flagged_new = set()
        
        for t in recent_txns:
            m_lower = t.merchant_name.lower()
            if m_lower not in prior_merchants and m_lower not in flagged_new and t.amount > 2000:
                new_merchants.append({
                    "merchant": t.merchant_name,
                    "amount": t.amount,
                    "date": t.date.strftime("%d/%m/%Y"),
                    "category": t.category,
                    "first_ever_transaction": True
                })
                flagged_new.add(m_lower)
                
        new_merchants.sort(key=lambda x: x["amount"], reverse=True)
        analysis["new_high_value_merchants"] = new_merchants[:5]
    
    return analysis


def run_financial_consultant(transactions: list[Transaction], api_key: str, provider: str = "google", model_id: str = "gemini-2.5-flash-lite") -> dict:
    """Public entry point - runs Phase 1 and Phase 2."""
    behaviour = analyse_behaviour(transactions)
    
    try:
        from agents.llm_factory import create_llm
        llm = create_llm(api_key, provider, model_id)
        human_msg = f"Here is the behavioural analysis:\n{json.dumps(behaviour, indent=2)}"
        
        response = llm.invoke([
            SystemMessage(content=FINANCIAL_CONSULTANT_SYSTEM),
            HumanMessage(content=human_msg)
        ])
        
        import re
        text = response.content.strip()
        
        # Extract JSON block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
            
        # Fix trailing commas
        text = re.sub(r',\s*([\]}])', r'\1', text)
                
        result = json.loads(text)
        result["type"] = "financial_consultant"
        result["raw_behaviour"] = behaviour  # keep for dashboard use
        return result
    except Exception as e:
        logger.error(f"Financial Consultant LLM call failed: {e}")
        return {
            "type": "financial_consultant",
            "error": str(e),
            "headline": "Could not generate financial analysis.",
            "behavioural_findings": [],
            "monthly_verdict": "Analysis failed. Please retry.",
            "health_rating": "Unknown"
        }
