# Règle documentaire du site — v1.2 · 11 octobre 2026

Cette règle vaut pour l'ensemble du site, au même titre que le versionnement
et la tenue des registres. Elle a été demandée explicitement par Chris.

## Une notion, un accès à son explication

Toute notion dont le lecteur a besoin possède une définition en langage courant.
À sa première apparition significative, la page donne une explication courte et
un lien vers une entrée de glossaire, un mini-article ou une section explicative.
Une page cible doit exister : ne pas remplacer la documentation par un lien cassé
ou un intitulé sans contenu. Plusieurs termes apparentés peuvent partager une
explication, par exemple paires et triplets dans la couverture.

Le glossaire permet une lecture rapide ; le mini-article développe une seule
question avec un exemple concret, éventuellement manipulable, puis sa portée.
Le parcours d'introduction donne un ordre de lecture. Le plan documentaire suit
les notions, questions, URL, versions, état et validations.

## Progressivité et dépendances

Chaque notion déclare ses prérequis, versionnés, jusqu'aux définitions de base.
Chaque page ou article déclare les notions nécessaires à sa lecture. Exemple :
recouvrement entre deux grilles → paire de grilles → paire et grille → numéro et
étoile. Les paires de numéros communes ont une autre chaîne : paire de numéros et
recouvrement. Ne pas confondre ces objets.

Pour tout article du pipeline éditorial, le Scout inscrit cette déclaration dès
la proposition, quel que soit le sujet. Le Writer aborde les notions dans l'ordre
utile à la lecture, avec introduction ou rappel et lien vers l'explication publiée.
Les relecteurs vérifient leur traitement dans le texte final. Une liste interne
de dépendances ne suffit pas ; un inventaire inconnu reste à établir et bloque
la publication. Le raccordement structuré et sa qualification restent TD-SCOUT-001
dans le dépôt éditorial canonique.

La publication d'une page ou d'un article requiert des explications déjà publiées
pour tous ses prérequis directs et indirects. Un fichier local, un dossier d'entrée,
une validation éditoriale ou un drapeau « publié » ne prouve pas l'accès public à la
version attendue. Le contrôle vérifie le graphe, les versions, les empreintes et la
preuve d'accès public. Un cycle ou une dépendance absente bloque la publication.
Les liens complémentaires (« Pour continuer ») ne sont pas des prérequis.

Le glossaire peut être incrémenté directement : ses nouvelles définitions forment
un lot ordonné des notions de base vers les notions dépendantes. Elles doivent être
effectivement publiées avant de satisfaire les dépendances d'un article. Le niveau
expert n'exempte jamais du parcours de prérequis ; il évite de répéter toutes les
définitions dans le corps de l'article en proposant les accès nécessaires.

## Deux circuits de contenu

Le glossaire est incrémenté directement, avec version, vérification des définitions
et changelog. Un article, mini-article ou parcours éditorial entre dans le pipeline
canonique `../aleaquant-editorial-agents` : sujet, preuves, rédaction, contrôles,
relecture humaine et approbation du SHA exact avant import sur le site. Un dossier
d'entrée n'est pas un article approuvé ; un exemple fake ne valide pas ses preuves.
Les règles de ce dépôt sont dans son `AGENTS.md`. Aucun lien public ne doit viser
un article en attente : utiliser l'ancre réelle du glossaire.

La compétence de rédaction et de relecture suit le niveau de l'article. Le pipeline
éditorial définit ses profils d'initiation, approfondissement et expertise, avec
paramètres de modèle, prompt, effort et spécialistes. Les exigences de preuves et
les dépendances publiées sont communes à tous ces profils.

## Scout documentaire et choix des formats

Le Scout part de l'inventaire des notions et des dépendances bloquantes pour
proposer des idées. Il peut aussi retenir une notion pour son intérêt éditorial
propre. Une définition élémentaire comme paire reste au glossaire ; concentration
ou span peuvent justifier un article ou mini-article avec question, exemples et
limites. Ne pas créer un article par notion, ni exiger un effet de surprise.
Une explication de glossaire publiée peut suffire à un prérequis de lecture.

La mission et ses limites d'intégration sont décrites dans la
[politique canonique du Scout](../../aleaquant-editorial-agents/docs/SCOUT-NOTIONS-POLICY.md).
Le branchement automatique de l'inventaire reste à qualifier dans TD-SCOUT-001.

## Récit pour le lecteur et détails pour reproduire

Une page d'étude commence par la question, ce qui varie et ce qui reste constant,
les observations et ce qu'elles permettent de conclure. Expliquer les mots avant
de les employer : portefeuille, recouvrement, score, mutation, comparaison.

Les noms de variables internes, hashes, identifiants de run, graines, limites et
règles de sélection restent accessibles dans un volet « Protocole et
reproductibilité » fermé au départ. Ils ne forment pas un article scientifique.
Un terme comme « ablation » est défini ou remplacé par « étude de l'effet d'un
paramètre ». Le mot RANDOM désigne une méthode aléatoire, pas un poids nul.

Les exemples pédagogiques sont identifiés comme exemples, les mesures exactes
comme telles, les simulations avec leur incertitude et les garanties avec leurs
conditions. Une simulation, une modification ou un croisement ne vaut pas
preuve d'amélioration. Toute différence de périmètre de comparaison reste visible.

## Versionnement et registres

Pour chaque changement, mettre à jour la version de l'élément concerné et le
changelog avec son comportement, sa validation et sa portée. Conserver les
versions scientifiques et les exécutions précédentes.

Choisir le registre adapté : backlog pour une capacité utilisateur encore à
livrer, TODO pour une action de mise en service ou de vérification, dette
technique pour un composant ou une qualification manquante. Le plan documentaire
recense les pages ; les registres renvoient à ce plan sans dupliquer son contenu.
Une tâche ne se clôture qu'avec une preuve du résultat, jamais avec une simple
mention de sa limite.

## Vérification avant livraison

Vérifier définitions, exemples et calculs, liens et ancres, lecture mobile,
navigation vers les résultats et séparation récit/protocole. Signaler l'état
réel : produit localement, vérifié en recette ou publié à distance. Le générateur
`engine/build_glossary.py` produit uniquement le glossaire ; ses
versions et empreintes sont dans `dist/comprendre/documentation.json`.

## Historique

- v1.2 (2026-10-11) — exige la déclaration des dépendances par le Scout pour
  chaque article, leur traitement dans le texte et leur disponibilité publique.

- v1.1 (2026-10-11) — précise la mission du Scout et le choix glossaire/article
  selon dépendances et valeur éditoriale, sans publication nouvelle.
- v1.0 (2026-10-10) — règle documentaire transversale et progressivité.
