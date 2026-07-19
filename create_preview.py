import json
import math
import urllib.request
from datetime import date
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PREVIEW_SIZE = 3000
BG_COLOR = (255, 253, 248)
ACCENT_COLOR = (196, 158, 120)
FONT_COLOR = (55, 45, 40)
SUBTITLE_COLOR = (120, 100, 88)
FOOTER_COLOR = (160, 140, 128)
TITLE_AREA = 480
FOOTER_AREA = 130
PADDING = 60


def get_fonts():
    # Try system fonts first
    font_paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    regular_paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]

    bold_font = None
    regular_font = None

    for path in font_paths:
        if Path(path).exists():
            bold_font = path
            break

    for path in regular_paths:
        if Path(path).exists():
            regular_font = path
            break

    if bold_font and regular_font:
        print(f"  Using system fonts: {bold_font}")
        return (
            ImageFont.truetype(bold_font, 280),
            ImageFont.truetype(regular_font, 160),
            ImageFont.truetype(regular_font, 110),
            ImageFont.truetype(bold_font, 130),
        )
    else:
        print("  WARNING: No system fonts found, using default (will be small)")
        f = ImageFont.load_default()
        return f, f, f, f


def remove_white_background(img, threshold=240):
    """Remove white and near-white background from image."""
    img = img.convert("RGBA")
    data = img.getdata()
    new_data = []
    for r, g, b, a in data:
        if r >= threshold and g >= threshold and b >= threshold:
            new_data.append((r, g, b, 0))  # Make transparent
        else:
            new_data.append((r, g, b, a))
    img.putdata(new_data)
    return img


def paste_image_on_bg(canvas, img_path, x, y, w, h, bg_color):
    """Remove white background and paste image onto canvas background color."""
    img = Image.open(img_path).convert("RGBA")

    # Remove white background
    img = remove_white_background(img)

    # Create backing with canvas background color
    backing = Image.new("RGBA", img.size, bg_color + (255,))
    backing.paste(img, mask=img.split()[3])
    img_rgb = backing.convert("RGB")

    # Resize to fit cell
    pad = 20
    img_rgb.thumbnail((w - pad * 2, h - pad * 2), Image.LANCZOS)

    # Center in cell
    ox = x + (w - img_rgb.width) // 2
    oy = y + (h - img_rgb.height) // 2
    canvas.paste(img_rgb, (ox, oy))


def create_preview(image_dir, output_path, theme, image_count):
    images = sorted([f for f in image_dir.glob("*.png") if f.name != "preview.png"])
    n = len(images)
    if n == 0:
        return False

    print(f"  Creating preview with {n} images...")

    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)

    grid_y_start = TITLE_AREA
    grid_y_end = PREVIEW_SIZE - FOOTER_AREA
    grid_h = grid_y_end - grid_y_start
    grid_w = PREVIEW_SIZE - PADDING * 2

    cell_w = grid_w // cols
    cell_h = grid_h // rows

    canvas = Image.new("RGB", (PREVIEW_SIZE, PREVIEW_SIZE), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    # Top and bottom accent bars
    draw.rectangle([(0, 0), (PREVIEW_SIZE, 12)], fill=ACCENT_COLOR)
    draw.rectangle([(0, PREVIEW_SIZE - 12), (PREVIEW_SIZE, PREVIEW_SIZE)], fill=ACCENT_COLOR)

    # Place images
    for i, img_path in enumerate(images):
        row = i // cols
        col = i % cols
        x = PADDING + col * cell_w
        y = grid_y_start + row * cell_h
        paste_image_on_bg(canvas, img_path, x, y, cell_w, cell_h, BG_COLOR)

    # Fonts
    font_title, font_subtitle, font_footer, font_badge = get_fonts()

    # PNG count badge top left
    badge_w, badge_h = 420, 160
    badge_x, badge_y = PADDING, 30
    draw.rounded_rectangle(
        [(badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h)],
        radius=36, fill=ACCENT_COLOR
    )
    draw.text(
        (badge_x + badge_w // 2, badge_y + badge_h // 2),
        f"{image_count} PNG",
        font=font_badge, fill=(255, 255, 255), anchor="mm"
    )

    # Transparent badge top right
    tbadge_w = 560
    tbadge_x = PREVIEW_SIZE - PADDING - tbadge_w
    draw.rounded_rectangle(
        [(tbadge_x, badge_y), (tbadge_x + tbadge_w, badge_y + badge_h)],
        radius=36, fill=(180, 165, 150)
    )
    draw.text(
        (tbadge_x + tbadge_w // 2, badge_y + badge_h // 2),
        "Transparent PNG",
        font=font_badge, fill=(255, 255, 255), anchor="mm"
    )

    # Title
    title_clean = theme.replace("watercolor", "").replace("kawaii", "").strip().title()
    if len(title_clean) > 35:
        title_clean = title_clean[:35] + "..."
    draw.text(
        (PREVIEW_SIZE // 2, 270),
        title_clean,
        font=font_title, fill=FONT_COLOR, anchor="mm"
    )

    # Subtitle
    draw.text(
        (PREVIEW_SIZE // 2, 390),
        "Watercolor Clipart Bundle",
        font=font_subtitle, fill=SUBTITLE_COLOR, anchor="mm"
    )

    # Separator line
    draw.line(
        [(PADDING * 2, 445), (PREVIEW_SIZE - PADDING * 2, 445)],
        fill=ACCENT_COLOR, width=5
    )

    # Footer text
    draw.text(
        (PREVIEW_SIZE // 2, PREVIEW_SIZE - 60),
        "Commercial Use  •  Instant Download  •  300 DPI",
        font=font_footer, fill=FOOTER_COLOR, anchor="mm"
    )

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
    image_dir = Path(f"images/{today}/{safe_name}")

    if not image_dir.exists():
        print(f"Image directory not found: {image_dir}")
        return

    preview_path = image_dir / "preview.png"
    success = create_preview(image_dir, preview_path, theme, image_count)

    if success:
        listing["preview_path"] = str(preview_path)
        with open("listing_today.json", "w") as f:
            json.dump(listing, f, indent=2, ensure_ascii=False)
        print(f"\nDone. Preview created: {preview_path}")
    else:
        print("\nFailed to create preview.")


if __name__ == "__main__":
    main()
