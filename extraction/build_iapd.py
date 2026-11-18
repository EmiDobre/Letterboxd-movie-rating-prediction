"""Build the IAPD dataset from the official exports and optional film catalogs."""
import argparse
import csv
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile

import requests

from extraction.import_export import film_key, import_rows, read_export
from extraction.prepare import save_csv

FEATURES = (
    "genres", "directors", "cast", "runtime_minutes", "original_language",
    "languages", "countries", "description", "keywords", "production_type",
)
FILM_FIELDS = (
    "film_id", "film_url", "title", "release_year", "decade", *FEATURES,
    "tmdb_id", "metadata_sources", "tmdb_status",
)
INTERACTION_FIELDS = (
    "user_id", "film_id", "rating", "rating_date", "watched", "watched_added_date",
)


def title_key(title):
    return " ".join(unicodedata.normalize("NFKC", title).casefold().split())


def catalog_index(rows):
    index = defaultdict(list)
    for row in rows:
        index[title_key(row["title"]), str(row["release_year"])].append(row)
    return index


def unique_match(index, film):
    matches = index.get((title_key(film["title"]), str(film["release_year"])), [])
    return matches[0] if len(matches) == 1 else {}


def movielens_catalog(path):
    if not path:
        return {}
    with ZipFile(path) as archive:
        name, = [name for name in archive.namelist() if name.endswith("/movies.csv")]
        rows = list(csv.DictReader(archive.read(name).decode("utf-8-sig").splitlines()))
    catalog = []
    for row in rows:
        match = re.fullmatch(r"(.+) \((\d{4})\)", row["title"])
        if not match:
            continue
        title = re.sub(r"^(.+), (The|An|A)$", r"\2 \1", match[1])
        genres = row["genres"].split("|")
        if genres != ["(no genres listed)"]:
            catalog.append(dict(title=title, release_year=match[2], genres=genres))
    return catalog_index(catalog)


def letterboxd_catalog(catalog, pages):
    with catalog.open(encoding="utf-8-sig", newline="") as handle:
        by_slug = {row["film_slug"]: row for row in csv.DictReader(handle)}
    by_id = {}
    for path in sorted(pages.glob("*.json")):
        page = json.loads(path.read_text(encoding="utf-8"))
        match = re.search(r'id="url-field-film-\d+"[^>]*value="(https://boxd\.it/[A-Za-z0-9]+)"',
                          page["html"])
        if match:
            slug, _ = film_key(page["url"])
            if slug in by_slug:
                short_id, _ = film_key(match[1])
                by_id[short_id] = by_slug[slug]
    return by_slug | by_id


class TMDB:
    def __init__(self, token, cache):
        self.cache = cache
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"

    def get(self, endpoint, cache_file, **params):
        path = self.cache / cache_file
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        response = self.session.get(
            f"https://api.themoviedb.org/3/{endpoint}", params=params, timeout=15
        )
        response.raise_for_status()
        payload = response.json()
        path.parent.mkdir(parents=True, exist_ok=True)
        pending = path.with_suffix(".tmp")
        pending.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        pending.replace(path)
        return payload

    def lookup(self, film):
        candidates = []
        for kind, date_field, names in (
            ("movie", "release_date", ("title", "original_title")),
            ("tv", "first_air_date", ("name", "original_name")),
        ):
            params = {"query": film["title"], "include_adult": "true"}
            year_param = "primary_release_year" if kind == "movie" else "first_air_date_year"
            if film["release_year"]:
                params[year_param] = film["release_year"]
            cache_key = film["film_id"].replace(":", "_")
            for page in range(1, 6):
                result = self.get(f"search/{kind}", f"search_{kind}_{cache_key}_{page}.json",
                                  page=page, **params)
                for item in result["results"]:
                    year = item.get(date_field, "")[:4]
                    if year == str(film["release_year"]) and any(
                        title_key(item.get(name, "")) == title_key(film["title"]) for name in names
                    ):
                        candidate = (kind, item["id"])
                        if candidate not in candidates:
                            candidates.append(candidate)
                if page >= result["total_pages"]:
                    break
            else:
                return {}, "needs_review"
        if len(candidates) != 1:
            return {}, "ambiguous" if candidates else "unmatched"
        kind, tmdb_id = candidates[0]
        data = self.get(f"{kind}/{tmdb_id}", f"{kind}_{tmdb_id}.json",
                        append_to_response="credits,keywords")
        credits = data.get("credits", {})
        directors = [person["name"] for person in credits.get("crew", [])
                     if person.get("job") == "Director"]
        keywords = data.get("keywords", {})
        return {
            "tmdb_id": tmdb_id, "production_type": kind,
            "genres": [item["name"] for item in data.get("genres", [])],
            "directors": list(dict.fromkeys(directors)),
            "cast": [item["name"] for item in credits.get("cast", [])[:8]],
            "runtime_minutes": data.get("runtime") if kind == "movie" else None,
            "original_language": data.get("original_language"),
            "languages": [item["iso_639_1"] for item in data.get("spoken_languages", [])],
            "countries": [item["iso_3166_1"] for item in data.get("production_countries", [])],
            "description": data.get("overview"),
            "keywords": [item["name"] for item in keywords.get("keywords", keywords.get("results", []))],
        }, "matched"


