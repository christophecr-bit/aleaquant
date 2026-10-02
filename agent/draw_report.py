"""Agent de publication V0 : facts d'un tirage -> brouillon d'article -> validation humaine.

Auteur : AleaQuant · 2026-10-02 · Révision traçabilité : note publique, preuves et SHA de la version relue.

Le rédacteur n'a accès qu'au JSON de facts. Chaque phrase du brouillon est une
« claim » qui cite ses facts ; un garde vérifie que tout nombre écrit figure dans
les facts cités (aucun chiffre inventé). Rien n'est publié sans `approve`.

  python3 agent/draw_report.py draft  dist/data/facts/latest.json
  python3 agent/draw_report.py show   runs/EM-26077/draft.json
  python3 agent/draw_report.py approve runs/EM-26077/draft.json --reviewer "Christophe"
  python3 agent/draw_report.py reject  runs/EM-26077/draft.json --reviewer "Christophe" --comment "..."

`approve` écrit runs/<tirage>/article.json puis l'importe dans dist/articles.json
avec scripts/import_article.py (validation des SHA inchangée).
Le mode `template` est déterministe. Un mode LLM pourra réécrire le style sous le
même contrat (mêmes facts, mêmes claims, même garde).

Version : 0.3 | Date : 2026-10-02 | Auteur : AleaQuant
Historique : le sélecteur ignore les profils descriptifs non classés par une loi.
TODO : rendre le rédacteur template multi-jeux avec les faits propres à chaque jeu.
"""
import argparse
import datetime as dt
import json
import re
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from import_article import digest, import_article  # noqa: E402

WRITER = 'aleaquant-draw-report-template-v1'
MONTHS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre',
          'octobre', 'novembre', 'décembre']
FINE_GRAINED = {'main.sorted_gaps', 'main.decade_counts'}  # classes très fines : rareté trompeuse
NUMBER = re.compile(r'\d+(?:[.,]\d+)?')


def date_fr(iso):
    d = dt.date.fromisoformat(iso)
    return '%d %s %d' % (d.day, MONTHS[d.month - 1], d.year)


THOUSANDS = re.compile(r'(?<=\d)[\u202f\u00a0 ](?=\d{3}(?!\d))')


def normalize_numbers(text):
    """Ensemble des nombres d'un texte ; « 139 838 160 » compte pour un seul nombre."""
    text = THOUSANDS.sub('', THOUSANDS.sub('', text))
    return {n.replace(',', '.').lstrip('0') or '0' for n in NUMBER.findall(text)}


class Writer:
    def __init__(self, facts):
        self.facts = facts
        self.by_id = {f['fact_id']: f for f in facts['facts']}
        self.claims = []

    def claim(self, text, *fact_ids, category=None):
        missing = [i for i in fact_ids if i not in self.by_id]
        if missing:
            raise ValueError('fact inconnu : %s' % missing)
        cid = 'C%02d' % (len(self.claims) + 1)
        cat = category or self.by_id[fact_ids[0]].get('category', 'interpretation')
        self.claims.append({'claim_id': cid, 'text': text, 'category': cat, 'evidence_ids': list(fact_ids)})
        return text

    def f(self, fid):
        return self.by_id[fid]


def select(facts):
    """Facts remarquables : queues de loi (< 5 %) ou classes rares, hors classes trop fines."""
    notable, ordinary = [], []
    for f in facts['facts']:
        if f.get('category') != 'class_metric' or f['metric'] in FINE_GRAINED:
            continue
        tail = f.get('tail', 1.0)
        if tail < 0.05 or f['rarity'] in ('RARE', 'VERY_RARE'):
            notable.append((min(tail, f['p_class']), f))
        elif 0.25 <= f['p_class'] <= 0.7:
            ordinary.append((-f['p_class'], f))
    notable.sort(key=lambda t: t[0])
    ordinary.sort(key=lambda t: t[0])
    # deux métriques qui découpent le domaine de la même façon (étendue et écart moyen)
    # disent la même chose : on n'en garde qu'une
    kept, partitions = [], set()
    for _, f in notable:
        sig = (f['class_size'], round(f.get('tail', 1.0), 9))
        if sig not in partitions:
            partitions.add(sig)
            kept.append(f)
    return kept[:3], [f for _, f in ordinary[:2]]


def pct(p):
    return (('%.1f' % (100 * p)) if p >= 0.01 else ('%.2f' % (100 * p))).replace('.', ',') + ' %'


def nb(n):
    return f'{n:,}'.replace(',', ' ')


