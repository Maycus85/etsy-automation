import json
import os
import time
import requests
from datetime import date
from pathlib import Path

FAL_API_KEY = os.environ["FAL_API_KEY"]
FAL_URL = "https://fal.run"

HEADERS = {
    "Authorization": f"Key {FAL_API_KEY}",
    "Content-Type": "application/json"
}

# Style A: Realistic watercolor (OpenAI GPT-Image-2 via fal.ai)
# Best for: wedding, kitchen, birthday, serious themes
REALISTIC_MODEL = "fal-ai/gpt-image-1"
REALISTIC_SUFFIX = ", classic watercolor painting style, soft warm pastel tones, beige and cream tones, natural hand-painted texture with visible brushstrokes, no anime style, no cartoon outlines, no digital look, isolated on pure white transparent background, no shadows, no text, no frame, professional clipart, high detail, commercial use"

# Style B: Kawaii anime watercolor (Nano Banana via fal.ai)
# Best for: animals, fantasy, kids, cute themes
KAWAII_MODEL = "fal-ai/nano-banana-2"
KAWAII_SUFFIX = ", kawaii watercolor style, soft pastel colors, cute anime-inspired illustration, gentle brushstrokes, isolated on pure white transparent background, no shadows, no text, no frame, professional clipart, commercial use"

# Items to generate per theme (20 total)
ITEMS_PER_THEME = 20


def build_item_prompts(theme: str, n: int) -> list[str]:
    """Ask Claude to generate N distinct item prompts for a theme."""
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"""Generate exactly {n} distinct clipart item descriptions for the theme: "{theme}"

Rules:
- Each item should be a single specific object or character
- Items should be varied and cover the theme well
- Keep each description short (5-10 words max)
- No duplicates
- Make them suitable for watercolor clipart illustration

Respond ONLY with a JSON array of {n} strings. Example: ["a cute teacup with roses", "a small watering can"]"""
        }]
    )

    text = message.content[0].text.strip()
    import re
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text).strip()
    return json.loads(text)


def generate_image(model: str, prompt: str, output_path: Path) -> bool:
    """Generate a single image and save it."""
    try:
        response = requests.post(
            f"{FAL_URL}/{model}",
            headers=HEADERS,
            json={
                "prompt": prompt,
                "image_size": "square_hd",
                "num_images": 1,
            },
            timeout=120
        )
        response.raise_for_status()
        data = response.json()

        # Get image URL from response
        image_url = data["images"][0]["url"]

        # Download image
        img_response = requests.get(image_url, timeout=60)
        img_response.raise_for_status()

        output_path.write_bytes(img_response.content)
        return True

    except Exception as e:
        print(f"  Error generating image: {e}")
        return False


def generate_theme_images(theme: str, theme_index: int, output_dir: Path):
    """Generate all images for a theme in both styles."""
    print(f"\nTheme {theme_index + 1}: {theme}")

    # Create output directories
    safe_name = theme.replace(" ", "_").replace("/", "_")[:50]
    realistic_dir = output_dir / f"{theme_index:02d}_{safe_name}_realistic"
    kawaii_dir = output_dir / f"{theme_index:02d}_{safe_name}_kawaii"
    realistic_dir.mkdir(parents=True, exist_ok=True)
    kawaii_dir.mkdir(parents=True, exist_ok=True)

    # Generate item prompts
    print(f"  Generating {ITEMS_PER_THEME} item prompts...")
    items = build_item_prompts(theme, ITEMS_PER_THEME)
    print(f"  Items: {items[:3]}...")

    # Generate realistic style images
    print(f"  Generating {ITEMS_PER_THEME} realistic watercolor images...")
    for i, item in enumerate(items):
        output_path = realistic_dir / f"{i+1:02d}.png"
        if output_path.exists():
            print(f"    [{i+1}/{ITEMS_PER_THEME}] Already exists, skipping")
            continue
        prompt = f"A single watercolor clipart illustration of {item}{REALISTIC_SUFFIX}"
        success = generate_image(REALISTIC_MODEL, prompt, output_path)
        print(f"    [{i+1}/{ITEMS_PER_THEME}] {'OK' if success else 'FAILED'}: {item}")
        time.sleep(1)  # Rate limiting

    # Generate kawaii style images
    print(f"  Generating {ITEMS_PER_THEME} kawaii watercolor images...")
    for i, item in enumerate(items):
        output_path = kawaii_dir / f"{i+1:02d}.png"
        if output_path.exists():
            print(f"    [{i+1}/{ITEMS_PER_THEME}] Already exists, skipping")
            continue
        prompt = f"A single cute illustration of {item}{KAWAII_SUFFIX}"
        success = generate_image(KAWAII_MODEL, prompt, output_path)
        print(f"    [{i+1}/{ITEMS_PER_THEME}] {'OK' if success else 'FAILED'}: {item}")
        time.sleep(1)  # Rate limiting

    return safe_name, items


def main():
    today = str(date.today())
    output_dir = Path(f"images/{today}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load today's themes
    with open("themes_today.json", "r") as f:
        data = json.load(f)

    themes = data["themes"]
    print(f"Generating images for {len(themes)} themes on {today}")

    results = []
    for i, theme in enumerate(themes):
        safe_name, items = generate_theme_images(theme, i, output_dir)
        results.append({
            "theme": theme,
            "safe_name": safe_name,
            "items": items,
            "realistic_dir": f"images/{today}/{i:02d}_{safe_name}_realistic",
            "kawaii_dir": f"images/{today}/{i:02d}_{safe_name}_kawaii"
        })

    # Save generation log
    log_path = output_dir / "generation_log.json"
    with open(log_path, "w") as f:
        json.dump({
            "date": today,
            "themes_processed": len(themes),
            "results": results
        }, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Images saved to {output_dir}")
    print(f"Log saved to {log_path}")


if __name__ == "__main__":
    main()
