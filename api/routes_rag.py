"""
RAG routes — chatbot, card recommendations, hindsight analysis, and Exa research.
"""

import logging
import asyncio

from fastapi import APIRouter, HTTPException

from agents.utils import get_llm

from api.models import AskRequest, AskResponse, CardRecommendRequest, HindsightRequest, ResearchRequest, CardExploreRequest
from rag.vectorstore import GuardianVectorStore
from rag.chatbot import GuardianChatbot
from rag.card_intelligence import CardIntelligenceRAG
from rag.finance_education import FinanceEducationRAG
from rag.hindsight_engine import HindsightEngine
from rag.exa_research import ExaResearch
from memory.supabase_client import SupabaseMemory
from ingestion.schema import Transaction

logger = logging.getLogger(__name__)
router = APIRouter(tags=["RAG"])

# Module-level singletons — shared across all requests
_vectorstore = None

def _get_vectorstore() -> GuardianVectorStore:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = GuardianVectorStore()
    return _vectorstore

_card_rag = None
_education_rag = None
_hindsight_engine = HindsightEngine()
_exa = ExaResearch()
_memory = SupabaseMemory()

# Per-user chatbot cache — keyed by user_id
_chatbot_cache: dict[str, GuardianChatbot] = {}


def _get_chatbot(user_id: str, api_key: str, provider: str = "google", model_id: str = "gemini-2.5-flash-lite") -> GuardianChatbot:
    """Get or create a chatbot instance for the given user."""
    # Include model_id in cache key to allow switching models
    cache_key = f"{user_id}:{provider}:{model_id}"
    if cache_key not in _chatbot_cache:
        _chatbot_cache[cache_key] = GuardianChatbot(
            api_key=api_key,
            vectorstore=_get_vectorstore(),
            user_id=user_id,
            provider=provider,
            model_id=model_id
        )
    return _chatbot_cache[cache_key]


# ── Chatbot endpoint ─────────────────────────────────────────────────────────

