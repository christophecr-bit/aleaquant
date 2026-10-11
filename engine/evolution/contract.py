"""Versioned evolution envelope; immutable portfolio contracts stay unchanged."""
from copy import deepcopy
from pathlib import Path

from portfolio_contract import SCHEMA as PROFILE_SCHEMA, choice, integer, number, obj, seq, validate_profile
from portfolio_import import digest, load_json, require, validate_schema
from portfolio_metrics import REGISTRY
from portfolio_pipeline import CRITERIA

VERSION = 'aleaquant-evolution-study-1.0'
SELECTION = 'exact_pareto_four_v1'
MUTATIONS = ('replace_number_v1', 'swap_numbers_v1', 'replace_grid_v1')
CROSSOVER = 'grid_crossover_v1'
STRING = {'type':'string'}
SHA = {'type':'string','pattern':r'[0-9a-f]{64}'}
SCHEMA = obj({
    'schema_version':choice(VERSION),
    'id':{'type':'string','pattern':r'[A-Za-z][A-Za-z0-9_-]{0,59}'},
    'version':integer(1,100000),'title':STRING,'question':STRING,
    'base_profile':PROFILE_SCHEMA,
    'parents':seq(obj({'source':STRING,'source_sha256':SHA,'id':STRING,'content_sha256':SHA}),2,12),
    'generation':obj({'seed':integer(0,2**32-101),'population_size':integer(2,12),
                      'schedule':seq(obj({'phase':choice('mutation','crossover'),'proposals':integer(1,20)}),1,10),
                      'selection':choice(SELECTION)}),
    'bounds':obj({'max_proposals':integer(1,100),'max_run_seconds':number(.001,600)}),
    'metrics':seq(STRING,1,30),
    'confirmation':obj({'max_finalists':integer(1,12),'evaluation':PROFILE_SCHEMA['properties']['evaluation']})
})


def study_id(study):
    return 'study:'+digest(study)


def validate_study(study):
    validate_schema(study,SCHEMA)
    require(all(0<len(study[k].strip())<=2000 for k in ('title','question')),'titre/question requis, 2000 caractères maximum')
    profile=study['base_profile'];validate_profile(profile)
    require(profile['pool']['method']=='explicit','évolution : pools explicites requis')
    generation=study['generation'];parents=study['parents']
    require(len(parents)==generation['population_size'],'population initiale : un parent par place requis')
    require(len({p['content_sha256'] for p in parents})==len(parents),'parents : contenus distincts requis')
    require(len({(p['source'],p['id']) for p in parents})==len(parents),'parents : contextes répétés')
    for parent in parents:
        path=Path(parent['source'])
        require(not path.is_absolute() and '..' not in path.parts and path.parts[:2]==('dist','data') and path.suffix=='.json',
                'source parent : chemin JSON relatif dans dist/data requis')
    schedule=generation['schedule'];phases=[s['phase'] for s in schedule]
    require(phases[0]=='mutation','les premières générations réalisent des mutations')
    require(phases==sorted(phases,key=lambda p:0 if p=='mutation' else 1),'mutations avant croisements requis')
    proposals=sum(s['proposals'] for s in schedule)
    require(proposals<=study['bounds']['max_proposals'],'nombre de propositions au-delà du budget')
    compare=profile['evaluation'];confirm=study['confirmation']['evaluation']
    confirmation_profile=deepcopy(profile);confirmation_profile['evaluation']=confirm;validate_profile(confirmation_profile)
    forbidden={profile['pool']['seed']}|set(range(generation['seed'],generation['seed']+proposals))
    require(compare['seed']!=confirm['seed'],'confirmation : graine nouvelle requise')
    require(not ({compare['seed'],confirm['seed']}&forbidden),'graines MC réutilisées par pool/génération')
    metrics=study['metrics'];known={m['id'] for m in REGISTRY}
    require(len(set(metrics))==len(metrics) and set(metrics)<=known,'métriques inconnues ou répétées')
    require({c['metric_id'] for c in CRITERIA}<=set(metrics),'les quatre critères géométriques doivent être mesurés')
    max_records=len(parents)+proposals
    m=profile['constraints']['grid_count']
    require(max_records*m*compare['batch_size']<=2000000,'batch de comparaison au-delà du plafond de travail')
    require(study['confirmation']['max_finalists']*m*confirm['batch_size']<=2000000,'batch de confirmation au-delà du plafond de travail')
    return study


def load_study(path):
    return validate_study(load_json(Path(path).read_bytes()))


def schema_document():
    from portfolio_contract import schema_document as profile_schema
    schema=deepcopy(SCHEMA)
    schema['properties']['base_profile']=profile_schema()
    schema.update({'$schema':'https://json-schema.org/draft/2020-12/schema','$id':VERSION})
    return schema
