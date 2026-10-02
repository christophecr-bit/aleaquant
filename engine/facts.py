"""JSON de facts d'un tirage : la seule matière autorisée pour l'agent de publication.

Chaque fact porte un identifiant stable, un énoncé factuel en français, la ou les
valeurs, la méthode et une catégorie compatible avec le Research Pack
(exact_grid, class_metric, descriptive_profile, historical, exhaustive, interpretation).
Règle anti look-ahead : les comparaisons historiques n'utilisent que les tirages
strictement antérieurs au tirage analysé.

Version : 0.2 | Date : 2026-10-02 | Auteur : AleaQuant
Historique : 0.2 ajoute F.main.decade_sums, descriptif et sans rareté.
TODO : garder les métriques descriptives distinctes des class_metric munies d'une loi.
"""
from collections import Counter
from itertools import combinations
from math import comb

from common import (CURRENT_RULE, ENGINE_VERSION, MAIN_CAT, MAIN_FIELDS, STAR_FIELDS,
                    rule_domains, rule_star_total,
                    key, rarity)
from metrics import profil_dizaines

LABELS = {
    'sum': 'somme', 'span': 'étendue', 'min_gap': 'écart minimal', 'max_gap': 'écart maximal',
    'mean_gap': 'écart moyen', 'longest_consecutive_run': 'plus longue suite consécutive',
    'consecutive_pairs': 'paires consécutives', 'runs_ge2': 'suites d’au moins deux',
    'max_same_decade': 'maximum dans une même dizaine', 'occupied_decades': 'dizaines occupées',
    'odd_count': 'nombre d’impairs', 'low_count': 'nombre de numéros bas (1–25)',
    'repeated_terminal_digits': 'finales répétées',
    'terminal_pair_collisions': 'paires de même finale',
    'is_arithmetic_progression': 'progression arithmétique complète',
    'longest_arithmetic_progression': 'plus longue progression arithmétique',
    'arithmetic_triples': 'triplets arithmétiques',
    'clusteredness_close_pairs_5': 'paires distantes d’au plus 5',
    'sorted_gaps': 'écarts ordonnés', 'decade_counts': 'répartition par dizaines',
}
STAR_LABELS = {'gap': 'écart des étoiles', 'consecutive': 'étoiles consécutives',
               'odd_count': 'étoiles impaires', 'low_count': 'étoiles basses (1–6)',
               'sum': 'somme des étoiles', 'terminal_coincidence': 'étoiles de même finale'}


def decade_sums_fact(numbers, domain):
    """Fait descriptif des sous-totaux par dizaine, sans classe de rareté."""
    profile = profil_dizaines(numbers, domain)
    parts = [f"D{b['decade']} : somme {b['sum']} pour {b['count']} "
             f"{'numéro' if b['count'] == 1 else 'numéros'}" for b in profile]
    return {
        'fact_id': 'F.main.decade_sums',
        'metric': 'main.decade_sums',
        'label': 'Somme par dizaine',
        'value': {'profile': list(profile)},
        'category': 'descriptive_profile',
        'method': 'somme déterministe des valeurs par tranche de dix',
        'statement': 'Sommes et effectifs par dizaine : ' + ' ; '.join(parts) + '.',
    }


def fmt(x):
    if isinstance(x, float):
        return ('%.4f' % x).rstrip('0').rstrip('.').replace('.', ',')
    return str(x)


def nb(n):
    return f'{n:,}'.replace(',', '\u202f')


def plural(n, word):
    return '%s %s%s' % (nb(n), word, '' if n <= 1 else 's')


def pct(p):
    if p >= 0.01:
        return ('%.1f' % (100 * p)).replace('.', ',') + ' %'
    if p >= 0.0001:
        return ('%.2f' % (100 * p)).replace('.', ',') + ' %'
    return 'moins de 0,01 %'


class LawIndex:
    """Probabilités exactes P(X = v), P(X ≤ v), P(X ≥ v) pour chaque métrique."""

    def __init__(self, law: dict, total: int, numeric: bool):
        self.total, self.numeric = total, numeric
        self.count = dict(law)
        if numeric:
            items = sorted(((float(k), c) for k, c in law.items()))
            acc, self.le = 0, {}
            for v, c in items:
                acc += c
                self.le[v] = acc

    def p(self, k):
        return self.count.get(k, 0) / self.total

    def tails(self, k):
        v = float(k)
        le = self.le[v] / self.total
        ge = 1 - le + self.count[k] / self.total
        return le, ge


