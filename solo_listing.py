"""
Solo Listing Script
Downloads selected PNGs from Dropbox, creates preview with white background + watermark,
analyzes each image with Claude Vision, and uploads as individual Etsy listings.
"""
import argparse
import base64
import json
import os
import re
import requests
import anthropic
import dropbox as dropbox_module
from pathlib import Path
from PIL import Image
import io

ETSY_API_BASE = "https://openapi.etsy.com/v3"
ETSY_KEYSTRING = os.environ["ETSY_KEYSTRING"]
ETSY_SHARED_SECRET = os.environ["ETSY_SHARED_SECRET"]
ETSY_REFRESH_TOKEN = os.environ["ETSY_REFRESH_TOKEN"]
ETSY_ACCESS_TOKEN = os.environ["ETSY_ACCESS_TOKEN"]
ETSY_SHOP_ID = os.environ.get("ETSY_SHOP_ID", "48022234")
PREVIEW_SIZE = 2000


def get_dbx():
    return dropbox_module.Dropbox(
        oauth2_refresh_token=os.environ["DROPBOX_REFRESH_TOKEN"],
        app_key=os.environ["DROPBOX_APP_KEY"],
        app_secret=os.environ["DROPBOX_APP_SECRET"]
    )


def get_fresh_token():
    r = requests.post("https://api.etsy.com/v3/public/oauth/token",
                      data={"grant_type": "refresh_token",
                            "client_id": ETSY_KEYSTRING,
                            "refresh_token": ETSY_REFRESH_TOKEN})
    if r.status_code == 200:
        return r.json().get("access_token", ETSY_ACCESS_TOKEN)
    return ETSY_ACCESS_TOKEN


def download_png_from_dropbox(dropbox_folder: str, filename: str, local_path: Path) -> bool:
    """Download a single PNG from Dropbox."""
    try:
        dbx = get_dbx()
        dropbox_path = f"{dropbox_folder}/{filename}"
        dbx.files_download_to_file(str(local_path), dropbox_path)
        return True
    except Exception as e:
        print(f"  Error downloading {filename}: {e}")
        return False


def create_preview(png_path: Path, output_path: Path) -> Path:
    """Create preview image with white background and watermark."""
    img = Image.open(png_path).convert("RGBA")

    # Create white background
    preview = Image.new("RGB", (PREVIEW_SIZE, PREVIEW_SIZE), (255, 255, 255))

    # Resize image to fit, keeping aspect ratio with padding
    img_ratio = img.width / img.height
    if img_ratio > 1:
        new_w = int(PREVIEW_SIZE * 0.75)
        new_h = int(new_w / img_ratio)
    else:
        new_h = int(PREVIEW_SIZE * 0.75)
        new_w = int(new_h * img_ratio)

    img_resized = img.resize((new_w, new_h), Image.LANCZOS)

    # Center on white background
    bg = Image.new("RGBA", (PREVIEW_SIZE, PREVIEW_SIZE), (255, 255, 255, 255))
    x = (PREVIEW_SIZE - new_w) // 2
    y = (PREVIEW_SIZE - new_h) // 2
    bg.paste(img_resized, (x, y), img_resized)

    # Apply watermark
    wm_path = Path("watermark.png")
    if wm_path.exists():
        wm = Image.open(wm_path).convert("RGBA")
        wm = wm.resize((PREVIEW_SIZE, PREVIEW_SIZE), Image.LANCZOS)
        result = Image.alpha_composite(bg, wm)
        result.convert("RGB").save(str(output_path), "PNG")
    else:
        bg.convert("RGB").save(str(output_path), "PNG")

    return output_path


def analyze_image_with_claude(img_path: Path, pack_theme: str) -> dict:
    """Use Claude Vision to analyze the image and generate listing content."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    with open(img_path, "rb") as f:
        img_data = base64.standard_b64encode(f.read()).decode("utf-8")

    # Determine media type
    suffix = img_path.suffix.lower()
    media_type = "image/png" if suffix == ".png" else "image/jpeg"

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": img_data,
                    }
                },
                {
                    "type": "text",
                    "text": f"""Analyze this watercolor clipart image from a "{pack_theme}" pack.

