"""
Custom Generation Script
Generates images for a specific theme, style and color palette.
Called by the Custom Theme Generation GitHub Action.
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

# Color palette descriptions for prompts
COLOR_PALETTES = {
    "neutral": "",
    "pastel": ", soft pastel color palette, muted gentle tones",
    "baby-pink": ", baby pink color palette, blush rose dusty pink tones",
    "baby-blue": ", baby blue color palette, soft sky blue powder blue tones",
    "fire-red": ", bold fire red color palette, bright red orange tones",
    "eucalyptus": ", eucalyptus green color palette, sage mint olive green tones",
    "butterlemon": ", butter lemon color palette, soft yellow ivory cream tones",
    "moody-autumn": ", moody autumn color palette, deep orange rust brown tones",
    "gold-cream": ", gold cream color palette, warm gold champagne ivory tones",
    "citrus": ", citrus color palette, bright orange yellow lime green tones",
    "navy": ", navy blue color palette, dark navy white contrast tones",
    "dark-gothic": ", dark gothic color palette, deep black purple midnight tones",
    "coffee-faded": ", faded coffee color palette, washed out beige taupe brown tones",
    "teal-orange": ", teal and orange color palette, vibrant teal warm orange contrast",
}

# Style suffixes
STYLE_SUFFIXES = {
    "aquarell": ", watercolor illustration style, natural animal features allowed, no kawaii style, no chibi faces, soft pastel colors, delicate brushstrokes, botanical art style, isolated on pure white background, transparent background, no shadows, no text, no frame, professional clipart, commercial use",
    "comic-kindlich": ", children's book illustration style, cute and friendly, bold clean outlines, flat colors, simple shapes, cartoon style, cheerful and colorful, isolated on pure white background, transparent background, no shadows, no text, no frame, professional clipart, commercial use",
    "kawaii": ", kawaii chibi style, cute friendly face, soft pastel watercolor, gentle brushstrokes, isolated on pure white background, transparent background, no shadows, no text, no frame, professional clipart, commercial use",
    "silhouette": ", pure black silhouette, flat solid black shape, no details, no gradients, no colors, crisp clean edges, isolated on pure white background, transparent background, no shadows, no text, no frame, professional clipart, commercial use",
}


def build_item_prompts(theme: str, n: int, style: str) -> list:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    style_hints = {
        "aquarell": "realistic watercolor objects or animals with natural features",
        "comic-kindlich": "cute children's book style characters or objects, friendly and simple",
        "kawaii": "kawaii cute characters with friendly expressions and big eyes",
        "silhouette": "dark silhouette shapes, no color or detail",
    }

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": f"""Generate exactly {n} distinct clipart item descriptions for the theme: "{theme}"

Style: {style_hints.get(style, "watercolor illustration")}

Rules:
- Each item is one specific object or character
- Keep each description under 8 words
- No duplicates
- All items must relate directly to the theme

Respond ONLY with a JSON array of {n} strings."""}]
    )
    text = message.content[0].text.strip()
    text = re.sub(r"```json\s*|```\s*", "", text).strip()
    return json.loads(text)


def generate_image(prompt: str, output_path: Path) -> bool:
    try:
        response = requests.post(FAL_URL, headers=HEADERS, json={
            "prompt": prompt,
            "aspect_ratio": "1:1",
            "resolution": "2K",
            "num_images": 1,
            "output_format": "png",
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
    parser.add_argument("--style", default="aquarell",
                        choices=["aquarell", "comic-kindlich", "kawaii", "silhouette"])
    parser.add_argument("--color", default="neutral")
    parser.add_argument("--count", type=int, default=20)
    args = parser.parse_args()

    theme = args.theme
    style = args.style
    color = args.color
    count = args.count
    today = str(date.today())

    # Build style suffix with color palette
    style_suffix = STYLE_SUFFIXES.get(style, STYLE_SUFFIXES["aquarell"])
    color_suffix = COLOR_PALETTES.get(color, "")
    full_suffix = style_suffix.replace(", isolated on", f"{color_suffix}, isolated on")

    safe_name = theme.replace(" ", "_").replace("/", "_")[:50]
    output_dir = Path(f"images/{today}/{safe_name}")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating {count} images")
    print(f"  Theme: {theme}")
    print(f"  Style: {style}")
    print(f"  Color: {color}")

    items = build_item_prompts(theme, count, style)
    print(f"  Items: {items[:3]}...")

    success_count = 0
    for i, item in enumerate(items):
        output_path = output_dir / f"{i+1:02d}.png"
        prompt = f"A single illustration of {item}{full_suffix}"

        success = False
        for attempt in range(3):
            success = generate_image(prompt, output_path)
            if success:
                break
            print(f"    Retry {attempt+1}/3...")
            time.sleep(3)

        status = "OK" if success else "FAILED"
        print(f"  [{i+1}/{count}] {status}: {item}")
        if success:
            success_count += 1
        time.sleep(1)

    # Save log and themes_today.json for downstream scripts
    log = {
        "date": today,
        "theme": theme,
        "style": style,
        "color_palette": color,
        "items": items,
        "images_generated": success_count,
        "output_dir": str(output_dir)
    }
    with open(output_dir / "log.json", "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

    today_output = {
        "date": today,
        "theme": theme,
        "theme_type": "kawaii" if style == "kawaii" else ("silhouette" if style == "silhouette" else "clean"),
        "season": "summer"
    }
    with open("themes_today.json", "w") as f:
        json.dump(today_output, f, indent=2, ensure_ascii=False)

    if Path("listing_today.json").exists():
        Path("listing_today.json").unlink()

    print(f"\nDone. {success_count}/{count} images saved to {output_dir}")


if __name__ == "__main__":
    main()
