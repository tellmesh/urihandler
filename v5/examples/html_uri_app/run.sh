#!/usr/bin/env sh
set -eu

DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PORT="${PORT:-41735}"

python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$DIR"
