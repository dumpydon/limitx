#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
exec .venv/bin/python -m limitx.profile \
  --scenario mixed --operations "${1:-20000}" --seed 42 --limit 25 \
  --output /tmp/limitx-profile.prof
