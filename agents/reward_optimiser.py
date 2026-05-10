"""
Reward Optimiser Agent — Transaction-Level Card Recommendation

Flow:
1. Build spending profile from actual transactions (with top transactions per category)
2. Load indian_cards.json and score every card deterministically
3. Use LLM to generate transaction-level "what you missed" insights
4. Return top pick + runner-ups with concrete benefits
"""

import json
import logging
import os
import re
import asyncio
from pathlib import Path
from functools import partial
from langchain_core.messages import SystemMessage, HumanMessage
from agents.utils import get_llm, months_of_data

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Category mapping: parser categories → card reward categories
# ---------------------------------------------------------------------------
PARSER_TO_CARD_CATEGORY = {
    "food_dining": "dining",
    "groceries": "groceries",
    "streaming": "streaming",
    "entertainment": "entertainment",
    "travel": "travel",
    "fuel": "fuel",
    "shopping": "shopping",
    "health": "shopping",        # health purchases map to general shopping
    "subscription": "streaming", # subscriptions behave like streaming
    "other": "shopping",         # fallback to base shopping rate
}

# Categories where credit cards earn no meaningful rewards — skip entirely
NON_REWARDABLE_CATEGORIES = {
    "transfer",
    "emi_loan",
    "investment",
    "utilities",
    "insurance",
}

# Path to the card database
CARDS_JSON_PATH = Path(__file__).parent.parent / "knowledge" / "cards" / "indian_cards.json"


