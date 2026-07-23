import json
import os
import time
import requests
import base64
import numpy as np
from datetime import date
from pathlib import Path
from PIL import Image

FAL_API_KEY = os.environ["FAL_API_KEY"]
FAL_URL = "https://fal.run/fal-ai/nano-banana-2"
FAL_REMBG_URL = "https://fal.run/fal-ai/imageutils/rembg"

HEADERS = {
    "Authorization": f"Key {FAL_API_KEY}",
    "Content-Type": "application/json"
}

MIN_FILE_SIZE_KB = 30
MAX_RETRIES = 3
WHITE_BORDER_THRESHOLD = 0.30


def has_white_background(img_path: Path) -> tuple:
    """Check if image has a white background by sampling border pixels."""
    try:
        img = Image.open(img_path).convert("RGBA")
        arr = np.array(img)

        border_pixels = np.concatenate([
            arr[0, :, :],
            arr[-1, :, :],
            arr[:, 0, :],
            arr[:, -1, :],
        ])

        r, g, b, a = border_pixels[:,0], border_pixels[:,1], border_pixels[:,2], border_pixels[:,3]
        white = np.sum((r > 230) & (g > 230) & (b > 230) & (a > 200))
        total_border = len(border_pixels)
        white_ratio = white / total_border

        return white_ratio > WHITE_BORDER_THRESHOLD, white_ratio

    except Exception as e:
        return False, 0.0


def is_image_valid(img_path: Path) -> tuple:
    """Check if image is valid, has content, and has transparent background."""
    if not img_path.exists():
        return False, "File does not exist"

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

        has_white_bg, white_ratio = has_white_background(img_path)
        if has_white_bg:
            return False, f"White background ({white_ratio:.0%} white border)"

        return True, f"OK ({size_kb:.0f}KB, {content_ratio:.1%} content)"

    except Exception as e:
        return False, f"Error: {e}"


def remove_background_fal(img_path: Path) -> bool:
    """Remove background using fal.ai imageutils/rembg API."""
    try:
        with open(img_path, "rb") as f:
            img_data = f.read()

        response = requests.post(
            FAL_REMBG_URL,
            headers=HEADERS,
            json={
                "image_url": f"data:image/png;base64,{base64.b64encode(img_data).decode()}"
            },
            timeout=120
        )

        if response.status_code not in [200, 201]:
            print(f"    fal rembg failed: {response.text}")
            return False

        result = response.json()
        image_url = result["image"]["url"]
        img_response = requests.get(image_url, timeout=60)
        img_response.raise_for_status()
        img_path.write_bytes(img_response.content)
        return True

    except Exception as e:
        print(f"    fal rembg error: {e}")
        return False


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

    # Style suffix
    if theme_type == "kawaii":
        style_suffix = ", kawaii chibi style, cute friendly face, soft pastel watercolor, gentle brushstrokes, pure transparent background, no white background, no shadows, no text, no frame, professional clipart, commercial use"
    elif theme_type == "silhouette":
        style_suffix = ", pure black silhouette, flat solid black shape, no details, no gradients, transparent background, no white background, no text, no frame, professional clipart, commercial use"
    else:
        style_suffix = ", watercolor illustration style, no faces, soft pastel colors, delicate brushstrokes, pure transparent background, no white background, no shadows, no text, no frame, professional clipart, commercial use"

    # Load item prompts from log
    log_path = image_dir / "log.json"
    items = []
    if log_path.exists():
        with open(log_path) as f:
            log = json.load(f)
        items = log.get("items", [])

    # Get target count from generate_images script constant
    target = 20
    try:
        import generate_images
        target = generate_images.TARGET_IMAGES
    except:
        pass

    # Check all expected images exist and are valid
    print(f"Quality checking images (target: {target})...")
    
    issues = []
    for i in range(1, target + 1):
        img_path = image_dir / f"{i:02d}.png"
        valid, reason = is_image_valid(img_path)
        status = "✓" if valid else "✗"
        print(f"  [{i}/{target}] {status} {img_path.name}: {reason}")
        if not valid:
            issues.append((i, img_path, reason))

    if not issues:
        print(f"\nAll {target} images passed quality check!")
        return

    print(f"\nFixing {len(issues)} images...")

    for idx, img_path, reason in issues:
        fixed = False

        # Try rembg first for white background issues
        if "White background" in reason or not img_path.exists():
            if img_path.exists():
                print(f"  Removing background from {img_path.name}...")
                success = remove_background_fal(img_path)
                if success:
                    valid, new_reason = is_image_valid(img_path)
                    if valid:
                        print(f"    Fixed with rembg: {new_reason}")
                        fixed = True

        # Regenerate if still not fixed
        if not fixed:
            item_idx = idx - 1
            item = items[item_idx] if item_idx < len(items) else theme
            prompt = f"A single illustration of {item}{style_suffix}"

            for attempt in range(MAX_RETRIES):
                print(f"  Regenerating {img_path.name} (attempt {attempt+1}/{MAX_RETRIES})...")
                success = regenerate_image(prompt, img_path)
                if success:
                    # Try rembg on regenerated image
                    remove_background_fal(img_path)
                    valid, new_reason = is_image_valid(img_path)
                    if valid:
                        print(f"    Fixed after regeneration: {new_reason}")
                        fixed = True
                        break
                    else:
                        print(f"    Still invalid: {new_reason}")
                time.sleep(2)

        if not fixed:
            print(f"  WARNING: Could not fix {img_path.name}")

    print(f"\nQuality check complete.")


if __name__ == "__main__":
    main()