@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """
    Main chat endpoint. Routes question to the correct knowledge base
    automatically using the LLM router.

    Modes:
    - **card**: Credit card intelligence
    - **education**: Personal finance education
    - **hindsight**: Retrospective card optimisation
    - **research**: Live web research via Exa AI
    - **auto** (default if not specified): Auto-routes via LLM classifier
    """
    try:
        # BYOK: Fetch provider config if not explicitly sent
        api_key = request.api_key
        
        # Heuristic: Detect provider from key if not explicitly provided
        detected_provider = "google"
        if api_key and api_key.startswith("sk-"):
            detected_provider = "openai"
        elif api_key and api_key.startswith("openrouter"):
            detected_provider = "openrouter"

        provider = request.provider or detected_provider
        model_id = request.model_id or ("gpt-4o-mini" if provider == "openai" else "gemini-2.5-flash-lite")

        try:
            config = await _memory.get_provider_config(request.user_id)
        except Exception as e:
            logger.warning(f"Provider config lookup failed for {request.user_id}: {e}")
            config = None

        if config:
            if not api_key:
                api_key = config["api_key"]
            if not request.provider:
                provider = config["provider"]
            if not request.model_id:
                model_id = config["model_id"]

        if not api_key:
            raise HTTPException(status_code=400, detail="api_key is required (BYOK)")

        # If mode is explicitly set to a legacy mode, handle it directly
        if request.mode in ("card", "education", "hindsight", "research"):
            # Update request with fetched values
            request.api_key = api_key
            return await _handle_legacy_mode(request)

        # Auto-routing via chatbot (mode == "auto" or anything else)
        try:
            user_context = _memory.get_user_context_summary(request.user_id)
        except Exception:
            user_context = ""
        
        chatbot = _get_chatbot(request.user_id, api_key, provider, model_id)
        result = await chatbot.chat(
            question=request.question,
            user_context=user_context
        )
        return AskResponse(
            answer=result["answer"],
            mode=result["route"],
            metadata={"source_label": result["source_label"]}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.post("/chat/reset/{user_id}")
async def reset_chat(user_id: str):
    """Clears conversation memory for a user."""
    keys_to_remove = [k for k in _chatbot_cache if k.startswith(f"{user_id}:")]
    for key in keys_to_remove:
        _chatbot_cache[key].clear_history()
        del _chatbot_cache[key]
    return {"status": "reset", "user_id": user_id}


# ── Legacy mode handler ─────────────────────────────────────────────────────

async def _handle_legacy_mode(request: AskRequest) -> AskResponse:
    """Handle explicit mode requests (backwards compatibility)."""
    vs = _get_vectorstore()

    if request.mode == "card":
        card_rag = CardIntelligenceRAG(vs)
        chromadb_result = card_rag.answer(
            question=request.question, 
            api_key=request.api_key,
            provider=request.provider,
            model_id=request.model_id
        )
        exa_results = _exa.search_card_details(request.question, num_results=3)
        answer = chromadb_result["answer"]
        if exa_results:
            exa_context = "\n".join([f"- {r['title']}: {r['content'][:300]}" for r in exa_results[:3]])
            answer = _enrich_with_exa(
                request.question, 
                answer, 
                exa_context, 
                request.api_key,
                request.provider,
                request.model_id
            )
        return AskResponse(
            answer=answer,
            mode="card",
            metadata={
                "source_cards": chromadb_result.get("source_cards", []),
                "recommended_card": chromadb_result.get("recommended_card"),
                "exa_sources": [r.get("url", "") for r in exa_results],
            },
        )

    elif request.mode == "education":
        edu_rag = FinanceEducationRAG(vs)
        chromadb_result = edu_rag.answer(
            question=request.question, 
            api_key=request.api_key,
            provider=request.provider,
            model_id=request.model_id
        )
        exa_results = _exa.search_finance_regulations(request.question, num_results=3)
        answer = chromadb_result["answer"]
        if exa_results:
            exa_context = "\n".join([f"- {r['title']}: {r['content'][:300]}" for r in exa_results[:3]])
            answer = _enrich_with_exa(
                request.question, 
                answer, 
                exa_context, 
                request.api_key,
                request.provider,
                request.model_id
            )
        return AskResponse(
            answer=answer,
            mode="education",
            metadata={
                "topics_covered": chromadb_result.get("topics_covered", []),
                "exa_sources": [r.get("url", "") for r in exa_results],
            },
        )

    elif request.mode == "hindsight":
        retriever = vs.get_hindsight_retriever(request.user_id, k=4)
        docs = retriever.invoke(request.question)
        if docs:
            answer = "\n\n".join(doc.page_content for doc in docs)
        else:
            answer = "No hindsight data found. Please run an analysis first."
        return AskResponse(
            answer=answer,
            mode="hindsight",
            metadata={"documents_found": len(docs)},
        )

    elif request.mode == "research":
        exa_results = _exa.search_card_details(request.question, num_results=5)
        if not exa_results:
            exa_results = _exa.search_finance_regulations(request.question, num_results=5)
        if exa_results:
            context = "\n\n".join([f"**{r['title']}**\n{r['content'][:500]}\nSource: {r['url']}" for r in exa_results])
            answer = _synthesise_research(
                request.question, 
                context, 
                request.api_key,
                request.provider,
                request.model_id
            )
        else:
            answer = "Exa research is unavailable. Please check that EXA_API_KEY is set."
        return AskResponse(
            answer=answer,
            mode="research",
            metadata={
                "sources": [{"title": r.get("title", ""), "url": r.get("url", "")} for r in exa_results],
                "results_count": len(exa_results),
            },
        )

    raise HTTPException(status_code=400, detail=f"Invalid mode: '{request.mode}'.")


# ── Existing routes (unchanged) ──────────────────────────────────────────────

@router.post("/research")
async def research(request: ResearchRequest):
    """
    Dedicated Exa research endpoint for live web intelligence.

    - **card**: Search for credit card details and comparisons
    - **regulation**: Search for financial regulations and RBI/SEBI updates
    - **merchant**: Deep research on a specific merchant's practices
    """
    if not request.api_key:
        raise HTTPException(status_code=400, detail="api_key is required (BYOK)")

    if not _exa.is_available:
        raise HTTPException(status_code=503, detail="Exa research unavailable — EXA_API_KEY not set.")

    try:
        if request.research_type == "card":
            results = _exa.search_card_details(request.query)
            summary = _synthesise_research(request.query, _format_results(results), request.api_key)
            return {"type": "card", "summary": summary, "sources": results}

        elif request.research_type == "regulation":
            results = _exa.search_finance_regulations(request.query)
            summary = _synthesise_research(request.query, _format_results(results), request.api_key)
            return {"type": "regulation", "summary": summary, "sources": results}

        elif request.research_type == "merchant":
            if not request.merchant:
                raise HTTPException(status_code=400, detail="merchant is required for merchant research")
            report = _exa.research_merchant(request.merchant)
            return {"type": "merchant", "merchant": request.merchant, **report}

        else:
            raise HTTPException(status_code=400, detail=f"Invalid research_type: '{request.research_type}'.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Research failed: {e}")
        raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")


@router.post("/card-recommend")
async def card_recommend(request: CardRecommendRequest):
    """Get card recommendations with ChromaDB + live Exa enrichment."""
    if not request.api_key:
        raise HTTPException(status_code=400, detail="api_key is required (BYOK)")

    try:
        vs = _get_vectorstore()
        loop = asyncio.get_event_loop()
        findings = await loop.run_in_executor(None, _memory.get_findings, request.user_id, False)
        user_spend_context = None
        if findings:
            category_spend: dict[str, float] = {}
            for f in findings:
                if f.get("type") == "reward" and f.get("category"):
                    cat = f["category"]
                    if cat not in category_spend:
                        category_spend[cat] = f.get("rupee_impact", 0)
            if category_spend:
                user_spend_context = category_spend

        # BYOK: Fetch provider config if not explicitly sent
        provider = "google"
        model_id = "gemini-2.5-flash-lite"
        api_key = request.api_key

        try:
            config = await _memory.get_provider_config(request.user_id)
        except Exception as e:
            logger.warning(f"Provider config lookup failed for {request.user_id}: {e}")
            config = None

        if config:
            if not api_key:
                api_key = config["api_key"]
            provider = config["provider"]
            model_id = config["model_id"]

        if not api_key:
            raise HTTPException(status_code=400, detail="api_key is required (BYOK)")

        card_rag = CardIntelligenceRAG(vs)
        chromadb_result = card_rag.answer(
            question=request.question, 
            api_key=api_key, 
            provider=provider,
            model_id=model_id,
            user_spend_context=user_spend_context,
        )
        exa_results = _exa.search_card_details(request.question, num_results=3)
        answer = chromadb_result["answer"]
        if exa_results:
            exa_context = "\n".join([f"- {r['title']}: {r['content'][:300]}" for r in exa_results[:3]])
            answer = _enrich_with_exa(request.question, answer, exa_context, api_key, provider, model_id)

        return {
            "answer": answer,
            "source_cards": chromadb_result.get("source_cards", []),
            "recommended_card": chromadb_result.get("recommended_card"),
            "user_spend_context": user_spend_context,
            "exa_sources": [r.get("url", "") for r in exa_results],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Card recommendation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")


@router.post("/hindsight/{run_id}")
async def generate_hindsight(run_id: str, request: HindsightRequest):
    """Generate a hindsight report for a specific analysis run."""
    if not request.api_key:
        raise HTTPException(status_code=400, detail="api_key is required (BYOK)")

    try:
        vs = _get_vectorstore()
        loop = asyncio.get_event_loop()
        findings = await loop.run_in_executor(None, _memory.get_findings, request.user_id, False)
        pseudo_transactions = []
        for f in findings:
            if f.get("merchant"):
                pseudo_transactions.append(
                    Transaction(
                        date=f.get("created_at", "2024-01-01T00:00:00"),
                        description=f.get("merchant", "Unknown"),
                        amount=f.get("rupee_impact", 0),
                        category=f.get("type", "other"),
                        merchant_name=f.get("merchant", "Unknown"),
                    )
                )
        # BYOK: Fetch provider config
        provider = "google"
        model_id = "gemini-2.5-flash-lite"
        api_key = request.api_key

        try:
            config = await _memory.get_provider_config(request.user_id)
        except Exception as e:
            logger.warning(f"Provider config lookup failed for {request.user_id}: {e}")
            config = None

        if config:
            if not api_key:
                api_key = config["api_key"]
            provider = config["provider"]
            model_id = config["model_id"]

        if not api_key:
            raise HTTPException(status_code=400, detail="api_key is required (BYOK)")

        result = _hindsight_engine.generate(
            user_id=request.user_id, 
            transactions=pseudo_transactions,
            vectorstore=vs, 
            api_key=api_key,
            provider=provider,
            model_id=model_id
        )
        return {"run_id": run_id, "user_id": request.user_id, **result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hindsight generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Hindsight generation failed: {str(e)}")


# ── Helper functions ─────────────────────────────────────────────────────────

def _enrich_with_exa(question: str, base_answer: str, exa_context: str, api_key: str, provider: str = "google", model_id: str = "gemini-2.5-flash-lite") -> str:
    """Merge ChromaDB answer with live Exa data using LLM."""
    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        llm = get_llm(api_key, provider, model_id)
        response = llm.invoke([
            SystemMessage(content=(
                "You are a financial assistant. You have two sources of information:\n"
                "1. Your knowledge base (already answered the question)\n"
                "2. Live web research from Exa AI\n\n"
                "Merge both into one comprehensive answer. If the live data contradicts the "
                "knowledge base, prefer the live data as it's more recent. Cite sources where relevant. "
                "Keep the answer concise — under 300 words."
            )),
            HumanMessage(content=(
                f"Question: {question}\n\n"
                f"Knowledge base answer:\n{base_answer}\n\n"
                f"Live web research:\n{exa_context}"
            )),
        ])
        return response.content.strip()
    except Exception as e:
        logger.warning(f"Exa enrichment LLM call failed: {e}")
        return base_answer


def _synthesise_research(query: str, context: str, api_key: str, provider: str = "google", model_id: str = "gemini-2.5-flash-lite") -> str:
    """Synthesise Exa search results into a coherent answer."""
    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        llm = get_llm(api_key, provider, model_id)
        response = llm.invoke([
            SystemMessage(content=(
                "You are a financial research analyst. Synthesise the web research results "
                "into a clear, actionable answer. Use Indian context (rupees, RBI, Indian banks). "
                "Cite sources. Keep it under 400 words."
            )),
            HumanMessage(content=f"Research query: {query}\n\nWeb results:\n{context}"),
        ])
        return response.content.strip()
    except Exception as e:
        logger.warning(f"Research synthesis failed: {e}")
        return f"Raw research results:\n{context[:1000]}"


def _format_results(results: list[dict]) -> str:
    """Format Exa results into a readable string."""
    if not results:
        return "No results found."
    return "\n\n".join([
        f"**{r.get('title', 'Untitled')}**\n{r.get('content', '')[:500]}\nSource: {r.get('url', '')}"
        for r in results
    ])


# ── Card Explorer endpoints ──────────────────────────────────────────────────

_cards_catalog = None

def _load_cards_catalog() -> dict:
    global _cards_catalog
    if _cards_catalog is None:
        import json
        from pathlib import Path
        cards_path = Path(__file__).parent.parent / "knowledge" / "cards" / "indian_cards.json"
        with open(cards_path, "r") as f:
            _cards_catalog = json.load(f)
    return _cards_catalog


@router.get("/cards")
async def get_cards_catalog():
    """Returns the full card catalog for the Card Explorer grid."""
    catalog = _load_cards_catalog()
    cards = []
    for card_id, card in catalog.items():
        cards.append({"id": card_id, **card})
    cards.sort(key=lambda c: c.get("annual_fee", 0), reverse=True)
    return {"cards": cards, "total": len(cards)}


@router.post("/card-explore")
async def explore_card(request: CardExploreRequest):
    """Deep dive on a single card: static KB + live Exa search."""
    catalog = _load_cards_catalog()
    card = catalog.get(request.card_id)
    if not card:
        raise HTTPException(status_code=404, detail=f"Card '{request.card_id}' not found.")

    live_results = []
    if request.api_key:
        try:
            live_results = _exa.search_card_deep_dive(card["name"], num_results=4)
        except Exception as e:
            logger.warning(f"Exa deep dive failed for {card['name']}: {e}")

    return {
        "card": {"id": request.card_id, **card},
        "live_offers": live_results,
        "exa_available": _exa.is_available,
    }
