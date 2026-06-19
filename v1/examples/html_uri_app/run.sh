#!/usr/bin/env sh
set -eu

DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ENV_FILE="${ENV_FILE:-$DIR/.env}"

if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

HOST="${HTML_URI_APP_HOST:-${HOST:-127.0.0.1}}"
PORT="${HTML_URI_APP_PORT:-${PORT:-41740}}"

echo "Serving HTML URI parameter console (v1) at http://$HOST:$PORT/"
python3 -m http.server "$PORT" --bind "$HOST" --directory "$DIR"
