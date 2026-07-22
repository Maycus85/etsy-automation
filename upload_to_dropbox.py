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


def upload_pngs_to_dropbox(image_dir: Path, dropbox_folder: str) -> str:
    """Upload all PNGs to a Dropbox folder and return shared folder link."""
    dbx = get_dropbox_client()

    images = sorted([f for f in image_dir.glob("*.png") if f.name != "preview.png"])
    print(f"  Uploading {len(images)} PNG files to Dropbox...")

    for i, img_path in enumerate(images):
        dropbox_path = f"{dropbox_folder}/{i+1:02d}.png"
        with open(img_path, "rb") as f:
            dbx.files_upload(
                f.read(),
                dropbox_path,
                mode=dropbox.files.WriteMode.overwrite
            )
        print(f"  [{i+1}/{len(images)}] Uploaded: {img_path.name}")

    # Create shared link for the folder
    try:
        link = dbx.sharing_create_shared_link_with_settings(dropbox_folder)
        url = link.url
    except dropbox.exceptions.ApiError:
        links = dbx.sharing_list_shared_links(dropbox_folder).links
        url = links[0].url

    print(f"  Dropbox folder link: {url}")
    return url


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
    print(f"Found {len(images)} images for theme: {theme}")

    # Upload PNGs to Dropbox folder
    dropbox_folder = f"/etsy-automation/{today}/{safe_name}"
    download_url = upload_pngs_to_dropbox(image_dir, dropbox_folder)

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

    print(f"\nDone. {len(images)} PNGs uploaded to Dropbox.")
    print(f"Folder link: {download_url}")


if __name__ == "__main__":
    main()
