# Covariance historique des positions — état exploratoire v0.1

Calcul local du 30/09/2026 depuis les dernières révisions de
`../aleaquant-data/data/aleaquant.sqlite3`, lues sans modification. Le rapport
intégral, avec les matrices et l'empreinte de l'ensemble des révisions de chaque
groupe, est dans [`order-position-history-2026-09-30.json`](order-position-history-2026-09-30.json).
La commande reproductible est :

```sh
python3 engine/order_position_history.py > covariance-historique.json
```

Le regroupement suit **jeu + règle + composante principale**. Les trois périodes
EuroMillions restent séparées malgré leur composante principale commune 5/50 ;
les deux formules du Loto et les deux du Keno ne sont jamais mélangées. Les
étoiles, le numéro Chance et la complémentaire n'entrent pas dans ces matrices.
Chaque matrice historique utilise la covariance d'échantillon, avec diviseur
`m − 1` ; la matrice théorique décrit le modèle uniforme sans remise.

| Jeu et règle | Tirages | Période couverte | Étendue moyenne observée | Attendue |
|---|---:|---|---:|---:|
| EuroMillions 5/50, étoiles 9 | 378 | 2004-02-13 → 2011-05-06 | 34,606 | 34 |
| EuroMillions 5/50, étoiles 11 | 562 | 2011-05-10 → 2016-09-23 | 33,874 | 34 |
| EuroMillions 5/50, étoiles 12 | 1 045 | 2016-09-27 → 2026-09-29 | 34,124 | 34 |
| Loto 6/49 | 4 858 | 1976-05-19 → 2008-10-04 | 35,739 | 35,714 |
| Loto 5/49 | 2 814 | 2008-10-06 → 2026-09-28 | 33,211 | 33,333 |
| Keno 20/70 | 19 133 | 1993-09-16 → 2025-11-02 | 64,238 | 64,238 |
| Keno 16/56 | 319 | 2025-11-03 → 2026-09-17 | 50,063 | 50,294 |

Ces chiffres ne sont qu'une lecture descriptive. Aucun test de significativité,
aucune correction de multiplicité et aucune calibration par simulation n'ont été
effectués. La covariance entre positions d'un tirage n'est **pas** une
autocovariance entre tirages successifs. L'identité de variance de l'étendue
est vérifiée pour chaque groupe historique ; elle ne constitue pas un second
indice indépendant. Les matrices complètes doivent être lues avec leur effectif :
le Keno 16/56, en particulier, ne compte que 319 observations dans cette archive.

La sélection par date éventuelle de la commande porte sur la **date du tirage**.
Elle emploie toujours la dernière révision connue dans la base actuelle : ce
n'est donc pas une reconstruction de l'information disponible à une date passée,
et elle ne doit pas servir telle quelle à un backtest. Avant un article ou un
audit public, il faut contrôler la fraîcheur de l'ingestion Keno (dernier tirage
local : 17/09/2026), définir des fenêtres à l'avance et calibrer l'incertitude
par jeu et par règle. Aucun de ces résultats ne prédit un tirage futur.
