#!/bin/sh
# Run every test script; exit non-zero if any fails.
cd "$(dirname "$0")" || exit 1
rc=0
for t in *_test.py; do
  echo "== $t"
  python3 "$t" || rc=1
done
exit $rc
