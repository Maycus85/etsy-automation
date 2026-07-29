import json
import os
from datetime import date
import anthropic

with open("themes.json", "r") as f:
    data = json.load(f)

priority_themes = data.get("priority_themes", [])
seed_themes = data["seed_themes"]
always_clean = data.get("always_clean_themes", [])
history = data.get("generated_history", [])
runs_since_kawaii = data.get("runs_since_kawaii", 5)
runs_since_silhouette = data.get("runs_since_silhouette", 9)
priority_index = data.get("priority_index", 0)

# Determine season
month = date.today().month
if month in [12, 1, 2]:
    season = "winter"
    season_hint = "Winter and Christmas themes are very welcome. Avoid summer or tropical themes."
elif month in [3, 4, 5]:
    season = "spring"
    season_hint = "Spring, Easter, and flower themes are very welcome. Avoid Christmas or winter themes."
elif month in [6, 7, 8]:
    season = "summer"
    season_hint = "Summer, beach, tropical, and garden themes are very welcome. Avoid Christmas or winter themes."
else:
    season = "autumn"
    season_hint = "Autumn, Halloween, harvest, and cozy themes are very welcome. Avoid summer or spring themes."

# Determine theme type
if runs_since_silhouette >= 9:
    theme_type = "silhouette"
    theme_type_instruction = f"""Today generate a SILHOUETTE theme.
Pure black flat shapes on transparent background.
Only use: Halloween, gothic dragons, ravens, skulls, candles, night sky.
Season note: {season_hint}"""
    runs_since_silhouette = 0
    runs_since_kawaii += 1

elif runs_since_kawaii >= 5:
    theme_type = "kawaii"
    theme_type_instruction = f"""Today generate a KAWAII CHARACTER theme.
Main subjects MUST be living creatures with cute faces.
Good: kawaii cats dressed as wizards, puppies in flower pots, baby dragons in teacups.
Do NOT use objects as main subject.
Season note: {season_hint}"""
    runs_since_kawaii = 0
    runs_since_silhouette += 1

else:
    theme_type = "clean"
    theme_type_instruction = f"""Today generate a CLEAN WATERCOLOR theme.
Main subjects MUST be objects, food, plants, or items - NOT animals or characters.
Good: kitchen utensils, wedding flowers, tropical fruits, autumn home decor.
Do NOT use animals or characters as main subject.
Do NOT generate themes with animals or birds as main focus.
Season note: {season_hint}"""
    runs_since_kawaii += 1
    runs_since_silhouette += 1

# Check if we have unused priority themes
available_priority = [t for t in priority_themes if t not in history]
today_theme = None

if available_priority and theme_type == "clean":
    # Use next priority theme for clean runs
    today_theme = available_priority[0]
    print(f"Using priority theme: {today_theme}")
    theme_source = "priority"
else:
    # Generate with Claude
    recent_text = "\n".join(f"- {t}" for t in history[-30:]) if history else "None yet."
    seed_text = "\n".join(f"- {t}" for t in seed_themes)
    priority_text = "\n".join(f"- {t}" for t in available_priority[:10]) if available_priority else "All priority themes used."

    prompt = f"""You are a creative director for an Etsy shop selling watercolor and clipart PNG bundles.

Your task: Generate exactly 1 theme idea for today's clipart bundle.

Current season: {season.upper()}

{theme_type_instruction}

These proven bestseller themes should inspire you (use variations if not used yet):
{priority_text}

Additional seed categories:
{seed_text}

Do NOT repeat any of these already used themes:
{recent_text}

Rules:
- One theme only
- Be creative and specific
- Specific enough to generate 50 distinct clipart images
- Keep it under 15 words
- Match the current season where possible

Respond ONLY with a single plain string. Just the theme."""

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}]
    )
    today_theme = message.content[0].text.strip().strip('"').strip("'")
    theme_source = "generated"

print(f"Today's theme ({theme_type}, {season}, {theme_source}): {today_theme}")

# Update data
today = str(date.today())
history.append(today_theme)

data["generated_history"] = history
data["last_updated"] = today
data["runs_since_kawaii"] = runs_since_kawaii
data["runs_since_silhouette"] = runs_since_silhouette

with open("themes.json", "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

today_output = {
    "date": today,
    "theme": today_theme,
    "theme_type": theme_type,
    "season": season,
    "source": theme_source
}

with open("themes_today.json", "w") as f:
    json.dump(today_output, f, indent=2, ensure_ascii=False)

# Reset listing_today.json
import os as os_module
if os_module.path.exists("listing_today.json"):
    os_module.remove("listing_today.json")

print(f"Saved theme for {today}: {today_theme}")
