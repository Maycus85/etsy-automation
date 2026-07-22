import json
import os
from datetime import date
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib import colors

def create_thankyou_pdf(output_path: Path, theme: str, short_title: str, 
                         image_count: int, dropbox_url: str):
    """Create a beautiful Thank You PDF with download link."""
    
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    # Background color - warm cream
    c.setFillColorRGB(1.0, 0.99, 0.97)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # Top accent bar
    c.setFillColorRGB(0.77, 0.62, 0.47)
    c.rect(0, height - 8, width, 8, fill=1, stroke=0)

    # Bottom accent bar
    c.rect(0, 0, width, 8, fill=1, stroke=0)

    # Shop name
    c.setFillColorRGB(0.77, 0.62, 0.47)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width / 2, height - 70, "The Feeling We Share")

    # Tagline
    c.setFillColorRGB(0.47, 0.39, 0.35)
    c.setFont("Helvetica-Oblique", 13)
    c.drawCentredString(width / 2, height - 95, "Where every feeling finds its perfect image")

    # Divider line
    c.setStrokeColorRGB(0.77, 0.62, 0.47)
    c.setLineWidth(1.5)
    c.line(2*cm, height - 110, width - 2*cm, height - 110)

    # Thank you heading
    c.setFillColorRGB(0.22, 0.18, 0.16)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, height - 155, "Thank You for Your Purchase!")

    # Thank you text
    c.setFont("Helvetica", 12)
    c.setFillColorRGB(0.35, 0.28, 0.25)
    thank_you_text = [
        "We are so happy you chose our artwork for your creative projects.",
        "Your support means the world to us and helps us create",
        "more beautiful designs every day. ✨"
    ]
    y = height - 185
    for line in thank_you_text:
        c.drawCentredString(width / 2, y, line)
        y -= 20

    # What you purchased box
    c.setFillColorRGB(0.95, 0.92, 0.88)
    c.roundRect(2*cm, height - 310, width - 4*cm, 90, 10, fill=1, stroke=0)

    c.setFillColorRGB(0.22, 0.18, 0.16)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(width / 2, height - 245, "Your Purchase:")

    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, height - 265, f"{short_title} — Watercolor Clipart Bundle")
    c.drawCentredString(width / 2, height - 283, f"{image_count} PNG Files | Transparent Background | 300 DPI | Commercial Use")

    # Download section
    c.setFillColorRGB(0.22, 0.18, 0.16)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 345, "📥 Download Your Files")

    c.setFont("Helvetica", 12)
    c.setFillColorRGB(0.35, 0.28, 0.25)
    download_instructions = [
        "Click the link below to download your PNG files:",
        "",
    ]
    y = height - 370
    for line in download_instructions:
        c.drawCentredString(width / 2, y, line)
        y -= 18

    # Download button style box
    c.setFillColorRGB(0.77, 0.62, 0.47)
    c.roundRect(3*cm, height - 430, width - 6*cm, 40, 8, fill=1, stroke=0)

    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, height - 406, "CLICK HERE TO DOWNLOAD YOUR FILES")

    # Actual URL (clickable)
    c.setFillColorRGB(0.77, 0.62, 0.47)
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, height - 448, dropbox_url)

    # Add hyperlink
    c.linkURL(dropbox_url, 
              (3*cm, height - 435, width - 3*cm, height - 395),
              relative=0)

    # How to use section
    c.setFillColorRGB(0.22, 0.18, 0.16)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 490, "How to Use Your Files")

    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0.35, 0.28, 0.25)
    instructions = [
        "1. Click the download link above",
        "2. Save the PNG files to your computer",
        "3. Open in Photoshop, Canva, Cricut, Procreate or any design tool",
        "4. All files have transparent backgrounds — ready to use!",
    ]
    y = height - 515
    for line in instructions:
        c.drawCentredString(width / 2, y, line)
        y -= 18

    # Terms reminder
    c.setFillColorRGB(0.95, 0.92, 0.88)
    c.roundRect(2*cm, 80, width - 4*cm, 70, 10, fill=1, stroke=0)

    c.setFillColorRGB(0.47, 0.39, 0.35)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(width / 2, 133, "Terms of Use")
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, 115, "✓ Personal & Commercial Use Allowed   ✓ Modify as needed")
    c.drawCentredString(width / 2, 98, "✗ Do not resell original files   ✗ Do not claim as your own artwork")

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
    output_path = image_dir / "thankyou.pdf"

    success = create_thankyou_pdf(output_path, theme, short_title, image_count, dropbox_url)

    if success:
        listing["thankyou_pdf_path"] = str(output_path)
        with open("listing_today.json", "w") as f:
            json.dump(listing, f, indent=2, ensure_ascii=False)
        print(f"\nDone. Thank You PDF: {output_path}")


if __name__ == "__main__":
    main()
