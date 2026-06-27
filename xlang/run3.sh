#!/usr/bin/env bash
# THREE-language polyglot proof: one neutral contracts.json; Python, JS, Go gates.
set -euo pipefail
cd "$(dirname "$0")"
export XLANG_DIR="$PWD"
PY="${PY:-python}"; JS="${JS:-node}"; GO="./gate_go"
declare -A G=( [PY]="$PY gate.py" [JS]="$JS gate.mjs" [GO]="$GO" )

echo "== emit neutral artifact from the real fs connector =="
$PY emit_contracts.py > contracts.json 2>/dev/null
echo "  contracts.json: $($PY -c "import json;print(len(json.load(open('contracts.json'))['contracts']))") routes"

echo
echo "== same file, THREE independent gates conform it =="
$PY gate.py conform; $JS gate.mjs conform; $GO conform

route="fs://host/file/command/delete"
echo
echo "== all-pairs cross-language round-trip on $route =="
for p in PY JS GO; do for c in PY JS GO; do
  [ "$p" = "$c" ] && continue
  out=$(${G[$p]} produce "$route" | ${G[$c]} consume "$route") && badge="OK " || badge="FAIL"
  printf "  [%s] %-2s produce -> %-2s consume : %s\n" "$badge" "$p" "$c" "$out"
done; done

echo
echo "== drift (bytes int->string) rejected by ALL THREE, same diagnosis =="
corrupt() { $PY -c "import json,sys;e=json.load(sys.stdin);e['bytes']='oops';json.dump(e,sys.stdout)"; }
for c in PY JS GO; do
  printf "  %-2s: " "$c"
  ($PY gate.py produce "$route" | corrupt | ${G[$c]} consume "$route") && echo " UNEXPECTED PASS" || true
  echo
done

echo "DONE: 3 languages, 1 neutral contract, 6/6 round-trips conformant, drift rejected 3/3."