def write(facts):
    w = Writer(facts)
    main = ' · '.join('%02d' % n for n in facts['main'])
    stars = ' · '.join('%02d' % n for n in facts['stars'])
    game = {'euromillions': 'EuroMillions', 'loto': 'Loto', 'keno': 'Keno'}.get(
        facts.get('game_id'), facts.get('game_id', 'Jeu').replace('_', ' ').title())
    title = '%s — tirage du %s : %s ★ %s' % (game, date_fr(facts['date']), main, stars)
    paras = []

    g = w.f('F.grid.probability')
    paras.append(w.claim('Le %s, EuroMillions a tiré %s, étoiles %s. Comme toute combinaison complète, '
                         'celle-ci avait une chance sur %s de sortir, ni plus ni moins qu’une autre.' % (
                             date_fr(facts['date']), main, stars, nb(g['value']['full_combinations'])),
                         'F.grid.probability'))

    notable, ordinary = select(facts)
    sum_in_notable = any(f['fact_id'] == 'F.main.sum' for f in notable)
    if notable:
        lines = []
        for f in notable:
            side = ''
            if f.get('tail', 1) < 0.05:
                side = ' Elle se situe dans une queue de la loi : %s des combinaisons atteignent ce niveau ou le dépassent.' % pct(f['tail'])
            lines.append(w.claim('%s : %s. La classe correspondante regroupe %s sur %s, soit %s.%s' % (
                f['label'].capitalize(), f['value'] if isinstance(f['value'], str) else str(f['value']).replace('.', ','),
                nb(f['class_size']) + (' combinaison' if f['class_size'] <= 1 else ' combinaisons'),
                nb(f['domain_size']), pct(f['p_class']), side), f['fact_id']))
        paras.append('Ce qui se remarque dans sa forme. ' + ' '.join(lines))
    else:
        paras.append(w.claim('Aucune des métriques suivies ne place ce tirage dans une queue de sa loi exacte '
                             'ni dans une classe rare : c’est une forme ordinaire.', 'F.main.sum', category='class_metric'))
    if not sum_in_notable:
        # évite de répéter l'info déjà donnée ci-dessus quand la somme elle-même est le fait notable
        s = w.f('F.main.sum')
        paras.append(w.claim('La somme des cinq numéros vaut %s : %s des combinaisons ont une somme inférieure '
                             'ou égale, %s une somme supérieure ou égale. Chaque valeur de somme est une classe '
                             'de grilles ; les classes centrales sont les plus peuplées.' % (
                                 s['value'], pct(s['p_le']), pct(s['p_ge'])), 'F.main.sum'))
    if ordinary:
        o = ordinary[0]
        paras.append(w.claim('À l’inverse, %s vaut %s, la valeur de la classe la plus peuplée : %s des combinaisons.' % (
            o['label'], str(o['value']).replace('.', ','), pct(o['p_class'])), o['fact_id']))

    p = w.f('F.pascal.subsets')['value']
    paras.append(w.claim('Une grille de cinq numéros contient autant de paires que de triplets : 10 et 10, '
                         'car C(5,2) = C(5,3) dans le triangle de Pascal. Le domaine, lui, compte %s paires '
                         'et %s triplets. Avant ce tirage, %d de ses 10 paires étaient déjà sorties ensemble, '
                         'et %d de ses 10 triplets.' % (nb(p['2']['domain'] if '2' in p else p[2]['domain']),
                                                        nb(p['3']['domain'] if '3' in p else p[3]['domain']),
                                                        (p['2'] if '2' in p else p[2])['already_seen'],
                                                        (p['3'] if '3' in p else p[3])['already_seen']),
                         'F.pascal.subsets'))
    h = w.f('F.history.exact_main')
    paras.append(w.claim(h['statement'], 'F.history.exact_main'))
    paras.append(w.claim(w.f('F.editorial.expectation')['statement'], 'F.editorial.expectation'))

    body = '\n\n'.join(paras)
    return title, body, w.claims


def guard(claims, facts):
    """Chaque nombre d'une claim doit apparaître dans ses facts (énoncé ou valeurs), ou dans le tirage."""
    by_id = {f['fact_id']: f for f in facts['facts']}
    allowed_base = normalize_numbers(', '.join(map(str, facts['main'] + facts['stars'])) + ', ' + facts['date'])
    allowed_base |= {'2', '3', '5', '10'}  # C(5,2), C(5,3), « cinq », « 10 paires »
    problems = []
    for c in claims:
        allowed = set(allowed_base)
        for fid in c['evidence_ids']:
            allowed |= normalize_numbers(json.dumps(by_id[fid], ensure_ascii=False))
            allowed |= normalize_numbers(by_id[fid]['statement'])
        extra = normalize_numbers(c['text']) - allowed
        # les pourcentages sont recalculés depuis p_class / tail : tolérance d'arrondi
        extra = {x for x in extra if not _is_rounded_pct(x, c, by_id)}
        if extra:
            problems.append('%s : nombres absents des facts %s' % (c['claim_id'], sorted(extra)))
    return problems


