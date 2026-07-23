import json
import os
import time
import requests
import numpy as np
from datetime import date
from pathlib import Path
from PIL import Image

FAL_API_KEY = os.environ["FAL_API_KEY"]
FAL_URL = "https://fal.run/fal-ai/nano-banana-2"

HEADERS = {
    "Authorization": f"Key {FAL_API_KEY}",
    "Content-Type": "application/json"
}

MIN_FILE_SIZE_KB = 50   # Minimum file size in KB
MAX_WHITE_RATIO = 0.97  # Max ratio of white pixels (if more = likely empty/broken)
MAX_RETRIES = 2


def is_image_valid(img_path: Path) -> tuple:
    """Check if image is valid and has actual content."""
    
    # Check file size
    size_kb = img_path.stat().st_size / 1024
    if size_kb < MIN_FILE_SIZE_KB:
        return False, f"File too small ({size_kb:.0f}KB < {MIN_FILE_SIZE_KB}KB)"

    # Check pixel content
    try:
        img = Image.open(img_path).convert("RGBA")
        arr = np.array(img)

        # Count near-white pixels (background)
        r, g, b, a = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]
        
        # Transparent pixels
        transparent = np.sum(a < 10)
        total = arr.shape[0] * arr.shape[1]
        
        # Near-white pixels (background)
        white = np.sum((r > 240) & (g > 240) & (b > 240))
        
        # Content pixels (not white and not transparent)
        content = total - transparent - white
        content_ratio = content / total

        if content_ratio < 0.03:
            return False, f"Not enough content ({content_ratio:.1%} content pixels)"

        return True, f"OK ({size_kb:.0f}KB, {content_ratio:.1%} content)"

    except Exception as e:
        return False, f"Error reading image: {e}"


def regenerate_image(prompt: str, output_path: Path, style_suffix: str) -> bool:
    """Regenerate a single image."""
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
        print(f"    Regeneration error: {e}")
        return False


def main():
    today = str(date.today())

    with open("themes_today.json", "r") as f:
        data = json.load(f)

    theme = data["theme"]
    theme_type = data.get("theme_type", "clean")
    safe_name = theme.replace(" ", "_").replace("/", "_")[:50]
    image_dir = Path(f"images/{today}/{safe_name}")

    if not image_dir.exists():
        print(f"Image directory not found: {image_dir}")
        return

    # Style suffix based on theme type
    if theme_type == "kawaii":
        style_suffix = ", kawaii chibi style, cute friendly face, soft pastel watercolor, gentle brushstrokes, isolated on pure white background, transparent background, no shadows, no text, no frame, professional clipart, commercial use"
    else:
        style_suffix = ", watercolor illustration style, no faces, no eyes, no expressions, soft pastel colors, delicate brushstrokes, isolated on pure white background, transparent background, no shadows, no text, no frame, professional clipart, commercial use"

    images = sorted([f for f in image_dir.glob("*.png") if f.name != "preview.png"])
    print(f"Quality checking {len(images)} images for theme: {theme}")

    failed = []
    for i, img_path in enumerate(images):
        valid, reason = is_image_valid(img_path)
        status = "✓" if valid else "✗"
        print(f"  [{i+1}/{len(images)}] {status} {img_path.name}: {reason}")
        if not valid:
            failed.append(img_path)

    if not failed:
        print(f"\nAll {len(images)} images passed quality check!")
        return

    print(f"\n{len(failed)} images failed. Regenerating...")

    # Load item prompts from log
    log_path = image_dir / "log.json"
    if log_path.exists():
        with open(log_path) as f:
            log = json.load(f)
        items = log.get("items", [])
    else:
        items = []

    for img_path in failed:
        idx = int(img_path.stem) - 1
        if idx < len(items):
            item = items[idx]
            prompt = f"A single illustration of {item}{style_suffix}"
        else:
            prompt = f"A single watercolor illustration{style_suffix}"

        success = False
        for attempt in range(MAX_RETRIES):
            print(f"  Regenerating {img_path.name} (attempt {attempt+1}/{MAX_RETRIES})...")
            success = regenerate_image(prompt, img_path, style_suffix)
            if success:
                valid, reason = is_image_valid(img_path)
                if valid:
                    print(f"    Regeneration successful: {reason}")
                    break
                else:
                    print(f"    Still invalid after regeneration: {reason}")
            time.sleep(2)

        if not success:
            print(f"    WARNING: Could not fix {img_path.name} after {MAX_RETRIES} attempts")

    print(f"\nQuality check complete.")


if __name__ == "__main__":
    main()
