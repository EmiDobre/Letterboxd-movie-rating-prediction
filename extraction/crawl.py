"""Collect public watched-film lists and film metadata from Letterboxd."""
import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

BASE = "https://letterboxd.com"
AGENT = "LetterboxdStudentResearch/1.0"
USER_ALIASES = {"taciinplm": "daria"}


def dataset_user(user):
    """Keep the public account URL separate from the project identifier."""
    return USER_ALIASES.get(user, user)


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def username(value):
    value = value.strip()
    if value.startswith(("http://", "https://")):
        parsed = urlparse(value)
        if parsed.hostname not in {"letterboxd.com", "www.letterboxd.com"}:
            raise ValueError("Profilul trebuie sa fie pe letterboxd.com")
        value = parsed.path.strip("/")
    if not re.fullmatch(r"[A-Za-z0-9_]{1,40}", value):
        raise ValueError(f"Username invalid: {value!r}")
    return value.lower()


class Client:
    def __init__(self, cache, delay=2.0, refresh=False):
        self.cache = cache
        cache.mkdir(parents=True, exist_ok=True)
        self.delay = max(2.0, delay)
        self.refresh = refresh
        self.session = requests.Session()
        self.session.headers["User-Agent"] = AGENT
        self.last_request = 0.0
        response = self._request(BASE + "/robots.txt")
        self.robots = RobotFileParser()
        self.robots.parse(response.text.splitlines())
        (cache / "robots.txt").write_text(response.text, encoding="utf-8")

    def _request(self, url):
        for attempt in range(3):
            time.sleep(max(0, self.delay - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            response = self.session.get(url, timeout=40, allow_redirects=False)
            if response.status_code in {403, 429}:
                raise RuntimeError(f"Acces oprit (HTTP {response.status_code}): {url}. Reincearca mai tarziu sau foloseste exportul oficial.")
            if response.status_code >= 500 and attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue
            response.raise_for_status()
            return response

    def get(self, url, hops=0):
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "letterboxd.com":
            raise ValueError(f"URL extern refuzat: {url}")
        if not self.robots.can_fetch(AGENT, url):
            raise RuntimeError(f"robots.txt nu permite: {url}")
        path = self.cache / (hashlib.sha256(url.encode()).hexdigest() + ".json")
        if path.exists() and not self.refresh:
            return json.loads(path.read_text(encoding="utf-8"))
        response = self._request(url)
        if response.is_redirect:
            if hops >= 5:
                raise RuntimeError("Prea multe redirectionari")
            return self.get(urljoin(url, response.headers["Location"]), hops + 1)
        if "html" not in response.headers.get("Content-Type", ""):
            raise RuntimeError(f"Raspunsul nu este HTML: {url}")
        result = {"url": url, "collected_at": now(), "html": response.text}
        write_json(path, result)
        return result


def parse_profile(html, user, source_url, collected_at):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for card in soup.select("li.griditem, li.poster-container"):
        poster = card.select_one("[data-item-slug], [data-film-slug]")
        if poster is None:
            continue
        slug = poster.get("data-item-slug") or poster.get("data-film-slug")
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", slug):
            raise ValueError(f"Film slug invalid: {slug}")
        rating_node = card.select_one(".rating")
        rating = None
        if rating_node:
            match = re.search(r"\brated-(\d+)\b", " ".join(rating_node.get("class", [])))
            if not match or not 1 <= int(match[1]) <= 10:
                raise ValueError(f"Rating nerecunoscut pentru {slug}")
            rating = int(match[1]) / 2
        img = poster.select_one("img")
        uid = card.select_one("[data-item-uid]")
        rows.append({"user_id": dataset_user(user), "film_slug": slug,
                     "film_id": uid.get("data-item-uid", "") if uid else poster.get("data-film-id", ""),
                     "title": img.get("alt", "") if img else poster.get("data-item-name", ""),
                     "rating": rating, "film_url": f"{BASE}/film/{slug}/",
                     "source_url": source_url, "collected_at": collected_at})
    if not rows:
    # An empty profile requires a recognized empty-state marker.
        raise ValueError(f"Nu am gasit filme la {source_url}: profil gol/privat sau HTML schimbat.")
    next_link = soup.select_one("a.next[href], a.paginate-next[href]")
    return rows, urljoin(BASE, next_link["href"]) if next_link else None


def as_list(value):
    return value if isinstance(value, list) else ([] if value is None else [value])


def names(value):
    return [item.get("name", "") if isinstance(item, dict) else item for item in as_list(value)]


def parse_film(html, slug, source_url, collected_at):
    soup = BeautifulSoup(html, "html.parser")
    movie = None
    for script in soup.select('script[type="application/ld+json"]'):
        text = re.sub(r"/\*.*?\*/", "", script.get_text(), flags=re.S).strip()
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            continue
        candidates = as_list(value)
        if isinstance(value, dict):
            candidates += as_list(value.get("@graph"))
        for candidate in candidates:
            if isinstance(candidate, dict) and "Movie" in as_list(candidate.get("@type")):
                movie = candidate
                break
    if not movie or not movie.get("name"):
        raise ValueError(f"Metadatele Movie lipsesc: {source_url}")
    duration = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?", movie.get("duration", ""))
    minutes = (int(duration[1] or 0) * 60 + int(duration[2] or 0)) if duration else None
    date = str(movie.get("dateCreated") or movie.get("datePublished") or "")
    aggregate = movie.get("aggregateRating") or {}
    return {"film_slug": slug, "title": movie["name"],
            "release_year": int(date[:4]) if re.match(r"^\d{4}", date) else None,
            "runtime_minutes": minutes, "genres": names(movie.get("genre")),
            "directors": names(movie.get("director")), "cast": names(movie.get("actor")),
            "countries": names(movie.get("countryOfOrigin")),
            "languages": names(movie.get("inLanguage")),
            "studios": names(movie.get("productionCompany")),
            "description": movie.get("description", ""),
            "global_rating": aggregate.get("ratingValue"),
            "global_rating_count": aggregate.get("ratingCount"),
            "source_url": source_url, "collected_at": collected_at}


def collect_user(client, user, max_pages, checkpoint=None):
    url = f"{BASE}/{user}/films/"
    visited, rows = set(), {}
    pages = 0
    while url:
        if url in visited:
            raise ValueError("Bucla de paginare detectata")
        if urlparse(url).path != f"/{user}/films/" and not re.fullmatch(
                rf"/{re.escape(user)}/films/page/\d+/", urlparse(url).path):
            raise ValueError(f"Paginare neasteptata: {url}")
        visited.add(url)
        page = client.get(url)
        items, url = parse_profile(page["html"], user, page["url"], page["collected_at"])
        for item in items:
            rows[item["film_slug"]] = item
        pages += 1
        if checkpoint:
            write_json(checkpoint, {"rows": list(rows.values()), "pages": pages, "complete": url is None})
        print(f"{user}: pagina {pages}, {len(rows)} filme", flush=True)
        if max_pages and pages >= max_pages:
            break
    return list(rows.values()), {"pages": pages, "complete": url is None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--users", nargs="+", required=True, help="Username-uri sau URL-uri de profil")
    parser.add_argument("--output", type=Path, default=Path("data/raw"))
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--max-pages", type=int, default=0, help="0 = toate; altfel colectare partiala")
    parser.add_argument("--refresh", action="store_true", help="Redescarca in loc sa reutilizeze cache-ul")
    args = parser.parse_args()
    if args.max_pages < 0:
        parser.error("--max-pages trebuie sa fie >= 0")
    users = list(dict.fromkeys(username(u) for u in args.users))
    manifest = {"started_at": now(), "users": [dataset_user(u) for u in users], "complete": False,
                "max_pages": args.max_pages, "profiles": {}, "errors": []}
    args.output.mkdir(parents=True, exist_ok=True)
    write_json(args.output / "manifest.json", manifest)
    try:
        client = Client(args.output / "pages", args.delay, args.refresh)
        ratings = []
        for user in users:
            checkpoint = args.output / "profiles" / f"{dataset_user(user)}.json"
            try:
                rows, status = collect_user(client, user, args.max_pages, checkpoint)
            except (requests.RequestException, ValueError, RuntimeError) as error:
                partial = json.loads(checkpoint.read_text(encoding="utf-8")) if checkpoint.exists() else {}
                rows = partial.get("rows", [])
                status = {"pages": partial.get("pages", 0), "complete": False, "error": str(error)}
                manifest["errors"].append(f"{dataset_user(user)}: {error}")
                print(f"{user}: {error}", flush=True)
            ratings.extend(rows)
            manifest["profiles"][dataset_user(user)] = status
            write_json(args.output / "interactions.json", ratings)
            write_json(args.output / "manifest.json", manifest)
        write_json(args.output / "interactions.json", ratings)
        if manifest["errors"]:
            manifest["interactions"] = len(ratings)
            raise SystemExit("Colectare profiluri incompleta. Datele disponibile si erorile au fost salvate; metadatele nu au fost pornite.")
        films = []
        for index, slug in enumerate(sorted({r["film_slug"] for r in ratings}), 1):
            page = client.get(f"{BASE}/film/{slug}/")
            films.append(parse_film(page["html"], slug, page["url"], page["collected_at"]))
            print(f"Metadate: {index} filme", flush=True)
        write_json(args.output / "films.json", films)
        manifest["complete"] = all(p["complete"] for p in manifest["profiles"].values())
        manifest["interactions"] = len(ratings)
        manifest["films"] = len(films)
    except (requests.RequestException, ValueError, RuntimeError) as error:
        manifest["errors"].append(str(error))
        raise SystemExit(str(error)) from error
    finally:
        manifest["finished_at"] = now()
        write_json(args.output / "manifest.json", manifest)


if __name__ == "__main__":
    main()
