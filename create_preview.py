import json
import math
import os
import urllib.request
from datetime import date
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PREVIEW_SIZE = 3000
BACKGROUND_COLOR = (255, 253, 248)  # Warm off-white
PADDING = 50
TITLE_HEIGHT = 200
FONT_COLOR = (55, 45, 40)
SUBTITLE_COLOR = (120, 100, 88)
FOOTER_COLOR = (170, 150, 138)
ACCENT_COLOR = (196, 158, 120)  # Warm gold


def download_font(url: str, path: Path) -> bool:
    try:
        urllib.request.urlretrieve(url, str(path))
        return True
    except Exception as e:
        print(f"  Font download failed: {e}")
        return False


def get_fonts():
    font_dir = Path("/tmp/fonts")
    font_dir.mkdir(exist_ok=True)

    bold_path = font_dir / "Playfair-Bold.ttf"
    regular_path = font_dir / "Lato-Regular.ttf"

    if not bold_path.exists():
        download_font(
            "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay-Bold.ttf",
            bold_path
        )

    if not regular_path.exists():
        download_font(
            "https://github.com/google/fonts/raw/main/ofl/lato/Lato-Regular.ttf",
            regular_path
        )

    try:
        font_title = ImageFont.truetype(str(bold_path), 110)
        font_subtitle = ImageFont.truetype(str(regular_path), 58)
        font_footer = ImageFont.truetype(str(regular_path), 44)
        font_badge = ImageFont.truetype(str(bold_path), 52)
        print("  Using Google Fonts (Playfair Display + Lato)")
    except Exception as e:
        print(f"  Falling back to default font: {e}")
        font_title = ImageFont.load_default()
        font_subtitle = font_title
        font_footer = font_title
        font_badge = font_title

    return font_title, font_subtitle, font_footer, font_badge


def create_preview(image_dir: Path, output_path: Path, theme: str, image_count: int, theme_type: str):
    images = sorted([f for f in image_dir.glob("*.png") if f.name != "preview.png"])
    n = len(images)

    if n == 0:
        print("  No images found.")
        return False

    print(f"  Creating preview with {n} images...")

    # Grid layout
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)

    grid_width = PREVIEW_SIZE - (PADDING * 2)
    grid_height = PREVIEW_SIZE - TITLE_HEIGHT - (PADDING * 2) - 80

    cell_w = grid_width // cols
    cell_h = grid_height // rows

    # Background
    canvas = Image.new("RGB", (PREVIEW_SIZE, PREVIEW_SIZE), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(canvas)

    # Subtle top accent line
    draw.rectangle([(0, 0), (PREVIEW_SIZE, 8)], fill=ACCENT_COLOR)

    # Place images
    for i, img_path in enumerate(images):
        row = i // cols
        col = i % cols

        x = PADDING + col * cell_w
        y = TITLE_HEIGHT + PADDING + row * cell_h

        img = Image.open(img_path).convert("RGBA")

        cell_padding = 15
        max_w = cell_w - cell_padding * 2
        max_h = cell_h - cell_padding * 2

        img.thumbnail((max_w, max_h), Image.LANCZOS)

        offset_x = (cell_w - img.width) // 2
        offset_y = (cell_h - img.height) // 2

        canvas.paste(img, (x + offset_x, y + offset_y), img)

    # Fonts
    font_title, font_subtitle, font_footer, font_badge = get_fonts()

    # PNG count badge (top left)
    badge_text = f"{image_count} PNG"
    draw.rounded_rectangle([(PADDING, 25), (PADDING + 200, 100)], radius=20, fill=ACCENT_COLOR)
    draw.text((PADDING + 100, 62), badge_text, font=font_badge, fill=(255, 255, 255), anchor="mm")

    # Transparent badge (top right)
    draw.rounded_rectangle([(PREVIEW_SIZE - PADDING - 280, 25), (PREVIEW_SIZE - PADDING, 100)], radius=20, fill=(200, 185, 170))
    draw.text((PREVIEW_SIZE - PADDING - 140, 62), "Transparent", font=font_badge, fill=(255, 255, 255), anchor="mm")

    # Title
    title_clean = theme.replace("watercolor", "").replace("kawaii", "").strip().title()
    draw.text((PREVIEW_SIZE // 2, 115), title_clean[:45], font=font_title, fill=FONT_COLOR, anchor="mm")

    # Subtitle line
    draw.text((PREVIEW_SIZE // 2, 175), "Watercolor Clipart Bundle", font=font_subtitle, fill=SUBTITLE_COLOR, anchor="mm")

    # Thin separator line
    draw.line([(PADDING * 3, 195), (PREVIEW_SIZE - PADDING * 3, 195)], fill=ACCENT_COLOR, width=2)

    # Footer
    draw.text(
        (PREVIEW_SIZE // 2, PREVIEW_SIZE - 35),
        "Commercial Use  •  Instant Download  •  Transparent PNG",
        font=font_footer,
        fill=FOOTER_COLOR,
        anchor="mm"
    )

    # Bottom accent line
    draw.rectangle([(0, PREVIEW_SIZE - 8), (PREVIEW_SIZE, PREVIEW_SIZE)], fill=ACCENT_COLOR)

    canvas.save(str(output_path), "PNG", optimize=True)
    print(f"  Preview saved: {output_path}")
    return True


def main():
    today = str(date.today())

    with open("listing_today.json", "r") as f:
        listing = json.load(f)

    theme = listing["theme"]
    safe_name = listing["safe_name"]
    image_count = listing["image_count"]
    theme_type = listing.get("theme_type", "clean")
    image_dir = Path(f"images/{today}/{safe_name}")

    if not image_dir.exists():
        print(f"Image directory not found: {image_dir}")
        return

    preview_path = image_dir / "preview.png"
    success = create_preview(image_dir, preview_path, theme, image_count, theme_type)

    if success:
        listing["preview_path"] = str(preview_path)
        with open("listing_today.json", "w") as f:
            json.dump(listing, f, indent=2, ensure_ascii=False)
        print(f"\nDone. Preview created: {preview_path}")
    else:
        print("\nFailed to create preview.")


if __name__ == "__main__":
    main()
