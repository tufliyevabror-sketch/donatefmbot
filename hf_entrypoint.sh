#!/usr/bin/env bash
set -e
if [ -n "${HF_DATASET_REPO:-}" ] && [ -n "${HF_TOKEN:-}" ]; then
  python /app/hf_persist.py restore || true
  python /app/hf_persist.py loop &
fi
exec "$@"
