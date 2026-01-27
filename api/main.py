# ===============================================================
# Script Name: main.py
# Script Location: /opt/RealmQuest/api/main.py
# Date: 2026-01-27
# Version: 18.88.0 (Path Safety)
# ===============================================================

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from chat_engine import router as chat_router
from campaign_manager import router as system_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# INIT ACTIVE CAMPAIGN PATHS
active_campaign = "the_collision_stone"
os.makedirs(f"/campaigns/{active_campaign}/assets/images", exist_ok=True)
os.makedirs(f"/campaigns/{active_campaign}/codex/npcs", exist_ok=True)

# Mount the ENTIRE campaigns folder
app.mount("/campaigns", StaticFiles(directory="/campaigns"))

app.include_router(chat_router, prefix="/game")
app.include_router(system_router, prefix="/system")

@app.get("/")
def health_check():
    return {"status": "active", "service": "RealmQuest API"}