import json
import os
import re
import anthropic
import requests
from datetime import date
from pathlib import Path

ETSY_API_BASE = "https://openapi.etsy.com/v3"
KEYSTRING = os.environ["ETSY_KEYSTRING"]
SHARED_SECRET = os.environ.get("ETSY_SHARED_SECRET", "")


def get_fresh_token() -> str:
    """Get a fresh access token using the refresh token."""
    refresh_token = os.environ.get("ETSY_REFRESH_TOKEN", "")
    if not refresh_token:
        return os.environ["ETSY_ACCESS_TOKEN"]

    response = requests.post(
        "https://api.etsy.com/v3/public/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": KEYSTRING,
            "refresh_token": refresh_token,
        }
    )
    if response.status_code == 200:
        token = response.json().get("access_token", "")
        print(f"  Token refreshed successfully")
        return token
    else:
        print(f"  Token refresh failed, using existing token: {response.text}")
        return os.environ["ETSY_ACCESS_TOKEN"]


ACCESS_TOKEN = get_fresh_token()

HEADERS = {
    "x-api-key": f"{KEYSTRING}:{SHARED_SECRET}",
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

PRICE = 3.49


def generate_description_de(theme: str, short_title: str, dropbox_url: str, image_count: int) -> str:
    """Generate German description for the primary listing field."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""Schreibe eine lange, SEO-optimierte Etsy-Produktbeschreibung auf DEUTSCH für ein Aquarell-Clipart-Bundle.

Produktdetails:
- Titel: {short_title}
- Thema: {theme}
- Anzahl Bilder: {image_count} PNG-Dateien
- Stil: Aquarell-Illustration, transparenter Hintergrund
- Aufloesung: 300 DPI, 2000x2000 Pixel
- Download-Link: {dropbox_url}

WICHTIG: Verwende KEIN Markdown. Keine **fett** oder *kursiv* Formatierung. Keine ## Ueberschriften. Nur normaler Text mit Emojis und Zeilenumbruechen.

Struktur:

1. EMOTIONALE EINLEITUNG (2-3 Saetze mit Emojis, warm und kreativ zum Thema)

2. "✨ Perfekt fuer:" mit 6-8 Anwendungsbeispielen als einfache Liste mit Bindestrichen

3. "📦 Was du bekommst:"
- {image_count} PNG-Dateien mit transparentem Hintergrund
- 300 DPI, 2000x2000 Pixel
- Sofort-Download ueber Dropbox-Link in der PDF

4. "📥 So laedt du herunter:"
- Nach dem Kauf die PDF-Datei von Etsy oeffnen
- Den Dropbox-Download-Link in der PDF anklicken
- Dateien werden direkt auf deinen Computer heruntergeladen

5. "✰✰✰✰✰ DATEIFORMAT ✰✰✰✰✰"
- PNG mit transparentem Hintergrund, 300 DPI

6. "✰✰✰✰✰ NUTZUNGSRECHTE ✰✰✰✰✰"
- Persoenliche und kommerzielle Nutzung erlaubt
- Darf NICHT unveraendert weiterverkauft werden
- Mit KI-Unterstuetzung erstellt

7. LANGER SEO-KEYWORD-BLOCK auf Deutsch - 3-4 Absaetze mit vielen Keyword-Variationen zum Thema "{theme}". Lesbar aber keyword-reich.

8. ABSCHLUSS-WARNBLOCK (genau so kopieren, ganz am Ende):
⚠️ Dies ist ein DIGITALES Produkt - kein physischer Artikel wird versendet.
💬 Bei Fragen helfe ich dir gerne vor dem Kauf weiter.
🔄 Bei Doppelkauf ist nur ein Austausch gegen andere Dateien moeglich (keine Rueckerstattung).
❌ Keine Rueckgabe bei digitalen Produkten - bei Download-Problemen gerne melden.

Gesamtlaenge: 600-900 Woerter. Nur auf DEUTSCH. Kein Markdown."""
        }]
    )
    return message.content[0].text.strip()


def generate_description_en(theme: str, short_title: str, dropbox_url: str, image_count: int) -> str:
    """Generate English description for the secondary language field."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""Write a long, SEO-optimized Etsy product description in ENGLISH for a watercolor clipart bundle.

Product details:
- Title: {short_title}
- Theme: {theme}
- Number of images: {image_count} PNG files
- Style: Watercolor illustration, transparent background
- Resolution: 300 DPI, 2000x2000 pixels
- Download link: {dropbox_url}

IMPORTANT: Do NOT use Markdown. No **bold** or *italic* formatting. No ## headings. Plain text only with emojis and line breaks.

Structure:

1. SHORT EMOTIONAL INTRO (2-3 sentences with emojis, warm and creative tone about the theme)

2. "✨ Perfect for:" with 6-8 use cases as simple dash list

3. "📦 What's included:"
- {image_count} PNG files with transparent background
- 300 DPI, 2000x2000 pixels
- Instant digital download via Dropbox link inside PDF

4. "📥 How to download:"
- After purchase open the PDF file from Etsy
- Click the Dropbox download link inside the PDF
- Files download directly to your computer

5. "✰✰✰✰✰ FILE FORMAT ✰✰✰✰✰"
- PNG with transparent background, 300 DPI

6. "✰✰✰✰✰ TERMS OF USE ✰✰✰✰✰"
- Personal and commercial use allowed
- May NOT be resold as-is
- Created with AI assistance

7. LONG SEO KEYWORD BLOCK - 3-4 paragraphs with many keyword variations for theme "{theme}". Readable but keyword-rich.

8. CLOSING WARNING BLOCK (copy exactly at the very end):
⚠️ This is a DIGITAL product - no physical item will be shipped.
💬 If you are unsure, please message me and I'll be happy to help before you purchase.
🔄 For duplicate purchases, only an exchange for other files is possible (no refunds).
❌ No returns on digital products - please contact me for any download issues.

Total length: 600-900 words. English only. No Markdown."""
        }]
    )
    return message.content[0].text.strip()


