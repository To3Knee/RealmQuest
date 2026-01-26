import os
API_URL = os.getenv("API_URL", "http://rq-api:8000")
SCRIBE_URL = os.getenv("SCRIBE_URL", "http://rq-scribe:9000")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
RMS_THRESHOLD = 200
SILENCE_TIMEOUT = 3.0      # Relaxed timing
MAX_RECORD_TIME = 30.0     # Longer queries
PRE_BUFFER_LEN = 50 
