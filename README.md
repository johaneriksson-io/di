# di

Download all images from a public Instagram post as JPEGs.

## Install

```sh
uv sync
```

## Usage

```sh
python3 di.py <instagram-url-or-shortcode> [output-dir]
```

**Examples:**

```sh
# Full URL — saves to current directory
python3 di.py https://www.instagram.com/p/ABC123/

# URL with query params
python3 di.py 'https://www.instagram.com/p/ABC123/?img_index=1'

# Bare shortcode
python3 di.py ABC123

# Save to a specific directory
python3 di.py https://www.instagram.com/p/ABC123/ ~/Downloads
```

Output files are named `{shortcode}_{n}.jpg` (e.g. `ABC123_1.jpg`, `ABC123_2.jpg`).

## Supported input

- Full post URLs: `https://www.instagram.com/p/{shortcode}/`
- Reel URLs: `https://www.instagram.com/reel/{shortcode}/`
- Bare shortcodes: `ABC123`

Carousel posts (multiple images) are fully supported — all slides are downloaded.

Video-only posts or slides are skipped.

## How it works

1. Extracts the shortcode from the URL
2. Hits Instagram's homepage to pick up a CSRF token and session cookies
3. Queries Instagram's GraphQL API (`POST /graphql/query/`) with `doc_id` `8845758582119845` (`PolarisPostActionLoadPostQueryQuery`) to get the post media data — no login required for public posts
4. For carousel posts (`XDTGraphSidecar`), iterates `edge_sidecar_to_children` to collect each slide; for single-image posts, takes the top-level media
5. Picks the highest-resolution variant from `display_resources` (by `config_width`), falling back to `display_url`
6. Downloads each image and converts to JPEG (quality 95) via Pillow, since Instagram often serves WebP

## Dependencies

- [requests](https://pypi.org/project/requests/) — HTTP client
- [Pillow](https://pypi.org/project/pillow/) — WebP-to-JPEG conversion

## Limitations

- Only works with **public** posts — private posts require authentication
- Instagram may rate-limit or block requests if used heavily
- The GraphQL `doc_id` is undocumented and may change without notice