def build_indexes(laws):
    idx = {}
    for f in MAIN_FIELDS:
        idx['main.' + f] = LawIndex(laws['main'][f], laws['main_total'], True)
    for f in MAIN_CAT:
        idx['main.' + f] = LawIndex(laws['main'][f], laws['main_total'], False)
    for f in STAR_FIELDS:
        idx['stars.' + f] = LawIndex(laws['stars'][f], laws['stars_total'], True)
    return idx


def metric_fact(metric_id, label, value, index, prior_values, n_prior):
    k = key(value)
    p = index.p(k)
    fact = {
        'fact_id': 'F.' + metric_id, 'metric': metric_id, 'label': label,
        'value': k if not index.numeric else value,
        'class_size': index.count.get(k, 0), 'domain_size': index.total,
        'p_class': p, 'rarity': rarity(p), 'category': 'class_metric',
        'method': 'loi exacte par énumération complète',
    }
    parts = ['%s = %s' % (label.capitalize(), k.replace('-', '·') if not index.numeric else fmt(value)),
             'classe de %s sur %s (%s)' % (plural(fact['class_size'], 'combinaison'), nb(index.total), pct(p))]
    if index.numeric:
        le, ge = index.tails(k)
        fact.update({'p_le': le, 'p_ge': ge, 'tail': min(le, ge)})
        if min(le, ge) < 0.05:
            side = 'basse' if le < ge else 'haute'
            parts.append('queue %s : %s des combinaisons sont à ce niveau ou au-delà' % (side, pct(min(le, ge))))
    seen = prior_values.get(k, 0)
    fact['historical_prior'] = {'count': seen, 'draws': n_prior,
                                'expected': round(p * n_prior, 2)}
    parts.append('observée %d fois sur %d tirages antérieurs (attendu %s)' % (
        seen, n_prior, fmt(round(p * n_prior, 1))))
    fact['statement'] = ' ; '.join(parts) + '.'
    return fact


