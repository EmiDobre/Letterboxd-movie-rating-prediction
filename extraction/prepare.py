"""Validate collected data, export CSVs, split by user, and report descriptives."""
import argparse
import csv
import hashlib
import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from extraction.crawl import write_json


def split_rows(rows, test_fraction=0.2, seed=42, train_size=None, test_size=None):
    if (train_size is None) != (test_size is None):
        raise ValueError("Specifică ambele dimensiuni train/test")
    if train_size is not None and (train_size < 1 or test_size < 1):
        raise ValueError("Dimensiunile train/test trebuie să fie pozitive")
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction trebuie să fie între 0 și 1")
    grouped = defaultdict(list)
    seen = set()
    for row in rows:
        key = (row["user_id"], row["film_slug"])
        if key in seen:
            raise ValueError(f"Interacțiune duplicată: {key}")
        seen.add(key)
        if row["rating"] is not None:
            rating = row["rating"]
            if isinstance(rating, bool) or not isinstance(rating, (int, float)) or not 0.5 <= rating <= 5 or rating * 2 != int(rating * 2):
                raise ValueError(f"Rating invalid: {key}: {rating}")
            grouped[row["user_id"]].append(row)
    train, test = [], []
    for user, items in sorted(grouped.items()):
        items = sorted(items, key=lambda r: r["film_slug"])
        stable_seed = int.from_bytes(hashlib.sha256(f"{seed}:{user}".encode()).digest()[:8], "big")
        random.Random(stable_seed).shuffle(items)
        if train_size is not None:
            if len(items) < train_size + test_size:
                # Keep insufficient histories in interactions.csv, without claiming 300/100.
                continue
            test.extend(items[:test_size])
            train.extend(items[test_size:test_size + train_size])
            continue
        count = min(len(items) - 1, max(1, round(len(items) * test_fraction))) if len(items) >= 2 else 0
        test.extend(items[:count])
        train.extend(items[count:])
    return train, test


def save_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
                             for key, value in row.items()})


