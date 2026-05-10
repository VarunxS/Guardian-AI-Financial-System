import json
import logging
import re
from collections import defaultdict
from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel, Field
from typing import Literal, Optional
from agents.utils import get_llm
from ingestion.schema import Transaction

logger = logging.getLogger(__name__)

FIXED_CATEGORIES = {"emi_loan", "investment", "transfer", "utilities", "insurance"}
SEMI_FIXED_CATEGORIES = {"groceries", "health", "fuel", "transport"}
DISCRETIONARY_CATEGORIES = {"food_dining", "shopping", "entertainment", "streaming", "subscription", "travel", "other"}

COMPRESSION_BALANCED = {
    "discretionary": 0.25,
    "semi_fixed": 0.10
}
COMPRESSION_CONSERVATIVE = {
    "discretionary": 0.50,
    "semi_fixed": 0.20
}

def forecast_category_spend(transactions: list[Transaction], statement_months: int = 1) -> dict:
    """
    Calculates monthly averages for each category using the explicit statement period.
    """
    debits = [t for t in transactions if t.amount > 0]
    if not debits or statement_months <= 0:
        return {"by_category": {}, "total": 0, "months_of_data": statement_months, "last_month_total": 0}

    # Group by category and sum all debits
    from collections import defaultdict
    category_totals = defaultdict(float)
    
    # We still need last_month_total, so let's find the latest month in the data
    monthly_data = defaultdict(float)
    
    for t in debits:
        category_totals[t.category] += t.amount
        month_key = t.date.strftime("%Y-%m")
        monthly_data[month_key] += t.amount

    sorted_months = sorted(monthly_data.keys())
    last_month_total = monthly_data[sorted_months[-1]] if sorted_months else 0

    forecasted_by_cat = {}
    for cat, total in category_totals.items():
        forecasted_by_cat[cat] = total / statement_months

    # Exclude internal moves and wealth building from 'Spending' overhead
    lifestyle_total = sum(v for k, v in forecasted_by_cat.items() if k not in ("transfer", "investment"))

    return {
        "by_category": forecasted_by_cat,
        "total": lifestyle_total,
        "months_of_data": statement_months,
        "last_month_total": last_month_total
    }

def compute_surplus(forecasted_total: float, monthly_income: float) -> dict:
    surplus = monthly_income - forecasted_total
    health = "strong" if surplus > monthly_income * 0.3 else "tight" if surplus > 0 else "negative"
    return {
        "monthly_income": monthly_income,
        "forecasted_total": forecasted_total,
        "forecasted_surplus": surplus,
        "surplus_health": health
    }

def simulate_scenarios(forecasted_by_cat: dict, surplus_base: dict, goals: list[dict]) -> list[dict]:
    scenarios = []
    income = surplus_base["monthly_income"]
    
    # Pre-calculate compressed surpluses
    def get_compressed_surplus(compression):
        compressed_total = 0
        for cat, val in forecasted_by_cat.items():
            if cat in DISCRETIONARY_CATEGORIES:
                compressed_total += val * (1 - compression["discretionary"])
            elif cat in SEMI_FIXED_CATEGORIES:
                compressed_total += val * (1 - compression["semi_fixed"])
            else:
                compressed_total += val
        return max(0, income - compressed_total)

    surplus_balanced = get_compressed_surplus(COMPRESSION_BALANCED)
    surplus_conservative = get_compressed_surplus(COMPRESSION_CONSERVATIVE)

    for goal in goals:
        remaining = max(0, goal["target_amount"] - (goal.get("saved_amount") or 0))
        if goal["goal_type"] == "trip":
            remaining *= 1.15 # 15% incidental buffer
        
        # Current Pace
        contrib_current = surplus_base["forecasted_surplus"] * goal["surplus_pct"]
        months_current = remaining / contrib_current if contrib_current > 0 else 9999
        
        # Balanced
        contrib_balanced = surplus_balanced * goal["surplus_pct"]
        months_balanced = remaining / contrib_balanced if contrib_balanced > 0 else 9999
        
        # Conservative
        contrib_conservative = surplus_conservative * goal["surplus_pct"]
        months_conservative = remaining / contrib_conservative if contrib_conservative > 0 else 9999

        scenarios.append({
            "goal_id": goal.get("goal_id", str(uuid4())),
            "name": goal["name"],
            "current_pace_months": round(months_current, 1),
            "balanced_months": round(months_balanced, 1),
            "conservative_months": round(months_conservative, 1),
            "days_saved_balanced": round((months_current - months_balanced) * 30) if months_current < 9999 else 0,
            "days_saved_conservative": round((months_current - months_conservative) * 30) if months_current < 9999 else 0,
            "monthly_contribution_current": contrib_current,
            "remaining_amount": remaining
        })
    
    return scenarios

