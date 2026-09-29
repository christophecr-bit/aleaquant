"""Import a trusted local editorial export; never contact or publish to a host."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()

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
    if not draft['body'].strip() or not draft['claims']:
        raise ValueError('Empty article')
    return article

def import_article(source, destination):
    article = validate(json.loads(source.read_text()))
    journal = json.loads(destination.read_text()) if destination.exists() else {'schema':'aleaquant-journal-v1','articles':[]}
    journal['articles'] = [a for a in journal['articles'] if a['article_id'] != article['article_id']] + [article]
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(journal, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(destination)
    return article['article_id']

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args=parser.parse_args()
    print(import_article(args.source, ROOT/'dist/articles.json'))
