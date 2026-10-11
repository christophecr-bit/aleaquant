#!/bin/bash
# AleaQuant · lanceur du pipeline local · version 0.4 · 2026-10-01
# Auteur : AleaQuant. Historique : v0.2 collecte les trois jeux ; v0.3 valide les lois
# et profils par régime ; v0.4 ajoute le rattrapage explicite des faits Keno historiques.
# TODO : construire les pages Keno à la demande et raccorder le workflow éditorial léger.
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
