#!/bin/bash
# Script Name: ingest.sh
# Location: /packs/ingest.sh

echo "📦 STARTING PACK INGESTION..."
cd /packs || exit

# 1. Import Hearing Rules (ASR)
echo "--- Importing ASR Pack ---"
python3 rq-pack-manager.py import --zip dnd-asr-language-pack-bundle-v1.1.0.zip --pack asr

# 2. Import Brain Rules (Dictionary)
echo "--- Importing Dictionary Pack ---"
python3 rq-pack-manager.py import --zip dnd-custom-dictionary-pack-v1.0.0.zip --pack dict

# 3. Compile Hearing Aid
echo "--- Compiling Redis Rules ---"
python3 rq-pack-manager.py compile-redis

# 4. Build Knowledge Base
echo "--- Building Chroma Embeddings ---"
export RQ_EMBED_PROVIDER=st
python3 rq-pack-manager.py build-chroma --collection rq_dnd_dictionary

echo "✅ INGESTION COMPLETE."