#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
exec .venv/bin/python -m cProfile -s cumulative -m limitx.bench \
  --scenario mixed --orders "${1:-20000}" --seed 42 --runs 1 --warmup 1000

