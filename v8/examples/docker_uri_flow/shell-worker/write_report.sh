#!/usr/bin/env sh
set -eu

slug="$1"
text="$2"
path="/data/${slug}.txt"

printf 'report=%s\n' "$text" > "$path"
printf '%s\n' "$path"
