import os
import chromadb
from google import genai
from openai import OpenAI

class AIEngine:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        
        self.chroma_client = None
        self.rules_collection = None
        try:
            self.chroma_client = chromadb.HttpClient(host="realmquest-chroma", port=8000)
            self.rules_collection = self.chroma_client.get_or_create_collection("dnd_rules")
            print("✅ RAG: Connected to ChromaDB")
        except: print("⚠️ RAG: Chroma Offline")

        self.google_client = None
        if self.gemini_key:
            try: self.google_client = genai.Client(api_key=self.gemini_key)
            except Exception as e: print(f"⚠️ Google Error: {e}")
        
        self.openai_client = None
        if self.openai_key: self.openai_client = OpenAI(api_key=self.openai_key)

    def retrieve_rules(self, query):
        if not self.rules_collection: return ""
        try:
            results = self.rules_collection.query(query_texts=[query], n_results=2)
            if results and results['documents']:
                return f"\n[RELEVANT RULES]:\n" + "\n".join(results['documents'][0]) + "\n"
        except: pass
        return ""

    def generate_story(self, system_prompt, player_input):
        physics_context = self.retrieve_rules(player_input)
        full_prompt = f"{system_prompt}\n{physics_context}\n\nPlayer: {player_input}"

        if self.google_client:
            try:
                response = self.google_client.models.generate_content(model=self.model_name, contents=full_prompt)
                return response.text
            except Exception as e: return f"Gemini Error: {e}"
        
        if self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": player_input}]
                )
                return response.choices[0].message.content
            except: pass
        return "Brain Offline."
