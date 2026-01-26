import os
import google.generativeai as genai

# Load Key
key = os.getenv("GEMINI_API_KEY")
print(f"🔑 Testing Key: {key[:5]}...{key[-5:]}")

try:
    genai.configure(api_key=key)
    print("📡 Contacting Google...")
    
    # Ask for list
    models = list(genai.list_models())
    
    print(f"✅ Connection Established! Found {len(models)} models.")
    print("------------------------------------------------")
    for m in models:
        if 'generateContent' in m.supported_generation_methods:
            print(f"   🌟 {m.name}")
    print("------------------------------------------------")

except Exception as e:
    print(f"❌ CRITICAL FAILURE: {e}")
