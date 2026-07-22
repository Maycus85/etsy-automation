import json
import os
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


def generate_description(theme: str, short_title: str, dropbox_url: str, image_count: int) -> str:
    """Generate a long SEO-optimized Etsy listing description using Claude."""
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

2. SHORT EMOTIONAL INTRO (2-3 sentences about the theme, warm and creative tone)

3. "✨ Perfect for:" with 6-8 creative use cases as bullet points (scrapbooking, Cricut, T-shirts, greeting cards, Canva, etc.)

4. "📦 What's included:" with technical details:
- Number of PNG files
- Transparent background
- 300 DPI resolution
- Instant digital download via Dropbox link

5. "📥 How to download:" 
- After purchase, open the PDF file
- Click the download link inside the PDF
- Direct link: {dropbox_url}
- Files download to your computer

6. "✰✰✰✰✰ FILE FORMAT ✰✰✰✰✰"
- PNG with transparent background
- 300 DPI, 2000x2000 pixels
- Commercial and personal use included

7. "✰✰✰✰✰ HOW TO DOWNLOAD ✰✰✰✰✰" (standard Etsy download instructions)

8. "✰✰✰✰✰ TERMS OF USE ✰✰✰✰✰"
- Personal and commercial use allowed
- May NOT resell designs as-is
- AI-assisted creation disclosure

9. "✰✰✰✰✰ RETURNS ✰✰✰✰✰"
- No returns on digital products
- Contact for download issues

10. LONG SEO KEYWORD BLOCK (very important for Etsy ranking):
Write 3-4 paragraphs that repeat the theme keywords in many variations. 
For example for "watercolor cats": mention "cat clipart", "kitten PNG", "cat printable", "cute cat art", "cat digital download", "cat illustration", "watercolor kitten", etc.
Make it readable but keyword-rich. Use the theme: "{theme}" as the basis.

Total length should be 600-900 words. Write in English."""
        }]
    )
    return message.content[0].text.strip()


def generate_tags(theme: str, short_title: str) -> list:
    """Generate 13 Etsy tags for the listing."""
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

    import re
    text = message.content[0].text.strip()
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text).strip()
    tags = json.loads(text)
    return [t[:20] for t in tags[:13]]


def get_shop_id() -> str:
    """Get the shop ID for the authenticated user."""
    response = requests.get(
        f"{ETSY_API_BASE}/application/shops",
        headers=HEADERS,
        params={"limit": 1}
    )
    response.raise_for_status()
    data = response.json()
    return str(data["results"][0]["shop_id"])


def upload_image(shop_id: str, image_path: Path) -> str:
    """Upload an image to Etsy and return the listing image ID."""
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


def create_listing(shop_id: str, title: str, description: str, tags: list, price: float) -> str:
    """Create a draft listing on Etsy and return listing ID."""
    payload = {
        "quantity": 999,
        "title": title[:140],
        "description": description,
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
    """Attach an already-uploaded image to a listing."""
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

    print(f"Uploading listing: {short_title}")

    # Generate description
    print("  Generating SEO description...")
    description = generate_description(theme, short_title, dropbox_url, image_count)
    print(f"  Description: {len(description)} characters")

    # Generate tags
    print("  Generating tags...")
    tags = generate_tags(theme, short_title)
    print(f"  Tags: {tags}")

    # Get shop ID
    print("  Getting shop ID...")
    shop_id = get_shop_id()
    print(f"  Shop ID: {shop_id}")

    # Upload preview image
    print(f"  Uploading preview image...")
    image_id = upload_image(shop_id, preview_path)
    print(f"  Image ID: {image_id}")

    # Build listing title
    title = f"{short_title} | {image_count} PNG Clipart | Watercolor | Transparent | Commercial Use"

    # Create listing
    print("  Creating draft listing...")
    listing_id = create_listing(shop_id, title, description, tags, 2.99)
    print(f"  Listing ID: {listing_id}")

    # Attach image
    attach_image_to_listing(shop_id, listing_id, image_id)
    print("  Preview image attached")

    # Save result
    listing["etsy_listing_id"] = listing_id
    listing["etsy_title"] = title
    listing["etsy_description"] = description
    listing["etsy_tags"] = tags
    with open("listing_today.json", "w") as f:
        json.dump(listing, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Draft listing: https://www.etsy.com/your/shops/me/tools/listings/{listing_id}")


if __name__ == "__main__":
    main()
