import json
import os
import shutil
from datetime import date, timedelta
from pathlib import Path

def main():
    today = str(date.today())
    
    # Check if listing was successfully uploaded to Etsy
    listing_path = Path("listing_today.json")
    if not listing_path.exists():
        print("No listing_today.json found, skipping cleanup.")
        return

    with open(listing_path, "r") as f:
        listing = json.load(f)

    etsy_listing_id = listing.get("etsy_listing_id")
    if not etsy_listing_id:
        print("No Etsy listing ID found, skipping cleanup.")
        return

    print(f"Etsy listing {etsy_listing_id} confirmed. Cleaning up images...")

    # Delete today's image folder from GitHub
    safe_name = listing.get("safe_name", "")
    image_dir = Path(f"images/{today}/{safe_name}")

    if image_dir.exists():
        shutil.rmtree(image_dir)
        print(f"  Deleted: {image_dir}")
    else:
        print(f"  Directory not found: {image_dir}")

    # Also clean up any folders older than 3 days
    images_root = Path("images")
    if images_root.exists():
        for date_folder in images_root.iterdir():
            if not date_folder.is_dir():
                continue
            try:
                folder_date = date.fromisoformat(date_folder.name)
                if (date.today() - folder_date).days > 3:
                    shutil.rmtree(date_folder)
                    print(f"  Deleted old folder: {date_folder}")
            except ValueError:
                pass

    print("\nCleanup complete.")


if __name__ == "__main__":
    main()
