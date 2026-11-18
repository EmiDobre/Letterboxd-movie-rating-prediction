# Predicția preferințelor cinematografice din Letterboxd

Scop: un model supervizat care prezice nota (0.5–5 stele) pe care un utilizator
ar acorda-o unui film, din notele sale anterioare și caracteristicile filmului.
**Sursa unică: Letterboxd.** Nu folosim IMDb sau Rotten Tomatoes.

Etapa actuală: colectare, validare, descriptivi și pregătirea datelor pentru o
evaluare retrospectivă. Nu există încă un model antrenat sau rezultate de predicție.

## Structură

```text
extraction/       crawler, preprocesare, teste
data/raw/         pagini brute + JSON + manifest (incluse în repository)
data/processed/   CSV train/test + raport descriptiv (generate)
docs/             metodologie și planul prezentării
```

## Instalare și rulare

Python 3.10+:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m extraction.crawl --users USERNAME1 USERNAME2
python -m extraction.prepare
python -m unittest discover -s extraction/tests -v
```

Înlocuiește username-urile cu profilurile alese. Sunt acceptate și linkuri de forma
`https://letterboxd.com/USERNAME/`. Se colectează toate paginile vizibile din `/films/`,
inclusiv filmele fără rating; metadatele fiecărui film se descarcă o singură dată.
Nu este nevoie de parolă. Datele private nu sunt accesibile acestui crawler.

Probă mică într-un director separat:

```bash
python -m extraction.crawl --users USERNAME --max-pages 1 --output /tmp/letterboxd-smoke
python -m extraction.prepare --input /tmp/letterboxd-smoke --output /tmp/letterboxd-smoke-processed --allow-partial
```

`--max-pages` marchează colectarea drept incompletă dacă mai există pagini.
Rularea fără limită poate dura mult: există minimum 2 secunde între cereri, cache
și retry limitat pentru erori de server. La HTTP 403/429 se oprește; nu ocolește
blocaje. `robots.txt` este verificat la fiecare rulare, înaintea paginilor solicitate.
După o întrerupere, aceeași comandă reutilizează paginile salvate. `--refresh`
redescarcă paginile. Profilurile goale/private sau HTML-ul neașteptat sunt raportate
ca erori, nu drept colectare completă cu zero filme.

## Date și evaluare

- Țintă: `rating`, nota utilizatorului. Absența notei nu înseamnă dezinteres.
- Caracteristici: an, durată, genuri, regizori, actori, țări, limbi, studiouri,
  eventual reprezentarea textului sinopsisului.
- `global_rating` și numărul de voturi sunt păstrate în `films.csv` pentru analiză,
  dar excluse din train/test: sunt valori curente și pot include nota țintă.
- Split reproductibil de 300 filme train și 100 test pentru fiecare utilizator cu minimum 400 de filme evaluate. Restul notelor se păstrează în `unused_ratings.csv`.
  Nu există aceeași pereche utilizator–film în ambele seturi. Același film poate
  apărea la utilizatori diferiți; evaluăm preferințele unor utilizatori cunoscuți.
- Utilizatorii cu mai puțin de 400 de note rămân în datele integrale, dar nu intră în experimentul fix 300/100. Modul procentual anterior este disponibil cu `--split-mode fraction`. Nu umplem artificial
  datele lipsă. Pentru ajustarea modelelor folosim ulterior validare în interiorul
  train; testul rămâne neatins până la evaluarea finală.
- Data vizionării nu este extrasă din `/films/`. Nu pretindem validare temporală.
  Pentru aceasta este necesară o etapă distinctă bazată pe diary/export.

În model nu introducem recenzia sau like-ul utilizatorului pentru filmul țintă.
Mediile preferințelor, vocabularul și orice transformare învățată se calculează
doar pe train; la validare, doar pe foldul de antrenare.

Baseline propus: media notelor utilizatorului din train. Apoi Ridge cu metadate
codificate și, în funcție de volum, modele cu arbori sau filtrare colaborativă.
Evaluare: MAE, RMSE, proporția predicțiilor la maximum 0.5 stele distanță, rezultate
per utilizator și medie macro. Nu promitem performanță înainte de experimente.

## Surse și limitări

- [Pagină de film verificată](https://letterboxd.com/film/inception/): metadate în JSON-LD.
- [Reguli robots.txt](https://letterboxd.com/robots.txt): verificate automat, se pot schimba.
- [Export oficial](https://letterboxd.com/user/exportdata/): alternativă pentru datele
  propriului cont dacă accesul automat este blocat; importatorul CSV nu este implementat aici.

Parserul a fost adaptat la HTML-ul observat în noiembrie 2026. Platforma poate schimba
structura. Un snapshot al unui profil activ se poate modifica în timpul paginării.
Datele descriu utilizatorii aleși și filmele pe care au decis să le evalueze, nu
preferințele întregii populații. Vezi [metodologia](docs/methodology.md).

## Deschiderea datelor în Excel

Fișierul `data/letterboxd_dataset_partial.xlsx` conține toate datele disponibile
în prezent: 288 perechi utilizator–film, 274 note și 190 filme distincte, din primele
pagini ale celor patru profiluri. Colectarea este **parțială**, blocată cu HTTP 403
la pagina a doua a fiecărui profil. Metadatele cinematografice nu sunt încă extrase.

Foile includ rezumatul, toate evaluările, filmele distincte, statisticile per
utilizator, câte o foaie pentru fiecare persoană și linkurile profilurilor.
CSV-urile rămân disponibile pentru algoritmi. Excel-ul se regenerează din proiect:

```bash
python -m extraction.export_excel
```

Scripturile sunt în `extraction/`, datele brute și tabelare în `data/`, iar
documentația în `docs/`. Datele brute sunt acum incluse la adăugarea în Git;
mediul `.venv/` și cache-ul Python sunt excluse. Nu s-a făcut push pe GitHub.
