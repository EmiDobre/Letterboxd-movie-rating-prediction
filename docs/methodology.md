# Etapa 1 — date și plan de analiză

## Ideea

Prezicem nota personală, nu media globală a unui film. Ascundem o parte din notele
existente și verificăm cât de aproape sunt predicțiile de acestea. Acest experiment
este posibil chiar dacă utilizatorul a văzut deja filmele: modelul nu vede notele
ascunse la antrenare. Nu este însă o demonstrație a predicției preferințelor viitoare
în timp, deoarece împărțirea actuală este aleatoare.

## Achiziție și preprocesare

1. Fixăm lista de profiluri publice și păstrăm lista în manifest.
2. Parcurgem `/USERNAME/films/` și linkurile `next`, extrăgând filmul și ratingul.
3. Extragem JSON-LD `Movie` din pagina fiecărui film unic.
4. Salvăm URL-ul, momentul colectării și răspunsul brut; cache-ul permite reluarea.
5. Validăm scala, unicitatea perechilor și acoperirea cu metadate.
6. Separăm filmele fără rating de exemplele supervizate; generăm CSV-uri și raport.
7. Facem split 300 train / 100 test per utilizator eligibil, cu seed fix; păstrăm restul notelor separat. Testul rămâne ascuns la antrenare.

Un film revăzut apare o singură dată în lista de filme, cu nota vizibilă la colectare.
Nu reconstruim istoricul modificărilor notei și nu tratăm revizionările ca exemple noi.

## Analize planificate

- Număr de utilizatori, filme unice, interacțiuni și note per utilizator.
- Histograma notelor, medie și deviație standard, dezechilibre ale scalei.
- Metadate lipsă și distribuții pe an, durată și genuri.
- Suprapunerea filmelor evaluate între utilizatori și densitatea matricei de note.
- Diferențele de preferințe pe gen/regizor; menționăm mărimea eșantionului pentru fiecare grup.
- Comparație baseline/model; erori per utilizator și filme absente din train.

Raportul automat acoperă numărări, distribuția notelor, top genuri, suprapunere și
lipsuri. Graficele detaliate pe an/durată și comparațiile între modele sunt analize
viitoare. Nu raportăm cifre inventate în lipsa profilurilor selectate.

## Prezentarea de 5–7 minute (discuții până la 10 minute)

1. **Problema și scopul — 45 s:** nota personală; sursă unică Letterboxd.
2. **Colectarea — 75 s:** profiluri, paginare, metadate, cache, limitări.
3. **Structura datelor — 60 s:** tabelele interactions/films și cheia comună.
4. **Descriptivi — 90 s:** valori și grafice din colectarea finală, nu din proba tehnică.
5. **Analize și evaluare — 75 s:** baseline, split, MAE/RMSE, prevenirea scurgerii informației.
6. **Limite și pașii următori — 30 s:** selecția utilizatorilor, volum, modelare.

Total propus: 6 min 15 s. PDF/PPTX se pregătește după colectarea profilurilor,
pentru ca slide-urile cu descriptivi să conțină date reale.
