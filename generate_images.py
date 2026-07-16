import json
import os
import time
import requests
from datetime import date
from pathlib import Path
import anthropic

FAL_API_KEY = os.environ["FAL_API_KEY"]
FAL_URL = "https://fal.run/fal-ai/nano-banana-2"

HEADERS = {
    "Authorization": f"Key {FAL_API_KEY}",
    "Content-Type": "application/json"
}

STYLE_SUFFIX = ", kawaii watercolor style, soft pastel colors, cute illustration, gentle brushstrokes, isolated on pure white background, transparent background, no shadows, no text, no frame, professional clipart, commercial use"

TARGET_IMAGES = 20  # Total images we want per theme


def build_item_prompts(theme: str, n: int) -> list:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""Generate exactly {n} distinct clipart item descriptions for the theme: "{theme}"

Rules:
- Each item is one specific object or character
- Keep each description under 8 words
- No duplicates
- Suitable for kawaii watercolor clipart

Respond ONLY with a JSON array of {n} strings.
Example: ["cute birthday cake with candles", "pastel balloon bouquet"]"""
        }]
    )

    text = message.content[0].text.strip()
    import re
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text).strip()
    return json.loads(text)


def generate_image(prompt: str, output_path: Path) -> bool:
    try:
        response = requests.post(
            FAL_URL,
            headers=HEADERS,
            json={
                "prompt": prompt,
                "aspect_ratio": "1:1",
                "resolution": "2K",
                "num_images": 1,
                "output_format": "png",
            },
            timeout=120
        )
        response.raise_for_status()
        data = response.json()

        image_url = data["images"][0]["url"]
        img_response = requests.get(image_url, timeout=60)
        img_response.raise_for_status()

        output_path.write_bytes(img_response.content)
        return True

    except Exception as e:
        print(f"  Error: {e}")
        return False


def main():
    today = str(date.today())

    # Load today's theme
    with open("themes_today.json", "r") as f:
        data = json.load(f)

    theme = data["theme"]
    print(f"Generating images for theme: {theme}")

    # Create output folder
    safe_name = theme.replace(" ", "_").replace("/", "_")[:50]
    output_dir = Path(f"images/{today}/{safe_name}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check how many images already exist
    existing = list(output_dir.glob("*.png"))
    existing_count = len(existing)
    remaining = TARGET_IMAGES - existing_count
    print(f"  Existing images: {existing_count}, need {remaining} more to reach {TARGET_IMAGES}")

    if remaining <= 0:
        print("  Already at target, nothing to generate.")
        return safe_name, []

    # Generate item prompts for remaining images
    print(f"Generating {remaining} item prompts...")
    items = build_item_prompts(theme, remaining)
    print(f"Items: {items}")

    # Generate images
    print(f"Generating {remaining} images...")
    success_count = 0
    for i, item in enumerate(items):
        output_path = output_dir / f"{existing_count + i + 1:02d}.png"
        prompt = f"A single cute illustration of {item}{STYLE_SUFFIX}"
        success = generate_image(prompt, output_path)
        status = "OK" if success else "FAILED"
        print(f"  [{existing_count + i + 1}/{TARGET_IMAGES}] {status}: {item}")
        if success:
            success_count += 1
        time.sleep(1)

    # Save log
    log = {
        "date": today,
        "theme": theme,
        "items": items,
        "images_generated": success_count,
        "output_dir": str(output_dir)
    }
    with open(output_dir / "log.json", "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

    print(f"\nDone. {success_count}/{ITEMS_PER_THEME} images saved to {output_dir}")


if __name__ == "__main__":
    main()
