"""
Manual Upload Script
Reads PNGs from uploads/FOLDER_NAME/ in the repository,
creates preview + thank you PDF, uploads to Dropbox and Etsy.
"""
import argparse
import json
import os
import math
import random
import re
import requests
import numpy as np
import anthropic
import dropbox as dropbox_module
from datetime import date
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
DROPBOX_REFRESH_TOKEN = os.environ["DROPBOX_REFRESH_TOKEN"]
DROPBOX_APP_KEY = os.environ["DROPBOX_APP_KEY"]
DROPBOX_APP_SECRET = os.environ["DROPBOX_APP_SECRET"]
ETSY_KEYSTRING = os.environ["ETSY_KEYSTRING"]
ETSY_SHARED_SECRET = os.environ["ETSY_SHARED_SECRET"]
ETSY_REFRESH_TOKEN = os.environ["ETSY_REFRESH_TOKEN"]
ETSY_ACCESS_TOKEN = os.environ["ETSY_ACCESS_TOKEN"]
ETSY_SHOP_ID = os.environ.get("ETSY_SHOP_ID", "48022234")
ETSY_API_BASE = "https://openapi.etsy.com/v3"
PRICE = 3.49

PREVIEW_SIZE = 3000
BG_COLOR = (255, 255, 255)
ACCENT_COLOR = (196, 158, 120)
FONT_COLOR = (55, 45, 40)
SUBTITLE_COLOR = (120, 100, 88)
TITLE_AREA = 320
PADDING = 80
random.seed(42)


def get_dbx():
    return dropbox_module.Dropbox(
        oauth2_refresh_token=DROPBOX_REFRESH_TOKEN,
        app_key=DROPBOX_APP_KEY,
        app_secret=DROPBOX_APP_SECRET
    )