def find_biggest_lever(forecasted_by_cat: dict, surplus_base: dict, goals: list[dict]) -> dict:
    best_lever = {"category": None, "total_days_saved": -1}
    income = surplus_base["monthly_income"]
    
    for cat in DISCRETIONARY_CATEGORIES:
        if cat not in forecasted_by_cat or forecasted_by_cat[cat] < 100: continue
        
        # Compress ONLY this category by 40%
        saving = forecasted_by_cat[cat] * 0.4
        new_surplus = surplus_base["forecasted_surplus"] + saving
        
        total_days = 0
        days_per_goal = {}
        
        for goal in goals:
            remaining = goal["target_amount"] - (goal.get("saved_amount") or 0)
            contrib_old = surplus_base["forecasted_surplus"] * goal["surplus_pct"]
            contrib_new = new_surplus * goal["surplus_pct"]
            
            if contrib_old > 0 and contrib_new > 0:
                months_old = remaining / contrib_old
                months_new = remaining / contrib_new
                days = round((months_old - months_new) * 30)
                total_days += days
                days_per_goal[goal.get("goal_id")] = days
        
        if total_days > best_lever["total_days_saved"]:
            best_lever = {
                "category": cat,
                "current_monthly": round(forecasted_by_cat[cat]),
                "suggested_monthly": round(forecasted_by_cat[cat] - saving),
                "monthly_saving": round(saving),
                "days_saved_per_goal": days_per_goal,
                "total_days_saved": total_days
            }
            
    return best_lever

def compute_behavioural_goal_impacts(transactions: list[Transaction], scenarios: list[dict], goals: list[dict]) -> list[dict]:
    if not goals or not scenarios: return []
    
    debits = [t for t in transactions if t.amount > 0]
    impacts = []
    
    # 1. Late Night
    has_timestamps = any(t.date.hour != 0 or t.date.minute != 0 for t in debits)
    late_night_excess = 0
    if has_timestamps:
        late_night_total = sum(t.amount for t in debits if t.date.hour >= 23 or t.date.hour < 2)
        late_night_excess = late_night_total * 0.6
    
    # 2. Food Delivery
    food_delivery_total = sum(t.amount for t in debits if t.category == "food_dining")
    order_count = len([t for t in debits if t.category == "food_dining"])
    food_excess = max(0, food_delivery_total - (order_count * 150)) # ₹150 buffer for home meal
    
    # 3. Weekend Spike
    weekend_total = sum(t.amount for t in debits if t.date.weekday() >= 5)
    weekday_total = sum(t.amount for t in debits if t.date.weekday() < 5)
    
    # Simple check for weekend intensity
    weekend_daily = weekend_total / 8 if weekend_total > 0 else 0
    weekday_daily = weekday_total / 22 if weekday_total > 0 else 0
    weekend_excess = (weekend_daily - weekday_daily) * 8 if (weekend_daily > weekday_daily * 1.5) else 0

    patterns = [
        ("Late Night Spend", late_night_excess, "Impulsive late-night orders identified from transaction timestamps."),
        ("Dining & Delivery", food_excess, "High frequency of restaurant/delivery spend vs home cooking."),
        ("Weekend Spikes", weekend_excess, "Significantly higher spending intensity on weekends vs weekdays.")
    ]
    
    primary_goal = scenarios[0] # Usually the one with highest pct
    
    for title, excess, obs in patterns:
        if excess < 800: continue # Higher threshold for significance
        
        # Calculate days cost on primary goal
        # Formula: (Excess / MonthlyContribution) * 30 days
        contribution = max(1, primary_goal.get("monthly_contribution_current", 1))
        days_cost = round((excess / contribution) * 30)
        
        if days_cost >= 2: # Show if it costs at least 2 days
            impacts.append({
                "behaviour": title,
                "observation": obs,
                "goal_name": primary_goal["name"],
                "days_cost": days_cost,
                "suggestion": f"Reducing this '{title}' pattern could save {days_cost} days on your {primary_goal['name']} goal."
            })
            
    return impacts

# ── Phase 2: New Pydantic Models ──────────────────────────────────────

class BehaviouralImpact(BaseModel):
    behaviour: str
    observation: str
    goal_name: str
    days_cost: int
    suggestion: str

