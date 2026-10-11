"""Strict paired-seed studies reuse the operational portfolio profile contract."""
from copy import deepcopy
from pathlib import Path

from portfolio_contract import SCHEMA as PROFILE_SCHEMA, choice, integer, number, obj, seq, validate_profile
from portfolio_import import digest, load_json, require, validate_schema
from portfolio_metrics import REGISTRY

VERSION = 'aleaquant-study-1.0'
AXIS = 'objectives.minimize_overlap.numbers'
PROTOCOL = 'same_pool_paired_seeds'
SELECTION = 'geometry_pareto_diverse_v1'
STRING = {'type':'string'}
SCHEMA = obj({
    'schema_version': choice(VERSION),
    'id': {'type':'string','pattern':r'[A-Za-z][A-Za-z0-9_-]{0,59}'},
    'version': integer(1,100000), 'title':STRING, 'question':STRING,
    'base_profile': PROFILE_SCHEMA,
    'vary':obj({'parameter':choice(AXIS),'values':seq(number(0,100),2,8)}),
    'generation':obj({'seeds':seq(integer(0,2**32-2),2,50),'repetitions':integer(2,50)}),
    'bounds':obj({'max_constructions':integer(4,100),'max_run_seconds':number(.001,600)}),
    'comparison':obj({'method':choice(PROTOCOL),'metrics':seq(STRING,1,30)}),
    'confirmation':obj({'selection':choice(SELECTION),'max_finalists':integer(2,12),
                        'evaluation':PROFILE_SCHEMA['properties']['evaluation']}),
    'references':seq(obj({'id':STRING,'content_sha256':{'type':'string','pattern':r'[0-9a-f]{64}'}}),0,100)
})


def study_id(study):
    return 'study:'+digest(study)


def template_profiles(study):
    profiles=[]
    for index,weight in enumerate(study['vary']['values']):
        p=deepcopy(study['base_profile'])
        p['id']=f"{study['id']}_w{index:02d}"
        p['search']['seed']=study['generation']['seeds'][0]
        p['objectives']['minimize_overlap']['numbers']=weight
        profiles.append(p)
    return profiles


def validate_study(study):
    validate_schema(study,SCHEMA)
    require(all(0<len(study[k].strip())<=2000 for k in ('title','question')),'titre/question de l’étude : texte requis, 2000 caractères maximum')
    p=study['base_profile'];validate_profile(p)
    require(p['pool']['method']=='explicit','étude appariée : pools explicites obligatoires')
    require(p['search']['method']=='prototype_greedy' and p['search']['candidate_count']==1,
            'étude appariée : une construction prototype_greedy par réglage et graine')
    weights=study['vary']['values'];seeds=study['generation']['seeds']
    require(len(set(weights))==len(weights) and weights==sorted(weights),'poids : valeurs distinctes et croissantes requises')
    require(weights[0]==0,'poids zéro requis comme témoin de l’ablation')
    require(len(set(seeds))==len(seeds),'graines de génération répétées')
    require(study['generation']['repetitions']==len(seeds),'répétitions : nombre incompatible avec les graines déclarées')
    require(len(weights)*len(seeds)<=study['bounds']['max_constructions'],'nombre de constructions au-delà de la limite déclarée')
    require(study['confirmation']['max_finalists']>=len(weights),'confirmation : limite insuffisante pour représenter chaque réglage')
    known={m['id'] for m in REGISTRY}
    metrics=study['comparison']['metrics']
    require(len(set(metrics))==len(metrics) and set(metrics)<=known,'métriques d’étude inconnues ou répétées')
    mandatory={'portfolio.distinct_pairs@v1','portfolio.distinct_triples@v1',
               'portfolio.number_overlap_square_sum@v1','portfolio.number_frequency_sd@v1'}
    require(mandatory<=set(metrics),'étude overlap : métriques de couverture, intersections et fréquences requises')
    confirm=deepcopy(p);confirm['evaluation']=study['confirmation']['evaluation'];validate_profile(confirm)
    compare_seed=p['evaluation']['seed'];confirm_seed=confirm['evaluation']['seed']
    require(compare_seed!=confirm_seed,'confirmation : nouvel échantillon, graine distincte de comparaison requise')
    require(not ({compare_seed,confirm_seed}&(set(seeds)|{p['pool']['seed']})),
            'évaluations : graines réutilisées par la génération ou le pool')
    work=len(weights)*len(seeds)*p['constraints']['grid_count']*p['evaluation']['batch_size']
    require(work<=2000000,'batch de comparaison : plafond de travail dépassé')
    work=study['confirmation']['max_finalists']*p['constraints']['grid_count']*confirm['evaluation']['batch_size']
    require(work<=2000000,'batch de confirmation : plafond de travail dépassé')
    refs=study['references']
    require(len({r['id'] for r in refs})==len(refs),'références d’étude répétées')
    for template in template_profiles(study):
        for seed in seeds:
            expanded=deepcopy(template);expanded['search']['seed']=seed;validate_profile(expanded)
    return study


def load_study(path):
    return validate_study(load_json(Path(path).read_bytes()))


def schema_document():
    schema=deepcopy(SCHEMA)
    from portfolio_contract import schema_document as profile_schema
    schema['properties']['base_profile']=profile_schema()
    schema.update({'$schema':'https://json-schema.org/draft/2020-12/schema','$id':VERSION})
    return schema
