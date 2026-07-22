import json
import os
import re
import anthropic
import requests
from datetime import date
from pathlib import Path

ETSY_API_BASE = "https://openapi.etsy.com/v3"
KEYSTRING = os.environ["ETSY_KEYSTRING"]
ACCESS_TOKEN = os.environ["ETSY_ACCESS_TOKEN"]

HEADERS = {
    "x-api-key": KEYSTRING,
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

ORIGINAL_PRICE = 5.99
SALE_PRICE = 2.99


def generate_description(theme: str, short_title: str, dropbox_url: str, image_count: int) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""Write a long, SEO-optimized Etsy product description for a watercolor clipart bundle.

Product details:
- Title: {short_title}
- Theme: {theme}
- Number of images: {image_count} PNG files
- Style: Watercolor illustration, transparent background
- Resolution: 300 DPI, 2000x2000 pixels
- Download link: {dropbox_url}

Follow this exact structure:

1. OPENING WARNING BLOCK (copy exactly):
⚠️ This is a DIGITAL product — no physical item will be shipped.
💬 If you are unsure, please message me and I'll be happy to help before you purchase.
🔄 For duplicate purchases, only an exchange for other files is possible (no refunds).

2. SHORT EMOTIONAL INTRO (2-3 sentences with emojis, warm and creative tone about the theme)

3. "✨ Perfect for:" with 6-8 creative use cases as bullet points

4. "📦 What's included:"
- {image_count} PNG files with transparent background
- 300 DPI, 2000x2000 pixels
- Instant digital download via Dropbox link inside PDF

5. "📥 How to download:"
- After purchase open the PDF file from Etsy
- Click the download link inside the PDF
- Files will download directly to your computer

6. "✰✰✰✰✰ FILE FORMAT ✰✰✰✰✰"
- PNG with transparent background, 300 DPI

7. "✰✰✰✰✰ TERMS OF USE ✰✰✰✰✰"
- Personal and commercial use allowed
- May NOT resell designs as-is
- Created with AI assistance

8. "✰✰✰✰✰ RETURNS ✰✰✰✰✰"
- No returns on digital products
- Contact for download issues

9. LONG SEO KEYWORD BLOCK - Write 3-4 paragraphs repeating theme keywords in many variations.
Use theme: "{theme}" as basis. Make it readable but keyword-rich.

Total length: 600-900 words. Write in English."""
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
    """Get the shop ID for the authenticated user."""
    response = requests.get(
        f"{ETSY_API_BASE}/application/users/me",
        headers=HEADERS
    )
    response.raise_for_status()
    user_id = response.json()["user_id"]

    response2 = requests.get(
        f"{ETSY_API_BASE}/application/users/{user_id}/shops",
        headers=HEADERS
    )
    response2.raise_for_status()
    return str(response2.json()["shop_id"])


def upload_image(shop_id: str, image_path: Path) -> str:
    headers = {
        "x-api-key": KEYSTRING,
        "Authorization": f"Bearer {ACCESS_TOKEN}",
    }
    with open(image_path, "rb") as f:
        response = requests.post(
            f"{ETSY_API_BASE}/application/shops/{shop_id}/listing-images",
            headers=headers,
            files={"image": (image_path.name, f, "image/png")}
        )
    response.raise_for_status()
    return str(response.json()["listing_image_id"])


def upload_digital_file(shop_id: str, listing_id: str, pdf_path: Path):
    """Upload the Thank You PDF as the digital download file."""
    headers = {
        "x-api-key": KEYSTRING,
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


def create_listing(shop_id: str, title: str, description: str, tags: list) -> str:
    payload = {
        "quantity": 999,
        "title": title[:140],
        "description": description,
        "price": ORIGINAL_PRICE,
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
    response.raise_for_status()
    return str(response.json()["listing_id"])


def attach_image_to_listing(shop_id: str, listing_id: str, image_id: str):
    response = requests.post(
        f"{ETSY_API_BASE}/application/shops/{shop_id}/listings/{listing_id}/images/{image_id}",
        headers=HEADERS
    )
    response.raise_for_status()


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

    print("  Generating SEO description...")
    description = generate_description(theme, short_title, dropbox_url, image_count)
    print(f"  Description: {len(description)} characters")

    print("  Generating tags...")
    tags = generate_tags(theme, short_title)
    print(f"  Tags: {tags}")

    print("  Getting shop ID...")
    shop_id = get_shop_id()
    print(f"  Shop ID: {shop_id}")

    print("  Uploading preview image...")
    image_id = upload_image(shop_id, preview_path)
    print(f"  Image ID: {image_id}")

    title = f"{short_title} | {image_count} PNG Clipart | Watercolor | Transparent | Commercial Use"

    print("  Creating draft listing...")
    listing_id = create_listing(shop_id, title, description, tags)
    print(f"  Listing ID: {listing_id}")

    attach_image_to_listing(shop_id, listing_id, image_id)
    print("  Preview image attached")

    # Upload Thank You PDF as digital download file
    if thankyou_pdf_path.exists():
        print("  Uploading Thank You PDF...")
        upload_digital_file(shop_id, listing_id, thankyou_pdf_path)
    else:
        print("  No Thank You PDF found, skipping digital file upload")

    # Save result
    listing["etsy_listing_id"] = listing_id
    listing["etsy_title"] = title
    listing["etsy_original_price"] = ORIGINAL_PRICE
    listing["etsy_sale_price"] = SALE_PRICE
    listing["etsy_tags"] = tags
    with open("listing_today.json", "w") as f:
        json.dump(listing, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Draft listing: https://www.etsy.com/your/shops/me/tools/listings/{listing_id}")
    print(f"Original price: {ORIGINAL_PRICE} EUR, Sale price: {SALE_PRICE} EUR")
    print("Note: Activate the sale manually in Etsy Shop Manager under 'Sales & Discounts'")


if __name__ == "__main__":
    main()
