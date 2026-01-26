# ===============================================================
# Script Name: ai_engine.py
# Script Location: /opt/RealmQuest/api/ai_engine.py
# Date: 2026-01-26
# Version: 18.10.0
# About: Image Generation with subdirectory support & Style Injection
# ===============================================================

import os
import requests
import uuid
from datetime import datetime
import chromadb
from google import genai
from openai import OpenAI

class AIEngine:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        
        # --- RAG SETUP ---
        self.chroma_client = None
        self.rules_collection = None
        try:
            # We assume the model cache is handled by Dockerfile ENV now
            self.chroma_client = chromadb.HttpClient(host="realmquest-chroma", port=8000)
            self.rules_collection = self.chroma_client.get_or_create_collection("dnd_rules")
            print("✅ RAG: Connected to ChromaDB")
        except: print("⚠️ RAG: Chroma Offline")

        # --- CLIENTS ---
        self.google_client = None
        if self.gemini_key:
            try: self.google_client = genai.Client(api_key=self.gemini_key)
            except Exception as e: print(f"⚠️ Google Error: {e}")
        
        self.openai_client = None
        if self.openai_key: self.openai_client = OpenAI(api_key=self.openai_key)

    def generate_story(self, system_prompt, player_input):
        # Prefer Gemini for Text
        if self.google_client:
            try:
                full_prompt = f"{system_prompt}\n\nPlayer: {player_input}"
                response = self.google_client.models.generate_content(model=self.model_name, contents=full_prompt)
                return response.text
            except Exception as e: return f"Gemini Error: {e}"
        
        # Fallback to OpenAI
        if self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": player_input}]
                )
                return response.choices[0].message.content
            except: pass
        return "Brain Offline."

    def generate_image(self, prompt, campaign_path="/campaigns/default", style="Cinematic Fantasy, D&D Art"):
        """Generates an image via DALL-E 3 and saves it locally"""
        if not self.openai_client:
            return None, "OpenAI Key Missing"

        try:
            # 1. Apply Portal Art Style
            # If the user selected "Oil Painting" in portal, it injects here.
            full_prompt = f"{style}: {prompt}"
            
            # 2. Generate URL
            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=full_prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url

            # 3. Download & Save
            # FIX: Save to /assets/images/ to keep root clean
            assets_dir = os.path.join(campaign_path, "assets", "images")
            os.makedirs(assets_dir, exist_ok=True)

            # Create Filename
            filename = f"vis_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.png"
            file_path = os.path.join(assets_dir, filename)

            img_data = requests.get(image_url).content
            with open(file_path, 'wb') as handler:
                handler.write(img_data)
            
            # Return filename (Bot searches for it recursively, so moving it is fine)
            return filename, None

        except Exception as e:
            return None, str(e)