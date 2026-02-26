#!/usr/bin/env bash
set -euo pipefail

# Run from project root so relative paths and .env resolution stay stable.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

uv run sm-tracker auth -p threads
