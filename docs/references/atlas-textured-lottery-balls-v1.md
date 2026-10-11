# Boules texturées de l'Atlas — référence v1.0

Date : 10 octobre 2026 · Statut : style validé par Chris · Produit : PB-018

Chris a validé l'aperçu par « ok je valide, on le note pour pas oublier ».
Le rendu retenu est une boule bleue satinée, avec un grain fin, un léger relief
et des chiffres sombres très lisibles sur une pastille claire.

[Image validée](atlas-textured-lottery-balls-v1.png) ·
[Cadrage produit](../PRODUCT-BACKLOG.md#cadrage-initial-de-pb-018--la-vitrine-visuelle-de-latlas)

## Réalisation à venir

- Adapter ce style aux présences de la matrice et préserver la lisibilité du
  numéro à petite taille ; prévoir une lecture agrandie pour une matrice dense.
- Faire varier l'intensité du bleu selon la fréquence du numéro, avec une
  échelle explicite et comparable. La texture reste décorative.
- Conserver étoiles séparées, cases absentes et valeurs hors pool identifiables.
- Vérifier les vues 20 et 30 grilles, mobile et clavier, puis relier la sélection
  au prompteur. La référence peut être traduite en une forme réutilisable en
  SVG ou CSS, sans fabriquer une image différente pour chaque numéro.

Les trois teintes de l'aperçu sont des variantes graphiques. Elles ne représentent
pas des fréquences mesurées pour les numéros 13, 30 et 43. La validation du style
ne vaut pas intégration de ces boules dans la matrice du site.

## Provenance

- Génération : outil intégré `image_gen`, aperçu de style, fond transparent.
- Original conservé : `/Users/chris/.codex/generated_images/01a1211b-dc2e-7741-95eb-f042795145f6/exec-c2ecb0a7-32c7-449b-a6e2-327fefac5b38.png`.
- Copie : `docs/references/atlas-textured-lottery-balls-v1.png`, identique à l'original.
- SHA-256 : `c2f867cec8e3afe1c01e83f9325b13219a40ec1f4f7d2506ec9f26b29c5dddd0`.

Prompt utilisé :

> Use case: stylized-concept. Asset type: one small visual concept sheet, preview only, for numbered lottery-ball marks in an AleaQuant portfolio presence matrix. Create a clean landscape composition with exactly three attractive lottery balls aligned horizontally, evenly spaced, fully visible, against a genuinely transparent background. Front-facing, no scene or lottery machine. Left ball pale icy blue with printed number '13', middle ball medium soft blue with printed number '30', right ball richer deeper blue with printed number '43'. The blue intensities suggest three possible intensity levels of the same UI mark, but add no frequency values or claims. Each ball is a modestly dimensional satin molded-plastic sphere, with very fine tactile micrograin texture, restrained soft highlight in upper left, subtle rim shading and very small soft contact shadow. Texture must look elegant and remain unobtrusive at thumbnail size, not glitter, not cracked, not rocky. Each number appears as perfectly readable dark charcoal bold sans-serif digits in a crisp light ivory circular inset on the face, same inset size and typography for all three balls. Keep spheres distinct and uncluttered with generous transparent space around them. Contemporary clean product illustration, almost realistic, pleasant and legible as a small matrix symbol. Only text in image is the three exact numbers '13', '30', '43'. No logo, no titles, no extra annotations, no branding, no border, no UI panel, no watermark. This is a graphic style preview, not scientific data.
