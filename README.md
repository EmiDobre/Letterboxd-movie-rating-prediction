# Predicția ratingurilor de film din Letterboxd

**IAPD · Etapa 1 · Propunerea proiectului și descrierea datelor**

Obiectivul este să prezicem nota de la 0,5 la 5 stele pe care un utilizator cunoscut ar acorda-o unui film, pornind de la notele sale anterioare și de la caracteristicile filmului.

[Prezentarea de 5–7 minute (PDF)](docs/iapd-propunere.pdf) · [Rezumatul datasetului](data/iapd/summary.json)

## Achiziția datelor

Am importat cinci exporturi oficiale Letterboxd și am asociat `ratings.csv` cu `watched.csv` prin codul filmului din linkul `boxd.it`. Am păstrat o singură înregistrare per pereche utilizator–film cu rating. Metadatele provin din paginile Letterboxd deja salvate și din MovieLens, unde genurile au fost potrivite după titlu și an.

## Datasetul actual

| Indicator | Valoare |
|---|---:|
| Participanți | 5 |
| Evaluări | 2.058 |
| Titluri distincte evaluate | 1.275 |
| Evaluări pe participant | 300–538 |
| Rating mediu | 3,61 / 5 |
| Titluri cu genuri | 790 / 1.275 |
| Titluri cu regizor, durată și sinopsis | 141 / 1.275 |

Cele 229 de vizionări fără rating au fost excluse. Metadatele lipsă rămân celule goale. Completarea prin TMDB este planificată pentru etapa de modelare.

## Analize planificate

1. Folosim media istorică a notelor fiecărui utilizator ca reper.
2. Testăm dacă genul, perioada, regizorul și durata reduc eroarea. Evaluăm separat contribuția sinopsisului pe aceleași observații de test.
3. Antrenăm pe evaluări mai vechi și testăm pe evaluări mai recente. Raportăm eroarea absolută medie (MAE), în stele.

## Structura repo-ului

| Director | Conținut |
|---|---|
| [`extraction/`](extraction/) | Import, preprocesare și teste. Punctul de intrare curent este `python -m extraction.build_iapd`. |
| [`data/`](data/) | Rezumatul, instrucțiunile de reproducere și datele de lucru. Exporturile participanților și CSV-urile cu evaluări se păstrează local. |
| [`docs/`](docs/) | Prezentarea etapei și documentația prototipului. |

[Instrucțiuni de acces și reproducere](data/iapd/README.md) · [MovieLens](https://grouplens.org/datasets/movielens/latest/)
