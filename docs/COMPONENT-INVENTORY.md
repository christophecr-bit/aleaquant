# Inventaire des composants AleaQuant

Auteur : AleaQuant · v0.1 · relevé du 2 octobre 2026

Cet inventaire indique où tournent les composants et comment ils sont reliés.
Il décrit l'état local observé à la date du relevé ; les versions installées
peuvent évoluer. Il ne contient aucune valeur de secret, clé API, jeton de tunnel
ou contenu de fichier `.env`.

## Projets et responsabilités

| Composant | Emplacement | Rôle / mode |
|---|---|---|
| Site et moteur de données | `/Users/chris/aleaquant/aleaquant-web` | Python produit les faits, lois, profils, pages et fichiers statiques sous `dist/`. Le dépôt sert de source pour les livraisons Worker. |
| Données et archive source | `/Users/chris/aleaquant/aleaquant-data` | Archive normalisée SQLite, révisions importées, règles de jeux et sources. Base observée : `data/aleaquant.sqlite3`. |
| Comité éditorial LangGraph | `/Users/chris/aleaquant/aleaquant-editorial-agents` | Graphes Python, agents LLM/mock, prompts, console de revue et checkpoints SQLite ; s'exécute localement sur le Mac. Le CLI optionnel ouvre ses graphes dans Studio via un serveur local de développement. |
| Laboratoire HPC / jeux | `/Users/chris/aleaquant/loto-keno-lab` | Recherche combinatoire, moteur et calculs Keno ; dépôt indépendant, voir son propre inventaire et ses consignes `AGENTS.md`. |

## Langages, runtimes et dépendances Python

Versions observées dans le shell le 2 octobre 2026 : Python 3.14.7 (`python3`),
Python 3.12.13 et 3.14.7 via Homebrew, Node 25.8.2, npm 11.20.0, Cargo 1.98.1,
SQLite CLI 3.49.1 (MacPorts, sur le PATH) et Wrangler 4.146.0 via `npx`.
Homebrew répertorie aussi SQLite 3.53.4 ; la version de la CLI et celle de la
formule installée ne sont donc pas la même observation.

Les paquets Python sont isolés selon le dépôt :

| Projet | Manifeste |
|---|---|
| Site / pipeline | [`requirements-dev.txt`](../requirements-dev.txt) et [`requirements-pipeline.txt`](../requirements-pipeline.txt) ; notamment PyYAML, OpenAI SDK et NumPy. |
| Comité LangGraph | [`pyproject.toml`](../../aleaquant-editorial-agents/pyproject.toml) ; LangGraph 1.2.12, langgraph-checkpoint-sqlite 3.1.1, Pydantic 2.13.5, LangChain 1.4.3 ; intégration OpenAI optionnelle ; extra local `studio` : `langgraph-cli[inmem]` 0.4.32, API server 0.15.1 et runtime mémoire 0.35.1. |

Les versions de paquet complètes de Homebrew sont archivées dans
[`homebrew-formulas-2026-10-02.txt`](inventory/homebrew-formulas-2026-10-02.txt)
et [`homebrew-casks-2026-10-02.txt`](inventory/homebrew-casks-2026-10-02.txt).
Quelques outils qui soutiennent directement l'exploitation locale : cloudflared,
Git, Node, Python, SQLite, pyenv, MLX et Ollama. Ce relevé comprend aussi des
logiciels personnels sans rôle AleaQuant ; leur présence ne signifie pas qu'ils
sont des dépendances du produit.

## Stockage SQLite

| Base locale | Tables observées | Usage |
|---|---|---|
| `/Users/chris/aleaquant/aleaquant-data/data/aleaquant.sqlite3` | `metadata`, `raw`, `revisions`, `rules`, `sources` | Archive des sources et des versions importées. |
| `/Users/chris/aleaquant/aleaquant-editorial-agents/runs/draw-publication.sqlite3` | `checkpoints`, `writes` | Checkpoints du workflow court de revue des articles de tirage. |
| `/Users/chris/aleaquant/aleaquant-editorial-agents/runs/checkpoints.sqlite3` | `checkpoints`, `writes` | Checkpoints du comité éditorial long. |

Les événements détaillés sont également écrits en fichiers `events.jsonl` sous
les répertoires `runs/` ignorés par Git. Les bases, événements et fichiers de
configuration locale exigent leur propre sauvegarde ; le Worker publié n'en est
pas une.

## Services locaux et exposition réseau

