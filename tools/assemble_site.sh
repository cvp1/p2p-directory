#!/bin/sh
# Copy the static parts of the site next to the built v1/ files.
# The spec becomes index.html with a minimal stdlib Markdown renderer.
set -eu
out="${1:-site}"
here="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$out/fixtures" "$out/templates"
cp "$here/find.html" "$out/find.html"
cp -R "$here/fixtures/." "$out/fixtures/"
cp "$here/templates/P2PDIR-listing.txt" "$out/templates/"
python3 "$here/tools/spec_html.py" "$here/SPEC.md" "$out/index.html"