Generate the following in JSON format:
{{
  "subject": "what is in the image in 2-4 words",
  "title": "SEO Etsy title max 140 chars: [Subject] Watercolor Clipart PNG, [Theme], [Use Cases], Commercial Use",
  "tags": ["13 tags max 20 chars each, include: watercolor clipart, png clipart, digital download, commercial use, transparent png, instant download, plus subject-specific tags"]
}}

Respond ONLY with valid JSON. Keep all strings on one line. No newlines inside strings."""
                }
            ]
        }]
    )

    text = message.content[0].text.strip()
    text = re.sub(r"```json\s*|```\s*", "", text).strip()
    result = json.loads(text)

    # Generate descriptions separately
    client2 = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    subject = result["subject"]

    desc_msg = client2.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": f"""Write a long SEO-optimized Etsy description in English for a single watercolor clipart PNG.

Subject: {subject}
Pack theme: {pack_theme}
File: 1 PNG, transparent background, 300 DPI, instant download, commercial use

No Markdown. Plain text with emojis. Structure:
1. Emotional intro 2-3 sentences with emojis
2. "✨ Perfect for:" 6-8 use cases as dash list
3. "📦 What you get:" 1 PNG transparent 300 DPI instant download
4. "📥 How to download:" open Etsy downloads, save to computer
5. "✰✰✰✰✰ FILE FORMAT ✰✰✰✰✰"
6. "✰✰✰✰✰ TERMS OF USE ✰✰✰✰✰"
7. Long SEO keyword block with many variations of subject and theme
8. Closing warning with emojis

500-700 words."""}]
    )
    result["description_en"] = desc_msg.content[0].text.strip()

    desc_de_msg = client2.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": f"""Schreibe eine lange SEO-optimierte Etsy-Beschreibung auf Deutsch fuer ein einzelnes Aquarell-Clipart PNG.

Motiv: {subject}
Pack-Thema: {pack_theme}
Datei: 1 PNG, transparenter Hintergrund, 300 DPI, Sofort-Download, kommerzielle Nutzung

Kein Markdown. Normaler Text mit Emojis. Struktur:
1. Emotionale Einleitung 2-3 Saetze mit Emojis
2. "✨ Perfekt fuer:" 6-8 Anwendungsbeispiele als Strichliste
3. "📦 Was du bekommst:" 1 PNG transparent 300 DPI Sofort-Download
4. "📥 So laedt du herunter:"
5. "✰✰✰✰✰ DATEIFORMAT ✰✰✰✰✰"
6. "✰✰✰✰✰ NUTZUNGSRECHTE ✰✰✰✰✰"
7. Langer SEO-Block mit vielen Variationen
8. Abschluss-Warnblock mit Emojis