def build_draw_facts(draw, prior_rows, laws, idx, patterns, pascal_prior):
    """Facts d'un tirage. prior_rows contient les métriques déjà calculées des tirages antérieurs.

    prior_rows : liste de dicts {'main': {...}, 'stars': {...} ou None, 'rule':...}
    pascal_prior : Counter des paires / triplets / quadruplets vus avant le tirage.
    """
    main, stars = tuple(draw['main']), tuple(draw['stars'])
    mp, sp = patterns.main_pattern(main), patterns.stars_pattern(stars)
    n_prior = len(prior_rows)
    # dénominateur de la combinaison complète : règle en vigueur à la date du tirage
    # (9, 11 ou 12 étoiles). laws['stars_total'] vaut toujours C(12,2) puisque les lois
    # exactes sont bâties sur la règle courante ; l'utiliser ici fausserait les 940
    # tirages antérieurs à septembre 2016.
    total_main = laws['main_total']
    total_stars = rule_star_total(draw['rule'])
    main_domain, stars_domain = rule_domains(draw['rule'])
    facts = [{
        'fact_id': 'F.grid.probability', 'category': 'exact_grid', 'method': 'combinatoire exacte',
        'value': {'full_combinations': total_main * total_stars, 'rule_id': draw['rule'],
                  'main_domain': main_domain, 'stars_domain': stars_domain},
        # la règle est nommée dans le libellé : sans elle, un dénominateur de 2011
        # (11 étoiles) est incompréhensible pour qui connaît la règle actuelle.
        'statement': ('Sous la règle en vigueur à la date du tirage — 5 numéros sur %d et '
                      '2 étoiles sur %d —, chaque combinaison complète a la même '
                      'probabilité, 1 sur %s : %s + étoiles %s n’était ni plus ni moins '
                      'probable qu’une autre.') % (
            main_domain, stars_domain, nb(total_main * total_stars),
            '-'.join(map(str, main)), '-'.join(map(str, stars)))
    }, {
        'fact_id': 'F.editorial.expectation', 'category': 'interpretation',
        'method': 'principe éditorial AleaQuant',
        'statement': ('L’espérance de gain d’une mise est négative. Ces mesures décrivent '
                          'la forme du tirage ; elles ne permettent pas de prédire le suivant.')}]

    facts.append(decade_sums_fact(main, main_domain))

    for f in MAIN_FIELDS + MAIN_CAT:
        mid = 'main.' + f
        counts = Counter(r['main'][f] for r in prior_rows)
        facts.append(metric_fact(mid, LABELS[f], mp[f] if f in MAIN_CAT else _num(mp[f]),
                                 idx[mid], counts, n_prior))
    if draw['rule'] == CURRENT_RULE:
        star_rows = [r for r in prior_rows if r['rule'] == CURRENT_RULE]
        for f in STAR_FIELDS:
            sid = 'stars.' + f
            counts = Counter(r['stars'][f] for r in star_rows)
            facts.append(metric_fact(sid, STAR_LABELS[f], _num(sp[f]), idx[sid], counts, len(star_rows)))
    else:
        facts.append({'fact_id': 'F.stars.rule', 'category': 'interpretation', 'method': 'règlement',
                      'statement': 'Ce tirage relève d’une ancienne règle des étoiles (%s) : '
                                   'ses étoiles ne sont pas comparées à la loi à 12 étoiles.' % draw['rule']})

    # Triangle de Pascal : autant de paires que de triplets dans 5 numéros
    sub = {}
    for t in (2, 3, 4):
        subsets = list(combinations(main, t))
        seen = [s for s in subsets if pascal_prior[t].get(s, 0) > 0]
        top = max(subsets, key=lambda s: pascal_prior[t].get(s, 0))
        sub[t] = {'in_draw': len(subsets), 'domain': comb(50, t), 'already_seen': len(seen),
                  'most_seen': ['-'.join(map(str, top)), pascal_prior[t].get(top, 0)],
                  'expected_seen_per_subset': round(n_prior * comb(50 - t, 5 - t) / comb(50, 5), 3)}
    facts.append({
        'fact_id': 'F.pascal.subsets', 'category': 'exhaustive', 'method': 'combinatoire + historique antérieur',
        'value': sub,
        'statement': ('Cinq numéros contiennent %d paires et %d triplets : C(5,2) = C(5,3), symétrie du '
                      'triangle de Pascal. Mais le domaine compte %s paires contre %s triplets. '
                      'Avant ce tirage, %d de ses %d paires étaient déjà sorties ensemble '
                      '(la plus fréquente, %s, %d fois), contre %d de ses %d triplets.') % (
            sub[2]['in_draw'], sub[3]['in_draw'], nb(sub[2]['domain']), nb(sub[3]['domain']), sub[2]['already_seen'], sub[2]['in_draw'],
            sub[2]['most_seen'][0].replace('-', '–'), sub[2]['most_seen'][1],
            sub[3]['already_seen'], sub[3]['in_draw'])})
    exact_repeat = pascal_prior[5].get(main, 0)
    facts.append({
        'fact_id': 'F.history.exact_main', 'category': 'historical', 'method': 'historique antérieur',
        'value': {'count': exact_repeat, 'quadruplets_seen': sub[4]['already_seen']},
        'statement': ('Ces cinq numéros n’étaient jamais sortis ensemble auparavant' if exact_repeat == 0
                      else 'Ces cinq numéros étaient déjà sortis ensemble %d fois' % exact_repeat) +
                     '. ' + ('Aucun de ses 5 quadruplets n’avait été tiré.' if sub[4]['already_seen'] == 0 else
                             ('Un de ses 5 quadruplets avait déjà été tiré.' if sub[4]['already_seen'] == 1 else
                              '%d de ses 5 quadruplets avaient déjà été tirés.' % sub[4]['already_seen']))})

    signature = patterns.main_signature(mp)
    sig_prior = sum(1 for r in prior_rows if r['signature'] == signature)
    # le code brut (run=2;decade_max=4;decades=2) reste dans value pour les
    # comparaisons machine, mais le libellé le traduit : tel quel il est opaque.
    signature_fr = ('suite consécutive maximale de %s, maximum de %s numéros dans une même '
                    'dizaine, %s dizaines occupées') % (
        mp['longest_consecutive_run'], mp['max_same_decade'], mp['occupied_decades'])
    facts.append({'fact_id': 'F.signature', 'category': 'historical', 'method': 'signature patterns.py',
                  'value': {'signature': signature, 'signature_fr': signature_fr,
                            'prior': sig_prior, 'draws': n_prior},
                  'statement': 'Forme du tirage (%s) déjà observée %d fois sur %d tirages antérieurs.' % (
                      signature_fr, sig_prior, n_prior)})

    return {
        'schema': 'aleaquant-draw-facts-v1', 'engine': ENGINE_VERSION,
        'game_id': 'euromillions', 'draw_id': draw['id'], 'date': draw['date'], 'rule_id': draw['rule'],
        'main': list(main), 'stars': list(stars),
        'source': {'publisher': draw.get('publisher'), 'source_id': draw.get('source'),
                   'revision': draw.get('revision'), 'revision_sha256': draw.get('sha256')},
        'laws_patterns_sha256': laws['patterns_sha256'],
        'prior_draws': n_prior, 'no_look_ahead': True,
        'facts': facts,
    }


def _num(v):
    from common import num
    return num(v)
