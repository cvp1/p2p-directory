"""Size and length caps, control characters, and HTML staying inert."""
import json
import os
import re

from testlib import ROOT, check, done
import p2pdir

H = "P2PDIR 1\ngrid: EM12\n"
E = "entry: 7103.5 VARA_HF 500 attended daily\n"


def code(text, call="N9ABC"):
    try:
        p2pdir.parse_listing(text, call)
        return "ok"
    except p2pdir.ListingError as exc:
        return exc.code


pad = p2pdir.MAX_BYTES - len((H + E + "note: ").encode())
check("exactly 2048 bytes is accepted (positive control)",
      code(H + E + "note: " + "n" * 80 + "\n" + " " * (pad - 81)) == "ok")
check("2049 bytes is rejected", code(H + E + "note: x\n" + " " * (pad - 1)) == "too-big")
check("12 entries accepted", code(H + E * 12) == "ok")
check("13 entries rejected", code(H + E * 13) == "too-many-entries")
check("note of 80 accepted", code(H + E + "note: " + "a" * 80) == "ok")
check("note of 81 rejected", code(H + E + "note: " + "a" * 81) == "note-too-long")
check("hours of 40 accepted", code(H + "entry: 7103.5 VARA_HF 500 attended " + "h" * 40) == "ok")
check("hours of 41 rejected", code(H + "entry: 7103.5 VARA_HF 500 attended " + "h" * 41) == "hours-too-long")
check("a multibyte note counts characters", code(H + E + "note: " + "é" * 80) == "ok")
for ch, label in (("\x00", "NUL"), ("\x07", "BEL"), ("\x1b", "ESC"), ("\x7f", "DEL"), ("\x85", "NEL")):
    check(f"{label} in a note is rejected", code(H + E + f"note: a{ch}b") == "control-char")
check("a tab is allowed (positive control)", code(H + E + "note: a\tb") == "ok")

# HTML is stored verbatim; JSON keeps it as data; find.html never uses innerHTML.
row = p2pdir.parse_listing(H + "entry: 7103.5 VARA_HF 500 attended <img src=x onerror=alert(1)>\n"
                           "note: <script>alert(1)</script>", "N9ABC")
check("HTML kept verbatim in the row", row["note"] == "<script>alert(1)</script>")
blob = json.dumps(row)
check("JSON round-trips the HTML as a string", json.loads(blob)["note"] == row["note"])
with open(os.path.join(ROOT, "find.html"), encoding="utf-8") as fh:
    page = fh.read()
check("find.html never assigns innerHTML or outerHTML", not re.search(r"(inner|outer)HTML\s*=", page))
check("find.html never uses insertAdjacentHTML or document.write",
      "insertAdjacentHTML" not in page and "document.write" not in page)
check("find.html sets row text with textContent", "textContent" in page)
done()
