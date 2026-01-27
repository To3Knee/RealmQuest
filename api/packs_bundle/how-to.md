the packs **fit cleanly** into the stack, but they belong in **different places**:

* **MongoDB** = source-of-truth for packs (rules, versions, enabled/disabled, metadata)
* **Redis** = fast cache of “active ASR rules” so your bot can correct transcripts instantly
* **ChromaDB** = semantic retrieval (dictionary definitions / lore / rule explanations)

To eliminate the confusion and make this “one command per step,” there is a **single pack manager script** that imports the ZIP packs into Mongo, compiles the ASR cache into Redis, and (optionally) builds the Chroma dictionary collection.

## Download the pack manager script

* rq-pack-manager-v1.0.0.py

---

# Where each pack goes in the stack

## 1) ASR Compendium Expansion Pack v1.1.0 (speech cleanup)

**Goes to: Mongo + Redis**

* Mongo: stores all rules/hints and pack metadata
* Redis: stores compiled active rules for fast runtime correction

✅ **This is the only ASR pack you need to ingest** (it already includes core v1.0.0 merged/deduped)

ZIP:

* `dnd-asr-language-pack-bundle-v1.1.0.zip`
  (you already have it)

## 2) D&D Custom Dictionary v1.0.0 (definitions for RAG)

**Goes to: Mongo + Chroma**

* Mongo: stores the structured dictionary entries
* Chroma: stores embeddings for semantic retrieval (“what is opportunity attack?”)

ZIP:

* `dnd-custom-dictionary-pack-v1.0.0.zip`

---

# “What packs do I ingest?” (simple list)

You ingest **two ZIPs**:

1. **ASR pack (speech correction + hints)**

* dnd-asr-language-pack-bundle-v1.1.0.zip

2. **Dictionary pack (definitions / RAG)**

* dnd-custom-dictionary-pack-v1.0.0.zip

Optional/rollback only:

* data/dnd-asr-core-pack-v1.0.0.zip

---

# How to run it with your containers

Because your services are on the `realmquest_net` network, the script defaults already match your container names:

* Mongo URI default: `mongodb://realmquest-mongo:27017`
* Redis host default: `realmquest-redis`
* Chroma URL default: `http://realmquest-chroma:8000`

You can run the script either:

* on the host (if it can reach the docker network), or
* inside your API container (best), or
* as a one-off python container attached to `realmquest_net`

## Step 1 — Import the ASR pack into Mongo

```bash
python3 rq-pack-manager-v1.0.0.py import \
  --zip dnd-asr-language-pack-bundle-v1.1.0.zip \
  --pack asr
```

## Step 2 — Compile active ASR rules into Redis

```bash
python3 rq-pack-manager-v1.0.0.py compile-redis
```

## Step 3 — Import the Dictionary pack into Mongo

```bash
python3 rq-pack-manager-v1.0.0.py import \
  --zip dnd-custom-dictionary-pack-v1.0.0.zip \
  --pack dict
```

## Step 4 — Build Chroma dictionary collection (RAG)

Chroma needs embeddings. The script supports:

### Option A: OpenAI embeddings

```bash
export RQ_EMBED_PROVIDER=openai
export OPENAI_API_KEY="..."
# optional:
export RQ_OPENAI_EMBED_MODEL="text-embedding-3-small"

python3 rq-pack-manager-v1.0.0.py build-chroma --collection rq_dnd_dictionary
```

### Option B: Local embeddings via sentence-transformers

```bash
pip install sentence-transformers
export RQ_EMBED_PROVIDER=st
export RQ_ST_MODEL="all-MiniLM-L6-v2"

python3 rq-pack-manager-v1.0.0.py build-chroma --collection rq_dnd_dictionary
```

---

# What gets created in Mongo / Redis / Chroma

## Mongo collections

* `rq_packs` — pack registry (enabled, version, kind)
* `rq_asr_rules` — ASR corrections + hints (deterministic)
* `rq_dictionary_terms` — dictionary entries (definitions)

## Redis keys

* `rq:asr:meta` — what packs are active, compiled time
* `rq:asr:rules` — single JSON blob of sorted rules (priority/confidence/type)
* `rq:asr:hints` — set of canonical hint phrases

## Chroma collection

* `rq_dnd_dictionary` (default) — embedded dictionary docs for semantic retrieval

---

## One last sanity simplifier

If your immediate goal is: **“stop tavern→cavern and ale→nail”**:

Do only:

1. import ASR v1.1.0
2. compile-redis
   …and you’re done.

If you also want: **“DM, define X / recall rule text / explain condition”**:
Then do dictionary import + chroma build.

