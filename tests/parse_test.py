"""Every valid fixture renders to exactly its .json; every input field reaches
the output; every invalid fixture is rejected for the reason in its .why."""
import json

from testlib import check, done, fixture_names, read
import p2pdir

valid = fixture_names("valid")
invalid = fixture_names("invalid")
check("there are valid fixtures", len(valid) >= 5, str(len(valid)))
check("there are invalid fixtures", len(invalid) >= 15, str(len(invalid)))

for name in valid:
    call = name.split("--")[0]
    text = read("valid", name, ".txt")
    want = json.loads(read("valid", name, ".json"))
    try:
        got = p2pdir.parse_listing(text, call)
    except p2pdir.ListingError as exc:
        check(f"valid {name} parses", False, str(exc))
        continue
    check(f"valid {name} matches its .json", got == want, json.dumps(got)[:200])

    # Every value in the input appears in the output: a renderer that drops or
    # rewrites a field fails here even if the .json was regenerated from it.
    for raw in text.decode("utf-8-sig").replace("\r", "").split("\n"):
        key, _, rest = raw.strip().partition(":")
        key, rest = key.strip().lower(), rest.strip()
        if key == "entry":
            freq, mode, width, control, hours = rest.split(None, 4)
            hit = [e for e in got["entries"]
                   if e["centre_khz"] == float(freq) and e["mode"] == mode.upper()
                   and e.get("bw_hz", e.get("baud")) == int(width)
                   and e["control"] == control.lower() and e["hours"] == hours.strip()]
            check(f"valid {name}: entry '{rest[:30]}' carried whole", bool(hit))
        elif key == "grid":
            check(f"valid {name}: grid carried", got["grid"].upper() == rest.upper())
        elif key == "note":
            check(f"valid {name}: note carried", got["note"] == rest)

    # Round trip: canonical text of the row parses back to the same row.
    again = p2pdir.parse_listing(p2pdir.render_listing(got), call)
    again.pop("warnings", None)
    base = {k: v for k, v in got.items() if k != "warnings"}
    check(f"valid {name} round-trips", again == base)

for name in invalid:
    call = name.split("--")[0]
    why = read("invalid", name, ".why").decode().strip()
    try:
        p2pdir.parse_listing(read("invalid", name, ".txt"), call)
        check(f"invalid {name} rejected", False, "accepted")
    except p2pdir.ListingError as exc:
        check(f"invalid {name} rejected as {why}", exc.code == why, exc.code)

# Positive control for the field-coverage check: a parser that drops the note
# must be caught by the same comparison.
row = p2pdir.parse_listing(read("valid", "N9ABC--basic", ".txt"), "N9ABC")
row["note"] = ""
check("control: a dropped note is detected",
      row != json.loads(read("valid", "N9ABC--basic", ".json")))

done()
