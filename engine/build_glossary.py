"""Glossaire direct v1.0 ; aucun article ni statut de publication distante."""
from pathlib import Path
from hashlib import sha256
from html import escape
import json
from content_dependencies import empty_registry, notion_node, page_node, update_nodes

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.0'
DATE = '2026-10-10'

def term(identifier, label, definition, requires=(), related=()):
    return dict(id=identifier, label=label, definition=definition,
                requires=list(requires), related=list(related), version=VERSION)

# requires = prérequis de lecture ; related = navigation complémentaire, sans
# obligation de lecture. Ne jamais confondre ces deux relations dans le gate.
NOTIONS = [
    term('numero', 'Numéro', 'Une valeur du premier ensemble de la grille. Dans cette expérience EuroMillions, cinq numéros distincts sont choisis parmi 1 à 50.'),
    term('etoile', 'Étoile', 'Une valeur du second ensemble de la grille. Dans cette expérience, deux étoiles distinctes sont choisies parmi 1 à 12 ; elles sont comptées séparément des numéros.'),
    term('grille', 'Grille', 'Un choix de cinq numéros et de deux étoiles dans cette expérience EuroMillions. L’ordre de présentation ne change pas la grille.', ('numero','etoile')),
    term('portefeuille', 'Portefeuille', 'Un ensemble de grilles considéré et évalué ensemble. Le nombre de grilles et leur coût font partie de sa description.', ('grille',), ('budget','couverture')),
    term('pool', 'Pool', 'L’ensemble autorisé pour choisir les numéros ou les étoiles lors de la construction. Un pool de 15 numéros et 5 étoiles restreint les grilles construites ; le tirage simulé reste sur le domaine complet 50/12.', ('numero','etoile'), ('effet-pool',)),
    term('paire-base', 'Paire', 'Un ensemble de deux objets distincts, sans ordre. La paire A–B est la même que B–A.', (), ('paire','paire-grilles')),
    term('paire', 'Paire de numéros', 'Deux numéros distincts, sans ordre : {7,14} est une paire. Cinq numéros contiennent dix paires. Une paire d’étoiles suit la même définition dans l’ensemble des étoiles.', ('paire-base','numero'), ('couverture',)),
    term('triplet', 'Triplet', 'Trois numéros distincts, sans ordre. Les cinq numéros d’une grille contiennent dix triplets différents.', ('numero','grille'), ('couverture',)),
    term('paire-grilles', 'Paire de grilles', 'Deux grilles distinctes prises ensemble pour les comparer. Un portefeuille de 20 grilles contient 20 × 19 / 2 = 190 paires de grilles.', ('paire-base','grille'), ('recouvrement',)),
    term('recouvrement', 'Recouvrement entre deux grilles', 'Les numéros communs aux deux grilles, ou leur nombre selon la mesure affichée. Si A et B partagent 7, 14 et 22, leur intersection de numéros vaut 3. Les étoiles communes sont mesurées séparément.', ('paire-grilles',), ('recouvrement-paires','penalite-recouvrement')),
    term('recouvrement-paires', 'Paires de numéros communes', 'Les paires présentes dans les deux grilles. Si elles partagent k numéros, elles partagent k × (k−1) / 2 paires : pour k = 3, {7,14}, {7,22} et {14,22}, soit 3 paires.', ('paire','recouvrement'), ('penalite-recouvrement',)),
    term('couverture', 'Couverture', 'Le nombre de groupes distincts présents dans au moins une grille : numéros, paires ou triplets selon la mesure. Une paire présente dans cinq grilles compte une seule fois dans sa couverture.', ('portefeuille','paire','triplet'), ('collision','frequence')),
    term('collision', 'Collision de paires ou de triplets', 'La répétition d’un même groupe dans plusieurs grilles. La métrique précise son mode de comptage : les occurrences au-delà de la première et les coïncidences entre paires de grilles sont deux comptes différents.', ('couverture','paire-grilles'), ('recouvrement-paires',)),
    term('union', 'Union', 'Tous les numéros distincts présents dans les grilles réunies ; chaque numéro n’y figure qu’une fois. On calcule séparément l’union des étoiles.', ('portefeuille',)),
    term('frequence', 'Fréquence dans le portefeuille', 'Le nombre de grilles qui contiennent un numéro ou une étoile. Ici il décrit les grilles construites, pas les tirages passés. Le tableau complet comprend aussi les valeurs jamais choisies.', ('portefeuille',), ('dispersion',)),
    term('moyenne', 'Moyenne, minimum et maximum', 'La moyenne est la somme des valeurs divisée par leur nombre. Le minimum et le maximum sont les valeurs extrêmes. Une moyenne sur dix constructions peut masquer des résultats différents selon la graine.', (), ('graine','distribution')),
    term('dispersion', 'Dispersion des fréquences', 'Le degré d’inégalité des fréquences ; l’écart-type est l’une de ses mesures. Il faut préciser les valeurs incluses : la mesure de cette étude inclut les 50 numéros, donc les fréquences nulles hors du pool.', ('frequence','moyenne'), ('compromis-geometriques',)),
    term('distribution', 'Distribution', 'La répartition des cas entre des valeurs. Pour les intersections, on compte combien de paires de grilles partagent 0, 1, 2… numéros ; un histogramme représente ces nombres.', ('paire-grilles','recouvrement'), ('moyenne',)),
    term('poids', 'Poids d’un objectif', 'Un coefficient qui règle l’importance d’un terme dans le score. Garder les autres poids fixes signifie ne changer que le coefficient étudié, et conserver les autres valeurs.', (), ('score','ablation')),
    term('score', 'Score de construction', 'Une valeur utilisée pour choisir une proposition de grille. Le prototype récompense les nouvelles paires et triplets et pénalise les fréquences déjà élevées ainsi que le recouvrement. Ce score de recherche n’est pas une probabilité de gain.', ('poids','couverture','frequence','recouvrement'), ('construction',)),
    term('penalite-recouvrement', 'Pénalité des intersections au carré', 'Dans le prototype, une proposition reçoit une pénalité w × Σ k², où k est son nombre de numéros communs avec chaque grille déjà retenue. Trois numéros communs donnent 9w, et non 3w. C’est un coût dans le score ; ce n’est pas une interdiction de partager des numéros.', ('poids','recouvrement'), ('recouvrement-paires','score')),
    term('construction', 'Construction grille après grille', 'Le prototype ajoute une grille à la fois. Pour chaque ajout, il teste 1 200 propositions aléatoires et retient la meilleure selon le score, en écartant les doublons. Il ne revient pas sur les grilles déjà retenues : c’est une construction gloutonne.', ('portefeuille','score'), ('mutation','random')),
    term('ablation', 'Ablation et étude d’un paramètre', 'Une ablation retire un composant pour mesurer son effet. Cette étude fait varier la pénalité, avec un réglage à zéro qui la retire du score. Les autres objectifs restent actifs : zéro ne transforme donc pas la méthode en RANDOM.', ('poids','penalite-recouvrement','construction'), ('random','graines-appariees')),
    term('graine', 'Graine', 'Une valeur qui initialise un générateur pseudo-aléatoire. Avec les mêmes programmes, paramètres et environnement, elle permet de reproduire une construction ou un ensemble de tirages. Ce n’est pas une prévision des numéros tirés.', (), ('reproductibilite',)),
    term('graines-appariees', 'Graines appariées', 'Les mêmes graines sont utilisées pour les réglages comparés : la graine n° 1 sert aux quatre poids, puis la n° 2, etc. Les différences sont calculées entre constructions correspondant à la même graine ; elles peuvent néanmoins diverger après un choix de grille.', ('graine','poids'), ('tirages-communs',)),
    term('compromis-geometriques', 'Compromis géométriques', 'Les avantages et dégradations entre propriétés du portefeuille. Par exemple, une somme d’intersections plus faible peut aller avec moins de triplets couverts ou une intersection maximale plus élevée.', ('couverture','recouvrement','dispersion'), ('pareto',)),
    term('pareto', 'Front Pareto', 'Les candidats qu’aucun autre ne surpasse sur tous les critères déclarés sans dégradation. Ici les quatre critères sont couverture des paires, couverture des triplets, dispersion des fréquences et intersection maximale. La somme des intersections au carré est suivie séparément.', ('compromis-geometriques',), ('selection',)),
    term('selection', 'Sélection', 'Une règle déclarée qui retient certains candidats. Dans ces études, elle utilise les propriétés exactes et la diversité des réglages, sans choisir les graines ni les parents selon leurs résultats Monte-Carlo.', ('pareto',), ('monte-carlo','filiation')),
    term('mutation', 'Mutation', 'La modification d’un portefeuille complet existant : remplacer un numéro, échanger des numéros entre grilles ou remplacer une grille. L’enfant obtenu repasse les validations, les calculs, les preuves éventuelles et les évaluations.', ('portefeuille',), ('filiation','garantie')),
    term('croisement', 'Croisement', 'La création d’un enfant à partir de grilles de deux portefeuilles parents. Le prototype impose une contribution propre à chacun. L’enfant doit être valide et évalué ; il n’hérite pas automatiquement d’une garantie.', ('portefeuille',), ('filiation','garantie')),
    term('filiation', 'Filiation', 'Le lien enregistré entre un enfant, ses parents et l’opérateur qui l’a produit. Une génération rassemble un ensemble d’enfants ; le lien de parenté ne prouve pas une amélioration.', ('mutation','croisement',), ('selection',)),
    term('random', 'Référence aléatoire RANDOM', 'Un portefeuille construit par choix aléatoires uniformes dans les pools déclarés, sans classement par le score. Un témoin comparable conserve le nombre de grilles, le coût et les règles. Un poids de pénalité nul ne suffit pas à être RANDOM.', ('portefeuille','pool'), ('effet-pool','tirages-communs')),
    term('effet-pool', 'Effet du pool', 'L’effet associé à la restriction de l’ensemble de choix. RANDOM sur les mêmes pools et RANDOM sur 50 numéros et 12 étoiles sont deux références distinctes ; leur comparaison change aussi le pool.', ('pool','random'), ('probabilite',)),
    term('probabilite', 'Probabilité', 'Une proportion théorique d’issues d’un événement dans un modèle donné. Une fréquence mesurée sur des tirages simulés en est une estimation et garde une incertitude.', (), ('monte-carlo','intervalle-confiance')),
    term('monte-carlo', 'Simulation Monte-Carlo', 'L’évaluation sur de nombreux tirages aléatoires simulés après avoir figé les portefeuilles. Elle estime des événements comme « au moins une grille gagnante ». Elle ne prédit pas le prochain tirage.', ('portefeuille','probabilite','graine'), ('tirages-communs','intervalle-confiance')),
    term('tirages-communs', 'Tirages communs et confirmation indépendante', 'Pour comparer les candidats, chacun reçoit exactement les mêmes tirages simulés. La confirmation utilise un nouvel ensemble indépendant. Partager une graine de construction et partager des tirages d’évaluation sont deux protocoles différents.', ('monte-carlo',), ('graines-appariees',)),
    term('intervalle-confiance', 'Intervalle de confiance', 'Un intervalle calculé pour décrire l’incertitude d’une estimation. Ici Wilson à 95 % concerne la probabilité d’un événement pour un portefeuille. Il ne décrit ni la variabilité entre graines ni directement l’incertitude de la différence entre deux portefeuilles.', ('probabilite','monte-carlo'), ('significativite',)),
    term('significativite', 'Significativité statistique', 'La conclusion d’un test déclaré sur la compatibilité de résultats avec une hypothèse. Une différence de moyennes ou deux intervalles individuels ne suffisent pas à la démontrer. Les écarts de cette étude restent descriptifs.', ('intervalle-confiance','moyenne'), ('tirages-communs',)),
    term('esperance', 'Espérance', 'La moyenne théorique d’une quantité aléatoire. Pour le nombre de grilles gagnantes, on additionne leurs probabilités individuelles ; le recouvrement influence les gains simultanés, pas cette somme à nombre de grilles et règles identiques.', ('probabilite','portefeuille'), ('rang-gagnant',)),
    term('rang-gagnant', 'Grille gagnante et rang', 'Une grille dont les nombres de numéros et d’étoiles corrects satisfont un rang des règles déclarées. « Au moins une grille gagnante » et « au moins deux » sont des événements différents du portefeuille.', ('grille','portefeuille'), ('jackpot','meme-grille')),
    term('jackpot', 'Jackpot', 'Dans ce modèle EuroMillions, le rang où une même grille contient les cinq numéros et les deux étoiles du tirage. Sa probabilité exacte relève du calcul combinatoire ; une petite simulation observe rarement cet événement.', ('rang-gagnant',), ('probabilite',)),
    term('enumeration', 'Énumération exhaustive', 'Le parcours de tous les cas d’un ensemble précisément défini. Un résultat vérifié sur chaque cas est exact pour cet ensemble ; il faut conserver la définition de ce périmètre.', (), ('garantie',)),
    term('meme-grille', 'Résultat conjoint sur une même grille', 'La présence simultanée des numéros et étoiles requis dans une seule grille. Avoir les bons numéros dans A et les bonnes étoiles dans B ne remplit pas cette condition.', ('grille',), ('garantie','rang-gagnant')),
    term('garantie', 'Garantie conditionnelle', 'Une propriété prouvée pour tous les tirages satisfaisant une condition explicite, par exemple appartenir aux pools. Elle concerne les grilles exactes vérifiées et un résultat conjoint sur une même grille ; elle ne garantit pas que la condition arrivera au prochain tirage.', ('pool','enumeration','meme-grille'), ('mutation','croisement')),
    term('budget', 'Budget et coût réel', 'Le plafond autorisé et le coût des grilles effectivement construites sont deux valeurs distinctes. Dans cette configuration, 20 grilles à 2,50 € donnent un coût modélisé de 50 €. Cette valeur appartient aux règles enregistrées de l’expérience.', ('portefeuille',)),
    term('reproductibilite', 'Reproductibilité', 'La possibilité de refaire une exécution à partir de sa configuration, de ses graines, de ses sources et de ses versions enregistrées. Une empreinte SHA-256 identifie un contenu ; elle ne remplace pas sa validation scientifique.', ('graine',)),
]

