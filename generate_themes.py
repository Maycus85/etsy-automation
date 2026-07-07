import json
import os
import re
from datetime import date
import anthropic

# Load the themes file
with open("themes.json", "r") as f:
    data = json.load(f)

seed_themes = data["seed_themes"]
history = data.get("generated_history", [])

# Build context: last 10 used themes (to avoid repetition)
recent_themes = history[-10:] if len(history) >= 10 else history

# Build the prompt for Claude
recent_themes_text = "\n".join(f"- {t}" for t in recent_themes) if recent_themes else "None yet."
seed_themes_text = "\n".join(f"- {t}" for t in seed_themes)

prompt = f"""You are a creative director for an Etsy shop selling watercolor and kawaii-style clipart PNG bundles.

Your task: Generate exactly 10 theme ideas for today's clipart bundles.

Rules:
- 5 themes should be fresh variations or creative combinations of these seed categories:
{seed_themes_text}

- 5 themes should be completely new and creative ideas that would sell well on Etsy as kawaii/watercolor clipart
- Do NOT repeat any of these recently used themes:
{recent_themes_text}

- Think creatively: combine unexpected elements (e.g. "watercolor lions in teacups", "kawaii bread with faces")
- All themes must be suitable for kawaii or watercolor illustration style
- Each theme should be specific enough to generate 25 distinct images

Respond ONLY with a JSON array of exactly 10 strings. No explanation, no markdown, just the raw JSON array.
Example format: ["theme one", "theme two", "theme three"]"""

# Call Claude API
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1000,
    messages=[
        {"role": "user", "content": prompt}
    ]
)

# Parse the response
response_text = message.content[0].text.strip()

# Strip markdown code blocks if present
response_text = re.sub(r"```json\s*", "", response_text)
response_text = re.sub(r"```\s*", "", response_text)
response_text = response_text.strip()

new_themes = json.loads(response_text)

# Update history
today = str(date.today())
history.extend(new_themes)

# Save updated file
data["generated_history"] = history
data["last_updated"] = today

with open("themes.json", "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# Save today's themes separately for the next pipeline steps
today_output = {
    "date": today,
    "themes": new_themes
}

with open("themes_today.json", "w") as f:
    json.dump(today_output, f, indent=2, ensure_ascii=False)

print(f"Generated {len(new_themes)} themes for {today}:")
for i, theme in enumerate(new_themes, 1):
    print(f"  {i}. {theme}")
