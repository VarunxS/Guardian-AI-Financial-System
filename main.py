"""
Guardian API — FastAPI entry point.

Run with:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes_analysis import router as analysis_router
from api.routes_rag import router as rag_router
from api.routes_settings import router as settings_router

app = FastAPI(
    title="Guardian API",
    description="AI-powered personal finance agent — detects subscriptions, reward leaks, and more.",
    version="1.0.0",
)

# Enable CORS for all origins (needed for Streamlit / any frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analysis_router, prefix="/api")
app.include_router(rag_router, prefix="/api")
app.include_router(settings_router, prefix="/api")


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
