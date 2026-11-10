# p2p-directory

A public directory of amateur radio stations that welcome **peer-to-peer Winlink**
connections, in a form any Winlink client can read.

- **The spec, and how to get listed:** [SPEC.md](SPEC.md) (published as the site's front page)
- **Search:** `find.html` on the site
- **Data:** `v1/directory.json`, `.csv`, `.txt` on the site, rebuilt on every merge and nightly

## How it works

`listings/<CALL>.txt` holds one station's listing in the canonical text format, with a
sidecar `listings/<CALL>.json` recording when the operator last confirmed it. `build.py`
validates every listing with `p2pdir.py`, applies the stale (90 days) and removed (180
days) ages, and writes the published files. GitHub Actions runs the tests on every pull
request, and builds and deploys GitHub Pages on merge and nightly. There is no server.

Listings are added by the maintainer from operators who asked (a Winlink message from
their callsign, or an issue confirmed by Winlink message). Git history is the audit trail.

## Develop

Python 3.12+, standard library only.

```
sh tests/run_all.sh                          # every test
python3 p2pdir.py listings/N9ABC.txt         # validate one listing
python3 build.py --out /tmp/site/v1          # build the data
sh tools/assemble_site.sh /tmp/site          # the rest of the site
```

## Licences

Code: MIT ([LICENSE](LICENSE)). Directory data (`listings/` and everything built from it):
CC0 1.0 ([LICENSE-DATA](LICENSE-DATA)).
