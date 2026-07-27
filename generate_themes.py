import json
import os
from datetime import date
import anthropic

# Load the themes file
with open("themes.json", "r") as f:
    data = json.load(f)

seed_themes = data["seed_themes"]
always_clean = data.get("always_clean_themes", [])
history = data.get("generated_history", [])
runs_since_kawaii = data.get("runs_since_kawaii", 5)
runs_since_silhouette = data.get("runs_since_silhouette", 9)

# Determine current season
month = date.today().month
if month in [12, 1, 2]:
    season = "winter"
    season_hint = "Winter and Christmas themes are very welcome. Avoid summer, tropical, or spring themes."
elif month in [3, 4, 5]:
    season = "spring"
    season_hint = "Spring, Easter, and flower themes are very welcome. Avoid Christmas or winter themes."
elif month in [6, 7, 8]:
    season = "summer"
    season_hint = "Summer, beach, tropical, and garden themes are very welcome. Avoid Christmas or winter themes."
else:
    season = "autumn"
    season_hint = "Autumn, Halloween, harvest, and cozy themes are very welcome. Avoid summer or spring themes."

# Determine theme type for today
if runs_since_silhouette >= 9:
    theme_type = "silhouette"
    theme_type_instruction = f"""Today generate a SILHOUETTE theme.

These are special black silhouette cliparts, perfect for Halloween, gothic, and dark fantasy themes.
The style is pure black flat shapes on transparent background.

ONLY use these categories for silhouettes:
- Halloween: pumpkins, bats, ghosts, spiders, haunted houses, black cats, witches
- Dragons and dark fantasy creatures
- Gothic: ravens, skulls, candles, gravestones
- Night sky: moons, stars, owls

Season note: {season_hint}

Keep it dark, spooky, or gothic. NO cute animals, NO food, NO flowers."""
    runs_since_silhouette = 0
    runs_since_kawaii += 1

elif runs_since_kawaii >= 5:
    theme_type = "kawaii"
    theme_type_instruction = f"""Today generate a KAWAII CHARACTER theme.

IMPORTANT: The main subjects MUST be living creatures like animals, fantasy beings, or characters.
ALL 20 images in this pack will have cute faces - so the theme must support this consistently.

Good examples:
- "kawaii watercolor cats dressed as wizards"
- "watercolor puppies sleeping in flower pots"
- "kawaii forest animals having a picnic"
- "kawaii bunnies baking cupcakes"

Season note: {season_hint}

Do NOT use objects as the main subject.
Animals, fantasy creatures, or characters MUST be the PRIMARY subject."""
    runs_since_kawaii = 0
    runs_since_silhouette += 1

else:
    theme_type = "clean"
    theme_type_instruction = f"""Today generate a CLEAN WATERCOLOR theme.

IMPORTANT: The main subjects MUST be objects, food, plants, or items - NOT animals or characters.
ALL 20 images will have NO faces - pure watercolor illustration style.
Do NOT generate themes with animals or birds like flamingos. Animals always belong to the Kawaii theme type.

Good examples:
- "watercolor kitchen utensils collection"
- "watercolor wedding flowers and ribbons"
- "watercolor tropical fruits arrangement"
- "watercolor cozy autumn home decor"
- "watercolor bakery pastries and breads"

Season note: {season_hint}

Do NOT use animals or characters as the main subject.
Objects, food, plants, or decor MUST be the PRIMARY subject."""
    runs_since_kawaii += 1
    runs_since_silhouette += 1

# Build context
recent_text = "\n".join(f"- {t}" for t in history[-30:]) if history else "None yet."
seed_text = "\n".join(f"- {t}" for t in seed_themes)

prompt = f"""You are a creative director for an Etsy shop selling watercolor and silhouette clipart PNG bundles.

Your task: Generate exactly 1 theme idea for today's clipart bundle.

Current season: {season.upper()}

{theme_type_instruction}

These are the seed categories to draw inspiration from:
{seed_text}

Do NOT repeat any of these already used themes:
{recent_text}

Rules:
- One theme only, no lists
- Be creative and specific
- Specific enough to generate 20 distinct clipart images
- Keep it under 15 words
- Match the current season where possible

Respond ONLY with a single plain string. No JSON, no list, no explanation. Just the theme."""

# Call Claude API
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=100,
    messages=[
        {"role": "user", "content": prompt}
    ]
)

# Parse response
today_theme = message.content[0].text.strip().strip('"').strip("'")
print(f"Today's theme ({theme_type}, {season}): {today_theme}")

# Update history and counters
today = str(date.today())
history.append(today_theme)

data["generated_history"] = history
data["last_updated"] = today
data["runs_since_kawaii"] = runs_since_kawaii
data["runs_since_silhouette"] = runs_since_silhouette

with open("themes.json", "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# Save today's theme
today_output = {
    "date": today,
    "theme": today_theme,
    "theme_type": theme_type,
    "season": season
}

with open("themes_today.json", "w") as f:
    json.dump(today_output, f, indent=2, ensure_ascii=False)

# Reset listing_today.json for fresh run
import os
if os.path.exists("listing_today.json"):
    os.remove("listing_today.json")
    print("Reset listing_today.json for new run")

print(f"Saved theme for {today}: {today_theme}")
