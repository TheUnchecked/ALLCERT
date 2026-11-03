# ALLCERT

Aggregatore centralizzato delle segnalazioni e delle notizie dei CERT/CSIRT e delle agenzie di cybersicurezza europee, tra cui ACN e CSIRT Italia.

Un flusso GitHub Actions scarica ogni 3 ore i feed elencati in `sources.yml`, li normalizza, estrae le CVE, deduplica e pubblica una pagina di consultazione su GitHub Pages.

## Come funziona

| Elemento | Ruolo |
|---|---|
| `sources.yml` | Elenco delle fonti. Per aggiungerne una basta copiare un blocco. |
| `scripts/collect.py` | Scarica, normalizza e unisce i dati allo storico. |
| `data/items.json` | Elenco unificato delle segnalazioni (storico di 365 giorni). |
| `data/status.json` | Esito dell'ultimo controllo di ogni fonte. |
| `site/index.html` | Pagina di consultazione con filtri per Paese, fonte, periodo, CVE e testo. |
| `.github/workflows/aggiorna.yml` | Raccolta pianificata e pubblicazione. |

## Attivazione (una sola volta)

1. Nel repository: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. Scheda **Actions → Aggiorna segnalazioni → Run workflow** per la prima esecuzione.
3. La pagina sarà disponibile su `https://theunchecked.github.io/ALLCERT/`.

## Fonti da verificare

Le fonti con `verified: false` in `sources.yml` sono indirizzi candidati non ancora confermati. Dopo la prima esecuzione guarda il pannello "Stato delle fonti" nella pagina (o `data/status.json`): quelle in errore vanno corrette o disattivate con `enabled: false`.

## Prova in locale

```bash
pip install -r requirements.txt
python scripts/collect.py
mkdir -p _site/data && cp -r site/. _site/ && cp data/*.json _site/data/
python -m http.server -d _site 8000   # poi apri http://localhost:8000
```
