import json
import os
from datetime import date
from pathlib import Path
from PIL import Image
from reportlab.lib.pagesizes import inch
from reportlab.pdfgen import canvas

PAGE_SIZE = 12 * inch  # 12x12 inch per page


def create_pdf(image_dir: Path, output_path: Path, theme: str):
    """Create a PDF with one PNG per page from the given directory."""
    
    # Get all PNGs sorted
    images = sorted(image_dir.glob("*.png"))
    images = [img for img in images if img.name != "preview.png"]  # exclude preview later
    
    if not images:
        print(f"  No images found in {image_dir}")
        return False

    print(f"  Creating PDF with {len(images)} pages...")

    c = canvas.Canvas(str(output_path), pagesize=(PAGE_SIZE, PAGE_SIZE))

    for i, img_path in enumerate(images):
        print(f"  Adding page {i+1}/{len(images)}: {img_path.name}")
        
        # Draw image to fill the full page
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
    print(f"  PDF saved: {output_path}")
    return True


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

    # Count images
    images = sorted([f for f in image_dir.glob("*.png")])
    print(f"Found {len(images)} images for theme: {theme}")

    # Create PDF
    pdf_path = image_dir / f"{safe_name}.pdf"
    success = create_pdf(image_dir, pdf_path, theme)

    if success:
        print(f"\nDone. PDF created: {pdf_path}")
    else:
        print("\nFailed to create PDF.")


if __name__ == "__main__":
    main()
