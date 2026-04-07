import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.api import router as api_router

load_dotenv()

app_name = os.getenv("APP_NAME", "AI Attendance Backend")
allowed_origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")]
allow_credentials = allowed_origins != ["*"]

app = FastAPI(title=app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
def health_check():
    return {"message": "AI Attendance backend is running"}


app.include_router(api_router, prefix="/api/v1", tags=["AI Attendance"])
