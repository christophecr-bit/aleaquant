"""Pages statiques EuroMillions et Loto, lisibles sans JavaScript.

Entrées (lecture seule) : dist/data/facts/<draw>.json (un fichier par tirage, voir
build_data.py --facts), dist/data/draws.json (ordre chronologique, règle).
Sorties : dist/tirages/euromillions/<date>/index.html,
          dist/tirages/loto/<draw_id>/index.html (la date seule n'est pas unique),
          un index chronologique pour chaque jeu,
          dist/sitemap.xml, dist/rss.xml

Usage : python3 engine/build_pages.py
"""
import html
from hashlib import sha256
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import DATA, read_json  # noqa: E402
DIST = DATA.parent

RARITY_FR = {'COMMON': 'courante', 'UNCOMMON': 'peu courante', 'RARE': 'rare', 'VERY_RARE': 'très rare'}
SITE_URL = 'https://aleaquant.aleaquant.workers.dev'
NAV = ('<a class="brand" href="/">Alea<span>Quant</span><i>∴</i></a>'
       '<nav aria-label="Navigation principale">'
       '<a href="/#explorer">Explorer</a><a href="/tirages/">Tirages</a>'
       '<a href="/#atlas">Atlas</a><a href="/#geometries">Géométries</a><a href="/#lab">Lab</a>'
       '<a href="/#dictionnaire">Métriques</a><a href="/#journal">Le journal</a>'
       '<a href="/#methode">Méthode</a></nav>')
FOOTER = ('<footer><a class="brand" href="/">Alea<span>Quant</span></a>'
          '<p>Comprendre. Mesurer. Questionner.</p>'
          '<span>Une exploration scientifique, sans promesse de gain.</span></footer>')


def esc(s):
    return html.escape(str(s), quote=True)


def content_sha256(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(',', ':')).encode()).hexdigest()


def date_fr(d):
    mois = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août',
            'septembre', 'octobre', 'novembre', 'décembre']
    y, m, day = d.split('-')
    return f'{int(day)} {mois[int(m) - 1]} {y}'


def fmt_num(n):
    return f'{n:,}'.replace(',', ' ')


def pct(p):
    if p >= 0.01:
        return ('%.1f' % (100 * p)).replace('.', ',') + ' %'
    if p >= 0.0001:
        return ('%.2f' % (100 * p)).replace('.', ',') + ' %'
    return 'moins de 0,01 %'


def mcard(fact):
    label = esc(fact['label'])
    rarity = fact.get('rarity')
    chip = f'<span class="chip {rarity}">{RARITY_FR.get(rarity, rarity)}</span>' if rarity else ''
    value = fact['value']
    shown = str(value).replace('-', '·') if not isinstance(value, (int, float)) else value
    sub_bits = [f'classe : {pct(fact["p_class"])} des combinaisons']
    if 'p_le' in fact:
        sub_bits.append(f'{pct(fact["p_le"])} ≤ ce niveau')
    hp = fact.get('historical_prior')
    hist = ''
    if hp:
        hist = (f'<p class="small">Observée {fmt_num(hp["count"])} fois sur {fmt_num(hp["draws"])} '
                f'tirages antérieurs (attendu {hp["expected"]}).</p>')
    return (f'<div class="mcard"><h4>{label}{chip}</h4>'
            f'<div class="val">{esc(shown)}</div>'
            f'<div class="sub">{esc(" · ".join(sub_bits))}</div>{hist}</div>')


def balls_html(main, stars):
    m = ''.join(f'<span class="ball">{n:02d}</span>' for n in main)
    s = ''.join(f'<span class="ball star">{n:02d}</span>' for n in stars)
    return f'<div class="balls">{m}<span class="sep"></span>{s}</div>'


