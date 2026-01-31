# ===============================================================
# Script Name: ai_engine.py
# Script Location: /opt/RealmQuest/api/ai_engine.py
# Date: 2026-01-26
# Version: 18.17.0
# About: Multimodal Engine (Text, Image, & Gemini Audio)
# ===============================================================

import os
import requests
import uuid
import base64
from datetime import datetime
import chromadb
from google import genai
from google.genai import types
from openai import OpenAI

class AIEngine:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        
        # --- RAG SETUP ---
        self.chroma_client = None
        self.rules_collection = None
        try:
            self.chroma_client = chromadb.HttpClient(host="realmquest-chroma", port=8000)
            self.rules_collection = self.chroma_client.get_or_create_collection("dnd_rules")
            print("✅ RAG: Connected to ChromaDB")
        except: print("⚠️ RAG: Chroma Offline")

        # --- CLIENTS ---
        self.google_client = None
        if self.gemini_key:
            try: 
                self.google_client = genai.Client(api_key=self.gemini_key, http_options={"api_version": "v1alpha"})
                print("✅ AI: Gemini Client Ready")
            except Exception as e: print(f"⚠️ AI: Gemini Init Failed: {e}")

        self.openai_client = None
        if self.openai_key:
            try: 
                self.openai_client = OpenAI(api_key=self.openai_key)
                print("✅ AI: OpenAI Client Ready")
            except: pass

    # --- TEXT / STORY ---
    def generate_story(self, system_prompt, user_prompt):
        """Generates text response using RAG + Gemini/OpenAI"""
        context_text = ""
        if self.rules_collection:
            try:
                results = self.rules_collection.query(query_texts=[user_prompt], n_results=2)
                if results['documents']:
                    context_text = "\nRELEVANT RULES:\n" + "\n".join(results['documents'][0])
            except: pass

        full_prompt = f"{user_prompt}\n{context_text}"

        # 1. Try Gemini
        if self.google_client:
            try:
                # Config for text generation
                config = types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7
                )
                response = self.google_client.models.generate_content(
                    model=self.model_name,
                    contents=[full_prompt],
                    config=config
                )
                return response.text
            except Exception as e:
                print(f"⚠️ Gemini Text Fail: {e}")

        # 2. Fallback OpenAI
        if self.openai_client:
            try:
                completion = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": full_prompt}
                    ]
                )
                return completion.choices[0].message.content
            except Exception as e:
                return f"Error: {e}"
        
        return "AI Offline."

    # --- IMAGE ---
    def generate_image(
        self,
        prompt,
        campaign_path="/campaigns/default",
        style="Cinematic Fantasy, D&D Art",
        output_dir=None,
        output_filename=None,
    ):
        """Generates an image via DALL-E 3.

        Surgical extension:
        - Backwards compatible (default output remains campaign_path/assets/images)
        - Allows caller to specify output_dir and/or output_filename
        """
        if not self.openai_client:
            return None, "OpenAI Key Missing"

        try:
            full_prompt = f"{style}: {prompt}"
            response = self.openai_client.images.generate(
                model="dall-e-3", prompt=full_prompt, size="1024x1024", quality="standard", n=1
            )
            image_url = response.data[0].url

            assets_dir = output_dir or os.path.join(campaign_path, "assets", "images")
            os.makedirs(assets_dir, exist_ok=True)

            if output_filename:
                # Ensure a safe filename, always .png (DALL-E returns a PNG-friendly URL)
                safe = os.path.basename(str(output_filename)).strip() or "image"
                if not safe.lower().endswith(".png"):
                    safe = f"{safe}.png"
                filename = safe
            else:
                filename = f"vis_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.png"

            file_path = os.path.join(assets_dir, filename)

            img_data = requests.get(image_url).content
            with open(file_path, 'wb') as handler: handler.write(img_data)
            
            return filename, None
        except Exception as e:
            return None, str(e)

    # --- AUDIO: SPEECH (Priority 3) ---
    def generate_speech(self, text, voice_name="Puck"):
        """
        Generates TTS using Gemini 2.0 Flash Audio Modality.
        Voices: Puck, Charon, Kore, Fenrir, Aoede
        """
        if not self.google_client: return None

        try:
            # Gemini 2.0 Speech Config
            speech_config = types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            )
            
            config = types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=speech_config
            )

            response = self.google_client.models.generate_content(
                model=self.model_name,
                contents=[text],
                config=config
            )

            # Extract Audio Bytes
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    return part.inline_data.data # Returns base64/bytes
            return None
        except Exception as e:
            print(f"⚠️ Gemini Speech Fail: {e}")
            return None

    # --- AUDIO: SFX (Priority 3) ---
    def generate_sfx(self, prompt):
        """
        Attempts to generate Sound Effects using Gemini 2.0 Flash.
        Note: Current experimental support mainly focuses on Speech, 
        but native audio generation is evolving.
        """
        if not self.google_client: return None

        try:
            # We prompt specifically for a sound effect
            sfx_prompt = f"Generate a high quality sound effect of: {prompt}. Do not speak, just generate the sound."
            
            config = types.GenerateContentConfig(
                response_modalities=["AUDIO"]
            )

            response = self.google_client.models.generate_content(
                model=self.model_name,
                contents=[sfx_prompt],
                config=config
            )

            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    return part.inline_data.data
            return None
        except Exception as e:
            print(f"⚠️ Gemini SFX Fail: {e}")
            return None