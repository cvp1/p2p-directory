"""p2pdir — reference parser, validator and renderer for P2P directory listings.

Stdlib only. One listing is plain text (SPEC.md, "The listing format"):

    P2PDIR 1
    grid: EM12
    entry: 7103.5 VARA_HF 500 attended daily 1400-1600Z
    note: NVIS dipole, 100 W

`parse_listing(text, call)` returns a station dict ready for directory.json, or
raises `ListingError` whose `.code` names the first thing wrong. A listing is
accepted whole or not at all.
"""

from __future__ import annotations

import math
import re

SPEC_VERSION = 1
HEADER = "P2PDIR 1"
MAX_BYTES = 2048
MAX_ENTRIES = 12
MAX_NOTE = 80
MAX_HOURS = 40

# mode -> (third field name, allowed values, dial offset in Hz from centre)
# Dial offsets follow Pat v1.0.0 app/freq.go:68-92: modes containing "fm" are
# not shifted; PACTOR, ARDOP and VARA HF dial 1500 Hz below centre (USB);
# packet is not shifted.
MODES = {
    "VARA_HF": ("bw_hz", (500, 2300, 2750), -1500),
    "VARA_FM": ("bw_hz", (12500, 25000), 0),
    "ARDOP": ("bw_hz", (200, 500, 1000, 2000), -1500),
    "PACTOR": ("bw_hz", (500, 2400), -1500),
    "PACKET": ("baud", (300, 1200, 9600), 0),
    "ROBUST_PACKET": ("baud", (300, 600), None),  # no dial rule in v1
}

# Occupied width assumed for flagging when the third field is a baud rate.
PACKET_WIDTH_HZ = 500
ROBUST_PACKET_WIDTH_HZ = 500

CONTROLS = ("attended", "auto", "sked")

# Amateur allocations in kHz (union across ITU regions, LF/MF beacons left out).
BANDS = (
    ("160m", 1800, 2000), ("80m", 3500, 4000), ("60m", 5250, 5450),
    ("40m", 7000, 7300), ("30m", 10100, 10150), ("20m", 14000, 14350),
    ("17m", 18068, 18168), ("15m", 21000, 21450), ("12m", 24890, 24990),
    ("10m", 28000, 29700), ("6m", 50000, 54000), ("4m", 70000, 71000),
    ("2m", 144000, 148000), ("1.25m", 219000, 225000), ("70cm", 420000, 450000),
    ("33cm", 902000, 928000), ("23cm", 1240000, 1300000),
)

# 47 CFR 97.221(b): automatic control of data emissions on 6 m and up, and on
# these nine HF segments (kHz).
AUTO_SEGMENTS_KHZ = (
    (3585.0, 3600.0), (7100.0, 7105.0), (10140.0, 10150.0),
    (14095.0, 14099.5), (14100.5, 14112.0), (18105.0, 18110.0),
    (21090.0, 21100.0), (24925.0, 24930.0), (28120.0, 28189.0),
)
AUTO_ANYWHERE_FROM_KHZ = 50000.0
FLAG_HF_AUTO = "hf-auto-outside-97.221b"

CALL_RE = re.compile(r"^[A-Z0-9]{1,3}[0-9][A-Z]{1,4}$")
US_CALL_RE = re.compile(r"^(A[A-L]|K|N|W)")
GRID_RE = re.compile(r"^[A-R]{2}[0-9]{2}([A-X]{2})?$")
FREQ_RE = re.compile(r"^[0-9]{1,7}(\.[0-9]{1,3})?$")
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


class ListingError(ValueError):
    """A listing that must not be published. `code` is stable; `line` is 1-based."""

    def __init__(self, code: str, detail: str = "", line: int | None = None):
        self.code, self.detail, self.line = code, detail, line
        where = f" (line {line})" if line else ""
        super().__init__(f"{code}{where}: {detail}" if detail else f"{code}{where}")


def valid_call(call: str) -> bool:
    return bool(CALL_RE.match(call or ""))


def band_of(khz: float) -> str | None:
    for name, lo, hi in BANDS:
        if lo <= khz <= hi:
            return name
    return None


def occupied_hz(mode: str, width: int) -> int:
    if mode == "PACKET":
        return PACKET_WIDTH_HZ
    if mode == "ROBUST_PACKET":
        return ROBUST_PACKET_WIDTH_HZ
    return width


def flags_for(call: str, entry: dict) -> list[str]:
    """Labels for clients to show. Never a reason to refuse a listing."""
    flags = []
    khz = entry["centre_khz"]
    if entry["control"] == "auto" and US_CALL_RE.match(call) and khz < AUTO_ANYWHERE_FROM_KHZ:
        width = occupied_hz(entry["mode"], entry.get("bw_hz") or entry.get("baud"))
        lo, hi = khz - width / 2000.0, khz + width / 2000.0
        if not any(a <= lo and hi <= b for a, b in AUTO_SEGMENTS_KHZ):
            flags.append(FLAG_HF_AUTO)
    return flags


def dial_khz(centre_khz: float, mode: str) -> float | None:
    """Dial frequency to set on the rig (what Pat's `freq=` means), or None if
    v1 defines no rule for the mode."""
    rule = MODES.get(mode)
    if rule is None or rule[2] is None:
        return None
    return round(centre_khz + rule[2] / 1000.0, 3)


def _num(text: str) -> int | float:
    value = float(text)
    return int(value) if value.is_integer() else value