def approved_articles_by_draw():
    """Indexe uniquement les récits approuvés, toujours par identifiant de tirage."""
    journal_path = DIST / 'articles.json'
    if not journal_path.exists():
        return {}
    articles = {}
    for article in read_json(journal_path).get('articles', []):
        if article.get('kind') != 'draw_report' or article.get('status') != 'HUMAN_APPROVED':
            continue
        draw_id = article.get('research_pack', {}).get('draw_id')
        if not draw_id or article.get('article_id') != f'tirage-{draw_id}':
            continue
        draft = article.get('draft', {})
        pack = article['research_pack']
        decision = article.get('human_decision', {})
        if (article.get('schema') != 'aleaquant-article-v1'
                or decision.get('approved') is not True
                or not str(decision.get('reviewer', '')).strip()
                or content_sha256(draft) != article.get('draft_sha256')
                or content_sha256(draft) != decision.get('draft_sha256')
                or content_sha256(pack) != draft.get('research_pack_sha256')):
            continue
        facts_path = DATA / 'facts' / f'{draw_id}.json'
        if not facts_path.is_file() or sha256(facts_path.read_bytes()).hexdigest() != article['research_pack'].get('facts_sha256'):
            continue
        if draw_id in articles:
            raise ValueError(f'Plusieurs articles approuvés pour {draw_id}')
        articles[draw_id] = article
    return articles


def article_html(article):
    if article is None:
        return ''
    draft = article['draft']
    paragraphs = ''.join(f'<p>{esc(part.strip())}</p>' for part in draft['body'].split('\n\n') if part.strip())
    return (f'<article class="draw-article" aria-labelledby="article-title">'
            f'<span class="eyebrow">ARTICLE · RELU ET APPROUVÉ</span>'
            f'<h2 id="article-title">{esc(draft["title"])}</h2>'
            f'<div class="draw-article-body">{paragraphs}</div></article>')


def page_html(facts, prev_id, next_id, article=None):
    f_by_id = {f['fact_id']: f for f in facts['facts']}
    draw_id, date, rule = facts['draw_id'], facts['date'], facts['rule_id']
    main, stars = facts['main'], facts['stars']
    is_current_rule = 'F.stars.rule' not in f_by_id
    metric_facts = [f for f in facts['facts'] if f.get('category') == 'class_metric']
    cards = ''.join(mcard(f) for f in metric_facts)

    pascal = f_by_id.get('F.pascal.subsets')
    history = f_by_id.get('F.history.exact_main')
    signature = f_by_id.get('F.signature')
    expectation = f_by_id.get('F.editorial.expectation')
    stars_rule = f_by_id.get('F.stars.rule')
    grid_prob = f_by_id.get('F.grid.probability')

    callouts = []
    if pascal:
        callouts.append(f'<div class="callout"><span class="big">C(5,2)=C(5,3)</span><div><strong>Triangle de Pascal</strong><p>{esc(pascal["statement"])}</p></div></div>')
    if history:
        callouts.append(f'<div class="callout"><span class="big">{"0" if history["value"]["count"] == 0 else history["value"]["count"]}</span><div><strong>Déjà-vu</strong><p>{esc(history["statement"])}</p></div></div>')
    if not is_current_rule and stars_rule:
        callouts.append(f'<p class="small"><em>{esc(stars_rule["statement"])}</em></p>')
    if signature:
        callouts.append(f'<p class="small">{esc(signature["statement"])}</p>')

    prevnext = '<nav class="draw-pager" aria-label="Tirages voisins">'
    prevnext += f'<a href="../{prev_id}/">← Tirage précédent</a>' if prev_id else '<span></span>'
    prevnext += '<a href="../">Tous les tirages</a>'
    prevnext += f'<a href="../{next_id}/">Tirage suivant →</a>' if next_id else '<span></span>'
    prevnext += '</nav>'

    title = f'Tirage EuroMillions du {date_fr(date)} — {draw_id} | AleaQuant'
    desc = (f'Analyse AleaQuant du tirage EuroMillions {draw_id} ({date_fr(date)}) : '
            f'loi exacte, rareté des métriques, historique antérieur. Comprendre n’est pas prédire.')
    ld = {
        '@context': 'https://schema.org', '@type': 'Article',
        'headline': f'Tirage EuroMillions du {date_fr(date)}',
        'datePublished': date, 'description': desc,
        'author': {'@type': 'Organization', 'name': 'AleaQuant'},
        'publisher': {'@type': 'Organization', 'name': 'AleaQuant'},
    }
    canonical = f'{SITE_URL}/tirages/euromillions/{date}/'

    return f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="article"><meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{canonical}">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='9' fill='%230e2928'/%3E%3Cpath d='M10 29 20 10 30 29M15 22h10' stroke='%23d8f36a' stroke-width='3' fill='none'/%3E%3C/svg%3E">
