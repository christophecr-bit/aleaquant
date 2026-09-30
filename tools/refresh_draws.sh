#!/bin/bash
# AleaQuant · lanceur du pipeline local · version 0.2 · 2026-09-30
# Auteur : AleaQuant. Historique : trois jeux via aleaquant-data ; 0.1 : EuroMillions seul.
# TODO : brancher la publication Keno après validation de son rendu à la demande.
set -euo pipefail
CONF="$(cd "$(dirname "$0")" && pwd)/refresh.conf"
if [ ! -f "$CONF" ]; then
  echo "configuration absente : $CONF" >&2
  exit 2
fi
# shellcheck source=/dev/null
source "$CONF"
export WEB_DIR DATA_DIR LAB_DIR
if [ ! -x "$PYTHON_BIN" ]; then
  echo "Python du pipeline absent : $PYTHON_BIN ; installer requirements-pipeline.txt" >&2
  exit 2
fi
exec "$PYTHON_BIN" "$WEB_DIR/tools/refresh_draws.py" "$@"
