import asyncio
import json
import sys
import os

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def main():
    print("=" * 60)
    print("Guardian — BYOK Setup & Test Run")
    print("=" * 60)
    
    provider = input("Enter your API provider (openai, openrouter, mistral, gemini) [default: openai]: ").strip().lower() or "openai"
    
    # Try to load from env based on provider
    env_key_map = {
        "openai": "OPENAI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "gemini": "GEMINI_API_KEY"
    }
    
    api_key = os.getenv(env_key_map.get(provider, "OPENAI_API_KEY"))
    if not api_key:
        api_key = input(f"Enter your {provider.capitalize()} API key: ").strip()
        
    if not api_key:
        print(f"ERROR: API key for {provider} is required.")
        sys.exit(1)
        
    exa_api_key = os.getenv("EXA_API_KEY") or input("Enter your Exa API key (optional, press Enter to skip): ").strip()

    from ingestion.parser import StatementParser
    parser = StatementParser()
    upload = parser.parse("sample_data/sample_transactions.csv", "bank_csv", "test_user_001")
    txns = upload.transactions
    print(f"\n✓ Parsed {len(txns)} transactions")
    print(f"Date range: {min(t.date for t in txns).strftime('%d/%m/%Y')} to {max(t.date for t in txns).strftime('%d/%m/%Y')}\n")

    print("\n" + "=" * 60)
    print("INDIVIDUAL AGENT TESTS")
    print("=" * 60)

    from agents.subscription_hunter import run_subscription_hunter
    print("\n[1/3] Subscription Hunter...")
    sub_findings = run_subscription_hunter(txns, api_key, provider)
    print(f"  ✓ {len(sub_findings)} subscription findings")
    print(json.dumps(sub_findings, indent=2))

    from rag.vectorstore import GuardianVectorStore
    vectorstore = GuardianVectorStore()

    from agents.reward_optimiser import run_reward_optimiser
    print("\n[2/3] Reward Optimiser...")
    rw_findings = run_reward_optimiser(
        transactions=txns, 
        api_key=api_key, 
        provider=provider, 
        vectorstore=vectorstore, 
        exa_api_key=exa_api_key
    )
    print(f"  ✓ {len(rw_findings)} reward findings")
    print(json.dumps(rw_findings, indent=2))

    from agents.budget_goals_agent import run_budget_goals_agent
    print("\n[3/3] Budget & Goals Agent...")
    
    # Set test income and goals for the test run
    TEST_INCOME = 85000.0
    TEST_GOALS = [
        {
            "goal_id": "test-goal-1",
            "name": "Royal Enfield Classic 350",
            "goal_type": "product",
            "target_amount": 210000,
            "saved_amount": 34000,
            "surplus_pct": 0.6
        },
        {
            "goal_id": "test-goal-2",
            "name": "Emergency Fund",
            "goal_type": "emergency_fund",
            "target_amount": 150000,
            "saved_amount": 12000,
            "surplus_pct": 0.4
        }
    ]

    budget = run_budget_goals_agent(txns, TEST_INCOME, TEST_GOALS, api_key, provider)
    print(f"  ✓ Budget & Goals Report")
    print(json.dumps(budget, indent=2, default=str))

    # Validate output
    assert budget.get("type") == "budget_goals", "Wrong type"
    assert "goal_cards" in budget, "Missing goal_cards"
    assert "top_recommendation" in budget, "Missing recommendation"
    for card in budget.get("goal_cards", []):
        assert card["current_pace_months"] > 0, "Invalid timeline"
        assert card["balanced_months"] <= card["current_pace_months"], "Balanced should be <= current pace"
        assert card["conservative_months"] <= card["balanced_months"], "Conservative should be <= balanced"
    print("  ✓ All agent validations passed.")

    print("\n" + "=" * 60)
    print("FULL PIPELINE TEST (LangGraph)")
    print("=" * 60)

    from agents.supervisor import run_guardian
    print("\nRunning full Guardian pipeline...")
    final_state = await run_guardian("test_user_001", txns, api_key, provider, exa_api_key)

    report = final_state.get("budget_goals_report", {})
    summary = report.get("budget_summary", {})
    print(f"\n📊 Surplus Health: {summary.get('surplus_health', 'N/A')}")
    print(f"📝 One-line Verdict: {summary.get('one_line_verdict', 'N/A')}")
    
    print(f"\n💡 Goal Progress:")
    for card in report.get("goal_cards", []):
        print(f"  - {card.get('goal_name')}: {card.get('current_pace_months')} months at current pace")
        print(f"    Lever: {card.get('biggest_lever_sentence')}")

    errors = final_state.get("errors", [])
    if errors:
        print(f"\n⚠️ Errors: {errors}")

    print(f"\n{'=' * 60}")
    print("Test run complete!")

    # ── Chatbot backend test ─────────────────────────────────────────
    # ... (rest remains same)
    print("\n" + "=" * 60)
    print("CHATBOT ROUTING TEST")
    print("=" * 60)

    from rag.chatbot import GuardianChatbot
    bot = GuardianChatbot(
        api_key=api_key,
        vectorstore=vectorstore,
        user_id="test_user_001",
        provider=provider,
    )

    test_questions = [
        "What is CIBIL score?",                          # should route → education
        "Which card is best for dining?",                # should route → card
        "How much reward did I miss last month?",        # should route → hindsight or unclear
        "Is HDFC Infinia worth it for my travel spend?", # should route → unclear (merged)
    ]

    for q in test_questions:
        result = bot.chat(q, user_context="")
        print(f"\nQ: {q}")
        print(f"Route: {result['route']} {result['source_label']}")
        print(f"A: {result['answer'][:200]}...")

    print(f"\n{'=' * 60}")
    print("All tests complete!")


if __name__ == "__main__":
    asyncio.run(main())