<link rel="stylesheet" href="../../../style.css"><link rel="stylesheet" href="../../../atlas.css">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body><a class="skip" href="#main">Aller au contenu</a><header>{NAV}<span class="edition">ÉDITION EXPÉRIMENTALE · V0</span></header>
<main id="main"><section class="section" aria-labelledby="draw-title">
<div class="section-head"><div><span class="eyebrow">DRAW / EUROMILLIONS · {esc(draw_id)}</span>
<h1 id="draw-title">Tirage du {date_fr(date)}</h1></div>
<p>{esc(grid_prob["statement"]) if grid_prob else ""}</p></div>
<div class="draw-head"><div>{balls_html(main, stars)}
<p class="draw-meta">{date_fr(date)} · tirage {esc(draw_id)} · {fmt_num(facts["prior_draws"])} tirages antérieurs dans l’historique · règle {esc(rule)}</p></div></div>
{article_html(article)}
{"".join(callouts)}
<div class="metric-grid">{cards}</div>
<p class="small">Loi exacte : énumération complète, sans simulation. Comparaisons historiques calculées uniquement sur les tirages antérieurs à ce tirage (aucun regard en avant).</p>
{f'<p class="callout"><em>{esc(expectation["statement"])}</em></p>' if expectation else ""}
<p><a class="text-link" href="/#{esc(draw_id)}">Explorer ce tirage dans l’outil interactif →</a></p>
{prevnext}
</section></main>{FOOTER}</body></html>'''


def index_html(rows):
    items = ''.join(
        f'<li><a href="{d}/">{date_fr(d)} — {esc(did)}</a></li>'
        for did, d, *_ in reversed(rows))
    title = 'Tous les tirages EuroMillions | AleaQuant'
    desc = 'Index chronologique de tous les tirages EuroMillions analysés par AleaQuant, du plus récent au plus ancien.'
    return f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE_URL}/tirages/euromillions/">
<link rel="alternate" type="application/rss+xml" title="AleaQuant — Tirages EuroMillions" href="/rss.xml">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='9' fill='%230e2928'/%3E%3Cpath d='M10 29 20 10 30 29M15 22h10' stroke='%23d8f36a' stroke-width='3' fill='none'/%3E%3C/svg%3E">
<link rel="stylesheet" href="../../style.css"><link rel="stylesheet" href="../../atlas.css"></head>
<body><a class="skip" href="#main">Aller au contenu</a><header>{NAV}<span class="edition">ÉDITION EXPÉRIMENTALE · V0</span></header>
<main id="main"><section class="section"><div class="section-head"><div><span class="eyebrow">DRAW / EUROMILLIONS</span>
<h1>Tous les tirages</h1></div><p>{fmt_num(len(rows))} tirages, du plus récent au plus ancien. Chaque page détaille la loi exacte de ses métriques et son historique antérieur (sans regard en avant).</p></div>
<ul class="draw-index">{items}</ul></section></main>{FOOTER}</body></html>'''


def loto_draw_label(facts):
    label = date_fr(facts['date'])
    session = facts.get('session')
    if session:
        label += ' — ' + {'1': '1er tirage', '2': '2e tirage'}.get(str(session),
                                                            f'tirage {session}')
    return label


def loto_balls_html(components):
    """Distingue Chance et complémentaire, qui n'avaient pas le même rôle."""
    main = ''.join(f'<span class="ball">{n:02d}</span>' for n in components['main'])
    if 'chance' in components:
        secondary, label = components['chance'], 'Numéro Chance'
    elif 'complementaire' in components:
        secondary = components['complementaire']
        label = 'Numéro complémentaire — tiré, mais non coché sur la grille'
    else:
        raise ValueError('composante secondaire Loto absente')
    other = ''.join(f'<span class="ball loto-secondary">{n:02d}</span>' for n in secondary)
    return (f'<div class="balls">{main}<span class="sep"></span>{other}'
            f'<span class="draw-component-label">{esc(label)}</span></div>')


