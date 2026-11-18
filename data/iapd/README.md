# Setul de date IAPD

Exporturile oficiale Letterboxd furnizează istoricul celor cinci participanți. Directorul local `raw/letterboxd_exports/` conține câte un subdirector cu ID pseudonimizat. Pentru reproducere, extrage `ratings.csv` și `watched.csv` din fiecare ZIP în acel subdirector și folosește același ID la rulările următoare.

Fișierul local opțional `raw/letterboxd_exports/user_names.json` asociază fiecare director de export cu numele afișat în coloana `user_id`. Setul rezultat păstrează doar interacțiunile cu rating.

```powershell
python -m extraction.build_iapd --movielens data/raw/letterboxd_exports/ml-latest-small.zip
```

Arhiva opțională [MovieLens Latest Small](https://grouplens.org/datasets/movielens/latest/) adaugă genurile după o potrivire unică titlu–an. Cache-ul Letterboxd existent furnizează metadate atunci când codul scurt din pagina salvată coincide cu cel din export.

Pentru îmbogățirea cu TMDB, configurează local variabila `TMDB_READ_TOKEN` (API Read Access Token), apoi adaugă `--tmdb` comenzii. Răspunsurile API sunt păstrate local pentru reluare. Potrivirile exacte titlu–an unice sunt acceptate, iar cele ambigue sau absente apar în raport. Sursa metadatelor este TMDB pentru câmpurile completate de API. [Documentația TMDB](https://developer.themoviedb.org/docs/search-and-query-for-details)

| Fișier | Conținut |
|---|---|
| `interactions.csv` | Perechile utilizator–titlu cu rating și datele din export. |
| `films.csv` | Un rând per titlu evaluat, cu an, deceniu, metadate și proveniență. |
| `dataset_with_features.csv` | Asocierea evaluărilor cu metadatele filmelor. |
| `rated_dataset_with_features.csv` | Rândurile cu etichetă de rating, înainte de separarea train/test. |
| `metadata_to_review.csv` | Titlurile fără o potrivire TMDB acceptată, inclusiv cele încă neinterogate. |
| `summary.json` | Numărători, distribuția ratingurilor și acoperirea metadatelor. |

CSV-urile și ZIP-urile participanților sunt locale. Repo-ul poate distribui codul, descriptivii agregați și prezentarea. Câmpurile goale indică date indisponibile. `rating_date` și `watched_added_date` sunt datele de înregistrare din export.
