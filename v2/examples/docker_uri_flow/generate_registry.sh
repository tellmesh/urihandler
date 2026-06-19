#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/../../.." && pwd)"
OUT_DIR="$DIR/generated"

mkdir -p "$OUT_DIR"

echo "== scan artifacts -> generated/bindings.v2.json =="
PYTHONPATH="$ROOT/adapters/python" python3 -m urirun.v2 scan "$DIR" \
  --out "$OUT_DIR/bindings.v2.json" \
  --registry-out "$OUT_DIR/registry.json"

echo "== validate generated bindings =="
PYTHONPATH="$ROOT/adapters/python" python3 -m urirun.v2 validate "$OUT_DIR/bindings.v2.json"

echo "== list generated registry =="
PYTHONPATH="$ROOT/adapters/python" python3 -m urirun.v2 list "$OUT_DIR/registry.json" \
  | tee "$OUT_DIR/routes.txt"

echo
echo "Generated:"
echo "  $OUT_DIR/bindings.v2.json"
echo "  $OUT_DIR/registry.json"
echo "  $OUT_DIR/routes.txt"
