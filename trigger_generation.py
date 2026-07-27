"""
Manual trigger script for image generation.
Called by the Manual Theme Generation GitHub Action.
"""
import argparse
import json
import os
import re
import time
import requests
import anthropic
from datetime import date
from pathlib import Path

FAL_API_KEY = os.environ["FAL_API_KEY"]
FAL_URL = "https://fal.run/fal-ai/nano-banana-2"

HEADERS = {
    "Authorization": f"Key {FAL_API_KEY}",
    "Content-Type": "application/json"
}

TARGET_IMAGES = 20

KAWAII_STYLE = ", kawaii chibi style, cute friendly face, soft pastel watercolor, gentle brushstrokes, isolated on pure white background, transparent background, no shadows, no text, no frame, professional clipart, commercial use"
CLEAN_STYLE = ", watercolor illustration style, natural animal features allowed, no kawaii style, no chibi faces, no cartoon expressions, soft pastel colors, delicate brushstrokes, botanical art style, isolated on pure white background, transparent background, no shadows, no text, no frame, professional clipart, commercial use"
SILHOUETTE_STYLE = ", pure black silhouette, flat solid black shape, no details, no gradients, no colors, crisp clean edges, isolated on pure white background, transparent background, no shadows, no text, no frame, professional clipart, commercial use"


def build_item_prompts(theme: str, n: int, style: str) -> list:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    if style == "kawaii":
        style_hint = "kawaii cute characters with friendly expressions"
    elif style == "silhouette":
        style_hint = "dark gothic silhouette shapes, no color"
    else:
        style_hint = "clean watercolor objects or realistic animals"

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": f"""Generate exactly {n} distinct clipart item descriptions for the theme: "{theme}"
Style: {style_hint}
Rules:
- Each item is one specific object or character
- Keep each description under 8 words
- No duplicates
Respond ONLY with a JSON array of {n} strings."""}]
    )
    text = message.content[0].text.strip()
    text = re.sub(r"```json\s*|```\s*", "", text).strip()
    return json.loads(text)


def generate_image(prompt: str, output_path: Path) -> bool:
    try:
        response = requests.post(FAL_URL, headers=HEADERS, json={
            "prompt": prompt, "aspect_ratio": "1:1", "resolution": "2K",
            "num_images": 1, "output_format": "png"
        }, timeout=120)
        response.raise_for_status()
        image_url = response.json()["images"][0]["url"]
        img_response = requests.get(image_url, timeout=60)
        img_response.raise_for_status()
        output_path.write_bytes(img_response.content)
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", required=True)
    parser.add_argument("--style", default="clean", choices=["clean", "kawaii", "silhouette"])
    parser.add_argument("--count", type=int, default=20)
    args = parser.parse_args()

    theme = args.theme
    style = args.style
    count = args.count
    today = str(date.today())

    if style == "kawaii":
        style_suffix = KAWAII_STYLE
    elif style == "silhouette":
        style_suffix = SILHOUETTE_STYLE
    else:
        style_suffix = CLEAN_STYLE

    safe_name = theme.replace(" ", "_").replace("/", "_")[:50]
    output_dir = Path(f"images/{today}/{safe_name}")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating {count} images for theme: {theme} ({style} style)")

    items = build_item_prompts(theme, count, style)
    print(f"Items: {items[:3]}...")

    success_count = 0
    for i, item in enumerate(items):
        output_path = output_dir / f"{i+1:02d}.png"
        prompt = f"A single illustration of {item}{style_suffix}"

        success = False
        for attempt in range(3):
            success = generate_image(prompt, output_path)
            if success:
                break
            print(f"  Retry {attempt+1}/3...")
            time.sleep(3)

        status = "OK" if success else "FAILED"
        print(f"  [{i+1}/{count}] {status}: {item}")
        if success:
            success_count += 1
        time.sleep(1)

    # Save log and themes_today.json for downstream scripts
    log = {"date": today, "theme": theme, "style": style, "items": items,
           "images_generated": success_count, "output_dir": str(output_dir)}
    with open(output_dir / "log.json", "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

    today_output = {"date": today, "theme": theme, "theme_type": style, "season": "summer"}
    with open("themes_today.json", "w") as f:
        json.dump(today_output, f, indent=2, ensure_ascii=False)

    # Reset listing_today.json
    if Path("listing_today.json").exists():
        Path("listing_today.json").unlink()

    print(f"\nDone. {success_count}/{count} images saved to {output_dir}")


if __name__ == "__main__":
    main()
