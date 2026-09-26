#!/usr/bin/env python3
"""Build Blender extension index.json (and optional index.html) for GitHub Pages."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib  # type: ignore


OPTIONAL_MANIFEST_KEYS = (
    "website",
    "tags",
    "copyright",
    "blender_version_max",
    "platforms",
)


def load_manifest(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def build_entry(manifest: dict, zip_path: Path, archive_url: str) -> dict:
    data = zip_path.read_bytes()
    entry = {
        "schema_version": manifest["schema_version"],
        "id": manifest["id"],
        "name": manifest["name"],
        "tagline": manifest["tagline"],
        "version": manifest["version"],
        "type": manifest["type"],
        "maintainer": manifest["maintainer"],
        "license": list(manifest["license"]),
        "blender_version_min": manifest["blender_version_min"],
        "archive_url": archive_url,
        "archive_size": len(data),
        "archive_hash": "sha256:" + hashlib.sha256(data).hexdigest(),
    }
    for key in OPTIONAL_MANIFEST_KEYS:
        if key in manifest:
            entry[key] = manifest[key]
    return entry


def write_html(path: Path, entry: dict, repository_url: str) -> None:
    drop_url = (
        f"{entry['archive_url']}"
        f"?repository={repository_url}"
        f"&blender_version_min={entry['blender_version_min']}"
    )
    path.write_text(
        f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{entry['name']}</title>
</head>
<body>
  <h1>{entry['name']}</h1>
  <p>{entry['tagline']} (v{entry['version']})</p>
  <p>Blender {entry['blender_version_min']}+ / Extension</p>
  <p>
    <a href="{drop_url}">Download zip (drag &amp; drop into Blender)</a>
  </p>
  <p>
    Remote Repository URL:<br>
    <code>{repository_url}</code>
  </p>
</body>
</html>
""",
        encoding="utf-8",
    )


def main() -> int:
    if len(sys.argv) < 4:
        print(
            "Usage: generate_extension_index.py <zip> <archive_url> <out_dir> [repository_url]",
            file=sys.stderr,
        )
        return 1

    zip_path = Path(sys.argv[1])
    archive_url = sys.argv[2]
    out_dir = Path(sys.argv[3])
    repository_url = sys.argv[4] if len(sys.argv) > 4 else ""

    root = Path(__file__).resolve().parents[1]
    manifest = load_manifest(root / "blender_manifest.toml")
    entry = build_entry(manifest, zip_path, archive_url)

    out_dir.mkdir(parents=True, exist_ok=True)
    index_path = out_dir / "index.json"
    index_path.write_text(
        json.dumps({"version": "v1", "blocklist": [], "data": [entry]}, indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )

    if repository_url:
        write_html(out_dir / "index.html", entry, repository_url)

    print(f"Wrote {index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
