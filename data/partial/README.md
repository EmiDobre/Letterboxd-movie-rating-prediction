# Colectare parțială — nu este datasetul final

Cele patru profiluri au permis prima pagină din lista filmelor (72 filme fiecare).
Pagina a doua a răspuns HTTP 403 în toate cazurile. `interactions.csv` combină
paginile disponibile; `summary.json` descrie strict acest fragment, nu conturile complete.
Împărțirea 300/100 nu a fost generată. Metadatele sunt colectate separat, cu
acoperirea raportată în `enrichment_report.json`.

Pentru continuare sunt necesare exporturile oficiale ale conturilor, în special
`ratings.csv` și `watched.csv`, păstrate separat pentru fiecare username.
Export: https://letterboxd.com/user/exportdata/ (fiecare persoană din propriul cont).
Nu sunt necesare parolele conturilor. Exporturile furnizează evaluările; metadatele
cinematografice sunt colectate din paginile filmelor, separat de istoricul profilurilor.

Datele brute/cache-ul sunt în `data/raw/`; sunt incluse în repository. CSV-ul parțial și
acest raport sunt vizibile în repository. Nu folosiți acest fragment ca eșantion
aleator și nu raportați 72 ca număr total de filme pentru un utilizator.

Pentru analiză deschideți `rated_dataset_with_features.csv` (doar note disponibile)
sau `dataset_with_features.csv` (include și filmele fără notă). Listele sunt celule
JSON; `metadata_status` arată dacă metadatele filmului au fost colectate.
