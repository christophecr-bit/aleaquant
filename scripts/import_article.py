"""Import a trusted local editorial export; never contact or publish to a host.

Auteur : AleaQuant · 2026-10-02 · Révision traçabilité : note publique, preuves et SHA de la version relue.

Version : 0.2 · Date : 2026-10-02 · Auteur : AleaQuant
Historique : impose jeu et date complète dans les titres d'analyse de tirage.
TODO : ajouter Keno lorsque ses exports de publication sont intégrés.
"""
import argparse
from datetime import date as Date
from hashlib import sha256
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MONTHS = ('janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet',
          'août', 'septembre', 'octobre', 'novembre', 'décembre')
GAME_NAMES = {'euromillions': 'EuroMillions', 'loto': 'Loto'}


def check_draw_title(title, draw_id):
    facts_path = ROOT / 'dist' / 'data' / 'facts' / f'{draw_id}.json'
    if not facts_path.is_file():
        raise ValueError(f'Faits absents : impossible de vérifier le titre de {draw_id}')
    facts = json.loads(facts_path.read_text(encoding='utf-8'))
    game = GAME_NAMES.get(facts.get('game_id'))
    if not game or game.casefold() not in title.casefold():
        raise ValueError('Le titre de tirage doit nommer explicitement le jeu')
    try:
        value = Date.fromisoformat(facts['date'])
        date_label = f'{value.day} {MONTHS[value.month - 1]} {value.year}'
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Date source absente ou invalide pour vérifier le titre') from exc
    if date_label.casefold() not in title.casefold():
        raise ValueError('Le titre de tirage doit contenir la date complète')

def digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from lint_language import lint as _lint  # noqa: E402


def validate(article):
    if article.get('schema') != 'aleaquant-article-v1' or article.get('status') != 'HUMAN_APPROVED':
        raise ValueError('Only human-approved editorial exports may be imported')
    decision, draft = article['human_decision'], article['draft']
    if decision['approved'] is not True or not decision['reviewer'].strip():
        raise ValueError('Missing human decision')
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', article['article_id']):
        raise ValueError('Invalid article ID')
    if decision['draft_sha256'] != digest(draft) or article['draft_sha256'] != digest(draft):
        raise ValueError('Draft changed after approval')
    if draft['research_pack_sha256'] != digest(article['research_pack']):
        raise ValueError('Research Pack changed after drafting')
    if article.get('kind') == 'draw_report':
        draw_id = article['research_pack'].get('draw_id')
        if not isinstance(draw_id, str) or not re.fullmatch(r'(?:EM|LO)-[A-Za-z0-9-]+', draw_id):
            raise ValueError('Identifiant de tirage absent ou invalide')
        if article['article_id'] != f'tirage-{draw_id}':
            raise ValueError('Article et tirage non concordants')
        check_draw_title(article['draft']['title'], draw_id)
        if article.get('guard', {}).get('mode') == 'compose':
            _sys.path.insert(0, str(ROOT / 'agent'))
            from article_traceability import validate_traceability
            facts = json.loads((ROOT / 'dist/data/facts' / f'{draw_id}.json').read_text())
            issues = validate_traceability(article, facts)
            if issues:
                raise ValueError('Traçabilité refusée : ' + '; '.join(issues))
    if not draft['body'].strip() or not draft['claims']:
        raise ValueError('Empty article')
    # chantier D3 : la ligne éditoriale est un test qui échoue, pas une consigne.
    infractions = _lint(draft['title'] + "\n" + draft['body'])
    if infractions:
        detail = ' ; '.join(f"{nom} — {extrait}" for nom, extrait, _ in infractions)
        raise ValueError(f'Vocabulaire refusé par le linter : {detail}')
    return article

def import_article(source, destination):
    article = validate(json.loads(source.read_text()))
    production = destination.resolve() == (ROOT / 'dist/articles.json').resolve()
    if production and article.get('kind') == 'draw_report':
        draw_id = article['research_pack']['draw_id']
        facts_path = ROOT / 'dist/data/facts' / f'{draw_id}.json'
        if not facts_path.is_file() or sha256(facts_path.read_bytes()).hexdigest() != article['research_pack'].get('facts_sha256'):
            raise ValueError(f'Faits absents ou modifiés depuis la rédaction : {draw_id}')
    journal = json.loads(destination.read_text()) if destination.exists() else {'schema':'aleaquant-journal-v1','articles':[]}
    if article.get('kind') == 'draw_report':
        for existing in journal['articles']:
            if (existing.get('kind') == 'draw_report'
                    and existing.get('research_pack', {}).get('draw_id') == article['research_pack']['draw_id']
                    and existing.get('article_id') != article['article_id']):
                raise ValueError('Un autre article est déjà associé à ce tirage')
    journal['articles'] = [a for a in journal['articles'] if a['article_id'] != article['article_id']] + [article]
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(journal, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(destination)
    if production and article.get('kind') == 'draw_report':
        import sys
        sys.path.insert(0, str(ROOT / 'engine'))
        from build_pages import refresh_draw_page
        refresh_draw_page(article['research_pack']['draw_id'])
    return article['article_id']

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args=parser.parse_args()
    print(import_article(args.source, ROOT/'dist/articles.json'))