def loto_page_html(facts, prev_id, next_id, article=None):
    """Page Loto fondée uniquement sur les faits du régime du tirage."""
    by_id = {f['fact_id']: f for f in facts['facts']}
    draw_id, date, rule = facts['draw_id'], facts['date'], facts['rule_id']
    label = loto_draw_label(facts)
    title = f'Tirage Loto du {label} — {draw_id} | AleaQuant'
    desc = (f'Analyse du tirage Loto {draw_id} du {label} : loi exacte des '
            'métriques et historique de la même formule, sans prédiction.')
    canonical = f'{SITE_URL}/tirages/loto/{draw_id}/'
    grid = by_id['F.grid.probability']['value']['grid']
    k, domain = grid['main']['picks'], grid['main']['domain']
    metrics = [f for f in facts['facts'] if f.get('category') == 'class_metric']
    cards = ''.join(mcard(f) for f in metrics)
    history = by_id.get('F.history.exact_main')
    signature = by_id.get('F.signature')
    expectation = by_id.get('F.editorial.expectation')
    callouts = []
    if history:
        callouts.append('<div class="callout"><span class="big">'
                        + esc(history['value']['count'])
                        + '</span><div><strong>Déjà-vu des numéros principaux</strong><p>'
                        + esc(history['statement']) + '</p></div></div>')
    if signature:
        callouts.append(f'<p class="small">{esc(signature["statement"])}</p>')
    pager = ('<nav class="draw-pager" aria-label="Tirages voisins">'
             + (f'<a href="../{esc(prev_id)}/">← Tirage précédent</a>' if prev_id else '<span></span>')
             + '<a href="../">Tous les tirages Loto</a>'
             + (f'<a href="../{esc(next_id)}/">Tirage suivant →</a>' if next_id else '<span></span>')
             + '</nav>')
    ld = {
        '@context': 'https://schema.org', '@type': 'Article',
        'headline': f'Tirage Loto du {label}',
        'datePublished': date, 'description': desc,
        'author': {'@type': 'Organization', 'name': 'AleaQuant'},
        'publisher': {'@type': 'Organization', 'name': 'AleaQuant'},
    }
    nav = NAV
    complement_note = ('La complémentaire historique n’entre pas dans la probabilité de '
                       'la grille.' if 'complementaire' in facts['components'] else '')
    return f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="article"><meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{canonical}">
<link rel="stylesheet" href="../../../style.css"><link rel="stylesheet" href="../../../atlas.css">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script></head>
<body><a class="skip" href="#main">Aller au contenu</a><header>{nav}<span class="edition">ÉDITION EXPÉRIMENTALE · V0</span></header>
<main id="main"><section class="section" aria-labelledby="draw-title">
<div class="section-head"><div><span class="eyebrow">DRAW / LOTO · {esc(draw_id)}</span>
<h1 id="draw-title">Tirage du {esc(label)}</h1></div>
<p>{esc(by_id['F.grid.probability']['statement'])}</p></div>
<div class="draw-head"><div>{loto_balls_html(facts['components'])}
<p class="draw-meta">{esc(label)} · {esc(draw_id)} · {fmt_num(facts['prior_draws'])} tirages antérieurs comparables · règle {esc(rule)}</p></div></div>
{article_html(article)}
{''.join(callouts)}
<div class="metric-grid">{cards}</div>
<p class="small">Loi exacte des {k} numéros parmi {domain} : énumération complète, sans simulation. L’historique compare seulement les tirages antérieurs de la même formule {k}/{domain}. {complement_note}</p>
{f'<p class="callout"><em>{esc(expectation["statement"])}</em></p>' if expectation else ''}
<p><a class="text-link" href="/tirages/euromillions/">Explorer aussi les tirages EuroMillions →</a></p>
{pager}
</section></main>{FOOTER}</body></html>'''


def loto_index_html(facts_list):
    date_min = facts_list[0]['date'] if facts_list else ''
    date_max = facts_list[-1]['date'] if facts_list else ''
    items = ''.join(
        f'<li data-date="{esc(f["date"])}"><a href="{esc(f["draw_id"])}/">{esc(loto_draw_label(f))}'
        f' — {esc(f["draw_id"])}</a></li>' for f in reversed(facts_list))
    title = 'Tous les tirages Loto | AleaQuant'
    desc = ('Index des tirages Loto analysés par AleaQuant. Les anciens premier et second '
            'tirages d’une même journée ont chacun leur page.')
    nav = NAV
    return f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE_URL}/tirages/loto/">
<link rel="stylesheet" href="../../style.css"><link rel="stylesheet" href="../../atlas.css">
<script src="../../loto-index.js" defer></script></head>
<body><a class="skip" href="#main">Aller au contenu</a><header>{nav}<span class="edition">ÉDITION EXPÉRIMENTALE · V0</span></header>
<main id="main"><section class="section"><div class="section-head"><div><span class="eyebrow">DRAW / LOTO</span>
<h1>Tous les tirages Loto</h1></div><p>{fmt_num(len(facts_list))} tirages. Les métriques et l’historique de chaque page respectent la formule en vigueur à sa date. <a href="/tirages/euromillions/">Voir aussi EuroMillions</a>.</p></div>
<div class="loto-date-search"><label for="loto-date">Aller à une date Loto</label>
<input id="loto-date" type="date" min="{esc(date_min)}" max="{esc(date_max)}">
<p id="loto-date-status" class="small" aria-live="polite">Choisir une date filtre la liste ; certaines dates ont deux tirages distincts.</p></div>
<ul class="draw-index" id="loto-index">{items}</ul></section></main>{FOOTER}</body></html>'''


