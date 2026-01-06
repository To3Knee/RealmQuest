import streamlit as st
import os
from dotenv import load_dotenv, set_key

# Load existing .env
env_path = "../.env"
load_dotenv(env_path)

st.set_page_config(page_title="RealmQuest Architect", page_icon="🌀")

st.title("🌀 RealmQuest Architect Portal")
st.subheader("Engine Configuration Control")

# API Management Section
with st.expander("🔑 API Credentials", expanded=True):
    gemini_key = st.text_input("Gemini API Key", value=os.getenv("GEMINI_API_KEY"), type="password")
    eleven_key = st.text_input("ElevenLabs API Key", value=os.getenv("ELEVENLABS_API_KEY"), type="password")
    discord_token = st.text_input("Discord Bot Token", value=os.getenv("DISCORD_TOKEN"), type="password")

# Campaign Selection
with st.expander("📜 Active Campaign Settings", expanded=True):
    repo_path = st.text_input("Local Campaign Path (Dev)", value=os.getenv("CAMPAIGN_PATH"))
    gh_repo = st.text_input("GitHub Repo (Prod)", value=os.getenv("GH_CAMPAIGN_REPO"))

if st.button("Save Configuration"):
    set_key(env_path, "GEMINI_API_KEY", gemini_key)
    set_key(env_path, "ELEVENLABS_API_KEY", eleven_key)
    set_key(env_path, "DISCORD_TOKEN", discord_token)
    set_key(env_path, "CAMPAIGN_PATH", repo_path)
    set_key(env_path, "GH_CAMPAIGN_REPO", gh_repo)
    st.success("✅ Configuration saved to .env")