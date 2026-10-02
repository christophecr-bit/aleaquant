"""Traçabilité publique et contrôles partagés, v1.0 — 2026-10-02.

Auteur : AleaQuant. Historique : notes dérivées des faits, jamais du LLM.
TODO : compléter les URL et dates de couverture à l'ingestion ; l'appariement
lexical reste un détecteur conservateur, pas une preuve sémantique universelle.
"""
import html
import json
import re
from urllib.parse import urlsplit

VERSION = 'traceability-v1'


def interpretation_issues(text):
    normalized = text.casefold().replace('’', "'")
    patterns = (r'au[- ]dessus de (?:sa|la|leur) r[ée]f[ée]rence',
                r'c.est (?:ici|l[àa]) que se trouve l.information')
    return ['Comparaison de rareté interne sans sens public : ' + m.group(0)
            for p in patterns for m in re.finditer(p, normalized)]


def scoped_rarity_issues(text, facts):
    """Un qualificatif ne peut emprunter la rareté d'une autre composante."""
    from guards import paragraph_evidence, guard_interpretive_words
    by_id = {f['fact_id']: f for f in facts.get('facts', [])}
    issues = []
    for paragraph in text.split('\n\n'):
        context = []
        for sentence in re.split(r'[.!?]\s+', paragraph):
            ids = paragraph_evidence(sentence, facts)
            metrics = [by_id[eid] for eid in ids if by_id[eid].get('metric')]
            if metrics:
                context = metrics
            if context:
                for word, _ in guard_interpretive_words(sentence, {'facts': context}):
                    issues.append(f'Rareté non justifiée pour la mesure citée : {word}')
    return issues


def build_methodology(facts, claims):
    """Projection publique sur liste blanche ; aucune clé, chemin local ou prompt."""
    components = []
    for prefix, label in [('main.', 'numéros principaux'), ('stars.', 'étoiles')]:
        group = [f for f in facts.get('facts', []) if f.get('metric', '').startswith(prefix)]
        domains = sorted({f['domain_size'] for f in group if isinstance(f.get('domain_size'), int)})
        priors = sorted({f['historical_prior']['draws'] for f in group
                         if isinstance(f.get('historical_prior', {}).get('draws'), int)})
        if group:
            components.append({'label': label, 'domains': domains, 'prior_draws': priors})
    source = facts.get('source') or {}
    sources = {k: source[k] for k in ('publisher', 'source_id', 'revision', 'revision_sha256') if k in source}
    url = source.get('url') or source.get('source_url')
    if isinstance(url, str) and urlsplit(url).scheme in ('http', 'https') and urlsplit(url).hostname and not urlsplit(url).username:
        sources['url'] = url
    note = [f"Cette analyse porte sur le tirage {facts.get('draw_id', '')} du {facts.get('date', '')}. "
            "Elle distingue les propriétés de la grille, leur fréquence théorique et les observations historiques."]
    for c in components:
        if len(c['domains']) == 1:
            note.append(f"Pour les {c['label']}, les fréquences de classe portent sur {format(c['domains'][0], ',').replace(',', ' ')} combinaisons possibles.")
        if len(c['prior_draws']) == 1:
            note.append(f"Les comparaisons historiques des {c['label']} portent sur {c['prior_draws'][0]:,} tirages antérieurs comparables.".replace(',', ' '))
    if facts.get('no_look_ahead') is True:
        note.append("L'historique exclut le tirage étudié et les suivants. Une absence signifie uniquement « non observé dans cet historique ».")
    note.extend(["Une fréquence de classe mesure la proportion de combinaisons donnant exactement la même valeur d'une mesure. Elle se distingue d'une probabilité de queue et de celle de la grille complète.",
                 "Le modèle suppose des tirages équiprobables et indépendants. Ces mesures décrivent le hasard ; elles ne permettent pas de prévoir les prochains numéros."])
    missing = []
    if 'url' not in sources:
        missing.append("Lien vers l'archive source non renseigné dans ce dossier.")
    if not facts.get('history_coverage'):
        missing.append("Dates de début et de fin de l'historique non renseignées dans ce dossier.")
    by_id = {f['fact_id']: f for f in facts.get('facts', [])}
    used = sorted({eid for c in claims for eid in c.get('evidence_ids', [])})
    return {'version': VERSION, 'note': '\n\n'.join(note), 'source': sources,
            'rule_id': facts.get('rule_id'), 'engine': facts.get('engine'),
            'facts_schema': facts.get('schema'), 'components': components,
            'limitations': missing,
            'evidence': [{'id': eid, 'statement': by_id[eid].get('statement', ''),
                          'method': by_id[eid].get('method', 'Méthode non renseignée')}
                         for eid in used if eid in by_id],
            'claims': [{'id': c['claim_id'], 'text': c['text'], 'evidence_ids': c['evidence_ids']}
                       for c in claims]}