| Écoute observée | Usage | Exposition |
|---|---|---|
| `127.0.0.1:4173` | Prévisualisation de `dist/` et maquette sous `/maquette/`, service persistant. | Loopback seulement. |
| 4174, 4180 et 4181 | Anciennes prévisualisations temporaires, arrêtées après redémarrage. | Aucun serveur relancé sur ces ports. |
| `127.0.0.1:8787` | Console privée de validation éditoriale. | Liée à loopback, accessible à distance par `review.aleaquant.org` via Cloudflare Access et Tunnel. |
| `127.0.0.1:2024` | Serveur LangGraph de développement pour Studio, démarré manuellement depuis `aleaquant-editorial-agents`. | Loopback seulement ; graphes en mémoire, arrêtés avec le processus. Le navigateur Studio se connecte à cette API locale. |

Le site local sur 4173 et la console de revue s’appuient désormais sur des
LaunchAgents utilisateur. Ils démarrent à l’ouverture de session ; le site public
Cloudflare reste indépendant du Mac.
Des LaunchAgents distincts exécutent le rafraîchissement des tirages et
cloudflared ; leurs fichiers locaux ne doivent jamais être copiés ici si leur
commande contient un jeton. Voir [`DEPLOYMENTS.md`](DEPLOYMENTS.md) pour les
procédures de livraison.

| LaunchAgent | Fonction | Déclenchement |
|---|---|---|
| `org.aleaquant.web-preview` | Sert `dist/` sur 127.0.0.1:4173, maquette incluse. | À l’ouverture de session, puis maintien actif. |
| `com.aleaquant.refresh` | Exécute `tools/refresh_draws.sh` pour récupérer les jeux puis calculer et vérifier leurs faits. | 08:12 et 13:12, heure locale ; modifications laissées dans les dépôts pour revue. |
| `org.aleaquant.review-console` | Démarre la console de validation sur `127.0.0.1:8787` et la relance si elle s'arrête. | À l'ouverture de session, puis maintien actif. |
| `com.cloudflare.cloudflared.aleaquant` | Maintient le tunnel vers les services explicitement routés, dont la console privée. | Service utilisateur maintenu actif ; son jeton reste dans la configuration locale protégée. |
| `sh.brew.ollama` | Service Ollama local fourni par Homebrew. | Actif via le service Homebrew ; les agents AleaQuant n'en dépendent pas par défaut. |

Pour lancer manuellement la prévisualisation **uniquement si le service 4173 est
arrêté**, la commande équivalente est :

```sh
python3 -m http.server 4173 --bind 127.0.0.1 --directory /Users/chris/aleaquant/aleaquant-web/dist
```

Le navigateur local utilise `http://127.0.0.1:4173/`. Le serveur ne publie rien
sur Cloudflare ; pour le rendre accessible à distance, il faut une configuration
d'accès dédiée et contrôlée, telle que le tunnel déjà réservé à la console.

## Hébergement et livraison

- **Site public** : Cloudflare Workers static assets, projet Worker `aleaquant`,
  fichiers générés depuis `dist/`, domaine public `aleaquant.org`.
- **Console privée** : Mac local → `127.0.0.1:8787` → Cloudflare Tunnel →
  Cloudflare Access → `review.aleaquant.org`. Disponibilité conditionnée au Mac,
  au réseau et au processus local.
- **Dépôt distant** : GitHub, dépôt `christophecr-bit/aleaquant` pour le site ;
  les autres dépôts restent indépendants. Le push Git et `wrangler deploy` sont
  deux opérations séparées dans le processus actuellement documenté.
- **Outils de livraison** : `npx wrangler` est la commande actuellement utilisée ;
  la version observée est 4.146.0. Wrangler n'est pas figé dans un lockfile du
  dépôt à la date du relevé.

## Relevé des ports et versions

Les ports ont été observés par `lsof` et les versions par les exécutables du
shell et Homebrew, sans lire les variables secrètes. La liste intégrale de
Homebrew est un instantané du jour, pas une liste de dépendances applicatives.

## Historique et TODO

- v0.2 (2026-10-02) — ajoute le CLI LangGraph local et son serveur Studio sur
  loopback ; le graphe du comité utilise un backend factice par défaut.
- v0.1 (2026-10-02) — premier relevé des dépôts, runtimes, dépendances, bases,
  ports locaux et hébergement ; aucune configuration secrète copiée.
- TODO AleaQuant : rafraîchir cet inventaire après installation, suppression ou
  migration d'un composant ; contrôler les ports avant d'exposer un service.

Contrôle et réparations après redémarrage : [SERVICES-POST-RESTART-20261002.md](SERVICES-POST-RESTART-20261002.md).
