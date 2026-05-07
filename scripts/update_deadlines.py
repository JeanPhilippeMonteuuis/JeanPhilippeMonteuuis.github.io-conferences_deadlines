#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests", "ruamel.yaml"]
# ///
"""
Fetch conference deadline updates from upstream sources and update local conferences.yml.

Only updates existing entries (deadline, year, date, place, link, comment).
Tags and local-only conferences are never modified.
"""

import sys
from pathlib import Path

import requests
from ruamel.yaml import YAML

SOURCES = [
    "https://raw.githubusercontent.com/sec-deadlines/sec-deadlines.github.io/master/_data/conferences.yml",
    "https://raw.githubusercontent.com/abhshkdz/ai-deadlines/gh-pages/_data/conferences.yml",
]

LOCAL_FILE = Path("_data/conferences.yml")
UPDATABLE_FIELDS = ["year", "deadline", "date", "place", "link", "comment"]


def fetch_upstream() -> dict[str, dict]:
    """Fetch and merge conferences from all upstream sources, keyed by lowercase name."""
    merged: dict[str, dict] = {}
    yaml = YAML()
    for url in SOURCES:
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            confs = yaml.load(r.text)
            if not confs:
                continue
            for c in confs:
                name = c.get("name", "").strip().lower()
                year = c.get("year", 0)
                # Keep the most recent edition per conference name
                if name not in merged or year > merged[name].get("year", 0):
                    merged[name] = dict(c)
        except Exception as e:
            print(f"Warning: could not fetch {url}: {e}", file=sys.stderr)
    return merged


def update_conferences(local_path: Path) -> list[str]:
    """Update local conferences with upstream data. Returns list of change descriptions."""
    yaml = YAML()
    yaml.preserve_quotes = True

    with local_path.open() as f:
        local_data = yaml.load(f)

    upstream = fetch_upstream()
    changes: list[str] = []

    for conf in local_data:
        name = conf.get("name", "").strip()
        name_key = name.lower()

        if name_key not in upstream:
            continue

        up = upstream[name_key]
        up_year = up.get("year", 0)
        local_year = conf.get("year", 0)

        # Skip if upstream data is older
        if up_year < local_year:
            continue

        for field in UPDATABLE_FIELDS:
            if field not in up:
                continue
            new_val = up[field]
            old_val = conf.get(field)
            if new_val != old_val:
                changes.append(f"{name} {up_year}: {field} updated")
                conf[field] = new_val

    if changes:
        with local_path.open("w") as f:
            yaml.dump(local_data, f)

    return changes


if __name__ == "__main__":
    changes = update_conferences(LOCAL_FILE)
    if changes:
        print(f"Updated {len(changes)} field(s):")
        for c in changes:
            print(f"  • {c}")
    else:
        print("No updates found.")
        sys.exit(0)
