"""
Exa Research module — uses Exa AI to fetch live web intelligence for:
1. Credit card details and comparisons
2. Financial regulations and education
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from exa_py import Exa

from config import settings

logger = logging.getLogger(__name__)


class ExaResearch:
    """Live web research via Exa AI search API."""

    def __init__(self):
        self._client: Exa | None = None
        if settings.exa_api_key:
            try:
                self._client = Exa(api_key=settings.exa_api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Exa client: {e}")
        else:
            logger.info("EXA_API_KEY not set — live research disabled.")

    @property
    def is_available(self) -> bool:
        return self._client is not None

    def search_card_details(self, query: str, num_results: int = 5) -> list[dict]:
        """Search for latest Indian credit card details, rewards, and comparisons.

        Args:
            query: Search query about credit cards
            num_results: Number of results to return

        Returns:
            List of dicts with title, url, content, published_date
        """
        if not self.is_available:
            return []
        try:
            # Clean query: take first 100 chars, remove conversational filler
            clean_query = query[:120].lower().replace("compare", "").replace("tell me", "").replace("find", "").strip()
            
            results = self._client.search_and_contents(
                f"latest offers rewards benefits Indian credit card {clean_query}",
                type="auto",
                num_results=num_results,
                text={"max_characters": 1500},
                # use_autoprompt=True,
                start_published_date=(datetime.now() - timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            logger.info(f"Exa found {len(results.results)} results for card query: {clean_query}")
            return [
                {
                    "title": r.title or "Untitled",
                    "url": r.url,
                    "content": r.text[:1500] if r.text else "",
                    "published_date": r.published_date or "",
                }
                for r in results.results
            ]
        except Exception as e:
            logger.error(f"Exa card search failed: {e}")
            return []

    def search_finance_regulations(self, topic: str, num_results: int = 5) -> list[dict]:
        """Search for latest Indian financial regulations and education content.

        Args:
            topic: Finance topic to research (e.g., "RBI credit card rules")
            num_results: Number of results to return

        Returns:
            List of dicts with title, url, content, published_date
        """
        if not self.is_available:
            return []
        try:
            clean_topic = topic[:120].strip()
            results = self._client.search_and_contents(
                f"India personal finance {clean_topic} latest RBI SEBI regulation 2024 2025",
                type="auto",
                num_results=num_results,
                text={"max_characters": 1500},
                # use_autoprompt=True,
                start_published_date=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            logger.info(f"Exa found {len(results.results)} results for finance topic: {clean_topic}")
            return [
                {
                    "title": r.title or "Untitled",
                    "url": r.url,
                    "content": r.text[:1500] if r.text else "",
                    "published_date": r.published_date or "",
                }
                for r in results.results
            ]
        except Exception as e:
            logger.error(f"Exa finance regulation search failed: {e}")
            return []

    def research_merchant(self, merchant: str) -> dict:
        """Deep research on a merchant.

        Args:
            merchant: Merchant name

        Returns:
            Dict with sources and general info.
        """
        if not self.is_available:
            return {"risk_level": "unknown", "sources": []}
        try:
            results = self._client.search_and_contents(
                f"{merchant} consumer reviews complaints India",
                type="auto",
                num_results=3,
                text={"max_characters": 1200},
                # use_autoprompt=True,
                start_published_date=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            
            complaints = [
                {
                    "title": r.title or "Untitled",
                    "url": r.url,
                    "content": r.text[:1200] if r.text else "",
                }
                for r in results.results
            ]
            return {
                "risk_level": "unknown",
                "sources": [c.get("url", "") for c in complaints if c.get("url")],
            }
        except Exception as e:
            logger.error(f"Exa merchant research failed for {merchant}: {e}")
            return {"risk_level": "unknown", "sources": []}

    def search_card_deep_dive(self, card_name: str, num_results: int = 5) -> list[dict]:
        """Deep dive search for a specific card's latest offers, reviews, and benefits.

        Args:
            card_name: Full card name (e.g. "HDFC Infinia")
            num_results: Number of results to return

        Returns:
            List of dicts with title, url, content, published_date
        """
        if not self.is_available:
            return []
        try:
            results = self._client.search_and_contents(
                f"{card_name} credit card review benefits offers rewards India 2025",
                type="auto",
                num_results=num_results,
                text={"max_characters": 1500},
                # use_autoprompt=True,
                start_published_date=(datetime.now() - timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            return [
                {
                    "title": r.title or "Untitled",
                    "url": r.url,
                    "content": r.text[:1500] if r.text else "",
                    "published_date": r.published_date or "",
                }
                for r in results.results
            ]
        except Exception as e:
            logger.error(f"Exa card deep dive failed for {card_name}: {e}")
            return []
