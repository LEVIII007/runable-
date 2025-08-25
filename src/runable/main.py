from fastapi import FastAPI
import uvicorn
from src.api.coding_agent.coding_agent import router as coding_agent_router
from src.config.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)

app = FastAPI(
    title="Trench AI",
    description="AI-powered coding agent with sandboxing and orchestration",
    version="0.1.0"
)

# Include API routers
app.include_router(coding_agent_router, prefix="/api/coding-agent", tags=["coding-agent"])

@app.get("/")
async def root():
    return {"message": "Hello from shashank!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

def start_server():
    """Start the FastAPI server with uvicorn"""
    import os
    port = int(os.getenv("API_PORT", 3000))
    uvicorn.run(
        "src.runable.main:app",
        host="0.0.0.0",
        port=port,
        reload=False  # Disable reload in production container
    )

if __name__ == "__main__":
    start_server()
