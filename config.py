"""
Guardian configuration — loads environment variables and exports Settings.
OPENAI_API_KEY is optional (BYOK architecture — users provide their own key per request).
"""
from __future__ import annotations

import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


PROVIDERS = {
    "google": {
        "label": "Google Gemini",
        "key_label": "Gemini API Key",
        "key_placeholder": "AIza••••••••••••••••••••••••••••••••••••",
        "key_link": "https://aistudio.google.com/app/apikey",
        "key_link_label": "Get free API key at Google AI Studio →",
        "langchain_package": "langchain-google-genai",
        "models": [
            {
                "id": "gemini-3-flash-preview",
                "label": "Gemini 3 Flash Preview",
                "tags": ["Cutting Edge", "Experimental"],
                "description": "Latest experimental Flash model from Google.",
                "use_for": "all"
            },
            {
                "id": "gemini-3.1-flash-lite-preview",
                "label": "Gemini 3.1 Flash-Lite",
                "tags": ["Fastest", "Experimental"],
                "description": "Ultra-lightweight preview model for maximum speed.",
                "use_for": "all"
            },
            {
                "id": "gemini-2.5-flash-lite",
                "label": "Gemini 2.5 Flash-Lite",
                "tags": ["Recommended", "Stable"],
                "description": "Best balance of speed and quality for Guardian.",
                "use_for": "all"
            }
        ]
    },
    "openai": {
        "label": "OpenAI",
        "key_label": "OpenAI API Key",
        "key_placeholder": "sk-proj-••••••••••••••••••••••",
        "key_link": "https://platform.openai.com/api-keys",
        "key_link_label": "Get API key at OpenAI Platform →",
        "langchain_package": "langchain-openai",
        "models": [
            {
                "id": "gpt-4o-mini",
                "label": "GPT-4o-mini",
                "tags": ["Recommended", "Reliable"],
                "description": "Standard high-performance mini model.",
                "use_for": "all"
            },
            {
                "id": "gpt-5.4-nano",
                "label": "GPT-5.4 Nano",
                "tags": ["Experimental", "Tiny"],
                "description": "Next-gen nano model for basic tasks.",
                "use_for": "all"
            },
            {
                "id": "gpt-4.1-mini",
                "label": "GPT-4.1 Mini",
                "tags": ["Legacy", "Stable"],
                "description": "Previous generation mini model.",
                "use_for": "all"
            }
        ]
    },
    "openrouter": {
        "label": "OpenRouter",
        "key_label": "OpenRouter API Key",
        "key_placeholder": "sk-or-v1-••••••••••••••••••••••••••••••••••••••••••••••••••",
        "key_link": "https://openrouter.ai/keys",
        "key_link_label": "Get API key at OpenRouter →",
        "langchain_package": "langchain-openai",
        "base_url": "https://openrouter.ai/api/v1",
        "allow_custom": True,
        "models": [
            {
                "id": "google/gemini-3-flash-preview",
                "label": "Gemini 3 Flash",
                "tags": ["Google", "Fast"],
                "description": "Latest Google preview via OpenRouter.",
                "use_for": "all"
            },
            {
                "id": "openai/gpt-4o-mini",
                "label": "GPT-4o-mini",
                "tags": ["OpenAI", "Reliable"],
                "description": "OpenAI mini model via OpenRouter.",
                "use_for": "all"
            },
            {
                "id": "nvidia/nemotron-3-nano-30b-a3b:free",
                "label": "Nvidia Nemotron (Free)",
                "tags": ["Free", "Fast"],
                "description": "High performance free model from Nvidia.",
                "use_for": "all"
            },
            {
                "id": "meta-llama/llama-3.1-70b-instruct",
                "label": "Llama 3.1 70B",
                "tags": ["Recommended", "Strong"],
                "description": "Strong open-weight model.",
                "use_for": "all"
            }
        ]
    },
    "mistral": {
        "label": "Mistral AI",
        "key_label": "Mistral API Key",
        "key_placeholder": "••••••••••••••••••••••••••••••••",
        "key_link": "https://console.mistral.ai/api-keys/",
        "key_link_label": "Get API key at Mistral Console →",
        "langchain_package": "langchain-mistralai",
        "models": [
            {
                "id": "mistral-small-latest",
                "label": "Mistral Small",
                "tags": ["Recommended", "Fast"],
                "description": "Best balance for Mistral users.",
                "use_for": "all"
            }
        ]
    }
}


@dataclass
class Settings:
    openai_api_key: Optional[str]  # Optional — BYOK: users provide their own key
    mistral_api_key: Optional[str]  # Optional — Mistral AI
    supabase_url: str
    supabase_key: str
    chroma_persist_dir: str
    exa_api_key: Optional[str]  # Optional — Exa AI research


def _load_settings() -> Settings:
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    chroma_persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

    if not supabase_url or not supabase_key:
        import logging
        logging.warning(
            "SUPABASE_URL and/or SUPABASE_KEY not set. "
            "Persistence to Supabase will be disabled. "
            "Set them in .env for full functionality."
        )

    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        mistral_api_key=os.getenv("MISTRAL_API_KEY") or None,
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        chroma_persist_dir=chroma_persist_dir,
        exa_api_key=os.getenv("EXA_API_KEY") or None,
    )


settings = _load_settings()
