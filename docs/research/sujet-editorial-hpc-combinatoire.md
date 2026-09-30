# Sujet éditorial — calcul haute performance en combinatoire

Auteur : AleaQuant · Date : 1er octobre 2026 · Version : 0.1.
Statut : idée cadrée, à rédiger et relire ; aucun article publié.
Rubrique : Recherche & méthode. Format : petit article technique illustré,
environ 700 à 1 000 mots, avec encadré facultatif pour les détails binaires.

## Angle

**Changer la manière de compter peut accélérer davantage que compter plus vite.**
Raconter une expérience réelle d'AleaQuant : passer du recalcul des intersections
à la mise à jour incrémentale de trente scores, puis à leur représentation en
quatre plans de bits. Le lecteur doit comprendre pourquoi cette organisation
rend l'exploration exacte de certains espaces combinatoires abordable.

## Trois propositions de titre

- Trente grilles dans quatre mots : les coulisses d'un calcul combinatoire
- Un numéro sort, un autre entre : accélérer l'exhaustif
- Huit milliards de combinaisons par seconde : ce que mesure notre benchmark

Préférence de travail : le premier, concret et moins dépendant d'un record.
Titre final à choisir à la relecture humaine.

## Fil narratif

1. Le problème : pour chaque combinaison, compter les correspondances avec
   trente grilles fixes. Montrer un petit exemple de deux intersections.
2. L'idée revolving-door / Algorithm R : visiter les combinaisons dans un
   ordre où un numéro sort et un autre entre ; actualiser les scores concernés.
3. La surprise des bitplanes : coder les trente scores par quatre mots de
   32 bits. Une opération booléenne agit sur plusieurs scores à la fois.
4. Le rôle de popcount et du SIMD Metal : compter les grilles atteignant un
   seuil, puis distribuer de nombreuses séquences indépendantes sur le GPU.
   Bien distinguer bitslicing interne et groupes SIMD matériels.
5. Ce qu'on a mesuré, comment on l'a vérifié, ce que cela ouvre pour l'Atlas.

## Preuves déjà disponibles

Point d'entrée : [capitalisation HPC](../../../loto-keno-lab/docs/CAPITALISATION-HPC-ATLAS.md).
Les sources primaires sont les rapports, codes et données du laboratoire :

- [B3 et protocole](../../../loto-keno-lab/reports/revolving_metal.md) :
  stabilité à 8,731 G combinaisons/s BALANCED et 8,722 RANDOM, 32 768 workers,
  sous-espaces structurés, scoring de trente grilles et réduction inclus.
- [Shader et Algorithm R](../../../loto-keno-lab/native/revolving_metal/kernels.metal),
  avec [attribution revdoor](../../../loto-keno-lab/native/revolving_metal/LICENSE.revdoor).
- [Worker durable](../../../loto-keno-lab/reports/b3_economic_worker_qualification.md) :
  plages colex, checkpoints et limites des essais bornés.

## Visuel à produire

Une figure déterministe à deux volets : transition d'une combinaison à la
suivante avec numéro sortant/entrant, puis transposition de quelques scores
binaires en quatre plans de bits. Utiliser un petit exemple vérifié et indiquer
que l'implémentation traite trente scores. Un graphe de débit facultatif doit
reprendre le même protocole A/B, le même nombre de workers et des unités identiques.

## Vigilances de rédaction et tâches restantes

- [ ] Rédiger un texte fluide depuis les preuves, sans dérouler un inventaire de jargon.
- [ ] Vérifier les valeurs du rapport contre les JSON archivés avant publication.
- [ ] Créer et contrôler l'exemple illustré ; conserver les attributions d'algorithmes.
- [ ] Dire ce que comprend le temps mesuré : initialisation résidente exclue,
      soumission/attente/lecture incluses ; pas un exhaustif complet de 16/56.
- [ ] Distinguer combinaisons/s, comparaisons grille × tirage/s et kernel seul.
- [ ] Expliquer que ce benchmark évalue des portefeuilles fixes ; il ne mesure
      ni la recherche d'un optimum ni les lois de toutes les features.
- [ ] Évoquer B1/B2 écartés : le progrès vient d'un essai comparé et vérifié.
- [ ] Relecture scientifique puis approbation humaine du titre, texte et figure.

La chute peut relier cette expérience à l'Atlas : calculer plus précisément les
distributions et comparer des géométries à budget égal. Le calcul n'améliore pas
la prédiction de la prochaine réalisation.