500-700 Woerter."""}]
    )
    result["description_de"] = desc_de_msg.content[0].text.strip()

    return result


def upload_listing_to_etsy(token: str, png_path: Path, preview_path: Path,
                            title: str, description_en: str, description_de: str,
                            tags: list, price: float) -> str:
    """Create Etsy listing, upload preview and digital file."""
    api_key = f"{ETSY_KEYSTRING}:{ETSY_SHARED_SECRET}"
    headers = {"x-api-key": api_key, "Authorization": f"Bearer {token}",
               "Content-Type": "application/json"}
    headers_file = {"x-api-key": api_key, "Authorization": f"Bearer {token}"}

    # Clean title
    title = title.strip().strip('"').strip("'")[:140]

    # Create listing
    payload = {
        "quantity": 999,
        "title": title,
        "description": description_en,
        "price": price,
        "who_made": "i_did",
        "when_made": "made_to_order",
        "taxonomy_id": 2078,
        "type": "download",
        "is_digital": True,
        "should_auto_renew": True,
        "state": "draft",
        "is_supply": False,
        "is_customizable": False,
        "processing_min": 0,
        "processing_max": 0,
        "tags": [t[:20] for t in tags[:13]],
    }
    r = requests.post(f"{ETSY_API_BASE}/application/shops/{ETSY_SHOP_ID}/listings",
                      headers=headers, json=payload)
    if r.status_code not in [200, 201]:
        print(f"  Error creating listing: {r.text}")
        r.raise_for_status()
    listing_id = str(r.json()["listing_id"])

    # Upload preview image
    with open(preview_path, "rb") as f:
        requests.post(
            f"{ETSY_API_BASE}/application/shops/{ETSY_SHOP_ID}/listings/{listing_id}/images",
            headers=headers_file,
            files={"image": (preview_path.name, f, "image/png")},
            data={"rank": 1}
        )

    # Upload PNG as digital file
    with open(png_path, "rb") as f:
        r2 = requests.post(
            f"{ETSY_API_BASE}/application/shops/{ETSY_SHOP_ID}/listings/{listing_id}/files",
            headers=headers_file,
            files={"file": (png_path.name, f, "image/png")},
            data={"name": png_path.name, "rank": 1}
        )
        if r2.status_code not in [200, 201]:
            print(f"  Warning: Digital file upload failed: {r2.text}")

    # German translation
    if description_de:
        requests.post(
            f"{ETSY_API_BASE}/application/shops/{ETSY_SHOP_ID}/listings/{listing_id}/translations/de",
            headers=headers,
            json={"title": title, "description": description_de}
        )
        print(f"  German translation added")

    return listing_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dropbox-folder", required=True, help="Dropbox folder path (e.g. /etsy-automation/2026-07-30/theme_name)")
    parser.add_argument("--theme", required=True, help="Pack theme name")
    parser.add_argument("--images", required=True, help="Comma-separated image numbers (e.g. 01,04,05,12)")
    parser.add_argument("--price", type=float, default=0.99)
    args = parser.parse_args()

    dropbox_folder = args.dropbox_folder
    theme = args.theme
    price = args.price
    image_numbers = [n.strip().zfill(2) for n in args.images.split(",")]

    print(f"Solo Listing: {theme}")
    print(f"Images: {image_numbers}")
    print(f"Price: {price} EUR")

    work_dir = Path("/tmp/solo_listings")
    work_dir.mkdir(parents=True, exist_ok=True)

    token = get_fresh_token()
    print("Token refreshed")

    created = []
    failed = []

    for num in image_numbers:
        filename = f"{num}.png"
        local_png = work_dir / filename
        local_preview = work_dir / f"preview_{num}.png"

        print(f"\n[{num}] Processing...")

        # Download from Dropbox
        print(f"  Downloading {filename}...")
        if not download_png_from_dropbox(dropbox_folder, filename, local_png):
            failed.append(num)
            continue

        # Create preview
        print(f"  Creating preview...")
        create_preview(local_png, local_preview)

        # Analyze with Claude Vision
        print(f"  Analyzing image with Claude...")
        try:
            content = analyze_image_with_claude(local_png, theme)
            title = content["title"]
            description_en = content["description_en"]
            description_de = content.get("description_de", "")
            tags = content["tags"]
            print(f"  Subject: {content['subject']}")
            print(f"  Title: {title[:60]}...")
        except Exception as e:
            print(f"  Error analyzing image: {e}")
            failed.append(num)
            continue

        # Upload to Etsy
        print(f"  Uploading to Etsy...")
        try:
            listing_id = upload_listing_to_etsy(
                token, local_png, local_preview, title,
                description_en, description_de, tags, price
            )
            print(f"  Created listing: {listing_id}")
            created.append({"num": num, "listing_id": listing_id, "title": title})
        except Exception as e:
            print(f"  Error creating listing: {e}")
            failed.append(num)
            continue

    print(f"\n{'='*50}")
    print(f"Done! Created {len(created)} listings, {len(failed)} failed.")
    if failed:
        print(f"Failed: {failed}")
    for item in created:
        print(f"  [{item['num']}] {item['listing_id']}: {item['title'][:50]}")


if __name__ == "__main__":
    main()
