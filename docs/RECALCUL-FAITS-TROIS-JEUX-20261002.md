# Recalcul des fiches des trois jeux — 2 octobre 2026

Auteur : AleaQuant. Lot : recalcul-trois-jeux-20261002.

## Résultat

| Jeu | Fiches recalculées | Régimes couverts |
|---|---:|---|
| EuroMillions | 1 985 | 378 en 5/50 + 2/9 ; 562 en 5/50 + 2/11 ; 1 045 en 5/50 + 2/12 |
| Loto | 7 673 | 4 858 en 6/49 + complémentaire ; 2 815 en 5/49 + Chance |
| Keno | 19 466 | 19 133 en 20/70 ; 333 en 16/56 |
| **Total** | **29 124** | historiques et régimes actuels du magasin local |

Recalcul depuis la base locale, sans récupération réseau ni nouvelle énumération HPC.
Les lois existantes sont réutilisées ; ce lot n'ajoute pas de loi manquante.

**Audit intégral : 650 775 faits précédents et toutes les métadonnées restent
strictement identiques.** Aucun fait supprimé, aucune valeur scientifique modifiée.
Seul `F.main.decade_sums` s'ajoute à 29 121 fiches ; les trois témoins précédents
le contenaient déjà. Chaque profil a été contrôlé : somme des effectifs égale au
nombre de numéros, somme des sous-totaux égale à la somme de la grille. Fréquences
de classe, cohérence des queues et bornes des comptages historiques contrôlées.

## Installation et approbation humaine

- 29 120 fiches installées après comparaison complète et contrôle de concurrence.
- 3 fiches identiques, déjà actualisées par le lot témoin, laissées telles quelles.
- 1 fiche recalculée mais conservée séparément : EM-2011053, liée à l'article
  approuvé du 6 septembre 2011. Sa version actuellement approuvée reste dans dist
  afin de ne pas faire disparaître l'article lors d'une reconstruction du site.
- Alias latest synchronisé. L'article EM-2011053 reste reconnu par le validateur.
- Sources précédentes sauvegardées dans le dossier before du lot.

Les fiches ne sont jamais refusées au motif de l'absence de puces de rareté.
Une somme par dizaine reste descriptive ; elle n'acquiert pas une rareté à cette
occasion. Les fiches, les puces de mise en avant et les textes LLM sont trois couches.
Aucun nouvel article généré dans ce lot global, aucune approbation ni publication.

## Validation et suite

Le déploiement exclut déjà data/facts/** via .assetsignore ; ce recalcul ne crée
aucun nouveau fichier de tirage et ne construit aucune nouvelle page statique.
Le test du premier Loto à cinq numéros a été corrigé : un profil descriptif n'a
ni historique, ni rareté, ni probabilité de classe. L'assertion zéro passé
comparable reste obligatoire pour toutes les métriques historiques concernées.

Suite web : 129 tests et 28 sous-tests réussis ; agents : 119 tests réussis.
Reste à revalider l'article EM-2011053 avec sa nouvelle fiche avant bascule de
cette unique source. Le rattrapage global des faits est calculé et qualifié.

## Reproduction

Depuis la racine du dépôt web :

```sh
../aleaquant-editorial-agents/.venv/bin/python -u engine/facts_generic.py \
  euromillions loto keno --force \
  --output runs-traceability/recalcul-trois-jeux-20261002/facts
```

Audit détaillé : runs-traceability/recalcul-trois-jeux-20261002/audit.json.
Journal d'installation : même dossier, installation.json. Calcul : calcul.log.
La comparaison a précédé toute installation. Ne pas écraser aveuglément une
fiche liée à une approbation : l'empreinte est une frontière de validation.
