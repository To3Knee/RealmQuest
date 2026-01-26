import os
from pymongo import MongoClient

# ENV VARS (Secrets)
MONGO_URL = os.getenv("MONGO_URL", "mongodb://realmquest-mongo:27017/")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY")

# DB CONNECTION
_db = None

def get_db():
    global _db
    if not _db:
        client = MongoClient(MONGO_URL)
        _db = client["realmquest"]
    return _db

def get_settings():
    """Fetches the Master Config from MongoDB"""
    db = get_db()
    conf = db["system_config"].find_one({"config_id": "main"})
    if not conf:
        return {} # Should not happen if bootstrap ran
    return conf

def update_settings(updates: dict):
    db = get_db()
    db["system_config"].update_one({"config_id": "main"}, {"$set": updates})
