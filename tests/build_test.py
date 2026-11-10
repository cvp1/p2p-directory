"""JSON, CSV and text agree; schema/count right; byte-identical reruns; a
rejected listing keeps its previously published row."""
import csv
import io
import json
import os
import shutil
import tempfile

from testlib import FIXTURES, check, done
import build

NOW = "2026-11-10T18:00:00Z"


def setup(root):
    os.makedirs(os.path.join(root, "listings"))
    for name in ("N9ABC--basic", "N9ABC--every-mode", "VE3XYZ--non-us-auto", "N9ABC--html-in-note"):
        call = {"N9ABC--basic": "N9ABC", "N9ABC--every-mode": "K1ABC",
                "VE3XYZ--non-us-auto": "VE3XYZ", "N9ABC--html-in-note": "W1AW"}[name]
        shutil.copy(os.path.join(FIXTURES, "valid", name + ".txt"), os.path.join(root, "listings", call + ".txt"))
        with open(os.path.join(root, "listings", call + ".json"), "w") as fh:
            json.dump({"confirmed": "2026-11-01", "source": "maintainer"}, fh)


def outputs(out):
    return {n: open(os.path.join(out, n), "rb").read() for n in ("directory.json", "directory.csv", "directory.txt")}


with tempfile.TemporaryDirectory() as root:
    setup(root)
    out = os.path.join(root, "out")
    check("strict build of valid listings succeeds", build.build(root, out, build.parse_now(NOW), True) == 0)
    first = outputs(out)
    build.build(root, out, build.parse_now(NOW), True)
    check("second run is byte-identical", outputs(out) == first)

    doc = json.loads(first["directory.json"])
    check("schema is 1", doc["schema"] == 1)
    check("count matches stations", doc["count"] == len(doc["stations"]) == 4)
    check("generated is the build clock", doc["generated"] == NOW)
    check("licence is CC0-1.0", doc["licence"] == "CC0-1.0")
    check("stations sorted by call", [s["call"] for s in doc["stations"]] == sorted(s["call"] for s in doc["stations"]))
    check("no parser warnings leak into JSON", all("warnings" not in s for s in doc["stations"]))

    rows = list(csv.DictReader(io.StringIO(first["directory.csv"].decode())))
    entries = [(s["call"], e) for s in doc["stations"] for e in s["entries"]]
    check("CSV has one row per entry", len(rows) == len(entries), f"{len(rows)} vs {len(entries)}")
    for (call, e), r in zip(entries, rows):
        same = (r["call"] == call and float(r["centre_khz"]) == e["centre_khz"] and r["mode"] == e["mode"]
                and r["control"] == e["control"] and r["hours"].lstrip("'") == e["hours"])
        check(f"CSV row {call} {e['centre_khz']} agrees with JSON", same)
    text = first["directory.txt"].decode()
    for call, e in entries:
        check(f"text lists {call} {e['centre_khz']}", f"{e['centre_khz']} kHz  {e['mode']}" in text)
    vara = next(r for r in rows if r["mode"] == "VARA_HF")
    check("CSV dial is centre - 1.5 kHz for VARA HF",
          abs(float(vara["dial_khz"]) - (float(vara["centre_khz"]) - 1.5)) < 1e-9)

    # Break one listing: strict refuses and writes nothing new; the nightly
    # (non-strict) build keeps that call's previous row untouched.
    with open(os.path.join(root, "listings", "N9ABC.txt"), "w") as fh:
        fh.write("P2PDIR 1\ngrid: EM12\nentry: 99999 FT8 1 auto x\n")
    check("strict build fails on a bad listing", build.build(root, out, build.parse_now(NOW), True) == 1)
    check("strict failure leaves outputs untouched", outputs(out) == first)
    check("non-strict build still succeeds", build.build(root, out, build.parse_now(NOW), False) == 0)
    after = {s["call"]: s for s in json.loads(outputs(out)["directory.json"])["stations"]}
    before = {s["call"]: s for s in doc["stations"]}
    check("rejected call keeps its previous row exactly", after.get("N9ABC") == before["N9ABC"])
    check("other calls unaffected", {k: v for k, v in after.items() if k != "N9ABC"}
          == {k: v for k, v in before.items() if k != "N9ABC"})

    # Positive control: with no previous output, the bad call is simply absent.
    os.remove(os.path.join(out, "directory.json"))
    build.build(root, out, build.parse_now(NOW), False)
    calls = {s["call"] for s in json.loads(outputs(out)["directory.json"])["stations"]}
    check("control: without a previous row the bad call is absent", "N9ABC" not in calls and len(calls) == 3)

    # Removing a listing file removes the station.
    os.remove(os.path.join(root, "listings", "VE3XYZ.txt"))
    build.build(root, out, build.parse_now(NOW), False)
    calls = {s["call"] for s in json.loads(outputs(out)["directory.json"])["stations"]}
    check("deleted listing file removes the station", "VE3XYZ" not in calls)

# CSV formula injection is neutralised.
check("CSV cell starting with = is made literal", build._cell("=HYPERLINK(1)") == "'=HYPERLINK(1)")
check("CSV plain cell unchanged", build._cell("daily") == "daily")
done()