class GoalFeasibility(BaseModel):
    goal_id: str
    goal_name: str
    status: Literal["achievable", "stretched", "unrealistic"]
    status_reason: str = Field(
        description="One sentence explaining why this classification. "
                    "Use rupee amounts and timeframes."
    )
    current_pace_months: float
    balanced_months: float
    conservative_months: float
    biggest_lever_sentence: str = Field(
        description="Names the category, current amount, suggested amount, "
                    "and exactly how many months/days this saves on THIS goal only."
    )
    motivation_line: str = Field(
        description="References a real milestone (festival, season, year) "
                    "if goal is within 12 months. Otherwise references "
                    "the progress already made."
    )
    quick_win: str = Field(
        description="One specific action this month. Names a merchant or "
                    "category, rupee amount, and days saved on THIS goal."
    )
    next_month_target: str = Field(
        description="One realistic, sustainable spending change for next month. "
                    "Calibrated to spending personality — not maximum possible cut."
    )
    acceleration_tips: list[str] = Field(
        description="Exactly 2 tips. Each names a specific category or merchant, "
                    "a rupee amount, and the goal impact. Never generic."
    )

class BudgetGoalsResponse(BaseModel):
    spending_personality: Literal[
        "comfort_spender", "anxious_saver", "inconsistent", "balanced"
    ]
    spending_personality_explanation: str = Field(
        description="2 sentences. What this personality means for this user "
                    "specifically, using their actual category data."
    )
    one_line_verdict: str = Field(
        description="One honest sentence about their overall financial situation. "
                    "Direct. No jargon. No hedging."
    )
    top_recommendation: str = Field(
        description="The single highest-leverage change across all goals. "
                    "Specific merchant or category, rupee amount, total days saved "
                    "across all goals combined."
    )
    goal_priority_note: str = Field(
        description="If surplus_pct allocation is suboptimal, explain why and "
                    "suggest a rebalance. If allocation is fine, say so in one "
                    "sentence and explain why it works."
    )
    goal_cards: list[GoalFeasibility]
    behavioural_goal_impacts: list[BehaviouralImpact] = Field(
        description="A list of friction points detected in the user's spending habits."
    )

# ── Phase 3: New LLM Call Architecture ───────────────────────────────────

