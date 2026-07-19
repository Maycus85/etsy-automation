import json
import math
import os
import anthropic
from datetime import date
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PREVIEW_SIZE = 3000
BG_COLOR = (255, 253, 248)
ACCENT_COLOR = (196, 158, 120)
FONT_COLOR = (55, 45, 40)
SUBTITLE_COLOR = (120, 100, 88)
TITLE_AREA = 320
PADDING = 80


def generate_short_title(theme: str) -> str:
    """Generate a clean 3-4 word title from the theme using Claude."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=50,
        messages=[{
            "role": "user",
            "content": f"""Create a short product title for an Etsy clipart listing based on this theme: "{theme}"

Rules:
- Maximum 4 words
- Do NOT use these words: Watercolor, Clipart, Bundle (they appear in the subtitle already)
- Focus on the subject and style, examples: "Elegant Wedding Flowers", "Kawaii Forest Animals", "Cozy Kitchen Utensils", "Autumn Harvest Elements"
- No punctuation, no quotes
- Descriptive and marketable

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


def paste_image_on_bg(canvas, img_path, x, y, w, h):
    img = Image.open(img_path).convert("RGBA")
    bg = Image.new("RGBA", img.size, BG_COLOR + (255,))
    bg.paste(img, mask=img.split()[3])
    img_rgb = bg.convert("RGB")
    pad = 30
    img_rgb.thumbnail((w - pad * 2, h - pad * 2), Image.LANCZOS)
    ox = x + (w - img_rgb.width) // 2
    oy = y + (h - img_rgb.height) // 2
    canvas.paste(img_rgb, (ox, oy))


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

    canvas = Image.new("RGB", (PREVIEW_SIZE, PREVIEW_SIZE), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    # Accent bars
    draw.rectangle([(0, 0), (PREVIEW_SIZE, 10)], fill=ACCENT_COLOR)
    draw.rectangle([(0, PREVIEW_SIZE - 10), (PREVIEW_SIZE, PREVIEW_SIZE)], fill=ACCENT_COLOR)

    # Images
    for i, img_path in enumerate(images):
        row = i // cols
        col = i % cols
        x = PADDING + col * cell_w
        y = grid_y_start + row * cell_h
        paste_image_on_bg(canvas, img_path, x, y, cell_w, cell_h)

    font_title, font_subtitle = get_fonts()

    # Title centered, single line
    draw.text(
        (PREVIEW_SIZE // 2, 110),
        short_title,
        font=font_title,
        fill=FONT_COLOR,
        anchor="mm"
    )

    # Subtitle - more space below title
    draw.text(
        (PREVIEW_SIZE // 2, 230),
        "Watercolor Clipart Bundle",
        font=font_subtitle,
        fill=SUBTITLE_COLOR,
        anchor="mm"
    )

    # Separator
    draw.line(
        [(PADDING * 2, 278), (PREVIEW_SIZE - PADDING * 2, 278)],
        fill=ACCENT_COLOR, width=3
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
    image_dir = Path(f"images/{today}/{safe_name}")

    if not image_dir.exists():
        print(f"Image directory not found: {image_dir}")
        return

    # Generate short title
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