def _is_rounded_pct(x, claim, by_id):
    try:
        v = float(x)
    except ValueError:
        return False
    for fid in claim['evidence_ids']:
        f = by_id[fid]
        for k in ('p_class', 'tail', 'p_le', 'p_ge'):
            if k in f and abs(100 * f[k] - v) < 0.051:
                return True
    return False


def draft(facts_path: Path, out_dir: Path):
    facts_bytes = facts_path.read_bytes()
    facts = json.loads(facts_bytes)
    title, body, claims = write(facts)
    problems = guard(claims, facts)
    used = sorted({i for c in claims for i in c['evidence_ids']})
    research_pack = {
        'question': 'Que dit la forme du tirage %s, sans prétendre prédire le suivant ?' % facts['draw_id'],
        'draw_id': facts['draw_id'], 'facts_schema': facts['schema'],
        'facts_sha256': sha256(facts_bytes).hexdigest(), 'engine': facts['engine'],
        'evidence': [{'evidence_id': f['fact_id'], 'claim': f['statement'], 'method': f['method'],
                      'category': f['category']} for f in facts['facts'] if f['fact_id'] in used],
    }
    d = {'title': title, 'body': body, 'claims': claims, 'writer': WRITER,
         'research_pack_sha256': digest(research_pack)}
    article = {'schema': 'aleaquant-article-v1', 'article_id': 'tirage-' + facts['draw_id'],
               'kind': 'draw_report', 'status': 'PENDING_HUMAN' if not problems else 'BLOCKED',
               'guard': {'problems': problems}, 'draft_sha256': digest(d), 'draft': d,
               'research_pack': research_pack, 'human_decision': None,
               'provenance': {'writer': WRITER, 'created_at': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
                              'facts_path': str(facts_path)}}
    out = out_dir / facts['draw_id'] / 'draft.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(article, ensure_ascii=False, indent=2) + '\n')
    return out, article


def decide(path: Path, reviewer: str, approved: bool, comment: str):
    article = json.loads(path.read_text())
    if article['status'] == 'BLOCKED':
        raise SystemExit('Brouillon bloqué par le garde : %s' % article['guard']['problems'])
    if article['draft_sha256'] != digest(article['draft']):
        raise SystemExit('Le brouillon a été modifié après génération : relancer draft.')
    if article.get('guard', {}).get('mode') == 'compose':
        from article_traceability import validate_traceability
        facts_path = ROOT / 'dist/data/facts' / (article['research_pack']['draw_id'] + '.json')
        if sha256(facts_path.read_bytes()).hexdigest() != article['research_pack']['facts_sha256']:
            raise SystemExit('Faits modifiés : régénérer avant approbation')
        issues = validate_traceability(article, json.loads(facts_path.read_text()))
        if issues:
            raise SystemExit('Traçabilité refusée : ' + '; '.join(issues))
    if not reviewer.strip():
        raise SystemExit('Nom du relecteur requis.')
    article['human_decision'] = {'approved': approved, 'reviewer': reviewer, 'comment': comment,
                                 'draft_sha256': article['draft_sha256'],
                                 'decided_at': dt.datetime.now().astimezone().isoformat(timespec='seconds')}
    article['status'] = 'HUMAN_APPROVED' if approved else 'HUMAN_REJECTED'
    out = path.with_name('article.json' if approved else 'rejected.json')
    out.write_text(json.dumps(article, ensure_ascii=False, indent=2) + '\n')
    if approved:
        return out, import_article(out, ROOT / 'dist' / 'articles.json')
    return out, None


def show(path: Path):
    a = json.loads(path.read_text())
    print('#', a['draft']['title'], '\n')
    print(a['draft']['body'], '\n')
    for c in a['draft']['claims']:
        print('  [%s] ← %s' % (c['claim_id'], ', '.join(c['evidence_ids'])))
    print('\nstatut :', a['status'], '| garde :', a['guard']['problems'] or 'OK')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('draft'); p.add_argument('facts', type=Path); p.add_argument('--out', type=Path, default=ROOT / 'runs')
    p = sub.add_parser('show'); p.add_argument('draft', type=Path)
    for name in ('approve', 'reject'):
        p = sub.add_parser(name); p.add_argument('draft', type=Path)
        p.add_argument('--reviewer', required=True); p.add_argument('--comment', default='')
    args = ap.parse_args()
    if args.cmd == 'draft':
        out, article = draft(args.facts, args.out)
        show(out)
        print('\nbrouillon :', out)
    elif args.cmd == 'show':
        show(args.draft)
    else:
        out, imported = decide(args.draft, args.reviewer, args.cmd == 'approve', args.comment)
        print(('publié dans dist/articles.json : %s' % imported) if imported else ('rejet enregistré : %s' % out))


if __name__ == '__main__':
    main()
