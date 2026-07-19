import json
import os
import math
from datetime import date
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PREVIEW_SIZE = 3000  # 3000x3000 pixels for the preview image
BACKGROUND_COLOR = (255, 253, 248)  # Warm off-white
PADDING = 40
TITLE_HEIGHT = 180
FONT_COLOR = (60, 50, 45)  # Warm dark brown


def create_preview(image_dir: Path, output_path: Path, theme: str, image_count: int):
    """Create a collage preview image with all PNGs and title text."""

    # Get all PNGs
    images = sorted([f for f in image_dir.glob("*.png")])
    n = len(images)

    if n == 0:
        print("  No images found.")
        return False

    print(f"  Creating preview with {n} images...")

    # Calculate grid layout
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)

    # Available space for grid
    grid_width = PREVIEW_SIZE - (PADDING * 2)
    grid_height = PREVIEW_SIZE - TITLE_HEIGHT - (PADDING * 2)

    cell_w = grid_width // cols
    cell_h = grid_height // rows

    # Create canvas
    canvas = Image.new("RGB", (PREVIEW_SIZE, PREVIEW_SIZE), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(canvas)

    # Place images in grid
    for i, img_path in enumerate(images):
        row = i // cols
        col = i % cols

        x = PADDING + col * cell_w
        y = TITLE_HEIGHT + PADDING + row * cell_h

        # Open and resize image
        img = Image.open(img_path).convert("RGBA")

        # Fit image in cell with padding
        cell_padding = 10
        max_w = cell_w - cell_padding * 2
        max_h = cell_h - cell_padding * 2

        img.thumbnail((max_w, max_h), Image.LANCZOS)

        # Center in cell
        offset_x = (cell_w - img.width) // 2
        offset_y = (cell_h - img.height) // 2

        # Paste with transparency
        canvas.paste(img, (x + offset_x, y + offset_y), img)

    # Add title text
    title_text = f"{image_count} PNG Clipart"
    subtitle_text = theme.title()

    # Try to load a font, fall back to default
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 90)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 55)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw title
    draw.text((PREVIEW_SIZE // 2, 55), title_text, font=font_large, fill=FONT_COLOR, anchor="mt")
    draw.text((PREVIEW_SIZE // 2, 135), subtitle_text[:60], font=font_small, fill=(120, 100, 90), anchor="mt")

    # Add subtle bottom text
    draw.text((PREVIEW_SIZE // 2, PREVIEW_SIZE - 30), "Transparent PNG • Commercial Use • Instant Download",
              font=font_small, fill=(160, 140, 130), anchor="mb")

    # Save as PNG
    canvas.save(str(output_path), "PNG", optimize=True)
    print(f"  Preview saved: {output_path}")
    return True


def main():
    today = str(date.today())

    # Load today's listing info
    with open("listing_today.json", "r") as f:
        listing = json.load(f)

    theme = listing["theme"]
    safe_name = listing["safe_name"]
    image_count = listing["image_count"]
    image_dir = Path(f"images/{today}/{safe_name}")

    if not image_dir.exists():
        print(f"Image directory not found: {image_dir}")
        return

    # Create preview
    preview_path = image_dir / "preview.png"
    success = create_preview(image_dir, preview_path, theme, image_count)

    if success:
        # Update listing_today.json with preview path
        listing["preview_path"] = str(preview_path)
        with open("listing_today.json", "w") as f:
            json.dump(listing, f, indent=2, ensure_ascii=False)
        print(f"\nDone. Preview created: {preview_path}")
    else:
        print("\nFailed to create preview.")


if __name__ == "__main__":
    main()
