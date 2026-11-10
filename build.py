"""build — validate every listing and write the published directory.

    python3 build.py [--now 2026-11-10T18:00:00Z] [--strict]

Reads `listings/<CALL>.txt` with its sidecar `listings/<CALL>.json`
(`{"confirmed": "YYYY-MM-DD", "source": "maintainer"}`), applies the
stale/remove ages, and writes `v1/directory.json`, `v1/directory.csv` and
`v1/directory.txt`.

A listing that fails validation does not change what is published for that
call: its row from the previous `v1/directory.json` is carried forward. With
`--strict` (CI on pull requests) any rejection exits 1 and nothing is written.
Same inputs and same `--now` give byte-identical output.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import sys

import p2pdir

STALE_DAYS = 90
REMOVE_DAYS = 180
LICENCE = "CC0-1.0"
SOURCES = ("maintainer", "message")
CSV_FIELDS = ("call", "grid", "confirmed", "stale", "centre_khz", "dial_khz", "mode",
              "bw_hz", "baud", "control", "hours", "flags", "note")


class MetaError(ValueError):
    pass


def parse_now(text: str | None) -> dt.datetime:
    if not text:
        return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(dt.timezone.utc)


def read_meta(path: str, today: dt.date) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            meta = json.load(fh)
    except FileNotFoundError:
        raise MetaError("meta-missing") from None
    except (OSError, ValueError) as exc:
        raise MetaError(f"meta-unreadable: {exc}") from None
    try:
        confirmed = dt.date.fromisoformat(str(meta.get("confirmed")))
    except ValueError:
        raise MetaError("meta-bad-confirmed") from None
    if confirmed > today:
        raise MetaError("meta-confirmed-in-future")
    source = meta.get("source", "maintainer")
    if source not in SOURCES:
        raise MetaError("meta-bad-source")
    return {"confirmed": confirmed.isoformat(), "source": source}


def age_row(row: dict, today: dt.date) -> dict | None:
    """Apply freshness to a station row; None means it is removed."""
    age = (today - dt.date.fromisoformat(row["confirmed"])).days
    if age >= REMOVE_DAYS:
        return None
    row = dict(row)
    row["stale"] = age >= STALE_DAYS
    return row


def previous_rows(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        return {s["call"]: s for s in doc.get("stations", []) if s.get("call")}
    except (OSError, ValueError, TypeError, AttributeError):
        return {}


def collect(root: str, today: dt.date, previous: dict) -> tuple[list, list, list]:
    """Return (rows, rejected, removed). rejected = [(call, reason)]."""
    listing_dir = os.path.join(root, "listings")
    rows, rejected, removed = [], [], []
    names = sorted(n for n in os.listdir(listing_dir) if n.endswith(".txt")) if os.path.isdir(listing_dir) else []
    for name in names:
        call = name[:-4].upper()
        try:
            with open(os.path.join(listing_dir, name), "rb") as fh:
                row = p2pdir.parse_listing(fh.read(), call)
            meta = read_meta(os.path.join(listing_dir, name[:-4] + ".json"), today)
        except (p2pdir.ListingError, MetaError) as exc:
            rejected.append((call, str(exc)))
            if call in previous:
                kept = age_row(previous[call], today)
                if kept is not None:
                    rows.append(kept)
            continue
        for warning in row.pop("warnings", []):
            print(f"{call}: {warning}", file=sys.stderr)
        station = {"call": row["call"], "grid": row["grid"], "note": row["note"],
                   "confirmed": meta["confirmed"], "source": meta["source"],
                   "entries": row["entries"]}
        aged = age_row(station, today)
        if aged is None:
            removed.append(call)
        else:
            rows.append(aged)
    rows.sort(key=lambda r: r["call"])
    return rows, rejected, removed


def render_json(rows: list, now: dt.datetime) -> str:
    doc = {"schema": p2pdir.SPEC_VERSION, "generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
           "licence": LICENCE, "count": len(rows), "stations": rows}
    return json.dumps(doc, indent=1, ensure_ascii=False) + "\n"


def _cell(value) -> str:
    text = "" if value is None else str(value)
    # Spreadsheet formula injection: a leading = + - @ is made literal.
    if text[:1] in ("=", "+", "-", "@"):
        text = "'" + text
    return text


def render_csv(rows: list) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(CSV_FIELDS)
    for r in rows:
        for e in r["entries"]:
            values = {"call": r["call"], "grid": r["grid"], "confirmed": r["confirmed"],
                      "stale": "yes" if r["stale"] else "no", "centre_khz": e["centre_khz"],
                      "dial_khz": p2pdir.dial_khz(e["centre_khz"], e["mode"]), "mode": e["mode"],
                      "bw_hz": e.get("bw_hz"), "baud": e.get("baud"), "control": e["control"],
                      "hours": e["hours"], "flags": " ".join(e["flags"]), "note": r["note"]}
            writer.writerow([_cell(values[f]) for f in CSV_FIELDS])
    return out.getvalue()


def render_text(rows: list, now: dt.datetime) -> str:
    lines = [f"P2P directory, schema {p2pdir.SPEC_VERSION}, generated "
             f"{now.strftime('%Y-%m-%dT%H:%M:%SZ')}, {len(rows)} stations, {LICENCE}", ""]
    for r in rows:
        stale = " STALE" if r["stale"] else ""
        lines.append(f"{r['call']}  {r['grid']}  confirmed {r['confirmed']}{stale}")
        for e in r["entries"]:
            width = f"{e['bw_hz']} Hz" if "bw_hz" in e else f"{e['baud']} bd"
            flags = f"  [{' '.join(e['flags'])}]" if e["flags"] else ""
            lines.append(f"  {e['centre_khz']} kHz  {e['mode']} {width}  {e['control']}  {e['hours']}{flags}")
        if r["note"]:
            lines.append(f"  note: {r['note']}")
        lines.append("")
    return "\n".join(lines)


def write_if_changed(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    os.replace(tmp, path)


def build(root: str, out_dir: str, now: dt.datetime, strict: bool) -> int:
    json_path = os.path.join(out_dir, "directory.json")
    rows, rejected, removed = collect(root, now.date(), previous_rows(json_path))
    for call, reason in rejected:
        print(f"REJECTED {call}: {reason}", file=sys.stderr)
    for call in removed:
        print(f"removed (older than {REMOVE_DAYS} days): {call}", file=sys.stderr)
    if strict and rejected:
        return 1
    write_if_changed(json_path, render_json(rows, now))
    write_if_changed(os.path.join(out_dir, "directory.csv"), render_csv(rows))
    write_if_changed(os.path.join(out_dir, "directory.txt"), render_text(rows, now))
    print(f"{len(rows)} stations written to {out_dir}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=here, help="repo root (holds listings/)")
    ap.add_argument("--out", help="output directory (default <root>/site/v1)")
    ap.add_argument("--now", help="UTC time to build as (ISO 8601); default now")
    ap.add_argument("--strict", action="store_true", help="exit 1 on any rejected listing, write nothing")
    args = ap.parse_args(argv)
    out = args.out or os.path.join(args.root, "site", "v1")
    return build(args.root, out, parse_now(args.now), args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