CSS = '''*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:1rem}body{margin:0;background:#f7f8f3;color:#153530;font:17px/1.65 system-ui,sans-serif}a{color:#116751;text-underline-offset:.2em}header,main,footer{max-width:1000px;margin:auto;padding:1.5rem}header{display:flex;gap:1rem;justify-content:space-between;flex-wrap:wrap;border-bottom:1px solid #cdd8cc}h1{font-size:clamp(2rem,6vw,3.5rem);line-height:1.15}h2{font-size:1.3rem;margin:0 0 .7rem}p{margin:.6rem 0}nav ul{columns:3;padding-left:1.3rem}li{break-inside:avoid;margin:.3rem 0}article{background:white;border:1px solid #d9e2d8;border-radius:12px;padding:1.5rem;margin:1rem 0;scroll-margin-top:1rem}.prerequisites{font-size:.9rem;border-top:1px solid #e1e8dd;padding-top:.6rem;color:#465e50}.meta{font-size:.9rem;color:#465e50}.skip{position:absolute;left:-9999px}.skip:focus{left:1rem;background:white;padding:.5rem}a:focus-visible{outline:3px solid #a4be50;outline-offset:3px}@media(max-width:640px){nav ul{columns:1}header,main,footer{padding:1rem}article{padding:1rem}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}'''

