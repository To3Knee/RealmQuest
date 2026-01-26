#!/bin/bash

# --- CONFIG ---
BASE_URL="https://raw.githubusercontent.com/5e-bits/5e-database/main/src"
DIR_2014="/opt/RealmQuest-Campaigns/rules/2014"
DIR_2024="/opt/RealmQuest-Campaigns/rules/2024"

# --- FILE LISTS ---
FILES_2014=(
  "5e-SRD-Ability-Scores.json"
  "5e-SRD-Alignments.json"
  "5e-SRD-Backgrounds.json"
  "5e-SRD-Classes.json"
  "5e-SRD-Conditions.json"
  "5e-SRD-Damage-Types.json"
  "5e-SRD-Equipment-Categories.json"
  "5e-SRD-Equipment.json"
  "5e-SRD-Feats.json"
  "5e-SRD-Features.json"
  "5e-SRD-Languages.json"
  "5e-SRD-Levels.json"
  "5e-SRD-Magic-Items.json"
  "5e-SRD-Magic-Schools.json"
  "5e-SRD-Monsters.json"
  "5e-SRD-Proficiencies.json"
  "5e-SRD-Races.json"
  "5e-SRD-Rule-Sections.json"
  "5e-SRD-Rules.json"
  "5e-SRD-Skills.json"
  "5e-SRD-Spells.json"
  "5e-SRD-Subclasses.json"
  "5e-SRD-Subraces.json"
  "5e-SRD-Traits.json"
  "5e-SRD-Weapon-Properties.json"
)

FILES_2024=(
  "5e-SRD-Ability-Scores.json"
  "5e-SRD-Alignments.json"
  "5e-SRD-Backgrounds.json"
  "5e-SRD-Conditions.json"
  "5e-SRD-Damage-Types.json"
  "5e-SRD-Equipment-Categories.json"
  "5e-SRD-Equipment.json"
  "5e-SRD-Feats.json"
  "5e-SRD-Languages.json"
  "5e-SRD-Magic-Schools.json"
  "5e-SRD-Proficiencies.json"
  "5e-SRD-Skills.json"
  "5e-SRD-Weapon-Mastery-Properties.json"
  "5e-SRD-Weapon-Properties.json"
)

# --- DOWNLOAD LOOPS ---
echo "⬇️ Starting 2014 Rules Download..."
for file in "${FILES_2014[@]}"; do
  echo "  - Pulling $file..."
  curl -s -o "$DIR_2014/$file" "$BASE_URL/2014/$file"
done

echo "⬇️ Starting 2024 Rules Download..."
for file in "${FILES_2024[@]}"; do
  echo "  - Pulling $file..."
  curl -s -o "$DIR_2024/$file" "$BASE_URL/2024/$file"
done

echo "✅ Download Complete!"
