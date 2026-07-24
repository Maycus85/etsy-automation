import json
import os
import dropbox
from datetime import date
from pathlib import Path


def get_dropbox_client():
    return dropbox.Dropbox(
        oauth2_refresh_token=os.environ["DROPBOX_REFRESH_TOKEN"],
        app_key=os.environ["DROPBOX_APP_KEY"],
        app_secret=os.environ["DROPBOX_APP_SECRET"]
    )


def upload_file(dbx, local_path: Path, dropbox_path: str):
    """Upload a single file to Dropbox."""
    with open(local_path, "rb") as f:
        dbx.files_upload(
            f.read(),
            dropbox_path,
            mode=dropbox.files.WriteMode.overwrite
        )


def get_shared_link(dbx, dropbox_path: str) -> str:
    """Get or create shared link for a Dropbox path."""
    try:
        link = dbx.sharing_create_shared_link_with_settings(dropbox_path)
        return link.url
    except dropbox.exceptions.ApiError:
        links = dbx.sharing_list_shared_links(dropbox_path).links
        return links[0].url


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
    preview_path = image_dir / "preview.png"

    print(f"Found {len(images)} images for theme: {theme}")

    dbx = get_dropbox_client()
    dropbox_folder = f"/etsy-automation/{today}/{safe_name}"

    # Upload numbered PNGs
    print(f"  Uploading {len(images)} PNG files...")
    for i, img_path in enumerate(images):
        dropbox_path = f"{dropbox_folder}/{i+1:02d}.png"
        upload_file(dbx, img_path, dropbox_path)
        print(f"  [{i+1}/{len(images)}] Uploaded: {img_path.name}")

    # Upload preview image
    if preview_path.exists():
        print(f"  Uploading preview image...")
        upload_file(dbx, preview_path, f"{dropbox_folder}/preview.png")
        print(f"  Preview uploaded to Dropbox")

    # Upload Thank You PDF
    thankyou_path = image_dir / "thankyou.pdf"
    if thankyou_path.exists():
        print(f"  Uploading Thank You PDF...")
        upload_file(dbx, thankyou_path, f"{dropbox_folder}/thankyou.pdf")
        print(f"  Thank You PDF uploaded to Dropbox")

    # Get shared folder link
    download_url = get_shared_link(dbx, dropbox_folder)
    print(f"  Dropbox folder link: {download_url}")

    # Save result
    result = {
        "date": today,
        "theme": theme,
        "safe_name": safe_name,
        "image_count": len(images),
        "dropbox_url": download_url,
        "dropbox_folder": dropbox_folder
    }

    with open("listing_today.json", "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nDone. {len(images)} PNGs + preview uploaded to Dropbox.")
    print(f"Folder link: {download_url}")


if __name__ == "__main__":
    main()