def describe(rows, films, train, test):
    rated = [r for r in rows if r["rating"] is not None]
    per_user = {}
    for user in sorted({r["user_id"] for r in rows}):
        values = [r["rating"] for r in rated if r["user_id"] == user]
        per_user[user] = {"watched": sum(r["user_id"] == user for r in rows),
                          "rated": len(values), "mean": statistics.mean(values) if values else None,
                          "train": sum(r["user_id"] == user for r in train),
                          "test": sum(r["user_id"] == user for r in test)}
    counts = Counter(r["film_slug"] for r in rated)
    fields = ["release_year", "runtime_minutes", "genres", "directors", "cast", "countries", "languages"]
    return {"users": len(per_user), "unique_films": len(films), "interactions": len(rows),
            "rated_interactions": len(rated), "unrated_interactions": len(rows) - len(rated),
            "rating_distribution": dict(sorted(Counter(str(r["rating"]) for r in rated).items())),
            "mean_rating": statistics.mean(r["rating"] for r in rated) if rated else None,
            "std_rating": statistics.pstdev(r["rating"] for r in rated) if rated else None,
            "rated_matrix_density": len(rated) / (len(per_user) * len(films)) if per_user and films else 0,
            "films_rated_by_multiple_users": sum(n > 1 for n in counts.values()),
            "missing_metadata": {field: sum(f.get(field) in (None, "", []) for f in films) for field in fields},
            "top_genres": dict(Counter(g for f in films for g in f.get("genres", [])).most_common(10)),
            "per_user": per_user,
            "test_films_absent_from_all_training": len({r["film_slug"] for r in test} - {r["film_slug"] for r in train})}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("data/processed"))
    parser.add_argument("--test-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--split-mode", choices=["fixed", "fraction"], default="fixed")
    parser.add_argument("--train-size", type=int, default=300)
    parser.add_argument("--test-size", type=int, default=100)
    parser.add_argument("--allow-partial", action="store_true", help="Doar pentru probe incomplete, marcate explicit")
    args = parser.parse_args()
    manifest = json.loads((args.input / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("errors"):
        raise SystemExit("Colectarea a eșuat; reia crawlerul înainte de preprocesare.")
    if not manifest.get("complete") and not args.allow_partial:
        raise SystemExit("Colectare incompletă. Reia fără --max-pages sau folosește explicit --allow-partial.")
    rows = json.loads((args.input / "interactions.json").read_text(encoding="utf-8"))
    films = json.loads((args.input / "films.json").read_text(encoding="utf-8"))
    if not rows or not films:
        raise SystemExit("Nu există date de procesat.")
    film_map = {f["film_slug"]: f for f in films}
    if len(film_map) != len(films):
        raise ValueError("Filme duplicate")
    if {r["film_slug"] for r in rows} != set(film_map):
        raise ValueError("Metadatele și interacțiunile nu acoperă aceleași filme")
    fixed = args.split_mode == "fixed"
    train, test = split_rows(rows, args.test_fraction, args.seed,
                             args.train_size if fixed else None,
                             args.test_size if fixed else None)
    args.output.mkdir(parents=True, exist_ok=True)
    save_csv(args.output / "interactions.csv", rows, list(rows[0]))
    save_csv(args.output / "films.csv", films, list(films[0]))
    # Only static film attributes are included in model-ready files.
    features = ["title", "release_year", "runtime_minutes", "genres", "directors", "cast", "countries", "languages", "studios", "description"]
    fields = ["user_id", "film_slug", "rating"] + features
    for name, subset in [("train", train), ("test", test)]:
        merged = [{**{k: row[k] for k in ["user_id", "film_slug", "rating"]},
                   **{k: film_map[row["film_slug"]].get(k) for k in features}} for row in subset]
        save_csv(args.output / f"{name}.csv", merged, fields)
    report = describe(rows, films, train, test)
    report["collection_complete"] = manifest["complete"]
    report["split"] = {"method": "fixed_per_user" if fixed else "random_per_user", "seed": args.seed,
                       "train_size": args.train_size if fixed else None,
                       "test_size": args.test_size if fixed else None,
                       "test_fraction": None if fixed else args.test_fraction,
                       "train_rows": len(train), "test_rows": len(test)}
    selected = {(r["user_id"], r["film_slug"]) for r in train + test}
    unused = [r for r in rows if r["rating"] is not None and (r["user_id"], r["film_slug"]) not in selected]
    save_csv(args.output / "unused_ratings.csv", unused, list(rows[0]))
    report["split"]["unused_rated_rows"] = len(unused)
    report["split"]["insufficient_users"] = [u for u, info in report["per_user"].items()
        if fixed and info["rated"] < args.train_size + args.test_size]
    report["source_hashes"] = {name: hashlib.sha256((args.input / name).read_bytes()).hexdigest()
                               for name in ["manifest.json", "interactions.json", "films.json"]}
    write_json(args.output / "summary.json", report)
    lines = ["# Descrierea setului de date", "",
             f"Colectare completă: {manifest['complete']}",
             f"Utilizatori: {report['users']}; filme unice: {len(films)}; interacțiuni: {len(rows)}.",
             f"Note disponibile: {report['rated_interactions']}; fără notă: {report['unrated_interactions']}.",
             f"Train: {len(train)}; test: {len(test)}. Split aleator per utilizator, seed {args.seed}.", "",
             "| Utilizator | Vizionate | Evaluate | Medie | Train | Test |", "|---|---:|---:|---:|---:|---:|"]
    for user, info in report["per_user"].items():
        mean = f"{info['mean']:.2f}" if info["mean"] is not None else "—"
        lines.append(f"| {user} | {info['watched']} | {info['rated']} | {mean} | {info['train']} | {info['test']} |")
    lines += ["", "## Distribuția notelor", "", "| Notă | Număr |", "|---|---:|"]
    lines += [f"| {rating} | {count} |" for rating, count in report["rating_distribution"].items()]
    lines += ["", "## Metadate lipsă (filme unice)", "", "| Câmp | Număr |", "|---|---:|"]
    lines += [f"| {field} | {count} |" for field, count in report["missing_metadata"].items()]
    lines += ["", "## Limite", "", "Evaluarea este retrospectivă; splitul nu este cronologic.",
              (f"Ținta este {args.train_size} train / {args.test_size} test per utilizator. Conturi insuficiente, păstrate doar în datele integrale: " +
               ", ".join(report["split"]["insufficient_users"])) if fixed else
              "Utilizatorii cu o singură notă apar doar în train.",
              "Evaluările neincluse în experiment sunt păstrate în unused_ratings.csv.",
              "Recenziile personale, like-urile și media globală nu sunt caracteristici în train/test.",
              "Orice medie a preferințelor, encoder sau imputare se învață exclusiv pe train."]
    (args.output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Salvat: {args.output}; {len(train)} train, {len(test)} test")


if __name__ == "__main__":
    main()
