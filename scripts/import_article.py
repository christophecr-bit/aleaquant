"""Import a trusted local editorial export; never contact or publish to a host."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

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
