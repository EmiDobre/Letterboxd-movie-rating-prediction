"""Export the collected partial dataset to a readable Excel workbook."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


def add_sheet(book, name, headers, rows):
    sheet = book.create_sheet(name)
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
        # Film titles and other source strings must remain text, never formulas.
        for cell in sheet[sheet.max_row]:
            if isinstance(cell.value, str):
                cell.data_type = "s"
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="235347")
    for index, column in enumerate(sheet.columns, 1):
        width = min(65, max(14, max(len(str(c.value or "")) for c in column) + 2))
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.sheet_view.showGridLines = False
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top")
    return sheet


def export(source, output, profiles):
    with (source / "interactions.csv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        records = list(reader)
    if not fields or not records:
        raise ValueError("Nu există interacțiuni de exportat")
    for record in records:
        record["rating"] = float(record["rating"]) if record["rating"] else None
    keys = [(r["user_id"], r["film_slug"]) for r in records]
    if len(keys) != len(set(keys)):
        raise ValueError("Perechi utilizator–film duplicate")
    summary = json.loads((source / "summary.json").read_text(encoding="utf-8"))
    if summary.get("complete") is not False:
        raise ValueError("Acest exportator descrie colectarea parțială; verifică raportul sursă")
    users = sorted({r["user_id"] for r in records})
    film_map = {r["film_slug"]: r for r in records}
    book = Workbook()
    book.remove(book.active)
    add_sheet(book, "Rezumat", ["Indicator", "Valoare"], [
        ["Stare", "COLECTARE PARȚIALĂ — prima pagină pentru fiecare profil"],
        ["Utilizatori", len(users)], ["Perechi utilizator–film", len(records)],
        ["Filme distincte", len(film_map)],
        ["Evaluări disponibile", sum(r["rating"] is not None for r in records)],
        ["Filme fără notă", sum(r["rating"] is None for r in records)],
        ["Blocaj", summary["blocker"]],
        ["Metadate cinematografice", "Încă necolectate; foaia Filme conține doar identificatori și titluri"],
        ["Train / test", "Încă negenerate; țintă 300 / 100 per utilizator cu minimum 400 de note"],
        ["Note lipsă", "Celula goală înseamnă notă indisponibilă, nu nota 0"],
        ["collected_at", "Momentul descărcării paginii, NU data vizionării"],
        ["Atenție", "72 este numărul colectat per profil, NU numărul total al filmelor sale"],
    ])
    add_sheet(book, "Evaluari", fields, [[r[k] for k in fields] for r in records])
    counts = Counter(r["film_slug"] for r in records)
    add_sheet(book, "Filme", ["film_slug", "film_id", "title", "film_url", "utilizatori_in_fragment"],
              [[slug, r["film_id"], r["title"], r["film_url"], counts[slug]]
               for slug, r in sorted(film_map.items())])
    add_sheet(book, "Utilizatori", ["username", "filme_colectate", "cu_nota", "fara_nota", "stare"],
              [[u, sum(r["user_id"] == u for r in records),
                sum(r["user_id"] == u and r["rating"] is not None for r in records),
                sum(r["user_id"] == u and r["rating"] is None for r in records), "PARȚIAL"] for u in users])
    for user in users:
        add_sheet(book, user[:31], fields, [[r[k] for k in fields] for r in records if r["user_id"] == user])
    profile_rows = json.loads(profiles.read_text(encoding="utf-8"))
    add_sheet(book, "Profiluri", ["link_primit", "profil_identificat", "status_HTTP_pagina_profil"],
              [[p["provided_url"], p["profile_url"], p["status"]] for p in profile_rows])
    output.parent.mkdir(parents=True, exist_ok=True)
    book.save(output)
    print(f"Excel salvat: {output} ({len(records)} perechi, {len(film_map)} filme distincte)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/partial"))
    parser.add_argument("--output", type=Path, default=Path("data/letterboxd_dataset_partial.xlsx"))
    parser.add_argument("--profiles", type=Path, default=Path("data/profiles.json"))
    args = parser.parse_args()
    export(args.input, args.output, args.profiles)


if __name__ == "__main__":
    main()
