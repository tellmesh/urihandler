#!/usr/bin/env bash
# Cross-ROUTE, cross-LANGUAGE handoff over a wire: producer in one language, consumer in another,
# composing through one neutral contract (with wires + ["int"] list schemas).
set -euo pipefail
cd "$(dirname "$0")"
PY="${PY:-python}"; JS="${JS:-node}"
declare -A G=( [PY]="$PY peer.py" [JS]="$JS peer.mjs" )

echo "== static wire conform (both languages) =="
$PY peer.py conform
$JS peer.mjs conform

rt() {  # rt <label> <prod-lang> <produce-route> <cons-lang> <producer> <consumer>
  local label="$1" pl="$2" route="$3" cl="$4" prod="$5" cons="$6"
  local out; out=$(${G[$pl]} produce "$route" | ${G[$cl]} consume "$prod" "$cons") && badge="OK " || badge="FAIL"
  printf "  [%s] %-26s -> %s\n" "$badge" "$label" "$out"
}

echo
echo "== cross-route cross-language handoff =="
rt "JS close  -> PY restore (full)"    JS window/command/close   PY window/command/close  window/command/restore
rt "PY close  -> JS restore (full)"    PY window/command/close   JS window/command/close  window/command/restore
rt "PY capture-> JS click (partial)"   PY screen/query/capture   JS screen/query/capture  abs/command/click
rt "JS capture-> PY click (partial)"   JS screen/query/capture   PY screen/query/capture  abs/command/click

echo
echo "== drift across the wire: corrupt snapshot (obj -> string), rejected by both =="
corrupt() { $PY -c "import json,sys;e=json.load(sys.stdin);e['snapshot']='not-an-object';json.dump(e,sys.stdout)"; }
for c in PY JS; do
  printf "  %-2s consumer: " "$c"
  ($PY peer.py produce window/command/close | corrupt | ${G[$c]} consume window/command/close window/command/restore) && echo " UNEXPECTED PASS" || echo ""
done

echo
echo "DONE: wires + [\"int\"] list schemas compose producer/consumer across languages; drift rejected."