def validate():
    nodes = {n['id']:n for n in NOTIONS}
    assert len(nodes)==len(NOTIONS), 'ID de notion répété'
    def visit(identifier, ancestors):
        assert identifier in nodes, 'notion absente : '+identifier
        assert identifier not in ancestors, 'cycle de prérequis : '+identifier
        for dependency in nodes[identifier]['requires']:
            visit(dependency, ancestors+[identifier])
    for n in NOTIONS:
        visit(n['id'], [])
        assert all(r in nodes for r in n['related'])

def build():
    validate()
    directory=ROOT/'dist/comprendre/glossaire'; directory.mkdir(parents=True,exist_ok=True)
    nodes={n['id']:n for n in NOTIONS}
    dependency_nodes={n['id']:notion_node(n,version=VERSION) for n in NOTIONS}
    def links(ids):
        return ' · '.join(f'<a href="#{i}">{escape(nodes[i]["label"])}</a>' for i in ids)
    entries=[]
    for n in NOTIONS:
        prereqs=('<p class="prerequisites">À connaître avant : '+links(n['requires'])+'</p>') if n['requires'] else '<p class="prerequisites">Définition de base · aucun prérequis déclaré</p>'
        related=('<p class="meta">Pour continuer : '+links(n['related'])+'</p>') if n['related'] else ''
        marker=dependency_nodes[n['id']]
        entries.append(f'<article id="{n["id"]}" data-notion-id="{n["id"]}" data-notion-version="{n["version"]}" data-notion-sha256="{marker["content_sha256"]}"><h2>{escape(n["label"])}</h2><p>{escape(n["definition"])}</p>{prereqs}{related}</article>')
    index=''.join(f'<li><a href="#{n["id"]}">{escape(n["label"])}</a></li>' for n in NOTIONS)
    html='''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Glossaire — AleaQuant</title><meta name="description" content="Les notions des portefeuilles, leurs définitions et leurs prérequis."><link rel="stylesheet" href="glossaire.css"></head><body><a class="skip" href="#main">Aller aux définitions</a><header><a href="/">AleaQuant</a><a href="/portefeuilles/">Atlas des portefeuilles</a></header><main id="main"><p class="meta">COMPRENDRE · GLOSSAIRE</p><h1>Les mots, dans l’ordre où l’on en a besoin.</h1><p>Chaque définition indique ses prérequis. Suivez « À connaître avant » pour remonter aux notions de base, puis revenez à votre lecture. Les liens « Pour continuer » proposent d’autres pistes.</p><p class="meta">Version '''+VERSION+' · '+DATE+' · '+str(len(NOTIONS))+''' définitions · intégration locale</p><nav aria-label="Définitions"><ul>'''+index+'</ul></nav>'+''.join(entries)+'''</main><footer><p>Les exemples décrivent cette expérience EuroMillions. Les définitions n’annoncent aucun résultat du prochain tirage.</p><a href="/portefeuilles/">Revenir aux candidats et études</a></footer></body></html>'''
    (directory/'index.html').write_text(html,encoding='utf-8')
    (directory/'glossaire.css').write_text(CSS,encoding='utf-8')
    registry={'schema':'aleaquant-documentation-1.0','version':VERSION,'built_at_date':DATE,
              'publication_status':'built_local','source':'engine/build_glossary.py',
              'source_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
              'page':{'url':'/comprendre/glossaire/','version':VERSION,'sha256':sha256(html.encode()).hexdigest()},
              'concepts':[dict(n,url='/comprendre/glossaire/#'+n['id'],
                               definition_sha256=sha256(json.dumps(n,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
                               publication_status='built_local') for n in NOTIONS]}
    (directory.parent/'documentation.json').write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    registry_path=ROOT/'configs/content-dependencies.json'
    existing=json.loads(registry_path.read_text()) if registry_path.exists() else empty_registry()
    catalogue=ROOT/'dist/portefeuilles/index.html'
    inventory=json.loads((ROOT/'docs/atlas-concept-inventory.json').read_text())
    atlas_node=page_node('page:portfolio-atlas','portefeuilles/index.html',
                         sha256(catalogue.read_bytes()).hexdigest(),
                         [c['id'] for c in inventory['concepts']],version='1.0')
    updated=update_nodes(existing,list(dependency_nodes.values())+[atlas_node],
                         managed_pages=['page:portfolio-atlas'])
    registry_path.parent.mkdir(parents=True,exist_ok=True)
    registry_path.write_text(json.dumps(updated,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'built_local','definitions':len(NOTIONS),'version':VERSION,'page_sha256':registry['page']['sha256']},ensure_ascii=False))

if __name__=='__main__': build()
