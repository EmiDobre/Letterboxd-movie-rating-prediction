# Date pentru modelare

> Documenta?ie a prototipului de colectare. Pentru etapa IAPD curent?, vezi [README-ul proiectului](../README.md) ?i [prezentarea](iapd-propunere.pdf).

## Fișierele parțiale

- `data/partial/interactions.csv`: utilizator–film–notă, fără metadate.
- `data/partial/films.csv`: metadatele filmelor descărcate.
- `data/partial/dataset_with_features.csv`: toate interacțiunile și metadatele asociate.
- `data/partial/rated_dataset_with_features.csv`: numai rândurile cu notă, candidați pentru modelare.
- `data/partial/enrichment_report.json`: acoperire, erori, filme lipsă.
- `data/letterboxd_dataset_partial.xlsx`: aceleași date, în foi ușor de inspectat.

Aceste fișiere NU sunt încă train/test. Istoricul este incomplet și primele pagini
nu reprezintă un eșantion aleator. Nu putem selecta 300/100 din 72 de filme per cont.
`metadata_status` indică dacă pagina filmului a fost extrasă; câmpurile individuale
pot rămâne lipsă. Nu inventăm valori pentru câmpurile absente.

Caracteristici: an, durată, genuri, regizori, actori, țări, limbi, studiouri și
sinopsis. Listele sunt stocate ca JSON în celulele CSV. `rating` este ținta.
Media globală rămâne în tabelul de filme, fiind exclusă din datasetul cu caracteristici.

## Descriere, stil și sentimente

Sinopsisul poate fi transformat ulterior în caracteristici TF-IDF pentru a surprinde
teme și vocabular. Vocabularul și ponderile TF-IDF trebuie învățate doar pe train.
Textul descrie povestea, nu reacția spectatorului. Nu folosim recenzia personală
a filmului țintă: aceasta poate dezvălui opinia pe care încercăm să o prezicem.
Stilul nu este un câmp structurat extras aici; regizorul, genul, perioada și
descrierea pot servi drept indicii, fără a pretinde că măsoară direct stilul.

## Cum completăm istoricul

Fiecare persoană descarcă exportul din https://letterboxd.com/user/exportdata/.
Păstrăm `ratings.csv` și, dacă este disponibil, `watched.csv` într-un director
separat pentru fiecare cont. Nu sunt necesare parolele conturilor.

```bash
python -m extraction.import_export --user emi_dobre --ratings CALE/ratings.csv --watched CALE/watched.csv
# Repetăm pentru celelalte conturi. Tabelul comun este actualizat automat.
python -m extraction.enrich --input data/imported/interactions.csv --output data/imported
```

Exportatorul Excel actual descrie colectarea parțială din `data/partial`.
După importurile complete vom genera raportul și împărțirea 300/100 din acele date.
Exporturile rezolvă lipsa evaluărilor; accesul la metadatele filmelor rămâne separat.

Pentru reluarea metadatelor parțiale, se reutilizează cache-ul:

```bash
python -m extraction.enrich
python -m extraction.export_excel
```
