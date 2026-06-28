#!/usr/bin/env bash
# Pin each extracted-package sibling's `urirun>=X` dependency floor to the hub's current
# VERSION, so a sibling can't silently require a STALE urirun. (urirun-widgets / -artifacts
# were pinned to urirun>=0.4.14 while the hub was 0.4.190 — a sibling installed from PyPI
# would then resolve an old urirun missing the APIs it actually uses.)
#
# Scope: the extracted packages only (NOT the ~40 feature connectors, which version
# independently). Idempotent — re-running with no drift is a no-op. Run from anywhere:
#
#   bash scripts/sync-sibling-floors.sh          # apply
#   bash scripts/sync-sibling-floors.sh --check  # report drift, exit 1 if any (CI gate)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SIB="$(cd "$ROOT/.." && pwd)"
V="$(cat "$ROOT/VERSION")"
CHECK="${1:-}"

PACKAGES=(
  urirun-connectors-toolkit urirun-contract urirun-runtime urirun-flow
  urirun-declarative urirun-widgets urirun-artifacts urirun-cdp
  urirun-connector-router urirun-connector-twin
)

drift=0
for name in "${PACKAGES[@]}"; do
  pp="$SIB/$name/pyproject.toml"
  [ -f "$pp" ] || continue
  before="$(grep -oE 'urirun>=[0-9][0-9.]*' "$pp" | head -1 || true)"
  [ -n "$before" ] || continue              # no urirun floor declared — leave as-is
  [ "$before" = "urirun>=$V" ] && continue   # already current
  drift=$((drift + 1))
  if [ "$CHECK" = "--check" ]; then
    echo "  DRIFT $name: $before (want urirun>=$V)"
  else
    sed -i -E "s/urirun>=[0-9][0-9.]*/urirun>=$V/g" "$pp"
    echo "  $name: $before -> urirun>=$V"
  fi
done

if [ "$CHECK" = "--check" ]; then
  [ "$drift" -eq 0 ] && echo "OK: all sibling floors == urirun>=$V" || { echo "FAIL: $drift sibling floor(s) drifted from urirun>=$V"; exit 1; }
else
  echo "synced $drift sibling floor(s) -> urirun>=$V"
fi
