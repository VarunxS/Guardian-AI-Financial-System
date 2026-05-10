import logging
from typing import Optional
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

def create_llm(api_key: str, provider: str = "google", model_id: str = "gemini-2.5-flash-lite", temperature: float = 0.3):
    """
    Returns the correct LangChain LLM instance based on provider.
    Defaults to Google Gemini 2.5 Flash-Lite.
    """
    provider = provider.lower().strip()
    
    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model_id,
            google_api_key=api_key,
            temperature=temperature,
            convert_system_message_to_human=False
        )

    elif provider == "openai":
        return ChatOpenAI(
            model=model_id,
            api_key=api_key,
            temperature=temperature
        )

    elif provider == "openrouter":
        return ChatOpenAI(
            model=model_id,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=temperature,
            default_headers={
                "HTTP-Referer": "https://guardian-finance.app",
                "X-Title": "Guardian Finance"
            }
        )

    elif provider == "mistral":
        try:
            from langchain_mistralai import ChatMistralAI
            return ChatMistralAI(
                model=model_id,
                api_key=api_key,
                temperature=temperature
            )
        except ImportError:
            # Fallback to OpenAI compatible endpoint for Mistral if package missing
            return ChatOpenAI(
                model=model_id,
                api_key=api_key,
                base_url="https://api.mistral.ai/v1",
                temperature=temperature
            )

    else:
        # Fallback to OpenAI if provider unknown
        return ChatOpenAI(
            model=model_id,
            api_key=api_key,
            temperature=temperature
        )
