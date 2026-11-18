"""Collect film metadata independently of incomplete profile crawling."""
import argparse
import csv
import json
from pathlib import Path

import requests

from extraction.crawl import BASE, Client, now, parse_film, write_json
from extraction.prepare import save_csv

FEATURES = ["release_year", "runtime_minutes", "genres", "directors", "cast",
            "countries", "languages", "studios", "description"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/partial/interactions.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/partial"))
    parser.add_argument("--cache", type=Path, default=Path("data/raw/film_pages"))
    args = parser.parse_args()
    with args.input.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    slugs = sorted({r["film_slug"] for r in rows})
    metadata_path = args.output / "film_metadata.json"
    films = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
    films = {s: f for s, f in films.items() if s in slugs}
    report = {"started_at": now(), "expected_films": len(slugs), "errors": [], "complete": False}
    try:
        client = Client(args.cache)
        for index, slug in enumerate(slugs, 1):
            if slug in films:
                continue
            try:
                page = client.get(f"{BASE}/film/{slug}/")
                films[slug] = parse_film(page["html"], slug, page["url"], page["collected_at"])
                write_json(metadata_path, films)
                print(f"Metadate {index}/{len(slugs)}: {slug}", flush=True)
            except ValueError as error:
                report["errors"].append({"film_slug": slug, "error": str(error)})
            except requests.HTTPError as error:
                if error.response is not None and error.response.status_code == 404:
                    report["errors"].append({"film_slug": slug, "error": str(error)})
                    continue
                raise
    except (requests.RequestException, RuntimeError) as error:
        report["errors"].append({"error": str(error)})
        print(str(error), flush=True)
    finally:
        args.output.mkdir(parents=True, exist_ok=True)
        write_json(metadata_path, films)
        report.update(finished_at=now(), collected_films=len(films), complete=len(films) == len(slugs),
                      missing_films=sorted(set(slugs) - set(films)))
        report["missing_fields"] = {key: sum(film.get(key) in (None, "", []) for film in films.values())
                                    for key in FEATURES}
        write_json(args.output / "enrichment_report.json", report)
        film_rows = list(films.values())
        save_csv(args.output / "films.csv", film_rows,
                 list(film_rows[0]) if film_rows else ["film_slug", "title"] + FEATURES)
        merged = []
        for row in rows:
            film = films.get(row["film_slug"], {})
            merged.append({"user_id": row["user_id"], "film_slug": row["film_slug"],
                           "title": film.get("title", row["title"]),
                           "rating": float(row["rating"]) if row["rating"] else None,
                           **{key: film.get(key) for key in FEATURES},
                           "metadata_status": "collected" if film else "missing",
                           "film_url": row["film_url"]})
        if merged:
            save_csv(args.output / "dataset_with_features.csv", merged, list(merged[0]))
            rated = [r for r in merged if r["rating"] is not None]
            save_csv(args.output / "rated_dataset_with_features.csv", rated, list(merged[0]))
        print(f"Salvat dataset: {len(merged)} randuri; metadate pentru {len(films)}/{len(slugs)} filme.")
    if not report["complete"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
