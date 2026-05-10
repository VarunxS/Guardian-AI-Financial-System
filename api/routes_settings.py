import asyncio
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from memory.supabase_client import SupabaseMemory
from config import PROVIDERS
from agents.llm_factory import create_llm
from langchain_core.messages import HumanMessage

router = APIRouter(tags=["Settings"])
_memory = SupabaseMemory()


def _storage_error_message() -> str:
    return (
        "Backend storage is not configured. Set SUPABASE_URL and SUPABASE_KEY "
        "on the Render backend service."
    )

class ProviderConfigRequest(BaseModel):
    user_id: str
    provider: str
    model_id: str
    api_key: str
    exa_api_key: Optional[str] = ""

class TestKeyRequest(BaseModel):
    provider: str
    model_id: str
    api_key: str

@router.get("/settings/providers")
async def get_providers():
    return PROVIDERS

@router.get("/settings/config/{user_id}")
async def get_config(user_id: str):
    if not _memory.is_connected:
        return {"configured": False, "db_error": _storage_error_message()}

    try:
        config = await _memory.get_provider_config(user_id)
        if not config:
            return {"configured": False}
        # Don't return the full API key for security, maybe just a masked version
        config["api_key_masked"] = config["api_key"][:4] + "••••" + config["api_key"][-4:] if len(config["api_key"]) > 8 else "••••"
        config["configured"] = True
        return config
    except Exception as e:
        if "PGRST205" in str(e) or "schema cache" in str(e).lower():
             return {"configured": False, "db_error": "Supabase table 'user_provider_config' missing. Run the SQL schema first."}
        return {"configured": False, "error": str(e)}

@router.post("/settings/config")
async def save_config(req: ProviderConfigRequest):
    if not _memory.is_connected:
        raise HTTPException(status_code=500, detail=_storage_error_message())

    try:
        await _memory.save_provider_config(
            user_id=req.user_id,
            provider=req.provider,
            model_id=req.model_id,
            api_key=req.api_key,
            exa_api_key=req.exa_api_key
        )
        return {"status": "success"}
    except Exception as e:
        if "PGRST205" in str(e) or "schema cache" in str(e).lower():
             raise HTTPException(status_code=400, detail="Database table missing. Please run the SQL migration in your Supabase dashboard.")
        raise HTTPException(status_code=500, detail=f"Failed to save: {str(e)}")

@router.post("/settings/test-key")
async def test_key(req: TestKeyRequest):
    try:
        llm = create_llm(api_key=req.api_key, provider=req.provider, model_id=req.model_id)
        # Minimal test call with timeout
        # Using wait_for on a thread is tricky, so we'll just wrap the whole thing
        await asyncio.wait_for(
            asyncio.to_thread(llm.invoke, [HumanMessage(content="Reply with the single word: ready")]),
            timeout=10.0
        )
        return {"valid": True}
    except asyncio.TimeoutError:
        return {"valid": False, "error": "Connection timed out. Check your internet or API provider status."}
    except Exception as e:
        err = str(e)
        detail = f"Connection error: {err[:120]}"
        if "401" in err or "authentication" in err.lower() or "api key" in err.lower():
            detail = "Invalid API key. Check that you copied it correctly."
        elif "429" in err or "quota" in err.lower():
            detail = "API quota exceeded. Check your billing at the provider."
        elif "404" in err or "model" in err.lower():
            detail = f"Model '{req.model_id}' not available on your account."
        
        return {"valid": False, "error": detail}
