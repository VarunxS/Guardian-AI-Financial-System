import asyncio
import json
import os
from dotenv import load_dotenv

from ingestion.schema import Transaction
from agents.supervisor import run_guardian

load_dotenv()

async def main():
    transactions = [
        Transaction(
            date="2023-10-01",
            description="NETFLIX.COM",
            amount=649.0,
            currency="INR",
            type="debit",
            category="Entertainment",
            payment_method="Credit Card",
            card_network="VISA",
            merchant_name="Netflix"
        ),
        Transaction(
            date="2023-10-05",
            description="NETFLIX.COM",
            amount=649.0,
            currency="INR",
            type="debit",
            category="Entertainment",
            payment_method="Credit Card",
            card_network="VISA",
            merchant_name="Netflix"
        ),
        Transaction(
            date="2023-10-10",
            description="APPLE.COM/BILL",
            amount=150.0,
            currency="USD",
            type="debit",
            category="Software",
            payment_method="Credit Card",
            card_network="MasterCard",
            merchant_name="Apple"
        ),
        Transaction(
            date="2023-10-15",
            description="ZOMATO",
            amount=1200.0,
            currency="INR",
            type="debit",
            category="Food & Dining",
            payment_method="UPI",
            merchant_name="Zomato"
        )
    ]

    print("Running Guardian Pipeline...")
    api_key = os.getenv("OPENAI_API_KEY")
    exa_api_key = os.getenv("EXA_API_KEY")

    final_state = await run_guardian(
        user_id="test_user_agent_run",
        transactions=transactions,
        api_key=api_key,
        provider="openai",
        exa_api_key=exa_api_key
    )

    print("\n=== SUBSCRIPTION FINDINGS ===")
    print(json.dumps(final_state.get("subscription_findings", []), indent=2))

    print("\n=== REWARD FINDINGS ===")
    print(json.dumps(final_state.get("reward_findings", []), indent=2))

    print("\n=== FINANCIAL FATHER REPORT ===")
    print(json.dumps(final_state.get("financial_father_report", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(main())
