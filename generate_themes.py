import json
import os
from datetime import date
import anthropic

# Load the themes file
with open("themes.json", "r") as f:
    data = json.load(f)

seed_themes = data["seed_themes"]
history = data.get("generated_history", [])
runs_since_kawaii = data.get("runs_since_kawaii", 5)  # Start with kawaii on first run

# Determine theme type for today
# Every 6th run is kawaii, rest is clean watercolor
if runs_since_kawaii >= 5:
    theme_type = "kawaii"
    theme_type_instruction = """Today generate a KAWAII theme - featuring cute animals, fantasy creatures, 
or characters with personality. Examples: "kawaii watercolor cats dressed as wizards", 
"watercolor puppies sleeping in flower pots", "kawaii dragons having a tea party" """
    runs_since_kawaii = 0
else:
    theme_type = "clean"
    theme_type_instruction = """Today generate a CLEAN WATERCOLOR theme - featuring objects, food, plants, 
or items WITHOUT characters or animals. Examples: "watercolor kitchen utensils collection", 
"watercolor wedding flowers and ribbons", "watercolor tropical fruits arrangement" """
    runs_since_kawaii += 1

# Build context
recent_text = "\n".join(f"- {t}" for t in history) if history else "None yet."
seed_text = "\n".join(f"- {t}" for t in seed_themes)

prompt = f"""You are a creative director for an Etsy shop selling watercolor clipart PNG bundles.

Your task: Generate exactly 1 theme idea for today's clipart bundle.

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
print(f"Today's theme ({theme_type}): {today_theme}")

# Update history and counter
today = str(date.today())
history.append(today_theme)

data["generated_history"] = history
data["last_updated"] = today
data["runs_since_kawaii"] = runs_since_kawaii

with open("themes.json", "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# Save today's theme
today_output = {
    "date": today,
    "theme": today_theme,
    "theme_type": theme_type
}

with open("themes_today.json", "w") as f:
    json.dump(today_output, f, indent=2, ensure_ascii=False)

print(f"Saved theme for {today}: {today_theme}")
