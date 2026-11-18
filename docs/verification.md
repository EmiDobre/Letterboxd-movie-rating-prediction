# Verificare tehnică — 18 noiembrie 2026

> Documenta?ie a prototipului de colectare. Pentru etapa IAPD curent?, vezi [README-ul proiectului](../README.md) ?i [prezentarea](iapd-propunere.pdf).

Acestea sunt probe ale implementării, **nu descriptivii datasetului proiectului**.
Profilurile pentru dataset nu au fost încă furnizate.

- 9 teste unitare trecute: markup actual/vechi, jumătăți de stea, filme fără note,
  pagină nerecunoscută, metadate JSON-LD, username-uri, split reproductibil/disjunct,
  duplicate, ratinguri invalide, descriptivi.
- Parser verificat pe prima pagină publică `/davidehrlich/films/`: 72 filme,
  59 cu rating vizibil și link către pagina 2. Nu s-a colectat întregul profil.
- Clientul a citit robots.txt și pagina live `/film/inception/`; parserul a extras
  titlul, anul 2010, durata 148 minute și genurile disponibile.
- Preprocesarea a generat CSV-uri și rapoarte într-un director separat din `/tmp`,
  folosind două interacțiuni sintetice marcate ca probă incompletă. Aceste exemple
  nu sunt incluse în `data/` și nu trebuie prezentate drept date reale.

Nu s-a executat încă o colectare completă pentru utilizatorii proiectului.
Cache-ul reduce cererile la reluare, dar colectarea multi-pagină trebuie verificată
pe profilurile selectate. Nu există rezultate de Machine Learning în această etapă.
