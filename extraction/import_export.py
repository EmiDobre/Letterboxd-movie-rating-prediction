"""Import one user's official Letterboxd CSV export without profile pagination."""
import argparse
import csv
import re
from pathlib import Path
from urllib.parse import urlparse

from extraction.crawl import dataset_user, now, username
from extraction.prepare import save_csv, split_rows


def read_export(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not {"Name", "Letterboxd URI"}.issubset(reader.fieldnames or []):
            raise ValueError(f"Lipsesc coloanele Name / Letterboxd URI: {path}")
        return list(reader)


def import_rows(user, ratings, watched):
    user = dataset_user(username(user))
    result = {}
    timestamp = now()
    # Watched first, then ratings, so evaluated rows take precedence.
    for entries, has_rating in [(watched, False), (ratings, True)]:
        for entry in entries:
            url = entry["Letterboxd URI"].strip()
            parsed = urlparse(url)
            match = re.fullmatch(r"/film/([A-Za-z0-9_-]+)/?", parsed.path)
            if parsed.hostname not in {"letterboxd.com", "www.letterboxd.com"} or not match:
                raise ValueError(f"URL de film nerecunoscut în export: {url}")
            rating = float(entry["Rating"]) if has_rating and entry.get("Rating") else None
            slug = match[1]
            result[slug] = {"user_id": user, "film_slug": slug, "film_id": "",
                            "title": entry["Name"], "rating": rating,
                            "film_url": f"https://letterboxd.com/film/{slug}/",
                            "source_url": "official_letterboxd_export",
                            "collected_at": timestamp}
    rows = list(result.values())
    split_rows(rows)  # Validate rating scale and uniqueness; no split is saved here.
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", required=True)
    parser.add_argument("--ratings", type=Path, required=True)
    parser.add_argument("--watched", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/imported"))
    args = parser.parse_args()
    ratings = read_export(args.ratings)
    if ratings and "Rating" not in ratings[0]:
        parser.error("Fișierul ratings trebuie să conțină coloana Rating")
    rows = import_rows(args.user, ratings, read_export(args.watched) if args.watched else [])
    if not rows:
        parser.error("Exportul nu conține filme")
    args.output.mkdir(parents=True, exist_ok=True)
    individual = args.output / "users" / f"{rows[0]['user_id']}.csv"
    save_csv(individual, rows, list(rows[0]))
    combined = []
    for path in sorted((args.output / "users").glob("*.csv")):
        with path.open(encoding="utf-8", newline="") as handle:
            combined.extend(csv.DictReader(handle))
    save_csv(args.output / "interactions.csv", combined, list(rows[0]))
    print(f"Importat {rows[0]['user_id']}: {len(rows)} filme, {sum(r['rating'] is not None for r in rows)} note.")
    print(f"Tabel comun: {args.output / 'interactions.csv'}")


if __name__ == "__main__":
    main()
