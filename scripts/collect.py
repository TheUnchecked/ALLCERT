#!/usr/bin/env python3
"""Raccoglie i flussi RSS/Atom elencati in sources.yml e produce:

  data/items.json   elenco unificato e deduplicato delle segnalazioni
  data/status.json  esito dell'ultimo controllo per ogni fonte

Uso:  python scripts/collect.py [--sources sources.yml] [--out data]
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import time
import urllib.request
from calendar import timegm
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import yaml

USER_AGENT = "ALLCERT-aggregator/1.0 (+https://github.com/TheUnchecked/ALLCERT)"
TIMEOUT = 30
RETRIES = 2
MAX_AGE_DAYS = 365   # le voci piu' vecchie vengono scartate
MAX_ITEMS = 8000     # limite di sicurezza sulle dimensioni del file
SUMMARY_CHARS = 400

CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_text(raw: str | None, limit: int | None = None) -> str:
    if not raw:
        return ""
    text = html.unescape(TAG_RE.sub(" ", raw))
    text = SPACE_RE.sub(" ", text).strip()
    if limit and len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def entry_date(entry) -> str | None:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                ts = timegm(parsed)
                return datetime.fromtimestamp(ts, timezone.utc).replace(microsecond=0).isoformat()
            except (OverflowError, ValueError):
                continue
    return None


def fetch(url: str) -> bytes:
    last_error: Exception | None = None
    for attempt in range(RETRIES + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
                },
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001 - registriamo qualunque errore di rete
            last_error = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"{type(last_error).__name__}: {last_error}")


def parse_source(source: dict, payload: bytes, seen_at: str) -> list[dict]:
    feed = feedparser.parse(payload)
    if feed.bozo and not feed.entries:
        raise RuntimeError(f"flusso non valido: {feed.bozo_exception}")
    items = []
    for entry in feed.entries:
        link = (entry.get("link") or "").strip()
        title = clean_text(entry.get("title"))
        if not link or not title:
            continue
        summary = clean_text(entry.get("summary") or entry.get("description"), SUMMARY_CHARS)
        cves = sorted({c.upper() for c in CVE_RE.findall(f"{title} {summary}")})
        item_id = hashlib.sha1(f"{source['id']}|{link}".encode("utf-8")).hexdigest()[:16]
        items.append(
            {
                "id": item_id,
                "source": source["id"],
                "title": title,
                "link": link,
                "summary": summary,
                "published": entry_date(entry),
                "first_seen": seen_at,
                "cves": cves,
            }
        )
    return items


def process_source(source: dict, seen_at: str) -> tuple[dict, list[dict]]:
    status = {
        "id": source["id"],
        "name": source["name"],
        "country": source["country"],
        "kind": source.get("kind", "notizie"),
        "url": source["url"],
        "verified": bool(source.get("verified", False)),
        "checked_at": seen_at,
        "ok": False,
        "count": 0,
        "error": None,
    }
    try:
        items = parse_source(source, fetch(source["url"]), seen_at)
        status["ok"] = True
        status["count"] = len(items)
        return status, items
    except Exception as exc:  # noqa: BLE001
        status["error"] = str(exc)[:300]
        return status, []


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def sort_key(item: dict) -> str:
    return item.get("published") or item["first_seen"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", default="sources.yml")
    parser.add_argument("--out", default="data")
    args = parser.parse_args()

    config = yaml.safe_load(Path(args.sources).read_text(encoding="utf-8"))
    sources = [s for s in config.get("sources", []) if s.get("enabled", True)]
    if not sources:
        print("Nessuna fonte attiva in sources.yml", file=sys.stderr)
        return 1

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    seen_at = now_iso()

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda s: process_source(s, seen_at), sources))

    # Unione con lo storico: le voci gia' note mantengono il loro first_seen.
    existing = {i["id"]: i for i in load_json(out_dir / "items.json", {}).get("items", [])}
    active_ids = {s["id"] for s in sources}
    for status, items in results:
        for item in items:
            old = existing.get(item["id"])
            if old:
                item["first_seen"] = old["first_seen"]
            existing[item["id"]] = item

    cutoff = (datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)).isoformat()
    merged = [i for i in existing.values() if i["source"] in active_ids and sort_key(i) >= cutoff]
    merged.sort(key=sort_key, reverse=True)
    merged = merged[:MAX_ITEMS]

    sources_meta = {
        st["id"]: {k: st[k] for k in ("name", "country", "kind", "url", "verified")}
        for st, _ in results
    }
    (out_dir / "items.json").write_text(
        json.dumps({"updated": seen_at, "sources": sources_meta, "items": merged}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    (out_dir / "status.json").write_text(
        json.dumps({"updated": seen_at, "sources": [st for st, _ in results]}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )

    ok = sum(1 for st, _ in results if st["ok"])
    print(f"Fonti riuscite: {ok}/{len(results)} - voci totali: {len(merged)}")
    for st, _ in results:
        mark = "OK " if st["ok"] else "ERR"
        detail = f"{st['count']} voci" if st["ok"] else st["error"]
        print(f"  [{mark}] {st['id']}: {detail}")

    # Fallire solo se nessuna fonte risponde (probabile problema di rete generale).
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
