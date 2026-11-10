One station per pair of files:

- `<CALL>.txt` — the listing exactly as the operator sent it (SPEC.md, "The listing format").
- `<CALL>.json` — `{"confirmed": "YYYY-MM-DD", "source": "maintainer"}`; `confirmed` is the
  date the operator last said the listing is right.

To add or refresh a listing: write both files, run `python3 build.py --strict --out /tmp/v1`,
open a pull request whose description says how the operator asked (message date, or the
issue and the confirming message). To remove one, delete both files.
