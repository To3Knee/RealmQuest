from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from campaign_manager import router as system_router
from chat_engine import router as game_router
import os

app = FastAPI()

# Enable CORS for the Portal
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routes
app.include_router(system_router, prefix="/system")
app.include_router(game_router, prefix="/game")

@app.get("/")
def root():
    return {"status": "RealmQuest API Online", "version": "v28.0"}
