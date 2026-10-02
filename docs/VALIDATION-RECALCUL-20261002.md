# Validation ciblée du recalcul et de la rédaction — 2 octobre 2026

Auteur : AleaQuant. Lot : recalcul-20261002. Aucun article publié.

## Fiches de faits : trois sur trois conformes

| Tirage | Régime | Avant → après | Comparaison |
|---|---|---|---|
| EM-26078 · 29 septembre 2026 | 5/50 + 2/12 | 31 → 32 faits | 31 anciens faits strictement identiques |
| EM-26077 · 25 septembre 2026 | 5/50 + 2/12 | 31 → 32 faits | 31 anciens faits strictement identiques |
| EM-2004010 · 16 avril 2004 | 5/50 + 2/9 | 26 → 27 faits | 26 anciens faits strictement identiques |

Seul F.main.decade_sums est ajouté. Métadonnées précédentes et 88 anciens faits
inchangés. Sommes des sous-totaux et effectifs contrôlées contre la grille.
L'alias latest.json suit EM-26078. Aucun HPC relancé. L'article approuvé
EM-2011053 et sa fiche n'ont pas été modifiés.

Une fiche valide ne nécessite aucune puce. Les puces sélectionnent les métriques
éditorialement notables ; l'absence de puce ne rejette ni une fiche ni un article.
Les sommes par dizaine sont descriptives, sans rareté. Le refus ci-dessous porte
sur le texte du rédacteur et non sur la qualité des fiches de faits.

## Générations et entrée dans la review

- EM-26078 : nouvelle métrique transmise et citée ; READY_FOR_HUMAN.
- EM-2004010 : nouvelle métrique transmise et citée ; READY_FOR_HUMAN. Le vrai test
  a découvert un faux positif : « sous-total » singulier n'était pas reconnu par
  l'appariement. Alias et test ajoutés ; même prose réévaluée, SHA actualisé.
- EM-26077 : nouvelle métrique transmise et citée, mais BLOCKED. Le texte attribue
  des raretés remarquables à des profils non informatifs. La tentative automatique
  unique de réparation reste insuffisante ; refus confirmé à l'entrée de la review.
  Aucun assouplissement du garde ni retouche manuelle pour faire passer cet article.

Les trois brouillons sont copiés dans le dossier des révisions privées. Les deux
conformes ont franchi l'entrée LangGraph et attendent une décision sur leur SHA.
Les anciennes versions sont conservées ; celles liées aux fiches précédentes
présentent désormais normalement un hash périmé et doivent rester des témoins.

## Reproductibilité et limites

Commande employée avant remplacement ciblé des fiches :

```sh
../aleaquant-editorial-agents/.venv/bin/python engine/facts_generic.py euromillions \
  --draw EM-26078 --draw EM-26077 --draw EM-2004010 \
  --output runs-traceability/recalcul-20261002/recomputed --force
```

Après comparaison, seules ces trois fiches et l'alias latest ont été installés.
Chaque article est généré par compose_draw_report.py avec --write et --out séparé.
Snapshots avant/après, manifest et brouillons : runs-traceability/recalcul-20261002/.
Les appels LLM réels sont séparés des tests ; coût affiché cumulé estimé : 0,04835 $.

Tests : 129 web (+28 sous-tests), 119 agents, tous réussis. JavaScript inchangé.
Ceci valide le raccord des faits, de la rédaction et du checkpoint, pas la qualité
littéraire de chaque sortie. Le retour humain automatique vers le Writer reste à
réaliser : aujourd'hui une remarque est enregistrée, pas exécutée par un agent.