def _parse_entry(rest: str, lineno: int) -> dict:
    parts = rest.split(None, 4)
    if len(parts) < 5:
        raise ListingError("entry-fields", "entry needs: centre_khz mode width control hours", lineno)
    freq, mode, width, control, hours = parts
    if not FREQ_RE.match(freq):
        raise ListingError("bad-frequency", freq, lineno)
    khz = float(freq)
    if band_of(khz) is None:
        raise ListingError("out-of-band", freq, lineno)
    mode = mode.upper()
    if mode not in MODES:
        raise ListingError("unknown-mode", mode, lineno)
    field, allowed, _ = MODES[mode]
    if not width.isdigit() or int(width) not in allowed:
        raise ListingError("bad-width", f"{mode} {field} must be one of {allowed}", lineno)
    control = control.lower()
    if control not in CONTROLS:
        raise ListingError("bad-control", control, lineno)
    hours = hours.strip()
    if len(hours) > MAX_HOURS:
        raise ListingError("hours-too-long", f"{len(hours)} > {MAX_HOURS}", lineno)
    entry = {"centre_khz": _num(freq), "mode": mode, field: int(width),
             "control": control, "hours": hours}
    return entry


def parse_listing(text: str | bytes, call: str) -> dict:
    """Parse and validate one listing for `call`. Returns the station row."""
    call = (call or "").upper()
    if not valid_call(call):
        raise ListingError("bad-call", call)
    raw = text if isinstance(text, bytes) else text.encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise ListingError("too-big", f"{len(raw)} > {MAX_BYTES} bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ListingError("not-utf8", str(exc)) from None
    text = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")

    header_seen = False
    grid = note = None
    entries: list[dict] = []
    warnings: list[str] = []
    for lineno, line in enumerate(text.split("\n"), 1):
        if CONTROL_CHARS.search(line):
            raise ListingError("control-char", "", lineno)
        line = line.strip()
        if not line:
            continue
        if not header_seen:
            first = " ".join(line.split()).upper()
            if re.fullmatch(r"P2PDIR \d+", first) and first != HEADER:
                raise ListingError("unsupported-version", first, lineno)
            if first != HEADER:
                raise ListingError("no-header", f"first line must be {HEADER!r}", lineno)
            header_seen = True
            continue
        key, sep, rest = line.partition(":")
        if not sep:
            raise ListingError("not-key-value", line[:40], lineno)
        key, rest = key.strip().lower(), rest.strip()
        if key == "grid":
            if grid is not None:
                raise ListingError("duplicate-key", "grid", lineno)
            g = rest[:2].upper() + rest[2:4] + rest[4:6].lower()
            if not GRID_RE.match(g.upper()) or len(rest) not in (4, 6):
                raise ListingError("bad-grid", rest, lineno)
            grid = g
        elif key == "note":
            if note is not None:
                raise ListingError("duplicate-key", "note", lineno)
            if len(rest) > MAX_NOTE:
                raise ListingError("note-too-long", f"{len(rest)} > {MAX_NOTE}", lineno)
            note = rest
        elif key == "entry":
            entries.append(_parse_entry(rest, lineno))
            if len(entries) > MAX_ENTRIES:
                raise ListingError("too-many-entries", f"> {MAX_ENTRIES}", lineno)
        else:
            warnings.append(f"line {lineno}: unknown key {key!r} ignored")
    if not header_seen:
        raise ListingError("no-header", "empty listing")
    if grid is None:
        raise ListingError("no-grid")
    if not entries:
        raise ListingError("no-entries")
    for entry in entries:
        entry["flags"] = flags_for(call, entry)
    row = {"call": call, "grid": grid, "note": note or "", "entries": entries}
    if warnings:
        row["warnings"] = warnings
    return row


def grid_to_latlon(grid: str) -> tuple[float, float]:
    """Centre of a 4- or 6-character Maidenhead square."""
    g = grid.upper()
    lon = (ord(g[0]) - 65) * 20 - 180 + int(g[2]) * 2
    lat = (ord(g[1]) - 65) * 10 - 90 + int(g[3])
    if len(g) >= 6:
        lon += (ord(g[4]) - 65) * (2 / 24) + (1 / 24)
        lat += (ord(g[5]) - 65) * (1 / 24) + (1 / 48)
    else:
        lon += 1
        lat += 0.5
    return lat, lon


def distance_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def render_listing(row: dict) -> str:
    """Canonical text for a station row (round-trips through parse_listing)."""
    lines = [HEADER, f"grid: {row['grid']}"]
    for e in row["entries"]:
        width = e.get("bw_hz", e.get("baud"))
        lines.append(f"entry: {e['centre_khz']} {e['mode']} {width} {e['control']} {e['hours']}")
    if row.get("note"):
        lines.append(f"note: {row['note']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    import sys

    ap = argparse.ArgumentParser(description="Validate a P2P directory listing.")
    ap.add_argument("file", help="listing text file (CALL.txt) or - for stdin")
    ap.add_argument("--call", help="callsign (default: the file name)")
    args = ap.parse_args(argv)
    if args.file == "-":
        data, call = sys.stdin.buffer.read(), args.call
    else:
        with open(args.file, "rb") as fh:
            data = fh.read()
        call = args.call or args.file.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    try:
        row = parse_listing(data, call or "")
    except ListingError as exc:
        print(f"rejected: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(row, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
