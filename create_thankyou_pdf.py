import json
import os
import dropbox as dropbox_module
from datetime import date
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from PIL import Image as PILImage


def get_dropbox_client():
    return dropbox_module.Dropbox(
        oauth2_refresh_token=os.environ["DROPBOX_REFRESH_TOKEN"],
        app_key=os.environ["DROPBOX_APP_KEY"],
        app_secret=os.environ["DROPBOX_APP_SECRET"]
    )


def upload_pdf_to_dropbox(pdf_path: Path, dropbox_folder: str):
    """Upload Thank You PDF to Dropbox folder."""
    try:
        dbx = get_dropbox_client()
        dropbox_path = f"{dropbox_folder}/thankyou.pdf"
        with open(pdf_path, "rb") as f:
            dbx.files_upload(
                f.read(),
                dropbox_path,
                mode=dropbox_module.files.WriteMode.overwrite
            )
        print(f"  Thank You PDF uploaded to Dropbox")
    except Exception as e:
        print(f"  Warning: Could not upload PDF to Dropbox: {e}")


def create_thankyou_pdf(output_path: Path, preview_path: Path, 
                         short_title: str, image_count: int, dropbox_url: str):
    """Create a visual Thank You PDF with preview as background and download button."""

    # Get preview image dimensions
    preview_img = PILImage.open(preview_path)
    img_w, img_h = preview_img.size

    # PDF size matches preview (square)
    pdf_size = 6 * inch  # 6x6 inch PDF
    c = canvas.Canvas(str(output_path), pagesize=(pdf_size, pdf_size))

    # Draw preview image as background (slightly dimmed)
    c.saveState()
    c.drawImage(str(preview_path), 0, 0, width=pdf_size, height=pdf_size,
                preserveAspectRatio=False)
    # Semi-transparent white overlay to dim the background
    c.setFillColorRGB(1, 1, 1, alpha=0.45)
    c.rect(0, 0, pdf_size, pdf_size, fill=1, stroke=0)
    c.restoreState()

    # Pink/rose colored download button in center
    button_w = pdf_size * 0.75
    button_h = pdf_size * 0.35
    button_x = (pdf_size - button_w) / 2
    button_y = (pdf_size - button_h) / 2

    # Rounded rectangle for button (using bezier curves)
    c.setFillColorRGB(0.98, 0.80, 0.82)  # Soft pink like the example
    c.roundRect(button_x, button_y, button_w, button_h, 20, fill=1, stroke=0)

    # Button text
    c.setFillColorRGB(0.15, 0.10, 0.08)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(pdf_size / 2, button_y + button_h * 0.62, "CLICK HERE")
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(pdf_size / 2, button_y + button_h * 0.30, "TO DOWNLOAD")

    # Add hyperlink over button
    c.linkURL(dropbox_url,
              (button_x, button_y, button_x + button_w, button_y + button_h),
              relative=0)

    # Small info text below button
    c.setFillColorRGB(0.25, 0.20, 0.18)
    c.setFont("Helvetica", 9)
    c.drawCentredString(pdf_size / 2, button_y - 20,
                        f"{image_count} PNG Files • Transparent Background • Commercial Use")

    c.save()
    print(f"  Thank You PDF saved: {output_path}")
    return True


def main():
    today = str(date.today())

    with open("listing_today.json", "r") as f:
        listing = json.load(f)

    theme = listing["theme"]
    short_title = listing.get("short_title", theme[:60])
    image_count = listing["image_count"]
    dropbox_url = listing["dropbox_url"]
    safe_name = listing["safe_name"]

    image_dir = Path(f"images/{today}/{safe_name}")
    preview_path = image_dir / "preview.png"
    output_path = image_dir / "thankyou.pdf"

    if not preview_path.exists():
        print("Preview not found, skipping Thank You PDF.")
        return

    success = create_thankyou_pdf(
        output_path, preview_path, short_title, image_count, dropbox_url
    )

    if success:
        listing["thankyou_pdf_path"] = str(output_path)
        with open("listing_today.json", "w") as f:
            json.dump(listing, f, indent=2, ensure_ascii=False)

        # Upload PDF to Dropbox
        dropbox_folder = listing.get("dropbox_folder", "")
        if dropbox_folder:
            upload_pdf_to_dropbox(output_path, dropbox_folder)

        print(f"\nDone. Thank You PDF: {output_path}")


if __name__ == "__main__":
    main()
