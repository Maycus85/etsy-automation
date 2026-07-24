import json
import math
import os
import random
import numpy as np
import anthropic
from datetime import date
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PREVIEW_SIZE = 3000
BG_COLOR = (255, 255, 255)
ACCENT_COLOR = (196, 158, 120)
FONT_COLOR = (55, 45, 40)
SUBTITLE_COLOR = (120, 100, 88)
TITLE_AREA = 320
PADDING = 80

random.seed(42)


def generate_short_title(theme: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=50,
        messages=[{
            "role": "user",
            "content": f"""Create a short product title for an Etsy clipart listing based on this theme: "{theme}"

Rules:
- Maximum 4 words
- Do NOT use these words: Watercolor, Clipart, Bundle
- Focus on the subject, examples: "Elegant Wedding Flowers", "Kawaii Forest Animals", "Cozy Kitchen Utensils"
- No punctuation, no quotes

Respond ONLY with the title, nothing else."""
        }]
    )
    return message.content[0].text.strip().strip('"').strip("'")


def get_fonts():
    bold_paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    regular_paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    bold_font = next((p for p in bold_paths if Path(p).exists()), None)
    regular_font = next((p for p in regular_paths if Path(p).exists()), None)
    if bold_font and regular_font:
        return (
            ImageFont.truetype(bold_font, 130),
            ImageFont.truetype(regular_font, 75),
        )
    f = ImageFont.load_default()
    return f, f


def crop_white_border(img, threshold=240):
    """Remove white border around image using numpy."""
    img_rgb = img.convert("RGB")
    arr = np.array(img_rgb)
    mask = np.any(arr < threshold, axis=2)
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    if not rows.any():
        return img
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    pad = 10
    rmin = max(0, rmin - pad)
    rmax = min(arr.shape[0], rmax + pad)
    cmin = max(0, cmin - pad)
    cmax = min(arr.shape[1], cmax + pad)
    return img.crop((cmin, rmin, cmax, rmax))


def paste_image_artistic(canvas, img_path, center_x, center_y, size, rotation):
    """Paste image with white background, crop white border, rotation."""
    img = Image.open(img_path).convert("RGBA")

    # Always composite onto white background
    bg = Image.new("RGB", img.size, (255, 255, 255))
    bg.paste(img, mask=img.split()[3])
    img_rgb = bg

    # Crop white border
    img_rgb = crop_white_border(img_rgb)

    # Resize
    img_rgb.thumbnail((size, size), Image.LANCZOS)

    # Rotate
    rotated = img_rgb.rotate(rotation, expand=True, fillcolor=(255, 255, 255))

    # Paste centered
    px = center_x - rotated.width // 2
    py = center_y - rotated.height // 2
    canvas.paste(rotated, (px, py))


def apply_watermark(canvas):
    """Apply watermark.png overlay onto the canvas if it exists."""
    watermark_path = Path("watermark.png")
    if not watermark_path.exists():
        print("  No watermark.png found, skipping watermark.")
        return canvas

    watermark = Image.open(watermark_path).convert("RGBA")
    watermark = watermark.resize((PREVIEW_SIZE, PREVIEW_SIZE), Image.LANCZOS)

    # Composite watermark over canvas
    canvas_rgba = canvas.convert("RGBA")
    combined = Image.alpha_composite(canvas_rgba, watermark)
    return combined.convert("RGB")


def create_preview(image_dir, output_path, short_title):
    images = sorted([f for f in image_dir.glob("*.png") if f.name != "preview.png"])
    n = len(images)
    if n == 0:
        return False

    print(f"  Creating preview with {n} images, title: {short_title}")

    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)

    grid_y_start = TITLE_AREA
    grid_h = PREVIEW_SIZE - TITLE_AREA - PADDING
    grid_w = PREVIEW_SIZE - PADDING * 2
    cell_w = grid_w // cols
    cell_h = grid_h // rows
    base_size = int(min(cell_w, cell_h) * 0.90)

    canvas = Image.new("RGB", (PREVIEW_SIZE, PREVIEW_SIZE), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    # Accent bars
    draw.rectangle([(0, 0), (PREVIEW_SIZE, 10)], fill=ACCENT_COLOR)
    draw.rectangle([(0, PREVIEW_SIZE - 10), (PREVIEW_SIZE, PREVIEW_SIZE)], fill=ACCENT_COLOR)

    # Place images with artistic randomness
    for i, img_path in enumerate(images):
        row = i // cols
        col = i % cols

        cell_cx = PADDING + col * cell_w + cell_w // 2
        cell_cy = grid_y_start + row * cell_h + cell_h // 2

        offset_x = random.randint(-int(cell_w * 0.12), int(cell_w * 0.12))
        offset_y = random.randint(-int(cell_h * 0.12), int(cell_h * 0.12))

        size_factor = random.uniform(0.85, 1.10)
        size = int(base_size * size_factor)

        rotation = random.uniform(-7, 7)

        paste_image_artistic(
            canvas, img_path,
            cell_cx + offset_x,
            cell_cy + offset_y,
            size, rotation
        )

    # Fonts
    font_title, font_subtitle = get_fonts()

    # Title
    draw.text(
        (PREVIEW_SIZE // 2, 110),
        short_title.upper(),
        font=font_title,
        fill=FONT_COLOR,
        anchor="mm"
    )

    # Subtitle
    draw.text(
        (PREVIEW_SIZE // 2, 230),
        "WATERCOLOR CLIPART BUNDLE",
        font=font_subtitle,
        fill=SUBTITLE_COLOR,
        anchor="mm"
    )

    # Separator
    draw.line(
        [(PADDING * 2, 278), (PREVIEW_SIZE - PADDING * 2, 278)],
        fill=ACCENT_COLOR, width=3
    )

    # Apply watermark overlay
    canvas = apply_watermark(canvas)

    canvas.save(str(output_path), "PNG", optimize=True)
    print(f"  Preview saved: {output_path}")
    return True


def main():
    today = str(date.today())

    with open("themes_today.json", "r") as f:
        listing = json.load(f)

    theme = listing["theme"]
    safe_name = theme.replace(" ", "_").replace("/", "_")[:50]
    image_dir = Path(f"images/{today}/{safe_name}")

    if not image_dir.exists():
        print(f"Image directory not found: {image_dir}")
        return

    print("  Generating short title...")
    short_title = generate_short_title(theme)
    print(f"  Short title: {short_title}")

    preview_path = image_dir / "preview.png"
    success = create_preview(image_dir, preview_path, short_title)

    if success:
        listing["preview_path"] = str(preview_path)
        listing["short_title"] = short_title
        with open("listing_today.json", "w") as f:
            json.dump(listing, f, indent=2, ensure_ascii=False)
        print(f"\nDone. Preview created: {preview_path}")
    else:
        print("\nFailed to create preview.")


if __name__ == "__main__":
    main()
