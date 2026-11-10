"""The assembled site has every page, the spec renders without raw markdown
left over, and the template's body is a valid listing once filled in."""
import os
import re
import subprocess
import sys
import tempfile

from testlib import ROOT, check, done
import p2pdir

sys.path.insert(0, os.path.join(ROOT, "tools"))
import spec_html  # noqa: E402

with tempfile.TemporaryDirectory() as out:
    rc = subprocess.run(["sh", os.path.join(ROOT, "tools", "assemble_site.sh"), out]).returncode
    check("assemble_site succeeds", rc == 0)
    for rel in ("index.html", "find.html", "templates/P2PDIR-listing.txt",
                "fixtures/valid/N9ABC--basic.txt", "fixtures/invalid/N9ABC--bad-width.why"):
        check(f"site has {rel}", os.path.exists(os.path.join(out, rel)))
    page = open(os.path.join(out, "index.html"), encoding="utf-8").read()
    check("no raw markdown links left", "](" not in page)
    check("no raw bold markers left", "**" not in page)
    check("spec has its tables", page.count("<table>") >= 3)
    check("every link has an href", len(re.findall(r"<a href=", page)) >= 8)

check("control: a code-text link renders as a link",
      spec_html.inline("[`x.json`](x.json)") == '<a href="x.json"><code>x.json</code></a>')
check("HTML in the spec is escaped", "<script>" not in spec_html.inline("<script>"))

# Fill the template the way Pat does (Def + Var) and parse the body.
tmpl = open(os.path.join(ROOT, "templates", "P2PDIR-listing.txt"), encoding="utf-8").read()
answers = {"grid": "EM12", "freq": "7103.5", "mode": "VARA_HF", "width": "500",
           "control": "attended", "hours": "daily 1400-1600Z", "note": "NVIS dipole"}
head, _, body = tmpl.partition("Msg:\n")
defined = re.findall(r"^Def:\s*(\w+)=", head, re.M)
check("template defines every field it uses", sorted(defined) == sorted(answers))
check("template prompts one per line (Pat's Ask regex takes one per line)",
      all(line.count("<Ask") + line.count("<Select") <= 1 for line in head.splitlines()))
filled = re.sub(r"<Var (\w+)>", lambda m: answers[m.group(1)], body)
row = p2pdir.parse_listing(filled, "N9ABC")
check("filled template body is a valid listing", row["entries"][0]["mode"] == "VARA_HF")
done()
