#!/usr/bin/env python3
# =============================================================================
# Script Name: rq-pack-manager.py
# Version: 1.0.3 (Fixes Name Mismatch & Dict Keys)
# Date: 2026-01-27
# =============================================================================

import argparse
import csv
import io
import json
import os
import sys
import zipfile
from datetime import datetime
from typing import Optional

try:
    from pymongo import MongoClient, UpdateOne
except Exception:
    MongoClient = None
    UpdateOne = None

try:
    import redis
except Exception:
    redis = None

try:
    import chromadb
except Exception:
    chromadb = None


DEFAULT_MONGO_URI = os.getenv("RQ_MONGO_URI", "mongodb://realmquest-mongo:27017")
DEFAULT_DB_NAME   = os.getenv("RQ_MONGO_DB", "realmquest")
DEFAULT_REDIS_HOST = os.getenv("RQ_REDIS_HOST", "realmquest-redis")
DEFAULT_REDIS_PORT = int(os.getenv("RQ_REDIS_PORT", "6379"))
DEFAULT_CHROMA_URL = os.getenv("RQ_CHROMA_URL", "http://realmquest-chroma:8000")
EMBED_PROVIDER = os.getenv("RQ_EMBED_PROVIDER", "").strip().lower()

def die(msg: str):
    print(f"ERROR: {msg}")
    sys.exit(1)

def mongo_client():
    if MongoClient is None: die("pymongo missing. pip install pymongo")
    return MongoClient(DEFAULT_MONGO_URI)

def redis_client():
    if redis is None: die("redis missing. pip install redis")
    return redis.Redis(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT, decode_responses=True)

def chroma_client():
    if chromadb is None: die("chromadb missing. pip install chromadb")
    return chromadb.HttpClient(host=DEFAULT_CHROMA_URL.split("://")[1].split(":")[0], port=8000)

def find_file_in_zip(z: zipfile.ZipFile, extension: str) -> Optional[str]:
    for name in z.namelist():
        if name.startswith("__") or "/." in name: continue
        if name.lower().endswith(extension): return name
    return None

def resolve_dict_row(doc):
    """Normalize dictionary rows to use 'headword'."""
    if "headword" in doc: return doc
    # Fallbacks
    for k in ["term", "word", "name", "title"]:
        if k in doc:
            doc["headword"] = doc[k]
            return doc
    return None

def import_pack(zip_path: str, kind: str, pack_name_arg: str, version: str, enable: bool):
    if not os.path.exists(zip_path): die(f"ZIP not found: {zip_path}")

    client = mongo_client()
    db = client[DEFAULT_DB_NAME]
    
    # 1. RESOLVE NAME FIRST (The Fix)
    final_pack_name = pack_name_arg
    if final_pack_name == "auto":
        final_pack_name = os.path.basename(zip_path)
    
    print(f"Importing as Pack Name: '{final_pack_name}'")

    try: z = zipfile.ZipFile(zip_path, 'r')
    except zipfile.BadZipFile: die("Invalid ZIP file.")

    target_file = None
    if kind == "asr":
        target_file = find_file_in_zip(z, ".csv") or find_file_in_zip(z, ".jsonl")
    elif kind == "dict":
        target_file = find_file_in_zip(z, ".jsonl") or find_file_in_zip(z, ".txt")

    if not target_file: die(f"No valid file found in ZIP for '{kind}'")
    print(f"Found data file: {target_file}")

    with z.open(target_file, 'r') as f:
        content = f.read().decode('utf-8')

    rows = []
    if kind == "asr":
        if target_file.endswith(".csv"):
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                if "heard" in row and "canonical" in row:
                    try: row["confidence"] = float(row.get("confidence", 1.0))
                    except: row["confidence"] = 1.0
                    try: row["priority"] = int(row.get("priority", 50))
                    except: row["priority"] = 50
                    rows.append(row)
        else:
            for line in content.splitlines():
                if line.strip(): rows.append(json.loads(line))
    elif kind == "dict":
        for line in content.splitlines():
            if line.strip():
                try:
                    doc = json.loads(line)
                    # Use robust resolver
                    valid = resolve_dict_row(doc)
                    if valid: rows.append(valid)
                except: pass

    if not rows: die("No valid rows found. Check JSON keys.")
    print(f"Extracted {len(rows)} rows. Beginning batch import...")

    coll_name = "rq_asr_rules" if kind == "asr" else "rq_dictionary_terms"
    coll = db[coll_name]
    
    BATCH_SIZE = 2000
    ops = []
    total = 0
    
    for i, r in enumerate(rows):
        uid = r.get("id") or (f"{r['heard']}_{r['canonical']}" if kind == "asr" else r.get("headword"))
        r["pack_name"] = final_pack_name  # USE CORRECT NAME
        
        if kind == "dict":
             ops.append(UpdateOne({"headword": r["headword"]}, {"$set": r}, upsert=True))
        else:
             ops.append(UpdateOne({"id": uid}, {"$set": r}, upsert=True))
        
        if len(ops) >= BATCH_SIZE:
            coll.bulk_write(ops)
            total += len(ops)
            print(f"  -> Wrote {total}/{len(rows)} records...")
            ops = []

    if ops:
        coll.bulk_write(ops)
        total += len(ops)
        print(f"  -> Wrote {total}/{len(rows)} records (Complete).")

    packs_coll = db["rq_packs"]
    pack_meta = {
        "name": final_pack_name,
        "kind": kind,
        "version": version,
        "enabled": enable,
        "imported_at": datetime.utcnow()
    }
    packs_coll.update_one({"name": pack_meta["name"]}, {"$set": pack_meta}, upsert=True)
    print(f"Pack enabled: {pack_meta['name']}")
    client.close()