def _load_cards_db() -> dict:
    """Load the indian_cards.json database."""
    try:
        with open(CARDS_JSON_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load cards database: {e}")
        return {}


def build_spending_profile(transactions, statement_months: int = 1) -> list[dict]:
    """
    Groups debit transactions by category.
    For each category, keeps total/monthly spend AND the top transactions.
    Excludes non-rewardable categories.
    """
    from collections import defaultdict

    months = statement_months
    category_data = defaultdict(lambda: {"total": 0, "count": 0, "transactions": []})

    for txn in transactions:
        if txn.amount > 0 and txn.category not in NON_REWARDABLE_CATEGORIES:
            cat = txn.category
            category_data[cat]["total"] += txn.amount
            category_data[cat]["count"] += 1
            category_data[cat]["transactions"].append({
                "merchant": txn.merchant_name,
                "amount": round(txn.amount, 2),
                "date": txn.date.strftime("%Y-%m-%d"),
                "description": txn.description[:60],
                "category": cat,
            })

    result = []
    for cat, data in category_data.items():
        # Sort transactions by amount descending, keep top 5
        top_txns = sorted(data["transactions"], key=lambda x: x["amount"], reverse=True)[:5]
        result.append({
            "category": cat,
            "card_category": PARSER_TO_CARD_CATEGORY.get(cat, "shopping"),
            "total_spend": round(data["total"], 2),
            "monthly_spend": round(data["total"] / months, 2),
            "transaction_count": data["count"],
            "top_transactions": top_txns,
        })

    result.sort(key=lambda x: x["monthly_spend"], reverse=True)
    return result[:7]  # Top 7 spending categories


def score_all_cards(spending_profile: list[dict], cards_db: dict) -> list[dict]:
    """
    Score every card against the user's actual spending profile.
    Returns all cards ranked by net_annual_value (rewards - annual fee).
    """
    scored = []

    for card_id, card in cards_db.items():
        rates = card.get("reward_rate_per_category", {})
        monthly_reward = 0.0
        category_rewards = []

        # Calculate precise monthly reward
        for sp in spending_profile:
            card_cat = sp["card_category"]
            rate = rates.get(card_cat, card.get("reward_rate_base", 1.0))
            reward = sp["monthly_spend"] * rate / 100
            monthly_reward += reward
            category_rewards.append({
                "category": sp["category"],
                "card_category": card_cat,
                "monthly_spend": sp["monthly_spend"],
                "rate": rate,
                "monthly_reward": round(reward, 2),
            })

        # CRITICAL: Fix consistency between monthly and annual values
        # Derive the total from the sum of rounded parts for pixel-perfect UI consistency
        monthly_reward_rounded = round(sum(cr["monthly_reward"] for cr in category_rewards), 2)
        annual_fee = card.get("annual_fee", 0)
        annual_reward = monthly_reward_rounded * 12
        net_annual = round(annual_reward - annual_fee, 2)

        scored.append({
            "card_id": card_id,
            "name": card.get("name", card_id),
            "issuer": card.get("issuer", ""),
            "tier": card.get("tier", "entry"),
            "image_url": card.get("image_url", "/assets/cards/generic.png"),
            "annual_fee": annual_fee,
            "card_network": card.get("card_network", ""),
            "estimated_monthly_reward": monthly_reward_rounded,
            "net_annual_value": net_annual,
            "category_rewards": sorted(category_rewards, key=lambda x: x["monthly_reward"], reverse=True),
            "key_perks": _extract_perks(card),
            "reward_type": card.get("reward_type", "Reward Points"),
            "lounge_access": card.get("lounge_access", {}),
            "joining_bonus": card.get("joining_bonus", ""),
            "description": card.get("description", ""),
        })

    scored.sort(key=lambda x: x["net_annual_value"], reverse=True)
    return scored


def _extract_perks(card: dict) -> list[str]:
    """Extract key perks from a card's data into a concise list."""
    perks = []
    lounge = card.get("lounge_access", {})
    if lounge.get("domestic") and lounge["domestic"] != "0":
        perks.append(f"{lounge['domestic']} domestic lounge access")
    if lounge.get("international") and lounge["international"] != "0":
        perks.append(f"{lounge['international']} international lounge access")
    if card.get("joining_bonus") and card["joining_bonus"] != "None":
        perks.append(f"Joining: {card['joining_bonus']}")
    if card.get("fuel_surcharge_waiver") and card["fuel_surcharge_waiver"] != "None":
        perks.append(f"Fuel waiver: {card['fuel_surcharge_waiver']}")
    if card.get("forex_markup") == 0:
        perks.append("Zero forex markup")
    for ins in card.get("insurance", []):
        perks.append(ins)
    return perks[:6]


def _build_missed_rewards_input(top_card: dict, spending_profile: list[dict]) -> list[dict]:
    """
    Build the list of top transactions with their deterministic reward info
    for the LLM to enrich with human-readable 'what you missed' descriptions.
    """
    all_txns = []
    rates = {cr["category"]: cr["rate"] for cr in top_card["category_rewards"]}

    for sp in spending_profile:
        card_cat = sp["card_category"]
        rate = rates.get(sp["category"], 1.0)
        for txn in sp["top_transactions"]:
            reward_amount = round(txn["amount"] * rate / 100, 2)
            all_txns.append({
                "merchant": txn["merchant"],
                "amount": txn["amount"],
                "date": txn["date"],
                "category": sp["category"],
                "card_name": top_card["name"],
                "reward_rate": rate,
                "reward_earned": reward_amount,
                "reward_type": top_card["reward_type"],
            })

    # Sort by reward amount and take top 8 most impactful
    all_txns.sort(key=lambda x: x["reward_earned"], reverse=True)
    return all_txns[:8]


async def run_reward_optimiser(
    transactions,
    api_key: str,
    provider: str = "google",
    model_id: str = "gemini-2.5-flash-lite",
    vectorstore=None,  # kept for backward compat with supervisor, not used
    exa_api_key: str = "",
    statement_months: int = 1
) -> list[dict]:
    """
    Main entry point for the reward optimiser agent.
    1. Build spending profile with actual transactions
    2. Score all cards deterministically
    3. LLM generates transaction-level 'what you missed' insights
    """
    # Step 1: Build spending profile
    spending_profile = build_spending_profile(transactions, statement_months)
    if not spending_profile:
        return []

    # Step 2: Score all cards
    cards_db = _load_cards_db()
    if not cards_db:
        return [{"type": "reward_optimisation", "error": "Card database unavailable", "summary": "Could not load card data."}]

    ranked_cards = score_all_cards(spending_profile, cards_db)
    if not ranked_cards:
        return []

    top_card = ranked_cards[0]
    runner_ups = ranked_cards[1:3]

    # Step 3: Build transaction-level missed rewards
    missed_txns = _build_missed_rewards_input(top_card, spending_profile)

    # Step 4: LLM call for human-readable insights
    print(f"[Guardian] Reward: Top pick is {top_card['name']} (net ₹{top_card['net_annual_value']:,.0f}/yr)", flush=True)
    print(f"[Guardian] Reward: Generating transaction-level insights (Model: {model_id})...", flush=True)

    system = """You are India's best credit card rewards advisor. You are given:
1. A recommended credit card and its reward structure
2. A list of the user's actual transactions with calculated reward amounts

Your job is to make the rewards TANGIBLE and EXCITING for the user.

For each transaction, write a short "what_you_missed" description that translates
the raw reward points/cashback into something the user can actually buy or visualize.
CRITICAL RULE: Do NOT just say "₹X back in your account". You MUST convert the ₹ value into a tangible, real-world item based on the category (e.g., "a free cappuccino at Starbucks", "a weekend movie ticket", "a Swiggy dessert", "a free Uber ride to work").

Also write:
1. "why_for_you" — A personalized pitch for why this card matches them. CRITICAL RULE: You MUST explicitly name their top 1-2 spending categories and their actual merchant names from the data provided. Make it undeniable that this card was chosen specifically for their exact spending habits.
2. "summary" — A punchy one-liner about how much they left on the table.

Return ONLY a valid JSON object with this structure:
{
  "missed_rewards": [
    {
      "merchant": str,
      "amount": float,
      "date": str,
      "category": str,
      "card_name": str,
      "reward_rate": float,
      "reward_earned": float,
      "reward_type": str,
      "what_you_missed": str
    }
  ],
  "why_for_you": str,
  "summary": str
}

No markdown. No commentary. Valid JSON only."""

    human = (
        f"Recommended card: {top_card['name']} ({top_card['issuer']})\n"
        f"Card type: {top_card['reward_type']}\n"
        f"Annual fee: ₹{top_card['annual_fee']:,}\n"
        f"Key perks: {', '.join(top_card['key_perks'][:4])}\n"
        f"Card description: {top_card['description']}\n\n"
        f"User's top transactions with calculated rewards:\n"
        f"{json.dumps(missed_txns, indent=2)}\n\n"
        f"Total estimated monthly reward: ₹{top_card['estimated_monthly_reward']:,.0f}\n"
        f"Net annual value after fee: ₹{top_card['net_annual_value']:,.0f}"
    )

    try:
        from agents.llm_factory import create_llm
        llm = create_llm(api_key, provider, model_id)
        response = llm.invoke([
            SystemMessage(content=system),
            HumanMessage(content=human)
        ])

        text = response.content.strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
        text = re.sub(r',\s*([\]}])', r'\1', text)

        llm_result = json.loads(text)
    except Exception as e:
        logger.warning(f"LLM enrichment failed, using fallback: {e}")
        llm_result = {
            "missed_rewards": [{**t, "what_you_missed": f"₹{t['reward_earned']:,.0f} in {t['reward_type']}"} for t in missed_txns],
            "why_for_you": f"{top_card['name']} is the best match for your spending profile.",
            "summary": f"You could save ₹{top_card['net_annual_value']:,.0f}/year with {top_card['name']}.",
        }

    # Step 5: Assemble final result
    result = {
        "type": "reward_optimisation",
        "top_pick": {
            "card_id": top_card["card_id"],
            "name": top_card["name"],
            "issuer": top_card["issuer"],
            "tier": top_card["tier"],
            "image_url": top_card["image_url"],
            "annual_fee": top_card["annual_fee"],
            "card_network": top_card["card_network"],
            "estimated_monthly_reward": top_card["estimated_monthly_reward"],
            "net_annual_value": top_card["net_annual_value"],
            "category_rewards": top_card["category_rewards"],
            "key_perks": top_card["key_perks"],
            "reward_type": top_card["reward_type"],
            "lounge_access": top_card["lounge_access"],
            "joining_bonus": top_card["joining_bonus"],
            "why_for_you": llm_result.get("why_for_you", ""),
        },
        "missed_rewards": llm_result.get("missed_rewards", missed_txns),
        "spending_profile": [
            {
                "category": sp["category"],
                "monthly_spend": sp["monthly_spend"],
                "transaction_count": sp["transaction_count"],
                "top_transactions": sp["top_transactions"][:3],
            }
            for sp in spending_profile
        ],
        "runner_ups": [
            {
                "card_id": r["card_id"],
                "name": r["name"],
                "issuer": r["issuer"],
                "image_url": r["image_url"],
                "net_annual_value": r["net_annual_value"],
                "estimated_monthly_reward": r["estimated_monthly_reward"],
                "annual_fee": r["annual_fee"],
                "one_liner": r["description"],
            }
            for r in runner_ups
        ],
        "total_missed_monthly": top_card["estimated_monthly_reward"],
        "total_missed_annual": round(top_card["estimated_monthly_reward"] * 12, 2),
        "summary": llm_result.get("summary", ""),
    }

    print(f"[Guardian] Reward Optimiser: Complete. Top pick: {top_card['name']}", flush=True)
    return [result]
