"""
Template Upload Script
Uploads editable Canva templates as Etsy listings.
Mockup images come from uploads/ folder in the repo.
Canva link goes into the description.
"""
import argparse
import json
import os
import re
import requests
import anthropic
from pathlib import Path

ETSY_API_BASE = "https://openapi.etsy.com/v3"
ETSY_KEYSTRING = os.environ["ETSY_KEYSTRING"]
ETSY_SHARED_SECRET = os.environ["ETSY_SHARED_SECRET"]
ETSY_REFRESH_TOKEN = os.environ["ETSY_REFRESH_TOKEN"]
ETSY_ACCESS_TOKEN = os.environ["ETSY_ACCESS_TOKEN"]
ETSY_SHOP_ID = os.environ.get("ETSY_SHOP_ID", "48022234")


def get_fresh_token():
    r = requests.post("https://api.etsy.com/v3/public/oauth/token",
                      data={"grant_type": "refresh_token", "client_id": ETSY_KEYSTRING,
                            "refresh_token": ETSY_REFRESH_TOKEN})
    if r.status_code == 200:
        print("  Token refreshed")
        return r.json().get("access_token", ETSY_ACCESS_TOKEN)
    return ETSY_ACCESS_TOKEN


def generate_description_en(theme: str, short_title: str, canva_link: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": f"""Write an SEO-optimized Etsy description in English for an editable Canva template listing.

Product: {short_title}
Theme: {theme}
Canva Template Link: {canva_link}

IMPORTANT: No Markdown, no bold, no headers. Plain text with emojis only.

Structure:
1. Short emotional intro (2-3 sentences with emojis)
2. "✨ Perfect for:" with 6 use cases
3. "📝 How it works:" explaining Canva editing process
4. "🔗 How to access your template:" explain that the Canva link will be available after purchase in the download section
5. "📦 What you get:" editable Canva template, instant access
6. "✰✰✰✰✰ TERMS OF USE ✰✰✰✰✰" personal and commercial use, not for resale
7. Long SEO keyword block for {theme}
8. Closing warning (digital product, no refunds)

600-900 words. English only. No Markdown."""}]
    )
    return message.content[0].text.strip()


def generate_description_de(theme: str, short_title: str, canva_link: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": f"""Schreibe eine SEO-optimierte Etsy-Beschreibung auf Deutsch fuer eine bearbeitbare Canva-Vorlage.

Produkt: {short_title}
Thema: {theme}
Canva-Link: {canva_link}

WICHTIG: Kein Markdown, kein Fettdruck. Nur normaler Text mit Emojis.

Struktur:
1. Kurze emotionale Einleitung (2-3 Saetze mit Emojis)
2. "✨ Perfekt fuer:" mit 6 Anwendungsbeispielen
3. "📝 So funktioniert es:" Canva-Bearbeitungsprozess erklaeren
4. "🔗 So greifst du auf deine Vorlage zu:" erklaere dass der Canva-Link nach dem Kauf im Download-Bereich verfuegbar ist
5. "📦 Was du bekommst:" bearbeitbare Canva-Vorlage, sofortiger Zugriff
6. "✰✰✰✰✰ NUTZUNGSRECHTE ✰✰✰✰✰" persoenliche und kommerzielle Nutzung
7. Langer SEO-Block fuer {theme}
8. Abschluss-Warnblock (digitales Produkt, keine Rueckerstattung)

600-900 Woerter. Nur Deutsch. Kein Markdown."""}]
    )
    return message.content[0].text.strip()


def generate_tags(theme: str) -> list:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": f"13 Etsy tags max 20 chars for editable Canva template. Theme: {theme}. Include: canva template, editable template, printable, digital download, instant download. JSON array only."}]
    )
    text = re.sub(r"```json\s*|```\s*", "", message.content[0].text.strip()).strip()
    return [t[:20] for t in json.loads(text)[:13]]


def generate_title(theme: str, short_title: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        messages=[{"role": "user", "content": f"SEO Etsy title for editable Canva template. Theme: {theme}, Short: {short_title}. Include: Editable, Canva Template, Printable, Digital Download. Max 140 chars. Only the title."}]
    )
    return message.content[0].text.strip()[:140]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True)
    parser.add_argument("--theme", required=True)
    parser.add_argument("--short-title", required=True)
    parser.add_argument("--canva-link", required=True)
    parser.add_argument("--price", type=float, default=8.99)
    args = parser.parse_args()

    image_dir = Path(args.folder)
    theme = args.theme
    short_title = args.short_title
    canva_link = args.canva_link
    price = args.price

    if not image_dir.exists():
        print(f"Folder not found: {image_dir}")
        return

    mockups = sorted([f for f in image_dir.glob("*.png")] +
                     [f for f in image_dir.glob("*.jpg")] +
                     [f for f in image_dir.glob("*.jpeg")])
    print(f"Found {len(mockups)} mockup images")

    token = get_fresh_token()
    api_key = f"{ETSY_KEYSTRING}:{ETSY_SHARED_SECRET}"
    headers = {"x-api-key": api_key, "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    headers_file = {"x-api-key": api_key, "Authorization": f"Bearer {token}"}

    print("  Generating title...")
    title = generate_title(theme, short_title)
    print(f"  Title: {title}")

    print("  Generating English description...")
    description_en = generate_description_en(theme, short_title, canva_link)

    print("  Generating German description...")
    description_de = generate_description_de(theme, short_title, canva_link)

    print("  Generating tags...")
    tags = generate_tags(theme)
    print(f"  Tags: {tags}")

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
        "is_customizable": True,
        "processing_min": 0,
        "processing_max": 0,
        "tags": tags,
    }
    r = requests.post(f"{ETSY_API_BASE}/application/shops/{ETSY_SHOP_ID}/listings",
                      headers=headers, json=payload)
    r.raise_for_status()
    listing_id = str(r.json()["listing_id"])
    print(f"  Listing created: {listing_id}")

    # Upload mockup images
    for i, mockup in enumerate(mockups[:5]):
        suffix = mockup.suffix.lower()
        mime = "image/png" if suffix == ".png" else "image/jpeg"
        with open(mockup, "rb") as f:
            requests.post(
                f"{ETSY_API_BASE}/application/shops/{ETSY_SHOP_ID}/listings/{listing_id}/images",
                headers=headers_file,
                files={"image": (mockup.name, f, mime)},
                data={"rank": i + 1}
            )
        print(f"  Mockup {i+1} uploaded: {mockup.name}")

    # Create Canva PDF
    print("  Creating Canva PDF...")
    pdf_path = image_dir / "canva_template.pdf"
    first_mockup = mockups[0] if mockups else None
    create_canva_pdf(pdf_path, short_title, canva_link, first_mockup)

    # Upload PDF as digital file to Etsy
    if pdf_path.exists():
        with open(pdf_path, "rb") as f:
            r2 = requests.post(
                f"{ETSY_API_BASE}/application/shops/{ETSY_SHOP_ID}/listings/{listing_id}/files",
                headers=headers_file,
                files={"file": (pdf_path.name, f, "application/pdf")},
                data={"name": pdf_path.name, "rank": 1}
            )
            if r2.status_code in [200, 201]:
                print("  Canva PDF uploaded to Etsy as digital file")
            else:
                print(f"  Warning: PDF upload failed: {r2.text}")

    # German translation
    requests.post(
        f"{ETSY_API_BASE}/application/shops/{ETSY_SHOP_ID}/listings/{listing_id}/translations/de",
        headers=headers,
        json={"title": title, "description": description_de}
    )
    print("  German translation added")

    print(f"\n✓ Done! Draft listing: https://www.etsy.com/your/shops/me/tools/listings/{listing_id}")
    print(f"  Price: {price} EUR")
    print(f"  Canva link in description: {canva_link}")


if __name__ == "__main__":
    main()


def create_canva_pdf(output_path: Path, short_title: str, canva_link: str, preview_image: Path = None):
    """Create a simple PDF with the Canva template link."""
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas as pdf_canvas

    pdf_size = 6 * inch
    c = pdf_canvas.Canvas(str(output_path), pagesize=(pdf_size, pdf_size))

    # Background
    c.setFillColorRGB(1.0, 0.99, 0.97)
    c.rect(0, 0, pdf_size, pdf_size, fill=1, stroke=0)

    # Top accent bar
    c.setFillColorRGB(0.77, 0.62, 0.47)
    c.rect(0, pdf_size - 8, pdf_size, 8, fill=1, stroke=0)
    c.rect(0, 0, pdf_size, 8, fill=1, stroke=0)

    # Shop name
    c.setFillColorRGB(0.77, 0.62, 0.47)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(pdf_size / 2, pdf_size - 55, "The Feeling We Share")

    # Thank you
    c.setFillColorRGB(0.22, 0.18, 0.16)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(pdf_size / 2, pdf_size - 100, "Thank You for Your Purchase!")

    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0.35, 0.28, 0.25)
    c.drawCentredString(pdf_size / 2, pdf_size - 125, f"Your template: {short_title}")

    # Instructions
    c.setFont("Helvetica-Bold", 13)
    c.setFillColorRGB(0.22, 0.18, 0.16)
    c.drawCentredString(pdf_size / 2, pdf_size - 175, "📝 How to access your Canva template:")

    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0.35, 0.28, 0.25)
    steps = [
        "1. Click the link below to open your template in Canva",
        "2. Click 'Use template' to make your own copy",
        "3. Edit names, dates, and details as needed",
        "4. Download as PDF or PNG when finished",
    ]
    y = pdf_size - 205
    for step in steps:
        c.drawCentredString(pdf_size / 2, y, step)
        y -= 20

    # Download button style
    bw, bh = pdf_size * 0.80, 50
    bx = (pdf_size - bw) / 2
    by = pdf_size * 0.35

    c.setFillColorRGB(0.77, 0.62, 0.47)
    c.roundRect(bx, by, bw, bh, 10, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(pdf_size / 2, by + 18, "CLICK HERE TO OPEN YOUR TEMPLATE")
    c.linkURL(canva_link, (bx, by, bx + bw, by + bh), relative=0)

    # URL text
    c.setFillColorRGB(0.77, 0.62, 0.47)
    c.setFont("Helvetica", 8)
    c.drawCentredString(pdf_size / 2, by - 15, canva_link[:80])

    # Terms
    c.setFillColorRGB(0.47, 0.39, 0.35)
    c.setFont("Helvetica", 9)
    c.drawCentredString(pdf_size / 2, 50, "Personal & Commercial Use • Do not resell original template")

    c.save()
    print(f"  Canva PDF saved: {output_path}")
    return output_path
