# ===============================================================
# Script Name: main.py
# Script Location: /opt/RealmQuest/api/main.py
# Date: 2026-01-31
# Version: 18.88.2 (Added roll engine router)
# ===============================================================

import os
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from chat_engine import router as chat_router
from campaign_manager import router as system_router
from characters import router as characters_router
from rolls import router as rolls_router

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI()

# --- CORS FIX (CONFIRMED) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("✅ CORS Policy: ENABLED (All Origins)")

# --- CAMPAIGN PATHS ---
# NOTE: Active campaign is primarily tracked in Mongo (system_config.active_campaign).
# This default is only used to ensure the base directory layout exists at boot.
active_campaign = os.getenv("RQ_DEFAULT_CAMPAIGN", "the_collision_stone")
try:
    os.makedirs(f"/campaigns/{active_campaign}/assets/images", exist_ok=True)
    os.makedirs(f"/campaigns/{active_campaign}/assets/avatars", exist_ok=True)
    os.makedirs(f"/campaigns/{active_campaign}/codex/npcs", exist_ok=True)
    os.makedirs(f"/campaigns/{active_campaign}/codex/locations", exist_ok=True)
    logger.info(f"✅ Active Campaign: {active_campaign}")
except Exception as e:
    logger.error(f"❌ Campaign Path Error: {e}")

# Mount the ENTIRE campaigns folder
app.mount("/campaigns", StaticFiles(directory="/campaigns"), name="campaigns")

# --- ROUTERS ---
app.include_router(chat_router, prefix="/game")
app.include_router(characters_router, prefix="/game")
app.include_router(rolls_router, prefix="/game")
app.include_router(system_router, prefix="/system")

@app.get("/")
def health_check():
    return {
        "status": "active", 
        "service": "RealmQuest API", 
        "cors": "enabled"
    }