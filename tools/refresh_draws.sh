#!/bin/bash
# Rafraîchit les tirages et tout ce qui en découle. Conçu pour launchd (chantier B3).
#
#   ingestion FDJ  ->  faits  ->  profils de rareté  ->  pages statiques
#
# Propriétés voulues :
#   - idempotent : sans nouveau tirage, il ne touche à rien et sort en 0 ;
#   - une seule instance à la fois (verrou) ;
#   - NE publie RIEN : ni git commit, ni wrangler deploy, ni approbation d'article.
#     La mise en ligne reste une décision humaine explicite, c'est la ligne éditoriale.
#
#   bash tools/refresh_draws.sh              # rafraîchit
#   bash tools/refresh_draws.sh --check      # dit seulement s'il y a du retard
#
set -uo pipefail

CONF="$(cd "$(dirname "$0")" && pwd)/refresh.conf"
[ -f "$CONF" ] || { echo "configuration absente : $CONF" >&2; exit 2; }
# shellcheck source=/dev/null
source "$CONF"

LOCK="/tmp/aleaquant-refresh.lock"
horodate() { date "+%Y-%m-%dT%H:%M:%S%z"; }
journal() { echo "[$(horodate)] $*"; }

if ! mkdir "$LOCK" 2>/dev/null; then
  journal "une autre instance tourne déjà ($LOCK) — abandon"
  exit 0
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

dernier_tirage() {
  python3 - "$WEB_DIR" << 'PY'
import json, sys
from pathlib import Path
m = Path(sys.argv[1]) / "dist" / "data" / "manifest.json"
print(json.loads(m.read_text(encoding="utf-8"))["last"] if m.exists() else "inconnu")
PY
}

avant="$(dernier_tirage)"
journal "dernier tirage publié localement : $avant"

if [ "${1:-}" = "--check" ]; then
  journal "--check : rien n'a été modifié"
  exit 0
fi

# 1. ingestion (seule étape qui a besoin du réseau)
journal "ingestion depuis la source officielle FDJ"
cd "$LAB_DIR" || { journal "dépôt du laboratoire introuvable : $LAB_DIR"; exit 2; }
sortie="$(PYTHONPATH=src python3 -m src.lottery_history.ingest \
  --store "$STORE" --fetch-url "$EUROMILLIONS_ARCHIVE_URL" 2>&1)"
statut=$?
journal "ingestion : $sortie"
if [ $statut -ne 0 ]; then
  journal "ÉCHEC de l'ingestion (réseau ? URL d'archive périmée ? voir refresh.conf)"
  exit 1
fi

nouveaux="$(printf '%s' "$sortie" | python3 -c '
import json, sys
try:
    print(len(json.load(sys.stdin).get("changed_draw_ids", [])))
except Exception:
    print(-1)
')"

if [ "$nouveaux" = "0" ]; then
  journal "aucun nouveau tirage — rien à recalculer"
  exit 0
fi
journal "$nouveaux tirage(s) nouveau(x) ou corrigé(s)"

# 2. recalculs (aucun réseau ; build_data a besoin de numpy)
cd "$WEB_DIR" || { journal "dépôt du site introuvable : $WEB_DIR"; exit 2; }
for etape in \
  "engine/build_data.py --facts 2000" \
  "engine/rarity_profiles.py" \
  "engine/build_pages.py" ; do
  journal "recalcul : $etape"
  # shellcheck disable=SC2086
  if ! python3 $etape > /tmp/aleaquant-refresh-etape.log 2>&1; then
    journal "ÉCHEC : $etape"
    tail -5 /tmp/aleaquant-refresh-etape.log | while read -r l; do journal "  $l"; done
    exit 1
  fi
done

apres="$(dernier_tirage)"
journal "dernier tirage publié localement : $apres (avant : $avant)"

# 3. état du dépôt, sans rien committer
modifies="$(git -C "$WEB_DIR" status --porcelain | wc -l | tr -d ' ')"
journal "$modifies fichier(s) modifié(s) dans le dépôt, non committés"
journal "à faire à la main, délibérément : git commit, puis npx wrangler deploy"
journal "terminé"