def generate_tags(theme: str, short_title: str) -> list:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": f"""Generate exactly 13 Etsy tags for a watercolor clipart bundle.
Theme: {theme}
Title: {short_title}

Rules:
- Each tag max 20 characters
- Mix specific and broad tags
- Include: watercolor clipart, PNG clipart, digital download, commercial use, transparent PNG, instant download
- Add theme-specific tags
- No duplicates

Respond ONLY with a JSON array of 13 strings."""
        }]
    )
    text = message.content[0].text.strip()
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text).strip()
    tags = json.loads(text)
    return [t[:20] for t in tags[:13]]


def get_shop_id() -> str:
    return os.environ.get("ETSY_SHOP_ID", "48022234")


def upload_image(shop_id: str, listing_id: str, image_path: Path):
    headers = {
        "x-api-key": f"{KEYSTRING}:{SHARED_SECRET}",
        "Authorization": f"Bearer {ACCESS_TOKEN}",
    }
    with open(image_path, "rb") as f:
        response = requests.post(
            f"{ETSY_API_BASE}/application/shops/{shop_id}/listings/{listing_id}/images",
            headers=headers,
            files={"image": (image_path.name, f, "image/png")},
            data={"rank": 1}
        )
    if response.status_code not in [200, 201]:
        print(f"  Warning: Could not upload image: {response.text}")
    else:
        print(f"  Image uploaded successfully")


def upload_digital_file(shop_id: str, listing_id: str, pdf_path: Path):
    headers = {
        "x-api-key": f"{KEYSTRING}:{SHARED_SECRET}",
        "Authorization": f"Bearer {ACCESS_TOKEN}",
    }
    with open(pdf_path, "rb") as f:
        response = requests.post(
            f"{ETSY_API_BASE}/application/shops/{shop_id}/listings/{listing_id}/files",
            headers=headers,
            files={"file": (pdf_path.name, f, "application/pdf")},
            data={"name": pdf_path.name, "rank": 1}
        )
    if response.status_code not in [200, 201]:
        print(f"  Warning: Could not upload digital file: {response.text}")
    else:
        print(f"  Digital file uploaded: {pdf_path.name}")


def add_german_translation(shop_id: str, listing_id: str, title: str, description_de: str):
    """Add German translation to the listing."""
    payload = {
        "title": title,
        "description": description_de,
    }
    response = requests.post(
        f"{ETSY_API_BASE}/application/shops/{shop_id}/listings/{listing_id}/translations/de",
        headers=HEADERS,
        json=payload
    )
    if response.status_code not in [200, 201]:
        print(f"  Warning: Could not add German translation: {response.text}")
    else:
        print(f"  German translation added")


def create_listing(shop_id: str, title: str, description: str, tags: list) -> str:
    payload = {
        "quantity": 999,
        "title": title[:140],
        "description": description,
        "price": PRICE,
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
        "tags": tags,
    }
    response = requests.post(
        f"{ETSY_API_BASE}/application/shops/{shop_id}/listings",
        headers=HEADERS,
        json=payload
    )
    if response.status_code not in [200, 201]:
        print(f"  Error: {response.status_code} - {response.text}")
    response.raise_for_status()
    return str(response.json()["listing_id"])


def main():
    today = str(date.today())

    with open("listing_today.json", "r") as f:
        listing = json.load(f)

    theme = listing["theme"]
    short_title = listing.get("short_title", theme[:100])
    dropbox_url = listing["dropbox_url"]
    image_count = listing["image_count"]
    preview_path = Path(listing["preview_path"])
    thankyou_pdf_path = Path(listing.get("thankyou_pdf_path", ""))

    print(f"Uploading listing: {short_title}")

    print("  Generating English description...")
    description_en = generate_description_en(theme, short_title, dropbox_url, image_count)
    print(f"  English description: {len(description_en)} characters")

    print("  Generating German description...")
    description_de = generate_description_de(theme, short_title, dropbox_url, image_count)
    print(f"  German description: {len(description_de)} characters")

    print("  Generating tags...")
    tags = generate_tags(theme, short_title)
    print(f"  Tags: {tags}")

    print("  Getting shop ID...")
    shop_id = get_shop_id()
    print(f"  Shop ID: {shop_id}")

    title = f"{short_title} | {image_count} PNG Clipart | Watercolor | Transparent | Commercial Use"

    print("  Creating draft listing...")
    listing_id = create_listing(shop_id, title, description_en, tags)
    print(f"  Listing ID: {listing_id}")

    print("  Uploading preview image...")
    upload_image(shop_id, listing_id, preview_path)

    print("  Adding German translation...")
    add_german_translation(shop_id, listing_id, title, description_de)

    if thankyou_pdf_path.exists():
        print("  Uploading Thank You PDF...")
        upload_digital_file(shop_id, listing_id, thankyou_pdf_path)
    else:
        print("  No Thank You PDF found, skipping")

    listing["etsy_listing_id"] = listing_id
    listing["etsy_title"] = title
    listing["etsy_price"] = PRICE
    listing["etsy_tags"] = tags
    with open("listing_today.json", "w") as f:
        json.dump(listing, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Draft listing: https://www.etsy.com/your/shops/me/tools/listings/{listing_id}")
    print(f"Price: {PRICE} EUR")


if __name__ == "__main__":
    main()