def compile_asr_to_redis(db, rds):
    enabled_packs = list(db["rq_packs"].find({"kind": "asr", "enabled": True}))
    if not enabled_packs:
        print("No enabled ASR packs found.")
        return

    pack_names = [p["name"] for p in enabled_packs]
    # Debug print
    print(f"Compiling from packs: {pack_names}")
    
    rules = list(db["rq_asr_rules"].find({"pack_name": {"$in": pack_names}}))
    print(f"Found {len(rules)} rules to compile.")

    rules.sort(key=lambda x: (x.get("priority", 0), x.get("confidence", 0)), reverse=True)

    active_rules = []
    active_hints = set()

    for r in rules:
        rtype = r.get("type", "phrase")
        if rtype == "hint":
            active_hints.add(r["canonical"])
        else:
            active_rules.append({
                "pattern": r["heard"],
                "replacement": r["canonical"],
                "type": rtype,
                "confidence": r["confidence"]
            })
    
    if not active_rules and not active_hints:
        print("Warning: Pack exists but yielded 0 rules. Check 'pack_name' alignment.")
        return

    pipe = rds.pipeline()
    pipe.set("rq:asr:rules", json.dumps(active_rules))
    pipe.delete("rq:asr:hints")
    if active_hints:
        pipe.sadd("rq:asr:hints", *list(active_hints))
    
    pipe.execute()
    print(f"Redis compiled: {len(active_rules)} rules active.")

def build_dictionary_in_chroma(db, collection_name="rq_dnd_dictionary"):
    if not EMBED_PROVIDER: die("RQ_EMBED_PROVIDER must be set (st or openai).")
    
    embedding_func = None
    if EMBED_PROVIDER == "openai":
        from chromadb.utils import embedding_functions
        embedding_func = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"), model_name="text-embedding-3-small")
    elif EMBED_PROVIDER == "st":
        from chromadb.utils import embedding_functions
        embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

    client = chroma_client()
    coll = client.get_or_create_collection(name=collection_name, embedding_function=embedding_func)

    enabled_packs = list(db["rq_packs"].find({"kind": "dict", "enabled": True}))
    if not enabled_packs:
        print("No enabled Dict packs.")
        return

    pack_names = [p["name"] for p in enabled_packs]
    terms = list(db["rq_dictionary_terms"].find({"pack_name": {"$in": pack_names}}))
    print(f"Found {len(terms)} terms to embed.")

    ids, docs, metas = [], [], []
    
    for term in terms:
        text = f"{term['headword']}: {term.get('definition', '')}"
        
        tags = term.get("tags", [])
        if isinstance(tags, list): tags = ", ".join(tags)
        
        meta = {
            "source": term.get("source", "custom"),
            "type": term.get("type", "general"),
            "tags": str(tags)
        }

        ids.append(term.get("id") or term["headword"])
        docs.append(text)
        metas.append(meta)

        if len(ids) >= 100:
            coll.upsert(ids=ids, documents=docs, metadatas=metas)
            print(f"Upserted {len(ids)} terms...")
            ids, docs, metas = [], [], []

    if ids: coll.upsert(ids=ids, documents=docs, metadatas=metas)
    print("✅ Chroma built successfully.")

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_imp = sub.add_parser("import")
    p_imp.add_argument("--zip", required=True)
    p_imp.add_argument("--pack", required=True, choices=["asr","dict"])
    p_imp.add_argument("--name", default="auto")
    p_imp.add_argument("--version", default="auto")
    p_imp.add_argument("--disable", action="store_true")

    sub.add_parser("compile-redis")
    
    p_ch = sub.add_parser("build-chroma")
    p_ch.add_argument("--collection", default="rq_dnd_dictionary")

    args = parser.parse_args()

    if args.cmd == "import":
        import_pack(args.zip, args.pack, args.name, args.version, (not args.disable))
    elif args.cmd == "compile-redis":
        compile_asr_to_redis(mongo_client()[DEFAULT_DB_NAME], redis_client())
    elif args.cmd == "build-chroma":
        build_dictionary_in_chroma(mongo_client()[DEFAULT_DB_NAME], args.collection)

if __name__ == "__main__":
    main()