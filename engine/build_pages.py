"""Pages statiques par tirage EuroMillions, une par tirage, lisibles sans JavaScript.

Entrées (lecture seule) : dist/data/facts/<draw>.json (un fichier par tirage, voir
build_data.py --facts), dist/data/draws.json (ordre chronologique, règle).
Sorties : dist/tirages/euromillions/<date>/index.html (une par tirage),
          dist/tirages/euromillions/index.html (index chronologique),
          dist/sitemap.xml, dist/rss.xml

Usage : python3 engine/build_pages.py
"""
import html
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
       '<a href="/#explorer">Explorer</a><a href="/tirages/euromillions/">Tirages</a>'
       '<a href="/#atlas">Atlas</a><a href="/#geometries">Géométries</a><a href="/#lab">Lab</a>'
       '<a href="/#dictionnaire">Métriques</a><a href="/#journal">Le journal</a>'
       '<a href="/#methode">Méthode</a></nav>')
FOOTER = ('<footer><a class="brand" href="/">Alea<span>Quant</span></a>'
          '<p>Comprendre. Mesurer. Questionner.</p>'
          '<span>Une exploration scientifique, sans promesse de gain.</span></footer>')


def esc(s):
    return html.escape(str(s), quote=True)


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


def page_html(facts, prev_id, next_id):
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


def build():
    draws_data = read_json(DATA / 'draws.json')
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
        (page_dir / 'index.html').write_text(page_html(facts, prev_id, next_id), encoding='utf-8')
        written += 1
    (out_dir / 'index.html').write_text(index_html(rows), encoding='utf-8')

    # sitemap.xml
    urls = [f'{SITE_URL}/', f'{SITE_URL}/tirages/euromillions/']
    urls += [f'{SITE_URL}/tirages/euromillions/{r[1]}/' for r in rows]
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

    print(json.dumps({'pages_written': written, 'total_draws': len(rows),
                       'sitemap_urls': len(urls)}, indent=1))


if __name__ == '__main__':
    build()
