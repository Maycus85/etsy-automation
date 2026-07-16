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

# Build context: all previously used themes to avoid repetition
recent_text = "\n".join(f"- {t}" for t in history) if history else "None yet."
seed_text = "\n".join(f"- {t}" for t in seed_themes)

prompt = f"""You are a creative director for an Etsy shop selling kawaii watercolor clipart PNG bundles.

Your task: Generate exactly 1 theme idea for today's clipart bundle.

These are the seed categories to draw inspiration from:
{seed_text}

Do NOT repeat any of these already used themes:
{recent_text}

Rules:
- One theme only, no lists
- Be creative and specific, combinations are welcome (e.g. "watercolor cats hosting a tea party", "kawaii vegetables with funny faces", "watercolor dogs dressed as wizards")
- Suitable for kawaii or watercolor illustration style
- Specific enough to generate 20 distinct clipart images from it
- Keep it under 15 words

Respond ONLY with a single plain string. No JSON, no list, no explanation. Just the theme.
Example: kawaii watercolor cats hosting a birthday tea party"""

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
print(f"Today's theme: {today_theme}")

# Update history
today = str(date.today())
history.append(today_theme)

data["generated_history"] = history
data["last_updated"] = today

with open("themes.json", "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# Save today's theme
today_output = {
    "date": today,
    "theme": today_theme
}

with open("themes_today.json", "w") as f:
    json.dump(today_output, f, indent=2, ensure_ascii=False)

print(f"Saved theme for {today}: {today_theme}")
