import json
import os
import dropbox
from datetime import date
from pathlib import Path
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from PIL import Image

PAGE_SIZE = 12 * inch  # 12x12 inch per page


def create_pdf(image_dir: Path, output_path: Path) -> bool:
    """Create a PDF with one PNG per page."""
    images = sorted([f for f in image_dir.glob("*.png")])

    if not images:
        print(f"  No images found in {image_dir}")
        return False

    print(f"  Creating PDF with {len(images)} pages...")
    c = canvas.Canvas(str(output_path), pagesize=(PAGE_SIZE, PAGE_SIZE))

    for i, img_path in enumerate(images):
        print(f"  Adding page {i+1}/{len(images)}: {img_path.name}")
        c.drawImage(
            str(img_path),
            0, 0,
            width=PAGE_SIZE,
            height=PAGE_SIZE,
            preserveAspectRatio=True,
            anchor='c'
        )
        c.showPage()

    c.save()
    print(f"  PDF saved locally: {output_path}")
    return True


def upload_to_dropbox(local_path: Path, dropbox_path: str) -> str:
    """Upload PDF to Dropbox and return a shared link."""
    dbx = dropbox.Dropbox(os.environ["DROPBOX_ACCESS_TOKEN"])

    print(f"  Uploading to Dropbox: {dropbox_path}")
    with open(local_path, "rb") as f:
        dbx.files_upload(
            f.read(),
            dropbox_path,
            mode=dropbox.files.WriteMode.overwrite
        )

    # Create shared link
    try:
        link = dbx.sharing_create_shared_link_with_settings(dropbox_path)
        url = link.url.replace("?dl=0", "?dl=1")  # Force direct download
    except dropbox.exceptions.ApiError:
        # Link already exists, get existing one
        links = dbx.sharing_list_shared_links(dropbox_path).links
        url = links[0].url.replace("?dl=0", "?dl=1")

    print(f"  Dropbox link: {url}")
    return url


def main():
    today = str(date.today())

    # Load today's theme
    with open("themes_today.json", "r") as f:
        data = json.load(f)

    theme = data["theme"]
    safe_name = theme.replace(" ", "_").replace("/", "_")[:50]
    image_dir = Path(f"images/{today}/{safe_name}")

    if not image_dir.exists():
        print(f"Image directory not found: {image_dir}")
        return

    images = sorted([f for f in image_dir.glob("*.png")])
    print(f"Found {len(images)} images for theme: {theme}")

    # Create PDF
    pdf_path = image_dir / f"{safe_name}.pdf"
    success = create_pdf(image_dir, pdf_path)

    if not success:
        print("Failed to create PDF.")
        return

    # Upload to Dropbox
    dropbox_path = f"/etsy-automation/{today}/{safe_name}.pdf"
    download_url = upload_to_dropbox(pdf_path, dropbox_path)

    # Save download URL for next steps
    result = {
        "date": today,
        "theme": theme,
        "safe_name": safe_name,
        "image_count": len(images),
        "dropbox_url": download_url,
        "pdf_path": str(pdf_path)
    }

    with open("listing_today.json", "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Delete local PDF to save space
    pdf_path.unlink()
    print(f"  Local PDF deleted after upload.")

    print(f"\nDone. Download URL saved to listing_today.json")
    print(f"URL: {download_url}")


if __name__ == "__main__":
    main()
