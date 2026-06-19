#!/usr/bin/env bash
# A brand-new standalone script we want to expose as a URI without changing it.
# It reads a positional channel argument and a MESSAGE environment variable.
set -eu
channel="${1:-general}"
echo "notify -> #${channel}: ${MESSAGE:-<no message>}"
