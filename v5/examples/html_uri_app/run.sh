#!/usr/bin/env sh
set -eu

DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ENV_FILE="${ENV_FILE:-$DIR/.env}"

if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

python3 "$DIR/backend.py"
