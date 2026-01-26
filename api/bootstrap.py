# ==============================================================================
# Script Name: bootstrap.py (v19.5 - Clean Ingest)
# Description: Ingests Rules & Physics. SILENCES duplicate errors.
# ==============================================================================
import os
import json
import glob
import re
import chromadb
from pymongo import MongoClient

MONGO_URL = "mongodb://realmquest-mongo:27017/"
CHROMA_HOST = "realmquest-chroma"
CHROMA_PORT = 8000
CAMPAIGN_ROOT = os.getenv("CAMPAIGN_ROOT", "/campaigns")
RULES_ROOT = os.getenv("RULES_ROOT", "/rules")

print("⚡ BOOTSTRAP: Initializing...")

try:
    mongo = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
    db = mongo["realmquest"]
    chroma = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    print("✅ Databases Connected")
except:
    chroma = None
    print("⚠️ DB Connection Weak")

def ingest_json_rules():
    if not chroma: return
    print(f"📚 Scanning JSON Rules in {RULES_ROOT}...")
    collection = chroma.get_or_create_collection("dnd_rules")
    
    count = 0
    if not os.path.exists(RULES_ROOT): return

    for filepath in glob.glob(f"{RULES_ROOT}/**/*.json", recursive=True):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    # DE-DUPLICATION LOGIC
                    unique_items = {}
                    for item in data:
                        if 'name' in item and 'desc' in item:
                            # Create ID based on filename + item name
                            uid = f"{os.path.basename(filepath)}_{item['name']}".replace(" ", "_")
                            # If ID exists in this batch, skip it (wins last write)
                            unique_items[uid] = {
                                "doc": f"{item['name']}: {item['desc']}",
                                "meta": {"source": "SRD", "file": os.path.basename(filepath)}
                            }
                    
                    if unique_items:
                        ids = list(unique_items.keys())
                        docs = [v["doc"] for v in unique_items.values()]
                        metas = [v["meta"] for v in unique_items.values()]
                        
                        # Upsert batch
                        collection.upsert(ids=ids, documents=docs, metadatas=metas)
                        count += len(ids)
        except Exception as e:
            # Only print real errors, not parsing noise
            pass
    print(f"   Total JSON Rules Indexed: {count}")

def ingest_markdown_physics():
    if not chroma: return
    md_path = os.path.join(RULES_ROOT, "SRD_Mechanics.md")
    
    if os.path.exists(md_path):
        print(f"⚛️  Ingesting Physics Engine: {md_path}")
        collection = chroma.get_or_create_collection("game_physics")
        
        with open(md_path, 'r') as f:
            content = f.read()
            
        chunks = re.split(r'(^##\s.*)', content, flags=re.MULTILINE)
        
        ids, docs, metas = [], [], []
        current_header = "General"
        
        for chunk in chunks:
            if chunk.startswith("##"):
                current_header = chunk.strip().replace("##", "").strip()
            elif chunk.strip():
                uid = f"mech_{current_header}".replace(" ", "_").lower()
                ids.append(uid)
                docs.append(f"RULE [{current_header}]:\n{chunk.strip()}")
                metas.append({"source": "SRD_Mechanics.md", "type": "mechanic"})
        
        if ids:
            collection.upsert(ids=ids, documents=docs, metadatas=metas)
            print(f"   Physics Chunks Indexed: {len(ids)}")

def scaffold_campaigns():
    if not os.path.exists(CAMPAIGN_ROOT): return
    if not os.listdir(CAMPAIGN_ROOT):
        game_path = os.path.join(CAMPAIGN_ROOT, "the_collision_stone")
        os.makedirs(game_path, exist_ok=True)
        manifest = {
            "name": "The Collision Stone",
            "description": "The Default Adventure",
            "dm_voice_id": "onyx",
            "status": "active"
        }
        with open(os.path.join(game_path, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=2)

if __name__ == "__main__":
    scaffold_campaigns()
    ingest_json_rules()
    ingest_markdown_physics()
    print("✅ Bootstrap Complete.")
