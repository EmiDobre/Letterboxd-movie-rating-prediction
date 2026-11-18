# Colectare parțială — nu este datasetul final

Cele patru profiluri au permis prima pagină din lista filmelor (72 filme fiecare).
Pagina a doua a răspuns HTTP 403 în toate cazurile. `interactions.csv` combină
paginile disponibile; `summary.json` descrie strict acest fragment, nu conturile complete.
Metadatele filmelor și împărțirea 300/100 nu au fost generate.

Pentru continuare sunt necesare exporturile oficiale ale conturilor, în special
`ratings.csv` și `watched.csv`, păstrate separat pentru fiecare username.
Export: https://letterboxd.com/user/exportdata/ (fiecare persoană din propriul cont).
Nu sunt necesare parolele conturilor. Exporturile furnizează evaluările; metadatele
cinematografice vor fi apoi colectate din paginile filmelor, dacă accesul permite.

Datele brute/cache-ul sunt în `data/raw/`; sunt incluse în repository. CSV-ul parțial și
acest raport sunt vizibile în repository. Nu folosiți acest fragment ca eșantion
aleator și nu raportați 72 ca număr total de filme pentru un utilizator.
