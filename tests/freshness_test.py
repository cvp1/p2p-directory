"""Fixed clock: 89 days fresh, 90 stale, 179 present, 180 removed."""
import datetime as dt
import json
import os
import tempfile

from testlib import check, done
import build

LISTING = "P2PDIR 1\ngrid: EM12\nentry: 7103.5 VARA_HF 500 attended daily\n"
NOW = "2026-11-10T12:00:00Z"
TODAY = dt.date(2026, 11, 10)


def run(ages):
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "listings"))
        for call, age in ages.items():
            with open(os.path.join(root, "listings", call + ".txt"), "w") as fh:
                fh.write(LISTING)
            with open(os.path.join(root, "listings", call + ".json"), "w") as fh:
                json.dump({"confirmed": (TODAY - dt.timedelta(days=age)).isoformat()}, fh)
        out = os.path.join(root, "out")
        rc = build.build(root, out, build.parse_now(NOW), strict=False)
        with open(os.path.join(out, "directory.json")) as fh:
            return rc, {s["call"]: s for s in json.load(fh)["stations"]}


rc, rows = run({"N0AAA": 0, "N0BBB": 89, "N0CCC": 90, "N0DDD": 179, "N0EEE": 180, "N0FFF": 400})
check("build succeeds", rc == 0)
check("positive control: a listing confirmed today is present and fresh",
      "N0AAA" in rows and rows["N0AAA"]["stale"] is False)
check("89 days: fresh", rows.get("N0BBB", {}).get("stale") is False)
check("90 days: stale", rows.get("N0CCC", {}).get("stale") is True)
check("179 days: still published, stale", rows.get("N0DDD", {}).get("stale") is True)
check("180 days: removed", "N0EEE" not in rows)
check("400 days: removed", "N0FFF" not in rows)

# A confirmed date in the future is a bad listing, not a forever-fresh one.
with tempfile.TemporaryDirectory() as root:
    os.makedirs(os.path.join(root, "listings"))
    open(os.path.join(root, "listings", "N0AAA.txt"), "w").write(LISTING)
    json.dump({"confirmed": "2027-01-01"}, open(os.path.join(root, "listings", "N0AAA.json"), "w"))
    rc = build.build(root, os.path.join(root, "out"), build.parse_now(NOW), strict=True)
    check("future confirmed date rejected under --strict", rc == 1)
    os.remove(os.path.join(root, "listings", "N0AAA.json"))
    rc = build.build(root, os.path.join(root, "out"), build.parse_now(NOW), strict=True)
    check("missing sidecar rejected under --strict", rc == 1)
done()