def games_index_html(em_count, loto_count):
    """Choix explicite du jeu ; seuls les jeux publiés sont proposés."""
    title = 'Choisir un jeu et explorer ses tirages | AleaQuant'
    desc = 'Tirages EuroMillions et Loto analysés selon leurs règles historiques.'
    return f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE_URL}/tirages/">
<link rel="stylesheet" href="../style.css"><link rel="stylesheet" href="../atlas.css"></head>
<body><a class="skip" href="#main">Aller au contenu</a><header>{NAV}<span class="edition">ÉDITION EXPÉRIMENTALE · V0</span></header>
<main id="main"><section class="section"><div class="section-head"><div><span class="eyebrow">DRAW / JEUX</span>
<h1>Choisir un jeu</h1></div><p>Les règles et les lois changent selon le jeu et la date du tirage.</p></div>
<div class="game-choices">
<a class="game-choice" href="/tirages/euromillions/"><strong>EuroMillions</strong><span>{fmt_num(em_count)} tirages analysés · cinq numéros et deux étoiles</span><em>Explorer EuroMillions →</em></a>
<a class="game-choice" href="/tirages/loto/"><strong>Loto</strong><span>{fmt_num(loto_count)} tirages analysés · formules historiques respectées</span><em>Explorer Loto →</em></a>
</div><p class="small">Keno est en préparation : ses lois et son historique ne sont pas encore publiés.</p>
</section></main>{FOOTER}</body></html>'''


def refresh_draw_page(draw_id):
    """Met à jour la seule page concernée après import d'un article approuvé."""
    facts_path = DATA / 'facts' / f'{draw_id}.json'
    if not facts_path.is_file():
        raise ValueError(f'Faits introuvables pour {draw_id}')
    facts = read_json(facts_path)
    article = approved_articles_by_draw().get(draw_id)
    if draw_id.startswith('EM-'):
        rows = read_json(DATA / 'draws.json')['rows']
        positions = [i for i, row in enumerate(rows) if row[0] == draw_id]
        if len(positions) != 1:
            raise ValueError(f'Tirage EuroMillions non unique dans draws.json : {draw_id}')
        i = positions[0]
        previous = rows[i - 1][1] if i else None
        following = rows[i + 1][1] if i + 1 < len(rows) else None
        output = DIST / 'tirages' / 'euromillions' / facts['date'] / 'index.html'
        content = page_html(facts, previous, following, article)
    elif draw_id.startswith('LO-'):
        loto = [read_json(path) for path in (DATA / 'facts').glob('LO-*.json')]
        loto.sort(key=lambda f: (f['date'], str(f.get('session') or ''), f['draw_id']))
        positions = [i for i, item in enumerate(loto) if item['draw_id'] == draw_id]
        if len(positions) != 1:
            raise ValueError(f'Tirage Loto non unique : {draw_id}')
        i = positions[0]
        previous = loto[i - 1]['draw_id'] if i else None
        following = loto[i + 1]['draw_id'] if i + 1 < len(loto) else None
        output = DIST / 'tirages' / 'loto' / draw_id / 'index.html'
        content = loto_page_html(facts, previous, following, article)
    else:
        raise ValueError(f'Page de tirage non prise en charge : {draw_id}')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding='utf-8')
    return output


def build():
    draws_data = read_json(DATA / 'draws.json')
    articles = approved_articles_by_draw()
    rows = draws_data['rows']  # [id, date, rule, main, stars, mvals, svals]
    ids = [r[0] for r in rows]
    out_dir = DIST / 'tirages' / 'euromillions'
    out_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for i, row in enumerate(rows):
        draw_id, date = row[0], row[1]
        fpath = DATA / 'facts' / f'{draw_id}.json'
        if not fpath.exists():
            continue
        facts = read_json(fpath)
        prev_id = rows[i - 1][1] if i > 0 else None
        next_id = rows[i + 1][1] if i < len(rows) - 1 else None
        page_dir = out_dir / date
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / 'index.html').write_text(
            page_html(facts, prev_id, next_id, articles.get(draw_id)), encoding='utf-8')
        written += 1
    (out_dir / 'index.html').write_text(index_html(rows), encoding='utf-8')

    # La date seule n'identifie pas les anciens tirages Loto : le premier et le
    # second tirage partagent une date sur 1 886 journées. L'URL utilise draw_id.
    loto_facts = [read_json(p) for p in (DATA / 'facts').glob('LO-*.json')]
    loto_facts.sort(key=lambda f: (f['date'], str(f.get('session') or ''), f['draw_id']))
    loto_dir = DIST / 'tirages' / 'loto'
    loto_dir.mkdir(parents=True, exist_ok=True)
    for i, facts in enumerate(loto_facts):
        draw_id = facts['draw_id']
        prev_id = loto_facts[i - 1]['draw_id'] if i else None
        next_id = loto_facts[i + 1]['draw_id'] if i + 1 < len(loto_facts) else None
        page_dir = loto_dir / draw_id
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / 'index.html').write_text(
            loto_page_html(facts, prev_id, next_id, articles.get(draw_id)), encoding='utf-8')
    (loto_dir / 'index.html').write_text(loto_index_html(loto_facts), encoding='utf-8')

    # Un point d'entrée commun rend explicite le jeu choisi, notamment depuis
    # la navigation des pages de tirage. Le Keno n'y figure pas avant qualification.
    game_dir = DIST / 'tirages'
    game_dir.mkdir(parents=True, exist_ok=True)
    (game_dir / 'index.html').write_text(
        games_index_html(len(rows), len(loto_facts)), encoding='utf-8')

    # sitemap.xml
    urls = [f'{SITE_URL}/', f'{SITE_URL}/tirages/', f'{SITE_URL}/tirages/euromillions/',
            f'{SITE_URL}/tirages/loto/']
    urls += [f'{SITE_URL}/tirages/euromillions/{r[1]}/' for r in rows]
    urls += [f'{SITE_URL}/tirages/loto/{f["draw_id"]}/' for f in loto_facts]
    sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
               ''.join(f'<url><loc>{esc(u)}</loc></url>\n' for u in urls) +
               '</urlset>\n')
    (DIST / 'sitemap.xml').write_text(sitemap, encoding='utf-8')

    # rss.xml : les 30 derniers tirages
    recent = list(reversed(rows))[:30]
    items = []
    for r in recent:
        did, date = r[0], r[1]
        link = f'{SITE_URL}/tirages/euromillions/{date}/'
        items.append(f'<item><title>Tirage EuroMillions du {date_fr(date)}</title>'
                     f'<link>{esc(link)}</link><guid>{esc(link)}</guid>'
                     f'<pubDate>{date}T20:00:00Z</pubDate></item>')
    rss = ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
           '<title>AleaQuant — Tirages EuroMillions</title>'
           f'<link>{SITE_URL}/tirages/euromillions/</link>'
           '<description>Analyse AleaQuant de chaque tirage EuroMillions : loi exacte, rareté, historique.</description>'
           + ''.join(items) + '</channel></rss>\n')
    (DIST / 'rss.xml').write_text(rss, encoding='utf-8')

    print(json.dumps({'euromillions_pages_written': written, 'loto_pages_written': len(loto_facts),
                       'total_draws': len(rows) + len(loto_facts),
                       'sitemap_urls': len(urls)}, indent=1))


if __name__ == '__main__':
    build()