def run_budget_goals_agent(
    transactions: list[Transaction],
    monthly_income: float,
    goals: list[dict],
    api_key: str,
    provider: str = "google",
    model_id: str = "gemini-2.5-flash-lite",
    statement_months: int = 1,
    precomputed_forecast: dict = None,
    precomputed_impacts: list[dict] = None
) -> dict:

    # ── Phase 1: Python math (unchanged) ─────────────────────────────
    forecasted = precomputed_forecast or forecast_category_spend(transactions, statement_months)
    surplus = compute_surplus(forecasted["total"], monthly_income) \
        if monthly_income > 0 \
        else {
            "forecasted_total": forecasted["total"],
            "forecasted_surplus": 0,
            "surplus_health": "unknown",
            "monthly_income": 0
        }

    if not goals or monthly_income <= 0:
        return {
            "type": "budget_goals",
            "error": "missing_profile",
            "message": "Complete your financial profile (Income & Goals) "
                       "for full predictive analysis.",
            "budget_summary": {
                "forecasted_total": forecasted["total"],
                "forecasted_surplus": surplus.get("forecasted_surplus", 0),
                "surplus_health": surplus.get("surplus_health", "unknown"),
                "one_line_verdict": "Provide income and goals in Settings "
                                    "to unlock Guardian's full strategy engine."
            },
            "raw": {
                "budget_forecast": forecasted,
                "surplus": surplus,
                "goals": goals,
                "monthly_income": monthly_income
            }
        }

    scenarios = simulate_scenarios(
        forecasted.get("by_category", {}), surplus, goals
    )
    biggest_lever = find_biggest_lever(
        forecasted.get("by_category", {}), surplus, goals
    )
    
    if precomputed_impacts is not None:
        behavioural_impacts = precomputed_impacts
    else:
        behavioural_impacts = compute_behavioural_goal_impacts(
            transactions, scenarios, goals
        )

    # ── Phase 2: Call 1 — Reasoning chain ────────────────────────────
    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        from agents.llm_factory import create_llm
        llm = create_llm(api_key, provider, model_id)

        reasoning_system_prompt = """
You are a senior personal finance advisor reviewing a client's
financial data before your first meeting with them.

You have their spending by category, monthly income, surplus,
goals with timelines, scenario simulations, and behavioural patterns.

Before you can advise them, you need to form honest opinions.
Think through each of these seven questions and write your analysis.
Be direct. Use their actual rupee amounts. Do not hedge.

1. GOAL FEASIBILITY: Is each goal actually achievable? Classify as
   achievable (under 24 months at balanced pace), stretched (24-48 months),
   or unrealistic (48+ months). Explain why with their numbers.

2. SPENDING PERSONALITY: What kind of spender are they?
   comfort_spender / anxious_saver / inconsistent / balanced.
   What does their category breakdown tell you about their habits?

3. BIGGEST BLOCKER: What single behaviour, if changed, has the most
   impact on all their goals combined? Name it with rupee amounts.

4. GOAL PRIORITY CONFLICT: Do their surplus_pct allocations make sense
   given the goal amounts and timelines? If not, what would you suggest?

5. QUICK WIN: What is one specific thing they can do THIS MONTH that
   will show up in their numbers immediately? Name a merchant or category.

6. MOMENTUM: Have they started saving toward their goals? How does that
   change what you tell them?

7. REALISTIC TARGET: Given their personality type, what is the maximum
   sustainable change they can actually maintain for 3+ months?
   Not the maximum possible — the maximum maintainable.

Write your thinking freely. This is internal reasoning only.
It will be used to generate advice for the client in the next step.
"""
        reasoning_human_msg = f"""Client financial data:

Monthly income: ₹{monthly_income:,.0f}
Forecasted monthly spend: ₹{forecasted['total']:,.0f}
Monthly surplus: ₹{surplus['forecasted_surplus']:,.0f}
Surplus health: {surplus['surplus_health']}

Spend by category:
{json.dumps(forecasted['by_category'], indent=2)}

Goals:
{json.dumps(goals, indent=2)}

Scenario simulations per goal:
{json.dumps(scenarios, indent=2)}

Biggest single lever:
{json.dumps(biggest_lever, indent=2)}

Behavioural patterns:
{json.dumps(behavioural_impacts, indent=2)}

Think through all seven questions carefully before forming any advice.
"""

        print("[Guardian] Phase 1: Reasoning through budget data...", flush=True)
        response = llm.invoke([
            SystemMessage(content=reasoning_system_prompt),
            HumanMessage(content=reasoning_human_msg)
        ])
        reasoning_text = response.content.strip()

        # ── Phase 3: Call 2 — Structured output ──────────────────────
        print("[Guardian] Phase 2: Generating structured advice...", flush=True)
        
        struct_system_prompt = """
You are Guardian's budget and goals advisor generating structured
advice for a personal finance dashboard.

You have already analysed this client's situation in your reasoning notes.
Now translate that analysis into the exact JSON schema provided.

Rules — strictly enforced:
- Every rupee amount must be a whole number (no decimals)
- biggest_lever_sentence must name: category + current ₹ + suggested ₹
  + months before + months after — for THIS goal only
- quick_win must name a specific merchant or category + exact ₹ + days saved
- next_month_target must be calibrated to spending_personality —
  comfort_spender gets smaller cuts, anxious_saver gets efficiency tips
- motivation_line must reference a specific real-world milestone
  (Diwali, summer, new year, graduation) if goal is under 12 months away
- acceleration_tips: exactly 2, each with specific ₹ and goal impact
- behavioural_goal_impacts: include the patterns identified in the raw data, 
  rewriting the 'suggestion' to be more motivational and specific.
- goal_priority_note: if allocation is fine say so and explain why —
  do not invent a problem where none exists
- one_line_verdict: honest, direct, no jargon, no hedging
- Return only valid JSON matching the schema. No markdown. No commentary.
"""
        struct_human_msg = f"""Your reasoning analysis:

{reasoning_text}

---

Raw financial data for reference:

Monthly income: ₹{monthly_income:,.0f}
Surplus: ₹{surplus['forecasted_surplus']:,.0f} ({surplus['surplus_health']})

Spend by category: {json.dumps(forecasted['by_category'])}

Goals: {json.dumps(goals)}

Scenarios: {json.dumps(scenarios)}

Biggest lever: {json.dumps(biggest_lever)}

Behavioural impacts: {json.dumps(behavioural_impacts)}

Now generate the structured JSON advice based on your reasoning above.
"""

        structured_llm = llm.with_structured_output(BudgetGoalsResponse)
        response_obj = structured_llm.invoke([
            SystemMessage(content=struct_system_prompt),
            HumanMessage(content=struct_human_msg)
        ])

        if isinstance(response_obj, BudgetGoalsResponse):
            result = response_obj.model_dump()
        else:
            result = response_obj

        # Inject deterministic math fields (never trust LLM for numbers)
        result["type"] = "budget_goals"
        result["raw"] = {
            "budget_forecast": forecasted,
            "surplus": surplus,
            "goals": goals,
            "scenarios": scenarios,
            "biggest_lever": biggest_lever,
            "behavioural_impacts": behavioural_impacts,
            "reasoning": reasoning_text   # store reasoning for debugging
        }

        # Always inject these from Python — never from LLM
        if "budget_summary" not in result:
            result["budget_summary"] = {}
        result["budget_summary"]["forecasted_total"] = \
            surplus["forecasted_total"]
        result["budget_summary"]["forecasted_surplus"] = \
            surplus["forecasted_surplus"]
        result["budget_summary"]["surplus_health"] = \
            surplus["surplus_health"]

        # Inject scenario numbers into each goal_card from Python
        # so UI always has accurate timelines regardless of LLM
        scenario_map = {s["goal_id"]: s for s in scenarios}
        
        # Verify card count matches goals
        if len(result.get("goal_cards", [])) != len(goals):
            logger.warning(f"Goal card count mismatch: {len(result.get('goal_cards', []))} vs {len(goals)}")
            # If the LLM dropped cards, we need to ensure they exist
            existing_ids = {c.get("goal_id") for c in result.get("goal_cards", [])}
            for goal in goals:
                if goal.get("goal_id") not in existing_ids:
                    # Inject a minimal fallback card
                    s = scenario_map.get(goal.get("goal_id"), {})
                    result["goal_cards"].append({
                        "goal_id": goal.get("goal_id"),
                        "goal_name": goal.get("name"),
                        "status": "stretched",
                        "status_reason": "Goal analysis fallback.",
                        "biggest_lever_sentence": "Optimization recommended.",
                        "motivation_line": "Keep going.",
                        "quick_win": "Review your spending.",
                        "next_month_target": "Maintain current surplus.",
                        "acceleration_tips": ["Save more", "Spend less"]
                    })

        for card in result.get("goal_cards", []):
            s = scenario_map.get(card.get("goal_id"), {})
            card["current_pace_months"] = s.get("current_pace_months", 0)
            card["balanced_months"] = s.get("balanced_months", 0)
            card["conservative_months"] = s.get("conservative_months", 0)
            card["days_saved_balanced"] = s.get("days_saved_balanced", 0)
            card["days_saved_conservative"] = s.get(
                "days_saved_conservative", 0
            )
            card["monthly_contribution"] = s.get(
                "monthly_contribution_current", 0
            )
            card["remaining_amount"] = s.get("remaining_amount", 0)
            
            # Add progress_pct for UI
            target = next((g["target_amount"] for g in goals if g.get("goal_id") == card.get("goal_id")), 1)
            saved = next((g.get("saved_amount", 0) or 0 for g in goals if g.get("goal_id") == card.get("goal_id")), 0)
            card["progress_pct"] = round((saved / max(1, target)) * 100)

        return result

    except Exception as e:
        logger.error(f"Budget Goals Agent failed: {e}")
        # Existing fallback return exactly as is
        return {
            "type": "budget_goals",
            "error": str(e),
            "raw": {
                "budget_forecast": forecasted,
                "surplus": surplus,
                "goals": goals,
                "scenarios": scenarios,
                "biggest_lever": biggest_lever,
                "behavioural_impacts": behavioural_impacts
            },
            "budget_summary": {
                "forecasted_total": forecasted["total"],
                "forecasted_surplus": surplus["forecasted_surplus"],
                "surplus_health": surplus["surplus_health"],
                "one_line_verdict": "Your budget is calculated, but AI advice is unavailable."
            },
            "goal_cards": [
                {
                    "goal_id": s["goal_id"],
                    "goal_name": s["name"],
                    "progress_pct": round((1 - s["remaining_amount"] / max(1, next(g["target_amount"] for g in goals if g.get("goal_id") == s["goal_id"]))) * 100),
                    "current_pace_months": s["current_pace_months"],
                    "balanced_months": s["balanced_months"],
                    "conservative_months": s["conservative_months"],
                    "biggest_lever_sentence": f"Focus on {biggest_lever['category']} to save {biggest_lever['total_days_saved']} days.",
                    "motivation_line": "Keep going, every rupee counts.",
                    "acceleration_tips": []
                } for s in scenarios
            ],
            "top_recommendation": "Maintain your current surplus to reach your primary goals."
        }
