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
| `data/feed.xml` | Flusso Atom unico con le ultime 100 voci (senza ripetizioni), da aggiungere a un lettore di feed. |
| `scripts/notify.py`, `notify.yml` | Notifiche Telegram per le voci nuove importanti. Spente finché non si impostano i segreti. |
| `scripts/common.py` | Funzioni condivise dagli script (gravità, titoli senza etichette). |
| `site/index.html` | Pagina di consultazione: scheda Registro (elenco per giorno) e scheda Quadro (mappa, andamento, gravità, prodotti). |
| `site/analisi.js` | Logica di analisi: unione delle voci con stesso titolo, gravità e prodotto ricavati dai titoli. |
| `site/europe.json` | Geometria della mappa (Natural Earth), generata da `scripts/build-map.mjs`. Non va rigenerata a ogni aggiornamento. |
| `.github/workflows/aggiorna.yml` | Raccolta pianificata e pubblicazione. |

## Attivazione (una sola volta)

1. Nel repository: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. Scheda **Actions → Aggiorna segnalazioni → Run workflow** per la prima esecuzione.
3. La pagina sarà disponibile su `https://theunchecked.github.io/ALLCERT/`.

## Voci non lette

La pagina ricorda nel browser quali voci hai già aperto. Le voci arrivate dopo la tua prima visita hanno l'etichetta "Nuova"; si possono filtrare con "Solo voci non lette" e azzerare con "Segna tutto come letto". La memoria è locale: cambiando browser o dispositivo riparte da zero.

## Flusso RSS

Indirizzo: `https://theunchecked.github.io/ALLCERT/data/feed.xml`. Contiene le ultime 100 voci, con le voci dallo stesso titolo contate una volta.

## Notifiche Telegram (facoltative)

Ogni 3 ore il flusso invia un messaggio per ogni voce nuova che rispetta le regole di `notify.yml` (per impostazione predefinita: gravità alta o critica, più tutte le voci nuove di CSIRT Italia e CERT-EU; al massimo 10 messaggi per esecuzione).

1. Su Telegram apri la chat con BotFather, invia `/newbot` e segui i passaggi: ti dà un **token**.
2. Scrivi un messaggio qualsiasi al tuo nuovo bot, poi apri `https://api.telegram.org/bot<TOKEN>/getUpdates` (sostituendo `<TOKEN>`) e cerca il numero in `"chat":{"id":...}`: è il **chat id**.
3. Nel repository: **Settings → Secrets and variables → Actions → New repository secret**. Crea `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`.

Il token è una password: non va scritto nei file del repository né condiviso. Senza i due segreti il passaggio viene saltato senza errori. Alla primissima esecuzione non parte nessuna notifica, per evitare un invio di massa di voci vecchie.

## Cosa mostra il Quadro

- **Segnalazioni per Paese**: indica quale CERT ha pubblicato, non dove si trova la vulnerabilità. Un Paese con più segnalazioni è un Paese i cui CERT pubblicano di più.
- **Gravità**: disponibile solo per CERT-Bund, che la scrive nel titolo (`[kritisch]`, `[hoch]`, `[mittel]`, `[niedrig]`).
- **Prodotti più citati**: ricavati dai titoli con una regola per fonte (CERT-Bund, CSIRT Italia, CERT-FR, CERT-EU). È un'indicazione, non un conteggio esatto. Per aggiungere una fonte si modifica `prodotto()` in `site/analisi.js`.

Tutti i grafici seguono i filtri della colonna laterale e hanno una tabella dei dati.

## Fonti da verificare

Le fonti con `verified: false` in `sources.yml` sono indirizzi candidati non ancora confermati. Dopo la prima esecuzione guarda il pannello "Stato delle fonti" nella pagina (o `data/status.json`): quelle in errore vanno corrette o disattivate con `enabled: false`.

## Prova in locale

```bash
pip install -r requirements.txt
python scripts/collect.py
mkdir -p _site/data && cp -r site/. _site/ && cp data/*.json _site/data/
python -m http.server -d _site 8000   # poi apri http://localhost:8000
```
