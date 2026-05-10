"""
One-time script to embed knowledge base documents into ChromaDB collections.
Run this before starting the Guardian server:
    python -m rag.ingest_knowledge
"""

import json
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from rag.vectorstore import GuardianVectorStore


def ingest_cards(vs: GuardianVectorStore) -> int:
    """
    Ingests indian_cards.json as category-level chunks into ChromaDB.
    Each card × category combination becomes one document.
    Run this once — it replaces any existing guardian_cards collection.
    """
    cards_path = Path(__file__).parent.parent / "knowledge" / "cards" / "indian_cards.json"
    with open(cards_path, "r") as f:
        catalog = json.load(f)

    documents = []
    for card_id, card in catalog.items():
        card_name = card["name"]
        annual_fee = card.get("annual_fee", 0)
        best_for = card.get("best_for", [])

        # Base document — general card info
        documents.append(Document(
            page_content=(
                f"Card: {card_name}\n"
                f"Annual fee: ₹{annual_fee}\n"
                f"Best for: {', '.join(best_for)}\n"
                f"Base reward rate: {card.get('reward_rate_base', 1)}%\n"
                f"Expiry policy: {card.get('expiry_policy', 'varies')}"
            ),
            metadata={
                "card_id": card_id,
                "card_name": card_name,
                "category": "general",
                "reward_rate": card.get("reward_rate_base", 1),
                "annual_fee": annual_fee,
                "type": "card_general"
            }
        ))

        # One chunk per category reward rate
        for category, rate in card.get("reward_rate_per_category", {}).items():
            # Compute break-even monthly spend for this category
            # i.e. how much must you spend here for the card to pay for itself
            monthly_fee = annual_fee / 12
            if rate > 0:
                breakeven = (monthly_fee / (rate / 100))
            else:
                breakeven = float('inf')

            documents.append(Document(
                page_content=(
                    f"Card: {card_name}\n"
                    f"Category: {category}\n"
                    f"Reward rate for {category}: {rate}%\n"
                    f"Annual fee: ₹{annual_fee} (₹{monthly_fee:.0f}/month)\n"
                    f"Break-even monthly spend in {category}: ₹{breakeven:,.0f}\n"
                    f"Best for: {', '.join(best_for)}"
                ),
                metadata={
                    "card_id": card_id,
                    "card_name": card_name,
                    "category": category,
                    "reward_rate": float(rate),
                    "annual_fee": annual_fee,
                    "type": "card_category_chunk"
                }
            ))

        # Milestone benefits as separate chunks
        for milestone in card.get("milestone_benefits", []):
            documents.append(Document(
                page_content=(
                    f"Card: {card_name}\n"
                    f"Milestone benefit: Spend ₹{milestone['spend_threshold']:,} "
                    f"annually to get: {milestone['benefit']}"
                ),
                metadata={
                    "card_id": card_id,
                    "card_name": card_name,
                    "category": "milestone",
                    "type": "card_milestone"
                }
            ))

    # Clear existing collection and re-ingest
    try:
        vs._chroma_client.delete_collection(vs.CARDS_COLLECTION)
    except Exception:
        pass
    
    vs.add_card_documents(documents)
    return len(documents)


def ingest_education(vs: GuardianVectorStore) -> int:
    """Load personal_finance.md → split → embed into guardian_education."""
    education_path = Path(__file__).parent.parent / "knowledge" / "education" / "personal_finance.md"
    with open(education_path, "r") as f:
        content = f.read()

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=80)
    chunks = splitter.split_text(content)

    docs = [
        Document(
            page_content=chunk,
            metadata={"type": "education", "source": "personal_finance.md"},
        )
        for chunk in chunks
    ]

    vs.add_education_documents(docs)
    return len(docs)


if __name__ == "__main__":
    print("Guardian Knowledge Base Ingestion")
    print("=" * 50)

    vs = GuardianVectorStore()

    print("\n[1/2] Ingesting card intelligence...")
    card_count = ingest_cards(vs)
    print(f"  ✓ Embedded {card_count} card documents into 'guardian_cards'")

    print("\n[2/2] Ingesting finance education...")
    edu_count = ingest_education(vs)
    print(f"  ✓ Embedded {edu_count} education chunks into 'guardian_education'")

    print(f"\n{'=' * 50}")
    print(f"Done! Total documents: {card_count + edu_count}")
    print(f"ChromaDB persisted at: {vs._chroma_client._identifier}")
