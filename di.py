#!/usr/bin/env python3
"""Download all images from an Instagram post."""

import json
import re
import sys
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.instagram.com/",
}

GQL_DOC_ID = "8845758582119845"  # PolarisPostActionLoadPostQueryQuery


def extract_shortcode(url: str) -> str:
    """Extract the shortcode from an Instagram URL."""
    match = re.search(r"instagram\.com/(?:p|reel)/([A-Za-z0-9_-]+)", url)
    if match:
        return match.group(1)
    if re.match(r"^[A-Za-z0-9_-]+$", url):
        return url
    raise ValueError(f"Could not extract shortcode from: {url}")


def fetch_post_data(shortcode: str) -> dict:
    """Fetch post data via Instagram's GraphQL API."""
    session = requests.Session()
    session.headers.update(HEADERS)
    session.headers.update({
        "X-IG-App-ID": "936619743392459",
        "X-Requested-With": "XMLHttpRequest",
    })

    # Get cookies/csrf
    session.get("https://www.instagram.com/", timeout=15)
    csrf = session.cookies.get("csrftoken", "")
    if csrf:
        session.headers["X-CSRFToken"] = csrf

    variables = json.dumps({
        "shortcode": shortcode,
        "fetch_tagged_user_count": None,
        "hoisted_comment_id": None,
        "hoisted_reply_id": None,
    })
    resp = session.post(
        "https://www.instagram.com/graphql/query/",
        data={"av": "0", "doc_id": GQL_DOC_ID, "variables": variables},
        timeout=15,
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"GraphQL request failed (HTTP {resp.status_code}). "
            "The post may be private or Instagram may be blocking requests."
        )

    data = resp.json()
    media = data.get("data", {}).get("xdt_shortcode_media")
    if not media:
        raise RuntimeError(
            "Could not fetch post data. The post may be private or deleted."
        )
    return media


def extract_image_urls(media: dict) -> list[str]:
    """Extract all image URLs from the GraphQL media data."""
    urls = []
    typename = media.get("__typename", "")

    if "Sidecar" in typename or "edge_sidecar_to_children" in media:
        edges = media.get("edge_sidecar_to_children", {}).get("edges", [])
        for edge in edges:
            node = edge.get("node", {})
            if node.get("is_video"):
                continue
            url = _best_display_url(node)
            if url:
                urls.append(url)
    else:
        if not media.get("is_video"):
            url = _best_display_url(media)
            if url:
                urls.append(url)

    return urls


def _best_display_url(node: dict) -> str | None:
    """Pick the highest-resolution image URL from a media node."""
    resources = node.get("display_resources", [])
    if resources:
        best = max(resources, key=lambda r: r.get("config_width", 0))
        return best.get("src")
    return node.get("display_url")


def download_images(image_urls: list[str], output_dir: Path, shortcode: str) -> list[Path]:
    """Download images to the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded = []

    for i, url in enumerate(image_urls, 1):
        print(f"  [{i}/{len(image_urls)}] Downloading...")
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()

        filename = f"{shortcode}_{i}.jpg"
        filepath = output_dir / filename
        img = Image.open(BytesIO(resp.content))
        img.convert("RGB").save(filepath, "JPEG", quality=95)

        downloaded.append(filepath)

    return downloaded


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <instagram-url-or-shortcode> [output-dir]")
        print(f"Example: {sys.argv[0]} https://www.instagram.com/p/ABC123/")
        sys.exit(1)

    url = sys.argv[1]
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")

    shortcode = extract_shortcode(url)
    print(f"Shortcode: {shortcode}")

    print("Fetching post data...")
    media = fetch_post_data(shortcode)

    image_urls = extract_image_urls(media)
    if not image_urls:
        print("No images found. The post may be private or contain only video.")
        sys.exit(1)

    print(f"Found {len(image_urls)} image(s)")
    downloaded = download_images(image_urls, output_dir, shortcode)

    print(f"\nDone! Downloaded {len(downloaded)} image(s):")
    for path in downloaded:
        print(f"  {path}")


if __name__ == "__main__":
    main()