def methodology_html(methodology):
    if not methodology:
        return ''
    esc = lambda v: html.escape(str(v), quote=True)
    m = methodology
    paragraphs = ''.join('<p>' + esc(p) + '</p>' for p in m['note'].split('\n\n'))
    details = []
    source = m.get('source', {})
    details.append('<p>Source : ' + esc(source.get('publisher', 'non renseignée')) +
                   ' · ' + esc(source.get('source_id', 'identifiant non renseigné')) + '</p>')
    url = source.get('url', '')
    if urlsplit(url).scheme in ('http', 'https') and urlsplit(url).hostname and not urlsplit(url).username:
        details.append('<p><a rel="noopener noreferrer" href="' + esc(url) + '">Archive source</a></p>')
    details.append('<p>Règle : ' + esc(m.get('rule_id')) + ' · Calculs : ' + esc(m.get('engine')) + '</p>')
    details.extend('<p>' + esc(x) + '</p>' for x in m.get('limitations', []))
    details.append('<ul>' + ''.join('<li>' + esc(e['id']) + ' — ' + esc(e['statement']) +
                   ' · Méthode : ' + esc(e['method']) + '</li>' for e in m.get('evidence', [])) + '</ul>')
    details.append('<ol>' + ''.join('<li>' + esc(c['text']) + ' — Preuves : ' +
                   esc(', '.join(c['evidence_ids'])) + '</li>' for c in m.get('claims', [])) + '</ol>')
    return '<section class="article-methodology"><h3>Sources et méthode</h3>' + paragraphs + '<details><summary>Sources et calculs</summary>' + ''.join(details) + '</details></section>'


def validate_traceability(article, facts):
    """Rejoué à la génération, review et import ; ne fait confiance ni au statut ni aux gardes sauvegardés."""
    from guards import paragraph_evidence, run_all_guards, guard_full_text, METHODO_NOTE
    draft = article['draft']
    claims = draft.get('claims', [])
    issues = []
    body = draft['body'].removesuffix(METHODO_NOTE).strip()
    checks = run_all_guards(body, facts)
    issues.extend(f'{name}: {item}' for name, values in checks.items() for item in values)
    for c in claims:
        expected = set(paragraph_evidence(c['text'], facts))
        cited = set(c.get('evidence_ids', []))
        local_facts = {**facts, 'facts': [f for f in facts.get('facts', []) if f['fact_id'] in cited]}
        for number in sorted(guard_full_text(c['text'], local_facts)):
            issues.append(f"{c['claim_id']} : nombre absent des preuves citées : {number}")
        if expected - cited:
            issues.append(f"{c['claim_id']} : preuves manquantes {', '.join(sorted(expected-cited))}")
        if cited - expected:
            issues.append(f"{c['claim_id']} : preuves sans rattachement détectable {', '.join(sorted(cited-expected))}")
        if not cited and re.search(r'\d', c['text']):
            issues.append(f"{c['claim_id']} : affirmation chiffrée sans preuve identifiée")
        if c['text'] not in body:
            issues.append(f"{c['claim_id']} : texte absent du corps")
    covered = body
    for c in sorted(claims, key=lambda c: len(c['text']), reverse=True):
        covered = covered.replace(c['text'], '')
    if re.search(r'\d', covered) or paragraph_evidence(covered, facts):
        issues.append('Affirmation factuelle détectée dans le corps hors registre des claims')
    pack = article['research_pack']
    actual = {e['evidence_id']: e for e in pack.get('evidence', [])}
    for f in facts.get('facts', []):
        e = actual.get(f['fact_id'])
        if e is None or e.get('claim') != f.get('statement', '') or e.get('method', '') != f.get('method', ''):
            issues.append(f"Preuve source absente ou altérée : {f['fact_id']}")
    expected_method = build_methodology(facts, claims)
    if draft.get('methodology') != expected_method:
        issues.append('Note méthodologique absente ou différente des faits validés : régénérer')
    mode = article.get('provenance', {}).get('mode')
    if mode not in ('batch', 'direct', 'text_import'):
        issues.append('Mode de génération absent ou inconnu : régénérer sans inventer de provenance')
    return list(dict.fromkeys(issues))


def refresh_review_metadata(article, facts):
    """Nouvelle version : réattribuer, rejouer, invalider toute décision précédente."""
    from guards import paragraph_evidence, METHODO_NOTE
    from draw_report import digest
    draft = article['draft']
    draft['body'] = draft['body'].removesuffix(METHODO_NOTE).strip()
    draft['claims'] = [{'claim_id': f'C{i}', 'text': p.strip(),
                        'evidence_ids': paragraph_evidence(p, facts)}
                       for i, p in enumerate(draft['body'].split('\n\n'), 1)
                       if p.strip() and (paragraph_evidence(p, facts) or re.search(r'\d', p))]
    used = {eid for c in draft['claims'] for eid in c['evidence_ids']}
    for e in article['research_pack']['evidence']:
        e['cited'] = e['evidence_id'] in used
    draft['research_pack_sha256'] = digest(article['research_pack'])
    draft['methodology'] = build_methodology(facts, draft['claims'])
    draft['draft_version'] = 'traceability-v1'
    article['human_decision'] = None
    article['draft_sha256'] = digest(draft)
    issues = validate_traceability(article, facts)
    article['guard'] = {'mode': 'compose', 'checks': {'traceability': issues}, 'problems': issues}
    article['status'] = 'BLOCKED' if issues else 'PENDING_HUMAN'
    return article