def get_fonts():
    bold_paths = ["/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    regular_paths = ["/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    bold = next((p for p in bold_paths if Path(p).exists()), None)
    regular = next((p for p in regular_paths if Path(p).exists()), None)
    if bold and regular:
        return ImageFont.truetype(bold, 130), ImageFont.truetype(regular, 75)
    f = ImageFont.load_default()
    return f, f


def crop_white_border(img, threshold=240):
    arr = np.array(img.convert("RGB"))
    mask = np.any(arr < threshold, axis=2)
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    if not rows.any():
        return img
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    pad = 10
    return img.crop((max(0, cmin-pad), max(0, rmin-pad),
                     min(arr.shape[1], cmax+pad), min(arr.shape[0], rmax+pad)))


def remove_bg(img):
    try:
        from rembg import remove
        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        out = remove(buf.getvalue())
        return Image.open(io.BytesIO(out)).convert("RGBA")
    except Exception:
        return img.convert("RGBA")


def create_preview(image_dir: Path, short_title: str) -> Path:
    images = sorted([f for f in image_dir.glob("*.png") if f.name != "preview.png"])
    n = len(images)
    if n == 0:
        return None

    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    grid_h = PREVIEW_SIZE - TITLE_AREA - PADDING
    grid_w = PREVIEW_SIZE - PADDING * 2
    cell_w = grid_w // cols
    cell_h = grid_h // rows
    base_size = int(min(cell_w, cell_h) * 0.90)

    canvas = Image.new("RGB", (PREVIEW_SIZE, PREVIEW_SIZE), BG_COLOR)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(0, 0), (PREVIEW_SIZE, 10)], fill=ACCENT_COLOR)
    draw.rectangle([(0, PREVIEW_SIZE-10), (PREVIEW_SIZE, PREVIEW_SIZE)], fill=ACCENT_COLOR)

    for i, img_path in enumerate(images):
        row = i // cols
        col = i % cols
        cx = PADDING + col * cell_w + cell_w // 2
        cy = TITLE_AREA + row * cell_h + cell_h // 2
        ox = random.randint(-int(cell_w*0.12), int(cell_w*0.12))
        oy = random.randint(-int(cell_h*0.12), int(cell_h*0.12))
        size = int(base_size * random.uniform(0.85, 1.10))
        rot = random.uniform(-7, 7)

        img = remove_bg(Image.open(img_path).convert("RGBA"))
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img_rgb = crop_white_border(bg)
        img_rgb.thumbnail((size, size), Image.LANCZOS)
        rotated = img_rgb.rotate(rot, expand=True, fillcolor=(255, 255, 255))
        canvas.paste(rotated, (cx + ox - rotated.width//2, cy + oy - rotated.height//2))

    font_title, font_subtitle = get_fonts()
    draw.text((PREVIEW_SIZE//2, 110), short_title.upper(), font=font_title, fill=FONT_COLOR, anchor="mm")
    draw.text((PREVIEW_SIZE//2, 230), "WATERCOLOR CLIPART BUNDLE", font=font_subtitle, fill=SUBTITLE_COLOR, anchor="mm")
    draw.line([(PADDING*2, 278), (PREVIEW_SIZE-PADDING*2, 278)], fill=ACCENT_COLOR, width=3)

    wm = Path("watermark.png")
    if wm.exists():
        wmimg = Image.open(wm).convert("RGBA").resize((PREVIEW_SIZE, PREVIEW_SIZE), Image.LANCZOS)
        canvas = Image.alpha_composite(canvas.convert("RGBA"), wmimg).convert("RGB")

    preview_path = image_dir / "preview.png"
    canvas.save(str(preview_path), "PNG", optimize=True)
    print(f"  Preview saved: {preview_path}")
    return preview_path


def upload_to_dropbox(image_dir: Path, folder_name: str) -> tuple:
    dbx = get_dbx()
    today = str(date.today())
    dropbox_folder = f"/etsy-automation/manual/{today}/{folder_name}"

    images = sorted([f for f in image_dir.glob("*.png") if f.name != "preview.png"])
    print(f"  Uploading {len(images)} PNGs...")
    for i, img_path in enumerate(images):
        with open(img_path, "rb") as f:
            dbx.files_upload(f.read(), f"{dropbox_folder}/{i+1:02d}.png",
                             mode=dropbox_module.files.WriteMode.overwrite)

    for fname in ["preview.png"]:
        fpath = image_dir / fname
        if fpath.exists():
            with open(fpath, "rb") as f:
                dbx.files_upload(f.read(), f"{dropbox_folder}/{fname}",
                                 mode=dropbox_module.files.WriteMode.overwrite)

    try:
        link = dbx.sharing_create_shared_link_with_settings(dropbox_folder)
        url = link.url
    except dropbox_module.exceptions.ApiError:
        links = dbx.sharing_list_shared_links(dropbox_folder).links
        url = links[0].url

    print(f"  Dropbox URL: {url}")
    return url, dropbox_folder


def create_thankyou_pdf(image_dir: Path, preview_path: Path, short_title: str, image_count: int, dropbox_url: str) -> Path:
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas as pdf_canvas

    pdf_size = 6 * inch
    output_path = image_dir / "thankyou.pdf"
    c = pdf_canvas.Canvas(str(output_path), pagesize=(pdf_size, pdf_size))
    c.drawImage(str(preview_path), 0, 0, width=pdf_size, height=pdf_size, preserveAspectRatio=False)
    c.setFillColorRGB(1, 1, 1, alpha=0.45)
    c.rect(0, 0, pdf_size, pdf_size, fill=1, stroke=0)
    bw, bh = pdf_size*0.75, pdf_size*0.35
    bx, by = (pdf_size-bw)/2, (pdf_size-bh)/2
    c.setFillColorRGB(0.98, 0.80, 0.82)
    c.roundRect(bx, by, bw, bh, 20, fill=1, stroke=0)
    c.setFillColorRGB(0.15, 0.10, 0.08)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(pdf_size/2, by+bh*0.62, "CLICK HERE")
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(pdf_size/2, by+bh*0.30, "TO DOWNLOAD")
    c.linkURL(dropbox_url, (bx, by, bx+bw, by+bh), relative=0)
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.25, 0.20, 0.18)
    c.drawCentredString(pdf_size/2, by-20, f"{image_count} PNG Files • Transparent Background • Commercial Use")
    c.save()

    # Upload PDF to Dropbox too
    dbx = get_dbx()
    dropbox_folder = f"/etsy-automation/manual/{date.today()}/{image_dir.name}"
    with open(output_path, "rb") as f:
        dbx.files_upload(f.read(), f"{dropbox_folder}/thankyou.pdf",
                         mode=dropbox_module.files.WriteMode.overwrite)
    print(f"  Thank You PDF saved and uploaded to Dropbox")
    return output_path


def get_fresh_etsy_token():
    r = requests.post("https://api.etsy.com/v3/public/oauth/token",
                      data={"grant_type": "refresh_token", "client_id": ETSY_KEYSTRING,
                            "refresh_token": ETSY_REFRESH_TOKEN})
    if r.status_code == 200:
        return r.json().get("access_token", ETSY_ACCESS_TOKEN)
    return ETSY_ACCESS_TOKEN


def upload_to_etsy(image_dir, theme, short_title, dropbox_url, image_count, preview_path, thankyou_pdf_path, folder_keywords=""):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    token = get_fresh_etsy_token()
    api_key = f"{ETSY_KEYSTRING}:{ETSY_SHARED_SECRET}"
    headers = {"x-api-key": api_key, "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    headers_file = {"x-api-key": api_key, "Authorization": f"Bearer {token}"}

    msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=100, messages=[{"role": "user",
        "content": f"SEO Etsy title for watercolor clipart. Theme: {theme}, Count: {image_count}. Start with '{image_count} PNG', add keywords, max 140 chars. Only the title."}])
    title = msg.content[0].text.strip()[:140]
    print(f"  Title: {title}")

    msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=2000, messages=[{"role": "user",
        "content": f"SEO Etsy description English, no Markdown, watercolor clipart. Theme: {theme}, Count: {image_count}, Download: {dropbox_url}. This pack contains these elements: {folder_keywords}. Emotional intro, Perfect for list, Whats included, How to download, File format, Terms, Long SEO block with element keywords, Closing warning. 600-900 words."}])
    description_en = msg.content[0].text.strip()

    msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=2000, messages=[{"role": "user",
        "content": f"SEO Etsy Beschreibung Deutsch, kein Markdown, Aquarell Clipart. Thema: {theme}, Anzahl: {image_count}, Download: {dropbox_url}. Dieses Pack enthaelt: {folder_keywords}. Emotionale Einleitung, Perfekt fuer Liste, Inhalt, Download, Dateiformat, Nutzungsrechte, SEO Block mit Element-Keywords, Abschluss-Warnblock. 600-900 Woerter."}])
    description_de = msg.content[0].text.strip()

    msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=300, messages=[{"role": "user",
        "content": f"13 Etsy tags max 20 chars for watercolor clipart theme: {theme}. JSON array only."}])
    text = re.sub(r"```json\s*|```\s*", "", msg.content[0].text.strip()).strip()
    tags = [t[:20] for t in json.loads(text)[:13]]

    payload = {"quantity": 999, "title": title, "description": description_en, "price": PRICE,
               "who_made": "i_did", "when_made": "made_to_order", "taxonomy_id": 2078,
               "type": "download", "is_digital": True, "should_auto_renew": True,
               "state": "draft", "is_supply": False, "is_customizable": False,
               "processing_min": 0, "processing_max": 0, "tags": tags}
    r = requests.post(f"{ETSY_API_BASE}/application/shops/{ETSY_SHOP_ID}/listings", headers=headers, json=payload)
    r.raise_for_status()
    listing_id = str(r.json()["listing_id"])
    print(f"  Listing: {listing_id}")

    with open(preview_path, "rb") as f:
        requests.post(f"{ETSY_API_BASE}/application/shops/{ETSY_SHOP_ID}/listings/{listing_id}/images",
                      headers=headers_file, files={"image": (preview_path.name, f, "image/png")}, data={"rank": 1})

    samples = sorted([f for f in image_dir.glob("*.png") if f.name != "preview.png"])
    if len(samples) >= 2:
        for idx in [0, min(4, len(samples)-1)]:
            with open(samples[idx], "rb") as f:
                requests.post(f"{ETSY_API_BASE}/application/shops/{ETSY_SHOP_ID}/listings/{listing_id}/images",
                              headers=headers_file, files={"image": (samples[idx].name, f, "image/png")})

    if thankyou_pdf_path.exists():
        with open(thankyou_pdf_path, "rb") as f:
            requests.post(f"{ETSY_API_BASE}/application/shops/{ETSY_SHOP_ID}/listings/{listing_id}/files",
                          headers=headers_file, files={"file": (thankyou_pdf_path.name, f, "application/pdf")},
                          data={"name": thankyou_pdf_path.name, "rank": 1})

    requests.post(f"{ETSY_API_BASE}/application/shops/{ETSY_SHOP_ID}/listings/{listing_id}/translations/de",
                  headers=headers, json={"title": title, "description": description_de})
    print("  German translation added")
    print(f"  Done: https://www.etsy.com/your/shops/me/tools/listings/{listing_id}")
    return listing_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True, help="Path to folder with PNGs (e.g. uploads/mermaid-pack)")
    parser.add_argument("--theme", required=True)
    parser.add_argument("--short-title", required=True)
    args = parser.parse_args()

    image_dir = Path(args.folder)
    theme = args.theme
    short_title = args.short_title
    folder_name = image_dir.name
    # Extract keywords from folder name (replace hyphens with spaces)
    folder_keywords = folder_name.replace("-", ", ").replace("_", ", ")

    if not image_dir.exists():
        print(f"Folder not found: {image_dir}")
        return

    images = sorted([f for f in image_dir.glob("*.png") if f.name != "preview.png"])
    image_count = len(images)
    print(f"Found {image_count} images in {image_dir}")

    print("\n1. Creating preview...")
    preview_path = create_preview(image_dir, short_title)

    print("\n2. Uploading to Dropbox...")
    dropbox_url, dropbox_folder = upload_to_dropbox(image_dir, folder_name)

    print("\n3. Creating Thank You PDF...")
    thankyou_pdf_path = create_thankyou_pdf(image_dir, preview_path, short_title, image_count, dropbox_url)

    print("\n4. Creating Etsy listing...")
    listing_id = upload_to_etsy(image_dir, theme, short_title, dropbox_url, image_count, preview_path, thankyou_pdf_path, folder_keywords)

    print(f"\n✓ Done! Draft listing: https://www.etsy.com/your/shops/me/tools/listings/{listing_id}")


if __name__ == "__main__":
    main()
