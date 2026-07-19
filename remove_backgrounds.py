import json
from datetime import date
from pathlib import Path
from rembg import remove
from PIL import Image

def process_image(img_path: Path) -> bool:
    """Remove background from image and save as transparent PNG."""
    try:
        with open(img_path, "rb") as f:
            input_data = f.read()

        output_data = remove(input_data)

        # Save back as PNG with transparency
        img_path.write_bytes(output_data)
        return True
    except Exception as e:
        print(f"  Error processing {img_path.name}: {e}")
        return False


def main():
    today = str(date.today())

    with open("themes_today.json", "r") as f:
        data = json.load(f)

    theme = data["theme"]
    safe_name = theme.replace(" ", "_").replace("/", "_")[:50]
    image_dir = Path(f"images/{today}/{safe_name}")

    if not image_dir.exists():
        print(f"Image directory not found: {image_dir}")
        return

    images = sorted([f for f in image_dir.glob("*.png") if f.name != "preview.png"])
    print(f"Removing backgrounds from {len(images)} images...")

    success_count = 0
    for i, img_path in enumerate(images):
        success = process_image(img_path)
        status = "OK" if success else "FAILED"
        print(f"  [{i+1}/{len(images)}] {status}: {img_path.name}")
        if success:
            success_count += 1

    print(f"\nDone. {success_count}/{len(images)} backgrounds removed.")


if __name__ == "__main__":
    main()
