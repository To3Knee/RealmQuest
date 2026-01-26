# //===============================================================
# //Script Name: schemas.py
# //Location: /opt/RealmQuest/api/schemas.py
# //About: The Data Contract. Strict Models for Portal & Bot.
# //===============================================================
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal

# --- 1. CAMPAIGN CONFIG (The Rules) ---
class CampaignFeatures(BaseModel):
    dice_rolling: Literal["auto", "manual"] = "manual"
    images_enabled: bool = True
    voice_enabled: bool = True
    ruleset: Literal["5e_strict", "homebrew", "narrative"] = "5e_strict"

class CampaignConfig(BaseModel):
    # FILE: campaign-config.json
    campaign_name: str
    dm_voice_id: str = "onyx" # Configurable by Player via Portal
    features: CampaignFeatures = Field(default_factory=CampaignFeatures)
    
# --- 2. NPC ARTIFACT (The "Real" Character) ---
class NpcStats(BaseModel):
    class_name: str = "Commoner"
    level: int = 1
    hp_current: int = 10
    hp_max: int = 10
    ac: int = 10

class NpcProfile(BaseModel):
    # FILE: {name}.json (e.g., garok-the-breaker.json)
    name: str 
    status: Literal["alive", "dead", "missing"] = "alive"
    voice_provider: Literal["elevenlabs", "openai"] = "elevenlabs"
    voice_id: str
    personality: str
    appearance: str
    current_location: str
    stats: NpcStats = Field(default_factory=NpcStats)
    memory_hooks: List[str] = [] # e.g. "Met party at tavern"

# --- 3. IMAGE MANIFEST (Player Control) ---
class ImageEntry(BaseModel):
    id: str
    filename: str
    prompt: str
    timestamp: float
    visible: bool = True # Portal sets False to "delete" (hide)

class ImageGallery(BaseModel):
    # FILE: image-manifest.json
    images: List[ImageEntry] = []

# --- 4. SESSION LOG (The Drift Anchor) ---
class SessionEvent(BaseModel):
    timestamp: float
    type: Literal["narrative", "roll", "combat", "loot", "chat"]
    actor: str
    content: str
    metadata: Dict = {}