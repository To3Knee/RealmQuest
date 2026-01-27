# ===============================================================
# Script Name: config.py
# Script Location: /opt/RealmQuest/bot/core/config.py
# Date: 2026-01-27
# Version: 21.0.0 (Tuned Hearing)
# ===============================================================

import os
from pymongo import MongoClient

# ENV VARS
MONGO_URL = os.getenv("MONGO_URL", "mongodb://realmquest-mongo:27017/")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY")

# DOCKER INTERNAL URLS
API_URL = os.getenv("API_URL", "http://realmquest-api:8000")
SCRIBE_URL = os.getenv("SCRIBE_URL", "http://realmquest-scribe:9000")

# AUDIO TUNING
RMS_THRESHOLD = 12         # Filter room noise / breathing
SILENCE_TIMEOUT = 2.5      # Wait for player to finish sentence
MAX_RECORD_TIME = 45.0     
PRE_BUFFER_LEN = 150       

# DB CONNECTION
_db = None

def get_db():
    global _db
    if not _db:
        client = MongoClient(MONGO_URL)
        _db = client["realmquest"]
    return _db

def get_settings():
    db = get_db()
    conf = db["system_config"].find_one({"config_id": "main"})
    if not conf: return {} 
    return conf

def update_settings(updates: dict):
    db = get_db()
    db["system_config"].update_one({"config_id": "main"}, {"$set": updates})