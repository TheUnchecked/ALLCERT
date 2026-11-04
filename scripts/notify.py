#!/usr/bin/env python3
"""Invia su Telegram le voci nuove importanti, secondo le regole di notify.yml.

Funziona solo se sono impostate le variabili TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID
(nel flusso arrivano dai segreti del repository). Se mancano, esce senza fare nulla.
Un errore di invio non fa mai fallire il flusso.

Uso:  python scripts/notify.py [--data data] [--config notify.yml] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

import yaml

from common import NOMI_LIVELLO, chiave_titolo, gravita

SITE_URL = "https://theunchecked.github.io/ALLCERT/"


def carica(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def scegli(items_doc: dict, ids: list[str], regole: dict) -> tuple[list[dict], int]:
    """Restituisce (voci da inviare, numero totale di candidate prima del limite)."""
    min_gravita = int(regole.get("min_gravita", 3))
    sempre_da = set(regole.get("sempre_da", []))
    massimo = int(regole.get("max_per_esecuzione", 10))

    per_id = {i["id"]: i for i in items_doc.get("items", [])}
    viste, candidate = set(), []
    for voce_id in ids:
        voce = per_id.get(voce_id)
        if not voce:
            continue
        g = gravita(voce["title"])
        if g < min_gravita and voce["source"] not in sempre_da:
            continue
        chiave = chiave_titolo(voce)
        if chiave in viste:
            continue
        viste.add(chiave)
        candidate.append((g, voce))
    candidate.sort(key=lambda x: -x[0])  # prima le piu' gravi
    return [v for _, v in candidate[:massimo]], len(candidate)


def testo_messaggio(voce: dict, sources: dict) -> str:
    meta = sources.get(voce["source"], {})
    g = gravita(voce["title"])
    intestazione = f"[{meta.get('country', '?')}] {meta.get('name', voce['source'])}"
    if g:
        intestazione += f" - gravità {NOMI_LIVELLO[g]}"
    return f"{intestazione}\n{voce['title']}\n{voce['link']}"


def invia(token: str, chat_id: str, testo: str) -> None:
    corpo = json.dumps({"chat_id": chat_id, "text": testo, "disable_web_page_preview": True}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=corpo, headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        resp.read()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data")
    parser.add_argument("--config", default="notify.yml")
    parser.add_argument("--dry-run", action="store_true", help="stampa i messaggi senza inviarli")
    args = parser.parse_args()

    config = {}
    if Path(args.config).exists():
        config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8")) or {}
    regole = config.get("telegram", {})

    data = Path(args.data)
    items_doc = carica(data / "items.json", {})
    ids = carica(data / "new.json", {}).get("ids", [])
    scelte, totale = scegli(items_doc, ids, regole)
    sources = items_doc.get("sources", {})

    messaggi = [testo_messaggio(v, sources) for v in scelte]
    if totale > len(scelte):
        messaggi.append(f"... e altre {totale - len(scelte)} voci importanti: {SITE_URL}")

    print(f"Voci nuove: {len(ids)} - da notificare: {totale} - messaggi: {len(messaggi)}")
    if not messaggi:
        return 0
    if args.dry_run:
        for m in messaggi:
            print("---\n" + m)
        return 0

    token, chat_id = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Notifiche Telegram non configurate (mancano TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID): salto.")
        return 0
    inviati = 0
    for m in messaggi:
        try:
            invia(token, chat_id, m)
            inviati += 1
        except Exception as exc:  # noqa: BLE001 - un errore di invio non deve bloccare il flusso
            print(f"Invio non riuscito: {type(exc).__name__}", file=sys.stderr)  # il token non va mai stampato
    print(f"Messaggi inviati: {inviati}/{len(messaggi)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
