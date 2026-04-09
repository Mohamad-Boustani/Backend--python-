import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.api import router as api_router

# Load environment variables before reading configuration values.
load_dotenv()

# Read the app name and allowed origins from the environment.
app_name = os.getenv("APP_NAME", "AI Attendance Backend")
allowed_origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")]
allow_credentials = allowed_origins != ["*"]

# Create the FastAPI application instance.
app = FastAPI(title=app_name, version="1.0.0")

# Add CORS so the Flutter app or browser client can call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint for quick server status checks.
@app.get("/")
def health_check():
    return {"message": "AI Attendance backend is running"}


# Register the versioned API routes under /api/v1.
app.include_router(api_router, prefix="/api/v1", tags=["AI Attendance"])