def build(exports, output, local, movielens, tmdb, user_names):
    users = sorted(exports.glob("*/ratings.csv"))
    if not users:
        raise ValueError(f"No ratings exports in {exports}")
    interactions, films = [], {}
    for ratings in users:
        folder = ratings.parent.name
        user = user_names.get(folder, folder)
        imported = import_rows(user, read_export(ratings), read_export(ratings.with_name("watched.csv")))
        for row in imported:
            if row["rating"] is None:
                continue
            film_id = row["film_slug"]
            year = int(row["release_year"]) if row["release_year"] else None
            films.setdefault(film_id, dict(film_id=film_id, film_url=row["film_url"],
                                           title=row["title"], release_year=year,
                                           decade=year // 10 * 10 if year else None))
            interactions.append({field: row[field] for field in INTERACTION_FIELDS if field != "film_id"}
                                | {"film_id": film_id})

    tmdb_available = tmdb is not None
    for film in films.values():
        sources = []
        partial = local.get(film["film_id"])
        if partial:
            for field in FEATURES:
                value = partial.get(field)
                if value:
                    film[field] = json.loads(value) if field in {
                        "genres", "directors", "cast", "countries", "languages"
                    } else value
            sources.append("letterboxd_local_verified_id")
        extra = unique_match(movielens, film)
        if extra:
            if not film.get("genres"):
                film["genres"] = extra["genres"]
                sources.append("movielens_title_year")
        status = "not_requested" if tmdb is None else "deferred"
        if tmdb_available:
            try:
                metadata, status = tmdb.lookup(film)
            except requests.RequestException as exc:
                code = exc.response.status_code if exc.response is not None else "network"
                print(f"TMDB stopped after {code}; rerun to resume from cache.")
                tmdb_available = False
                metadata, status = {}, f"error_{code}"
            if metadata:
                film.update({field: value for field, value in metadata.items() if value})
                sources.append("tmdb_title_year")
        film.update(metadata_sources=sources, tmdb_status=status)

    feature_columns = [field for field in FILM_FIELDS if field != "film_id"]
    merged = [row | {field: films[row["film_id"]].get(field) for field in feature_columns}
              for row in interactions]
    rated = [row for row in merged if row["rating"] is not None]
    save_csv(output / "interactions.csv", interactions, INTERACTION_FIELDS)
    save_csv(output / "films.csv", films.values(), FILM_FIELDS)
    save_csv(output / "dataset_with_features.csv", merged, INTERACTION_FIELDS + tuple(feature_columns))
    save_csv(output / "rated_dataset_with_features.csv", rated, INTERACTION_FIELDS + tuple(feature_columns))
    save_csv(output / "metadata_to_review.csv",
             (film for film in films.values() if film["tmdb_status"] != "matched"), FILM_FIELDS)
    counts = Counter(row["film_id"] for row in rated)
    summary = {
        "interactions": len(interactions), "unique_films": len(films), "rated": len(rated),
        "unrated": len(interactions) - len(rated), "unique_rated_films": len(counts),
        "mean_rating": sum(row["rating"] for row in rated) / len(rated) if rated else None,
        "rating_distribution": dict(sorted(Counter(row["rating"] for row in rated).items())),
        "rated_by_user": dict(Counter(row["user_id"] for row in rated)),
        "watched_by_user": dict(Counter(row["user_id"] for row in interactions if row["watched"])),
        "film_overlap": dict(sorted(Counter(counts.values()).items())),
        "metadata_coverage": {field: sum(bool(film.get(field)) for film in films.values())
                              for field in FEATURES},
        "metadata_sources": dict(Counter(source for film in films.values()
                                         for source in film["metadata_sources"])),
        "tmdb_status": dict(Counter(film["tmdb_status"] for film in films.values())),
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exports", type=Path, default=Path("data/raw/letterboxd_exports"))
    parser.add_argument("--local-catalog", type=Path, default=Path("data/partial/films.csv"))
    parser.add_argument("--local-pages", type=Path, default=Path("data/raw/film_pages"))
    parser.add_argument("--movielens", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/iapd"))
    parser.add_argument("--tmdb", action="store_true")
    args = parser.parse_args()
    token = os.environ.get("TMDB_READ_TOKEN")
    if args.tmdb and not token:
        parser.error("--tmdb requires TMDB_READ_TOKEN")
    tmdb = TMDB(token, args.exports / "tmdb_cache") if args.tmdb else None
    local = letterboxd_catalog(args.local_catalog, args.local_pages)
    names_path = args.exports / "user_names.json"
    user_names = json.loads(names_path.read_text(encoding="utf-8-sig")) if names_path.exists() else {}
    build(args.exports, args.output, local, movielens_catalog(args.movielens), tmdb, user_names)


if __name__ == "__main__":
    main()
