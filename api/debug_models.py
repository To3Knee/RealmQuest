import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load env vars directly
load_dotenv("/app/.env")
api_key = os.getenv("GEMINI_API_KEY")

print(f"🔑 Using API Key: {api_key[:5]}...{api_key[-5:] if api_key else 'None'}")

if not api_key:
    print("❌ ERROR: No API Key found!")
    exit(1)

genai.configure(api_key=api_key)

print("\n📡 Connecting to Google AI...")
try:
    print("📋 AVAILABLE MODELS:")
    print("--------------------------------------------------")
    count = 0
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"   ✅ {m.name}")
            count += 1
    print("--------------------------------------------------")
    print(f"Total Generating Models: {count}")
    
    if count == 0:
        print("⚠️  No generating models found. Your API key might be invalid or region-locked.")

except Exception as e:
    print(f"❌ CONNECTION FAILED: {e}")
