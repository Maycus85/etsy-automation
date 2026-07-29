"""
Megapack Listing Script
Creates an Etsy listing for a mega pack where:
- Images are already in Dropbox (no generation needed)
- Creates Thank You PDF with Dropbox link
- Creates a simple preview (title + watermark, no images)
- Uploads listing to Etsy as draft
- Buyer images added manually by seller
"""
import argparse
import json
import os
import re
import math
import requests
import anthropic
import dropbox as dropbox_module
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ETSY_API_BASE = "https://openapi.etsy.com/v3"
ETSY_KEYSTRING = os.environ["ETSY_KEYSTRING"]
ETSY_SHARED_SECRET = os.environ["ETSY_SHARED_SECRET"]
ETSY_REFRESH_TOKEN = os.environ["ETSY_REFRESH_TOKEN"]
ETSY_ACCESS_TOKEN = os.environ["ETSY_ACCESS_TOKEN"]
ETSY_SHOP_ID = os.environ.get("ETSY_SHOP_ID", "48022234")

PREVIEW_SIZE = 3000
BG_COLOR = (255, 253, 248)
ACCENT_COLOR = (196, 158, 120)
FONT_COLOR = (55, 45, 40)
SUBTITLE_COLOR = (120, 100, 88)


def get_dbx():
    return dropbox_module.Dropbox(
        oauth2_refresh_token=os.environ["DROPBOX_REFRESH_TOKEN"],
        app_key=os.environ["DROPBOX_APP_KEY"],
        app_secret=os.environ["DROPBOX_APP_SECRET"]
    )


def get_dropbox_folder_url(dropbox_input: str) -> tuple:
    """Accept either a Dropbox folder path or an existing share link.
    Returns (url, folder_path_or_none)"""
    # If it's already a Dropbox share link, use it directly
    if dropbox_input.startswith("https://www.dropbox.com"):
        # Convert to direct download link
        url = dropbox_input.replace("?dl=0", "?dl=1").replace("&dl=0", "&dl=1")
        if "dl=1" not in url:
            url += "&dl=1" if "?" in url else "?dl=1"
        print(f"  Using provided Dropbox share link")
        return url, None

    # Otherwise treat as folder path and create a link
    dbx = get_dbx()
    try:
        link = dbx.sharing_create_shared_link_with_settings(dropbox_input)
        return link.url, dropbox_input
    except dropbox_module.exceptions.ApiError:
        links = dbx.sharing_list_shared_links(dropbox_input).links
        return links[0].url, dropbox_input


def count_pngs_in_dropbox(dropbox_input: str) -> int:
    """Count PNGs - only works with folder paths, not share links."""
    if dropbox_input.startswith("https://"):
        print("  Note: Cannot count PNGs from share link, please provide count manually or use folder path")
        return 0
    dbx = get_dbx()
    try:
        result = dbx.files_list_folder(dropbox_input)
        count = sum(1 for e in result.entries
                    if isinstance(e, dropbox_module.files.FileMetadata)
                    and e.name.lower().endswith(".png"))
        return count
    except Exception as e:
        print(f"  Warning: Could not count PNGs: {e}")
        return 0


