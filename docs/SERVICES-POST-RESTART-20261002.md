# Contrôle des services après redémarrage — 2 octobre 2026

Auteur : AleaQuant · version 0.1 · contrôle vers 21 h 33–21 h 37, Europe/Paris.
État observé après redémarrage du Mac et ouverture de session. Aucun jeton consigné.

| Service | Résultat | Démarrage et portée |
|---|---|---|
| Site public aleaquant.org | HTTP 200 | Cloudflare Worker, indépendant du Mac ; aucun nouveau déploiement pendant ce contrôle. |
| Console Review | HTTP 200 sur 127.0.0.1:8787, journal d’erreurs vide | `org.aleaquant.review-console`, RunAtLoad et KeepAlive ; une exécution depuis ouverture de session. |
| Tunnel AleaQuant | `/ready` HTTP 200, 4 connexions actives, compteur d’erreurs de requête à zéro | `com.cloudflare.cloudflared.aleaquant`, RunAtLoad et KeepAlive ; une exécution depuis ouverture de session. |
| Access distant | review.aleaquant.org et private.aleaquant.org redirigent vers la connexion Access | Protection présente ; aucune authentification distante complète effectuée pendant ce contrôle. |
| SSH | Bannière OpenSSH 10.3 reçue sur 127.0.0.1:22 | `com.openssh.sshd` activé et chargé ; activation à la demande par socket. `not running` au repos ne signifie pas désactivé. |
| Site local | Restauré : HTTP 200 sur 4173 et cinq pages identiques aux fichiers locaux | Nouveau `org.aleaquant.web-preview` utilisateur, RunAtLoad + KeepAlive, écoute 127.0.0.1 seulement. |
| Récupération et calcul | Job chargé ; chemins réparés et préflight réussi | `com.aleaquant.refresh`, 08:12 et 13:12 heure locale, pas d’exécution au login. Aucun import forcé durant l’audit. |
| LangGraph Studio | Port 2024 fermé | Outil de développement manuel, pas un service automatique de production. |
| Ollama | Service utilisateur actif, port 11434 | Aucun agent AleaQuant n’en dépend par défaut. |

## Réparations effectuées

Les anciennes prévisualisations 4173/4174/4180/4181 étaient temporaires et ont
cessé avec le redémarrage. Une seule écoute persistante est désormais retenue :
http://127.0.0.1:4173/ ; maquette : http://127.0.0.1:4173/maquette/.
Le modèle versionné est `ops/launchd/org.aleaquant.web-preview.plist` ; sa copie
installée est `~/Library/LaunchAgents/org.aleaquant.web-preview.plist`.
Logs : `~/Library/Logs/AleaQuantPreview/`. L’installation a été chargée et répond ;
un second redémarrage physique n’a pas été exécuté pour retester le login.

`tools/refresh.conf` utilisait encore les chemins ~/aleaquant-web et
~/aleaquant-data. Le journal de collecte montrait un échec de fichier introuvable.
Les défauts sont maintenant relatifs à l’emplacement du dépôt ; les variables de
surcharge restent disponibles. Le LaunchAgent existant pointe déjà vers le bon
lanceur et n’a pas été modifié. Préflight : 1 985 EuroMillions, 7 673 Loto,
19 466 Keno ; zéro révision en attente de calcul, couverture SHA Keno 19 466/19 466.
Cela ne garantit pas que les archives distantes n’ont pas reçu de nouveaux tirages :
le contrôle n’a déclenché aucune ingestion réseau. Dernier succès journalisé avant
redémarrage : 08:12:49 ; prochaine échéance configurée après ce contrôle : 3 octobre,
08:12 (si session et machine disponibles). Le rattrapage après machine éteinte reste
à définir ; un LaunchAgent utilisateur ne s’exécute pas avant ouverture de session.

Les trois lois historiques Keno 20/70 encore absentes restent explicitement
signalées ; aucune loi, aucun long calcul HPC ni aucun article n’a été lancé.
Tests : syntaxe bash et plist valides ; 9 tests du pipeline réussis ; accueil,
maquette et pages des trois jeux HTTP 200, écoute locale confirmée.

## Points non résolus ou non vérifiés de bout en bout

- Le tunnel reçoit bien `private.aleaquant.org → ssh://localhost:22` et
  `review.aleaquant.org → http://localhost:8787`. Authentification SSH complète
  depuis un appareil extérieur non exercée ; ne pas assimiler le formulaire
  Access à une session terminal réussie.
- Ancien LaunchDaemon système `com.cloudflare.cloudflared` encore actif en plus
  du tunnel utilisateur. Il lance cloudflared sans arguments ; sa configuration
  accessible ne contient qu’un réglage de journal. Son rôle effectif n’est pas
  établi. Il a une seule exécution, sans boucle de redémarrage observée. Ne pas
  le supprimer avant clarification ; inspection/arrêt administrateur nécessitent
  sudo, indisponible sans mot de passe dans cette session. Aucun changement système.
- Processus Codex observés : un principal lié à VS Code et un auxiliaire
  `codex-code-mode-host`. Aucun processus Codex supplémentaire dans ce relevé ;
  aucun processus n’a été tué. Ce constat n’exclut pas une fuite future.

## Vérification ultérieure

Après la prochaine ouverture de session : ouvrir le site local et Review,
contrôler le tunnel et lire le résultat du prochain rafraîchissement dans
`~/Library/Logs/aleaquant-refresh.log`. Les états datés de ce rapport complètent
[COMPONENT-INVENTORY.md](COMPONENT-INVENTORY.md).
