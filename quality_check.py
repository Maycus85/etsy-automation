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

MIN_FILE_SIZE_KB = 50
MAX_RETRIES = 2
WHITE_BORDER_THRESHOLD = 0.30  # If more than 30% of border pixels are white, background is white


def has_white_background(img_path: Path) -> bool:
    """Check if image has a white background by sampling border pixels."""
    try:
        img = Image.open(img_path).convert("RGBA")
        arr = np.array(img)
        h, w = arr.shape[:2]

        # Sample border pixels (top, bottom, left, right rows)
        border_pixels = np.concatenate([
            arr[0, :, :],      # top row
            arr[-1, :, :],     # bottom row
            arr[:, 0, :],      # left column
            arr[:, -1, :],     # right column
        ])

        r, g, b, a = border_pixels[:,0], border_pixels[:,1], border_pixels[:,2], border_pixels[:,3]

        # White pixels: high RGB and not transparent
        white = np.sum((r > 230) & (g > 230) & (b > 230) & (a > 200))
        total_border = len(border_pixels)
        white_ratio = white / total_border

        return white_ratio > WHITE_BORDER_THRESHOLD, white_ratio

    except Exception as e:
        return False, 0.0


def remove_background_fal(img_path: Path) -> bool:
    """Remove background using fal.ai imageutils/rembg API - free service."""
    try:
        import base64

        # Upload image to fal.ai storage first
        with open(img_path, "rb") as f:
            img_data = f.read()

        # Upload to fal storage
        upload_response = requests.post(
            "https://fal.run/fal-ai/imageutils/rembg",
            headers=HEADERS,
            json={
                "image_url": f"data:image/png;base64,{base64.b64encode(img_data).decode()}"
            },
            timeout=120
        )

        if upload_response.status_code not in [200, 201]:
            print(f"    fal rembg failed: {upload_response.text}")
            return False

        result = upload_response.json()
        image_url = result["image"]["url"]

        # Download result
        img_response = requests.get(image_url, timeout=60)
        img_response.raise_for_status()
        img_path.write_bytes(img_response.content)
        print(f"    Background removed with fal.ai rembg")
        return True

    except Exception as e:
        print(f"    fal rembg error: {e}")
        return False


def is_image_valid(img_path: Path) -> tuple:
    """Check if image is valid, has content, and has transparent background."""

    # Check file size
    size_kb = img_path.stat().st_size / 1024
    if size_kb < MIN_FILE_SIZE_KB:
        return False, f"File too small ({size_kb:.0f}KB)"

    try:
        img = Image.open(img_path).convert("RGBA")
        arr = np.array(img)

        r, g, b, a = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]
        total = arr.shape[0] * arr.shape[1]

        transparent = np.sum(a < 10)
        white = np.sum((r > 240) & (g > 240) & (b > 240) & (a > 200))
        content = total - transparent - white
        content_ratio = content / total

        if content_ratio < 0.03:
            return False, f"Not enough content ({content_ratio:.1%})"

        # Check for white background
        has_white_bg, white_ratio = has_white_background(img_path)
        if has_white_bg:
            return False, f"White background detected ({white_ratio:.0%} white border pixels)"

        return True, f"OK ({size_kb:.0f}KB, {content_ratio:.1%} content)"

    except Exception as e:
        return False, f"Error: {e}"


def regenerate_image(prompt: str, output_path: Path) -> bool:
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

    if theme_type == "kawaii":
        style_suffix = ", kawaii chibi style, cute friendly face, soft pastel watercolor, gentle brushstrokes, pure transparent background, no white background, no shadows, no text, no frame, professional clipart, commercial use"
    else:
        style_suffix = ", watercolor illustration style, no faces, soft pastel colors, delicate brushstrokes, pure transparent background, no white background, no shadows, no text, no frame, professional clipart, commercial use"

    images = sorted([f for f in image_dir.glob("*.png") if f.name != "preview.png"])
    print(f"Quality checking {len(images)} images...")

    # Load item prompts from log
    log_path = image_dir / "log.json"
    items = []
    if log_path.exists():
        with open(log_path) as f:
            log = json.load(f)
        items = log.get("items", [])

    failed_bg = []
    failed_content = []

    for i, img_path in enumerate(images):
        valid, reason = is_image_valid(img_path)
        status = "✓" if valid else "✗"
        print(f"  [{i+1}/{len(images)}] {status} {img_path.name}: {reason}")

        if not valid:
            if "White background" in reason:
                failed_bg.append((i, img_path))
            else:
                failed_content.append((i, img_path))

    # Fix white backgrounds with rembg first
    if failed_bg:
        print(f"\nFixing {len(failed_bg)} images with white background using rembg...")
        for idx, img_path in failed_bg:
            success = remove_background_fal(img_path)
            if success:
                valid, reason = is_image_valid(img_path)
                if not valid:
                    print(f"    Still invalid after rembg: {reason}, will regenerate")
                    failed_content.append((idx, img_path))

    # Regenerate content failures
    if failed_content:
        print(f"\nRegenerating {len(failed_content)} images...")
        for idx, img_path in failed_content:
            item = items[idx] if idx < len(items) else theme
            prompt = f"A single illustration of {item}{style_suffix}"

            for attempt in range(MAX_RETRIES):
                print(f"  Regenerating {img_path.name} (attempt {attempt+1})...")
                success = regenerate_image(prompt, img_path)
                if success:
                    # Try rembg on regenerated image too
                    remove_background_fal(img_path)
                    valid, reason = is_image_valid(img_path)
                    if valid:
                        print(f"    Fixed: {reason}")
                        break
                    else:
                        print(f"    Still invalid: {reason}")
                time.sleep(2)

    total_issues = len(failed_bg) + len(failed_content)
    if total_issues == 0:
        print(f"\nAll {len(images)} images passed quality check!")
    else:
        print(f"\nQuality check complete. Processed {total_issues} issues.")


if __name__ == "__main__":
    main()
