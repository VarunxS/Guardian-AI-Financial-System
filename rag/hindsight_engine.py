"""
Hindsight Engine — analyses user's actual spending against optimal card mapping
and generates a retrospective report of missed rewards.
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path

from agents.llm_factory import create_llm
from langchain_core.documents import Document
from langchain_core.messages import SystemMessage, HumanMessage

from ingestion.schema import Transaction
from rag.vectorstore import GuardianVectorStore

logger = logging.getLogger(__name__)

HINDSIGHT_SYSTEM_PROMPT = (
    "You are a credit card optimisation expert. Given a user's actual spending "
    "data and the best available Indian credit cards, explain specifically how "
    "much reward rupee value they missed out on this month, and exactly which "
    "card they should have used for each category. Be specific with numbers. "
    "Use a direct, non-judgmental tone."
)


class HindsightEngine:
    """Retrospective analysis of user spend vs optimal card mapping."""

    def __init__(self):
        cards_path = Path(__file__).parent.parent / "knowledge" / "cards" / "indian_cards.json"
        with open(cards_path, "r") as f:
            self.cards_data: dict = json.load(f)

    def generate(
        self,
        user_id: str,
        transactions: list[Transaction],
        vectorstore: GuardianVectorStore,
        api_key: str,
        provider: str = "google",
        model_id: str = "gemini-2.5-flash-lite",
    ) -> dict:
        """
        Generate a hindsight report for a user's transactions.

        Args:
            user_id: User identifier
            transactions: List of parsed transactions
            vectorstore: GuardianVectorStore instance
            api_key: User's OpenAI API key (BYOK)

        Returns:
            Hindsight report dict
        """
        try:
            # Compute category spend totals (debits only)
            category_spend: dict[str, float] = defaultdict(float)
            for txn in transactions:
                if txn.amount > 0:
                    category_spend[txn.category] += txn.amount

            # Top 5 categories by spend
            sorted_categories = sorted(
                category_spend.items(), key=lambda x: x[1], reverse=True
            )[:5]

            category_breakdown = []
            total_missed = 0.0
            optimal_cards_set: set[str] = set()
            hindsight_docs: list[Document] = []

            for category, spend in sorted_categories:
                if spend < 100:
                    continue

                # Find best card for this category
                best_card_id, best_rate = self._find_best_card(category)
                if best_card_id is None:
                    continue

                best_card = self.cards_data[best_card_id]
                assumed_current_rate = 1.0  # conservative baseline
                current_reward = spend * assumed_current_rate / 100
                optimal_reward = spend * best_rate / 100
                missed = optimal_reward - current_reward

                if missed > 0:
                    total_missed += missed
                    optimal_cards_set.add(best_card["name"])

                    breakdown_entry = {
                        "category": category,
                        "user_spend": round(spend, 2),
                        "current_estimated_reward": round(current_reward, 2),
                        "optimal_card": best_card["name"],
                        "optimal_reward": round(optimal_reward, 2),
                        "missed_value": round(missed, 2),
                    }
                    category_breakdown.append(breakdown_entry)

                    # Create a Document for the hindsight collection
                    doc_text = (
                        f"User {user_id} spent ₹{spend:,.0f} on {category}. "
                        f"Best card: {best_card['name']} at {best_rate}% = ₹{optimal_reward:,.0f} reward. "
                        f"Missed ₹{missed:,.0f} by using a card with ~{assumed_current_rate}% rate."
                    )
                    hindsight_docs.append(
                        Document(
                            page_content=doc_text,
                            metadata={"user_id": user_id, "category": category},
                        )
                    )

            # Add hindsight docs to vectorstore
            if hindsight_docs:
                vectorstore.add_hindsight_docs(user_id, hindsight_docs)

            # Determine optimal card stack (top 2-3 cards covering all categories)
            optimal_stack = self._compute_optimal_stack(sorted_categories)

            # Generate LLM summary
            summary = self._generate_summary(
                api_key=api_key,
                provider=provider,
                model_id=model_id,
                total_missed=total_missed,
                category_breakdown=category_breakdown,
                optimal_stack=optimal_stack,
            )

            return {
                "total_missed_rewards": round(total_missed, 2),
                "category_breakdown": category_breakdown,
                "summary": summary,
                "optimal_card_stack": optimal_stack,
            }

        except Exception as e:
            logger.error(f"HindsightEngine error: {e}")
            return {
                "total_missed_rewards": 0,
                "category_breakdown": [],
                "summary": f"Unable to generate hindsight report: {str(e)}",
                "optimal_card_stack": [],
            }

    def _find_best_card(self, category: str) -> tuple[str | None, float]:
        """Find the card with the highest reward rate for a category."""
        best_card_id = None
        best_rate = 0.0

        for card_id, card in self.cards_data.items():
            rate = card.get("reward_rate_per_category", {}).get(
                category, card.get("reward_rate_base", 0)
            )
            if rate > best_rate:
                best_rate = rate
                best_card_id = card_id

        return best_card_id, best_rate

    def _compute_optimal_stack(
        self,
        sorted_categories: list[tuple[str, float]],
    ) -> list[str]:
        """Find 2-3 cards that optimally cover the user's top spending categories."""
        # For each category, find the best card
        category_best: dict[str, str] = {}
        for category, _ in sorted_categories:
            card_id, _ = self._find_best_card(category)
            if card_id:
                category_best[category] = self.cards_data[card_id]["name"]

        # Count which cards appear most frequently as "best"
        card_counts: dict[str, int] = defaultdict(int)
        for card_name in category_best.values():
            card_counts[card_name] += 1

        # Return top 3 by frequency
        sorted_cards = sorted(card_counts.items(), key=lambda x: x[1], reverse=True)
        return [card for card, _ in sorted_cards[:3]]

    def _generate_summary(
        self,
        api_key: str,
        provider: str,
        model_id: str,
        total_missed: float,
        category_breakdown: list[dict],
        optimal_stack: list[str],
    ) -> str:
        """Use GPT-4o for hindsight summary. Falls back to template."""
        fallback = (
            f"Based on your spending, you missed approximately ₹{total_missed:,.0f} "
            f"in rewards this period. The optimal card stack for your spending pattern "
            f"would be: {', '.join(optimal_stack)}."
        )

        try:
            llm = create_llm(api_key, provider, model_id, temperature=0.4)

            breakdown_text = "\n".join(
                f"- {b['category']}: Spent ₹{b['user_spend']:,.0f}, "
                f"earned ~₹{b['current_estimated_reward']:,.0f}, "
                f"could have earned ₹{b['optimal_reward']:,.0f} with {b['optimal_card']} "
                f"(missed ₹{b['missed_value']:,.0f})"
                for b in category_breakdown
            )

            prompt = (
                f"Total missed rewards: ₹{total_missed:,.0f}\n\n"
                f"Category breakdown:\n{breakdown_text}\n\n"
                f"Optimal card stack: {', '.join(optimal_stack)}"
            )

            response = llm.invoke([
                SystemMessage(content=HINDSIGHT_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ])
            return response.content.strip()
        except Exception as e:
            logger.warning(f"LLM call failed for hindsight summary: {e}")
            return fallback