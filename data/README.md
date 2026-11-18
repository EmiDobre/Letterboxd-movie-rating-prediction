# Date

`raw/` conține răspunsuri HTML în cache JSON (URL + momentul descărcării),
`interactions.json`, `films.json` și `manifest.json`. Este inclus în repository, împreună cu paginile colectate până acum. Momentan
nu există un dataset final.

`processed/` este generat de `python -m extraction.prepare`:

- `interactions.csv`: o pereche utilizator–film pe rând, cu rating opțional.
- `films.csv`: o înregistrare per film și metadate.
- `train.csv`, `test.csv`: doar interacțiuni cu note și metadatele statice asociate.
- `summary.json`, `summary.md`: statistici calculate din datele reale, seed și hash-uri de proveniență.

Listele din CSV sunt șiruri JSON; se citesc cu `json.loads`. Valorile lipsă sunt
celule goale, niciodată rating zero. `collected_at` este data colectării/cache-ului,
nu data vizionării. `film_slug` este cheia de legătură în snapshot; slugurile pot fi
modificate de platformă în timp. `film_id` este păstrat unde apare în pagina profilului.

Nu amestecați fișiere din colectări diferite. Rularea crawlerului reface tabelele
pentru lista exactă de utilizatori primită; cache-ul se reutilizează implicit.
Folosiți `--refresh` pentru un snapshot nou. Un manifest cu erori blochează preprocesarea.

Excel: `letterboxd_dataset_partial.xlsx`, generat cu `python -m extraction.export_excel`.
Conține toate datele parțiale existente, nu întregul istoric al profilurilor.