def create_simple_preview(output_path: Path, title: str, subtitle: str):
    """Create a preview with just title + watermark, no images."""
    canvas = Image.new("RGB", (PREVIEW_SIZE, PREVIEW_SIZE), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    # Accent bars
    draw.rectangle([(0, 0), (PREVIEW_SIZE, 14)], fill=ACCENT_COLOR)
    draw.rectangle([(0, PREVIEW_SIZE - 14), (PREVIEW_SIZE, PREVIEW_SIZE)], fill=ACCENT_COLOR)

    # Fonts
    bold_paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    regular_paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    bold = next((p for p in bold_paths if Path(p).exists()), None)
    regular = next((p for p in regular_paths if Path(p).exists()), None)

    if bold and regular:
        font_title = ImageFont.truetype(bold, 160)
        font_subtitle = ImageFont.truetype(regular, 90)
        font_info = ImageFont.truetype(regular, 70)
    else:
        font_title = font_subtitle = font_info = ImageFont.load_default()

    # Center title vertically
    draw.text((PREVIEW_SIZE // 2, PREVIEW_SIZE // 2 - 120),
              title.upper(), font=font_title, fill=FONT_COLOR, anchor="mm")

    draw.text((PREVIEW_SIZE // 2, PREVIEW_SIZE // 2 + 20),
              "WATERCOLOR CLIPART BUNDLE", font=font_subtitle, fill=SUBTITLE_COLOR, anchor="mm")

    draw.line([(200, PREVIEW_SIZE // 2 + 80), (PREVIEW_SIZE - 200, PREVIEW_SIZE // 2 + 80)],
              fill=ACCENT_COLOR, width=4)

    draw.text((PREVIEW_SIZE // 2, PREVIEW_SIZE // 2 + 150),
              subtitle, font=font_info, fill=SUBTITLE_COLOR, anchor="mm")

    # Watermark
    wm = Path("watermark.png")
    if wm.exists():
        wmimg = Image.open(wm).convert("RGBA").resize((PREVIEW_SIZE, PREVIEW_SIZE), Image.LANCZOS)
        canvas = Image.alpha_composite(canvas.convert("RGBA"), wmimg).convert("RGB")

    canvas.save(str(output_path), "PNG", optimize=True)
    print(f"  Simple preview saved: {output_path}")
    return output_path


def create_thankyou_pdf(output_path: Path, title: str, image_count: int, dropbox_url: str):
    """Create Thank You PDF with just title, thank you message and download link."""
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas as pdf_canvas

    pdf_size = 6 * inch
    c = pdf_canvas.Canvas(str(output_path), pagesize=(pdf_size, pdf_size))

    c.setFillColorRGB(1.0, 0.99, 0.97)
    c.rect(0, 0, pdf_size, pdf_size, fill=1, stroke=0)
    c.setFillColorRGB(0.77, 0.62, 0.47)
    c.rect(0, pdf_size - 8, pdf_size, 8, fill=1, stroke=0)
    c.rect(0, 0, pdf_size, 8, fill=1, stroke=0)

    c.setFillColorRGB(0.77, 0.62, 0.47)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(pdf_size / 2, pdf_size - 55, "The Feeling We Share")

    c.setFillColorRGB(0.22, 0.18, 0.16)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(pdf_size / 2, pdf_size - 100, "Thank You for Your Purchase!")

    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0.35, 0.28, 0.25)
    c.drawCentredString(pdf_size / 2, pdf_size - 128, f"Your bundle: {title}")
    c.drawCentredString(pdf_size / 2, pdf_size - 148, f"{image_count} PNG Files included")

    c.setFont("Helvetica-Bold", 13)
    c.setFillColorRGB(0.22, 0.18, 0.16)
    c.drawCentredString(pdf_size / 2, pdf_size - 195, "How to download your files:")

    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0.35, 0.28, 0.25)
    steps = [
        "1. Click the button below",
        "2. Your Dropbox folder will open",
        "3. Download all PNG files to your computer",
    ]
    y = pdf_size - 220
    for step in steps:
        c.drawCentredString(pdf_size / 2, y, step)
        y -= 20

    bw, bh = pdf_size * 0.80, 50
    bx = (pdf_size - bw) / 2
    by = pdf_size * 0.35

    c.setFillColorRGB(0.77, 0.62, 0.47)
    c.roundRect(bx, by, bw, bh, 10, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(pdf_size / 2, by + 18, "CLICK HERE TO DOWNLOAD YOUR FILES")
    c.linkURL(dropbox_url, (bx, by, bx + bw, by + bh), relative=0)

    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.47, 0.39, 0.35)
    c.drawCentredString(pdf_size / 2, 50,
                        "Personal & Commercial Use • Do not resell original files")
    c.save()
    print(f"  Thank You PDF saved: {output_path}")
    return output_path


def upload_pdf_to_dropbox(pdf_path: Path, dropbox_folder: str):
    dbx = get_dbx()
    with open(pdf_path, "rb") as f:
        dbx.files_upload(f.read(), f"{dropbox_folder}/thankyou.pdf",
                         mode=dropbox_module.files.WriteMode.overwrite)
    print("  Thank You PDF uploaded to Dropbox")


def get_fresh_etsy_token():
    r = requests.post("https://api.etsy.com/v3/public/oauth/token",
                      data={"grant_type": "refresh_token",
                            "client_id": ETSY_KEYSTRING,
                            "refresh_token": ETSY_REFRESH_TOKEN})
    if r.status_code == 200:
        print("  Token refreshed")
        return r.json().get("access_token", ETSY_ACCESS_TOKEN)
    return ETSY_ACCESS_TOKEN


def create_etsy_listing(title_input: str, dropbox_url: str, image_count: int, price: float):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    token = get_fresh_etsy_token()
    api_key = f"{ETSY_KEYSTRING}:{ETSY_SHARED_SECRET}"
    headers = {"x-api-key": api_key, "Authorization": f"Bearer {token}",
               "Content-Type": "application/json"}
    headers_file = {"x-api-key": api_key, "Authorization": f"Bearer {token}"}

    # Generate SEO title
    msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=100,
        messages=[{"role": "user", "content": f"""Create an SEO-optimized Etsy title for a MEGA watercolor clipart bundle.
Input title: {title_input}
Image count: {image_count}

Follow this pattern: "[Subject] Clipart Bundle: [Count] PNG, [Style], [Use Cases], Commercial Use"
Examples:
  "Mega Wedding Clipart Bundle: 200 PNG, Watercolor Flowers Rings Dresses, Digital Download, Commercial Use"
  "Ocean & Mermaid Mega Bundle: 150 PNG, Watercolor Sea Life, Baby Shower, Nursery, Commercial Use"

Max 140 chars. Only the title."""}])
    etsy_title = msg.content[0].text.strip()[:140]
    print(f"  Title: {etsy_title}")

    # Generate description EN
    msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=2000,
        messages=[{"role": "user", "content": f"""SEO Etsy description English, no Markdown, for a MEGA watercolor clipart bundle.
Title: {title_input}
Count: {image_count} PNG files
Download link available after purchase in PDF file.

Structure: Emotional intro, Perfect for list, Whats included, How to download (PDF with link), File format, Terms, Long SEO block, Closing warning. 600-900 words."""}])
    desc_en = msg.content[0].text.strip()

    # Generate description DE
    msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=2000,
        messages=[{"role": "user", "content": f"""SEO Etsy Beschreibung Deutsch, kein Markdown, fuer ein MEGA Aquarell Clipart Bundle.
Titel: {title_input}
Anzahl: {image_count} PNG Dateien
Download-Link nach dem Kauf in der PDF-Datei verfuegbar.

Struktur: Emotionale Einleitung, Perfekt fuer Liste, Inhalt, Download-Anleitung, Dateiformat, Nutzungsrechte, SEO Block, Abschluss-Warnblock. 600-900 Woerter."""}])
    desc_de = msg.content[0].text.strip()

    # Generate tags
    msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=300,
        messages=[{"role": "user", "content": f"13 Etsy tags max 20 chars for mega watercolor clipart bundle: {title_input}. Include: mega bundle, clipart bundle, watercolor png, digital download, commercial use, instant download. JSON array only."}])
    text = re.sub(r"```json\s*|```\s*", "", msg.content[0].text.strip()).strip()
    tags = [t[:20] for t in json.loads(text)[:13]]
    print(f"  Tags: {tags}")

    # Create listing
    payload = {"quantity": 999, "title": etsy_title, "description": desc_en,
               "price": price, "who_made": "i_did", "when_made": "made_to_order",
               "taxonomy_id": 2078, "type": "download", "is_digital": True,
               "should_auto_renew": True, "state": "draft", "is_supply": False,
               "is_customizable": False, "processing_min": 0, "processing_max": 0,
               "tags": tags}
    r = requests.post(f"{ETSY_API_BASE}/application/shops/{ETSY_SHOP_ID}/listings",
                      headers=headers, json=payload)
    r.raise_for_status()
    listing_id = str(r.json()["listing_id"])
    print(f"  Listing created: {listing_id}")

    # German translation
    requests.post(
        f"{ETSY_API_BASE}/application/shops/{ETSY_SHOP_ID}/listings/{listing_id}/translations/de",
        headers=headers, json={"title": etsy_title, "description": desc_de})
    print("  German translation added")

    return listing_id, etsy_title, headers_file


