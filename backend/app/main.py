"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import logger


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="Fraud Detection Multi-Agent System",
        description="Sistema Multi-Agente para Detección de Fraude Ambiguo",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify allowed origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routes
    app.include_router(router, prefix="", tags=["fraud-detection"])
    
    @app.get("/")
    async def root():
        """Root endpoint with API info."""
        return {
            "name": "Fraud Detection Multi-Agent System",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
            "endpoints": {
                "ingest": "POST /ingest",
                "transactions": "GET /transactions",
                "analyze": "POST /transactions/{id}/analyze",
                "hitl_queue": "GET /hitl",
            }
        }
    
    @app.on_event("startup")
    async def startup_event():
        logger.info(f"Starting Fraud Detection API in {settings.APP_ENV} mode")
        logger.info(f"Storage backend: {settings.STORAGE_BACKEND}")
        logger.info(f"LLM provider: {settings.LLM_PROVIDER}")
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
