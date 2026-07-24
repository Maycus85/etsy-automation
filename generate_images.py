import json
import os
import re
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

TARGET_IMAGES = 1

KAWAII_STYLE = ", kawaii chibi style, cute friendly face, soft pastel watercolor, gentle brushstrokes, isolated on pure white background, transparent background, no shadows, no text, no frame, professional clipart, commercial use"
CLEAN_STYLE = ", watercolor illustration style, no faces, no eyes, no expressions, soft pastel colors, delicate brushstrokes, botanical art style, isolated on pure white background, transparent background, no shadows, no text, no frame, professional clipart, commercial use"
SILHOUETTE_STYLE = ", pure black silhouette, flat solid black shape, no details, no gradients, no colors, crisp clean edges, isolated on pure white background, transparent background, no shadows, no text, no frame, professional clipart, commercial use"


def build_item_prompts(theme: str, n: int, style: str) -> list:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    if style == "kawaii":
        style_hint = "kawaii cute characters with friendly expressions"
    elif style == "silhouette":
        style_hint = "dark gothic silhouette shapes, no color"
    else:
        style_hint = "clean watercolor objects without faces or expressions"

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""Generate exactly {n} distinct clipart item descriptions for the theme: "{theme}"

Style: {style_hint}

Rules:
- Each item is one specific object or character
- Keep each description under 8 words
- No duplicates
- Suitable for watercolor clipart illustration

Respond ONLY with a JSON array of {n} strings.
Example: ["cute birthday cake with candles", "pastel balloon bouquet"]"""
        }]
    )

    text = message.content[0].text.strip()
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

    with open("themes_today.json", "r") as f:
        data = json.load(f)

    theme = data["theme"]
    theme_type = data.get("theme_type", "clean")
    print(f"Generating images for theme: {theme}")

    # Check always_clean_themes override
    with open("themes.json", "r") as f:
        themes_data = json.load(f)
    always_clean = themes_data.get("always_clean_themes", [])
    theme_lower = theme.lower()
    is_always_clean = any(keyword in theme_lower for keyword in always_clean)

    if theme_type == "silhouette":
        style_name, style_suffix = "silhouette", SILHOUETTE_STYLE
        print(f"  Style: Silhouette (from theme_type)")
    elif is_always_clean:
        style_name, style_suffix = "clean", CLEAN_STYLE
        print(f"  Style: Clean Watercolor (forced by always_clean_themes)")
    elif theme_type == "kawaii":
        style_name, style_suffix = "kawaii", KAWAII_STYLE
        print(f"  Style: Kawaii (from theme_type)")
    else:
        style_name, style_suffix = "clean", CLEAN_STYLE
        print(f"  Style: Clean Watercolor (from theme_type)")

    # Create output folder
    safe_name = theme.replace(" ", "_").replace("/", "_")[:50]
    output_dir = Path(f"images/{today}/{safe_name}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check existing images
    existing = list(output_dir.glob("*.png"))
    existing_count = len(existing)
    remaining = TARGET_IMAGES - existing_count
    print(f"  Existing: {existing_count}, need {remaining} more to reach {TARGET_IMAGES}")

    if remaining <= 0:
        print("  Already at target, nothing to generate.")
        return

    # Generate item prompts
    print(f"Generating {remaining} item prompts...")
    items = build_item_prompts(theme, remaining, style_name)
    print(f"Items: {items}")

    # Generate images with retry logic
    print(f"Generating {remaining} images ({style_name} style)...")
    success_count = 0
    for i, item in enumerate(items):
        output_path = output_dir / f"{existing_count + i + 1:02d}.png"
        prompt = f"A single illustration of {item}{style_suffix}"

        success = False
        for attempt in range(3):
            success = generate_image(prompt, output_path)
            if success:
                break
            print(f"    Retry {attempt+1}/3...")
            time.sleep(3)

        status = "OK" if success else "FAILED"
        print(f"  [{existing_count + i + 1}/{TARGET_IMAGES}] {status}: {item}")
        if success:
            success_count += 1
        time.sleep(1)

    # Save log
    log = {
        "date": today,
        "theme": theme,
        "style": style_name,
        "items": items,
        "images_generated": success_count,
        "output_dir": str(output_dir)
    }
    with open(output_dir / "log.json", "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

    print(f"\nDone. {success_count}/{TARGET_IMAGES} images saved to {output_dir}")


if __name__ == "__main__":
    main()