def upload_pdf_to_etsy(listing_id: str, pdf_path: Path, headers_file: dict):
    with open(pdf_path, "rb") as f:
        r = requests.post(
            f"{ETSY_API_BASE}/application/shops/{ETSY_SHOP_ID}/listings/{listing_id}/files",
            headers=headers_file,
            files={"file": (pdf_path.name, f, "application/pdf")},
            data={"name": pdf_path.name, "rank": 1})
        if r.status_code in [200, 201]:
            print("  Thank You PDF uploaded to Etsy")
        else:
            print(f"  Warning: PDF upload to Etsy failed: {r.text}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--dropbox-folder", required=True, help="Dropbox folder path OR share link")
    parser.add_argument("--price", type=float, default=6.99)
    parser.add_argument("--image-count", type=int, default=0, help="Manual image count if using share link")
    args = parser.parse_args()

    title = args.title
    dropbox_input = args.dropbox_folder
    price = args.price

    work_dir = Path("/tmp/megapack")
    work_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nMega Pack: {title}")

    print("\n1. Getting Dropbox folder URL...")
    dropbox_url, folder_path = get_dropbox_folder_url(dropbox_input)
    print(f"  URL: {dropbox_url}")

    print("\n2. Counting PNGs in Dropbox...")
    if args.image_count > 0:
        image_count = args.image_count
        print(f"  Using provided count: {image_count}")
    elif folder_path:
        image_count = count_pngs_in_dropbox(folder_path)
        print(f"  Found {image_count} PNG files")
    else:
        image_count = 0
        print("  Could not count automatically, using 0")

    print("\n3. Creating simple preview (title + watermark only)...")
    preview_path = work_dir / "preview.png"
    subtitle = f"{image_count} Transparent PNG Files • Commercial Use • Instant Download"
    create_simple_preview(preview_path, title, subtitle)

    print("\n4. Creating Thank You PDF...")
    pdf_path = work_dir / "thankyou.pdf"
    create_thankyou_pdf(pdf_path, title, image_count, dropbox_url)

    print("\n5. Uploading Thank You PDF to Dropbox...")
    upload_pdf_to_dropbox(pdf_path, dropbox_folder)

    print("\n6. Creating Etsy listing...")
    listing_id, etsy_title, headers_file = create_etsy_listing(title, dropbox_url, image_count, price)

    print("\n7. Uploading Thank You PDF to Etsy...")
    upload_pdf_to_etsy(listing_id, pdf_path, headers_file)

    print(f"\n✓ Done!")
    print(f"  Listing: https://www.etsy.com/your/shops/me/tools/listings/{listing_id}")
    print(f"  Price: {price} EUR")
    print(f"  Images: {image_count} PNG")
    print(f"\n  ⚠️  Don't forget to add preview images manually in Etsy!")


if __name__ == "__main__":
    main()
