"""Funzioni condivise dagli script (stessa logica di site/analisi.js)."""
from __future__ import annotations

import re

TAG_INIZIALI = re.compile(r"^(?:\s*\[[^\]]*\]\s*)+")
SPAZI = re.compile(r"\s+")

# Gravità indicata nel titolo dai bollettini CERT-Bund: [kritisch], [hoch], [mittel], [niedrig].
LIVELLI = {"kritisch": 4, "hoch": 3, "mittel": 2, "niedrig": 1}
NOMI_LIVELLO = {4: "critica", 3: "alta", 2: "media", 1: "bassa"}


def senza_tag(titolo: str) -> str:
    return SPAZI.sub(" ", TAG_INIZIALI.sub("", titolo or "")).strip()


def gravita(titolo: str) -> int:
    m = TAG_INIZIALI.match(titolo or "")
    if not m:
        return 0
    livelli = [LIVELLI.get(t.strip().lower(), 0) for t in re.findall(r"\[([^\]]*)\]", m.group(0))]
    return max(livelli, default=0)


def chiave_titolo(voce: dict) -> tuple:
    """Voci con stessa fonte, stessa gravità e stesso titolo (senza etichette) sono considerate la stessa."""
    return (voce["source"], gravita(voce["title"]), senza_tag(voce["title"]).lower())
