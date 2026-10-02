# Sources et méthode des articles — contrat v1.0

Auteur : AleaQuant · 2 octobre 2026.

## Décision et périmètre

Les articles de review sont des témoins, jamais des correctifs manuels du pipeline.
Le batch/direct construit la prose et le registre de claims séparément. Une prose
de liaison sans assertion détectée ne nécessite pas un claim artificiel. La note
publique est générée depuis les faits, jamais demandée au LLM.

## Contrat public et interne

`draft.methodology` porte la note, la source disponible, le régime, le moteur,
les populations théoriques et historiques séparées par composante, les limites,
les preuves utilisées et les liens claim → preuves. Ce champ est inclus dans le
SHA du draft ; le Research Pack reste lui-même lié au draft par son empreinte.
Les schémas Pydantic PublicMethodology/WebDraft du dépôt des agents vérifient le
transport. Le corps reste une prose éditoriale, sans duplication de la note.

Le rendu affiche « Sources et méthode » puis « Sources et calculs » dépliable :
page de tirage statique, lecteur du journal et console de review. Les chaînes sont
échappées ; seuls les liens HTTP(S) sans identifiant de connexion sont acceptés.
Aucun chemin local, clé, prompt, coût ou journal interne n'est projeté publiquement.
Un champ source manquant est signalé ; aucune URL ni date n'est reconstituée.

## Contrôles communs

Implémentation : `agent/article_traceability.py` et `agent/guards.py` dans le site.
Le workflow court importe ces fonctions via `aleaquant/tools/draw_traceability.py`.
Les consignes versionnées `constitution/traceability.md` sont chargées par le batch
et par Writer, Editor, Fact Checker, Final Reviewer du parcours long.

- Fin des appariements fondés sur un effectif isolé. La mesure et la composante
  identifient les références ; apostrophes françaises et paraphrases usuelles reconnues.
- Recontrôle des nombres contre les preuves citées, avec contexte du tirage.
- Détection des références manquantes/sans rattachement et assertions hors registre.
- Comparaisons internes « au-dessus de sa référence » bloquées et renvoyées à la
  réparation automatique. Contrôle local des qualificatifs entre numéros/étoiles.
- Recontrôle du contenu des preuves et de la note contre les faits source.
- Rejeu à la construction, à l'entrée LangGraph et à l'import ; les anciens voyants
  verts sauvegardés ne suffisent pas. Les dossiers compose anciens sans note sont
  à régénérer avant une nouvelle publication, pas à approuver silencieusement.

Les modes réels sont `batch`, `direct`, `text_import`. Un mode absent reste bloquant.
Aucun dossier historique n'est rebaptisé batch pour contourner le contrôle.
La collecte batch conserve le modèle réellement retourné et aligne writer/provenance.
Une modification de prose, preuves ou note invalide la décision et change le SHA.
NOT_REVIEWED est un état normal avant contrôle ; READY_FOR_HUMAN n'est pas approuvé.

## Métrique nouvelle et reproductibilité

Le générateur de faits et le prompt savent exposer `F.main.decade_sums`, sans rareté.
La fiche EM-26078 conservée sur disque ne contient pas encore ce fait. Les tests
vérifient sa transmission quand il existe ; ni l'article ni sa note ne l'inventent.
Les fiches anciennes exigent une régénération explicite (cache du refresh fondé sur
le SHA source). Décider ce rattrapage séparément car il invalide les articles liés
à leurs anciennes empreintes. Pas de recalcul global ni de publication dans ce lot.

## Validation et limites

Le témoin d'origine EM-26078 est figé dans `tests/fixtures/traceability/` et reste
inchangé dans la file originale. C2, C5, fuite de consigne, prose hors claims,
promesse de gain, nombres empruntés à une autre preuve, note falsifiée, modification
après décision, provenance et nouveau fait descriptif ont des tests permanents.

Le contrôle lexical est conservateur : des paraphrases peuvent lui échapper ou
nécessiter des alias. Il ne démontre pas toute la sémantique d'une phrase. Les URLs
et dates de couverture manquantes restent une dette d'ingestion. L'intégration des
notes aux articles de fond issus du parcours long reste à étendre ; les consignes
sont partagées mais ce lot réalise le contrat du parcours récurrent des tirages.

Tests : 128 web (+ 28 sous-tests), 119 agents, tous réussis. Pas d'API dans les tests.
Deux générations LLM réelles de contrôle, séparées des tests, ont produit des témoins
locaux ; aucun changement de faits, aucune approbation, aucun déploiement.
