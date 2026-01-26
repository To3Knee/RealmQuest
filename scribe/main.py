# //===============================================================
# //Script Name: main.py (The Scribe V2 - Anti-Hallucination)
# //===============================================================
import os
from fastapi import FastAPI, UploadFile, File
from faster_whisper import WhisperModel

app = FastAPI()

# Load Model with VAD (Voice Activity Detection) enabled settings
print("👂 Loading Scribe Ears (Whisper Small)...")
model = WhisperModel("small.en", device="cpu", compute_type="int8")
print("✅ Scribe Ready.")

HALLUCINATIONS = [
    "Thanks for watching!",
    "Thank you for watching!",
    "Subtitles by",
    "Subscribe",
    "you" # Common single-word hallucination
]

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    temp_filename = f"temp_{file.filename}"
    with open(temp_filename, "wb") as buffer:
        buffer.write(await file.read())

    # vad_filter=True : Ignores silence/static
    # beam_size=5 : Better accuracy
    segments, info = model.transcribe(
        temp_filename, 
        beam_size=5, 
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500)
    )
    
    text = " ".join([segment.text for segment in segments]).strip()
    
    # Cleanup
    os.remove(temp_filename)
    
    # Hallucination Check
    clean_text = text.lower().strip(" .!?,")
    for phantom in HALLUCINATIONS:
        if clean_text == phantom.lower().strip(" .!?,"):
            print(f"👻 Filtered Hallucination: '{text}'")
            return {"text": ""}

    print(f"📝 Heard: {text}")
    return {"text": text}
