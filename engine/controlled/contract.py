"""Strict envelope for generation and its untargeted RANDOM controls."""
from copy import deepcopy
from pathlib import Path

from portfolio_contract import choice, integer, number, obj, seq, validate_profile
from portfolio_import import digest, load_json, require, validate_schema
from portfolio_study_contract import validate_study as validate_ablation
from evolution.contract import validate_study as validate_evolution

VERSION='aleaquant-controlled-study-1.0'
SEEDS=dict(seq(integer(0,2**32-2),10,10))
CONTROLS={'type':'object','additionalProperties':False,'required':['same_pool'],
          'properties':{role:obj({'seeds':SEEDS}) for role in ('same_pool','full_domain')}}
SCHEMA=obj({'schema_version':choice(VERSION),
            'id':{'type':'string','pattern':r'[A-Za-z][A-Za-z0-9_-]{0,49}'},
            'version':integer(1,100000),'title':{'type':'string'},'question':{'type':'string'},
            'experiment_kind':choice('ablation','evolution'),'experiment':{},
            'random_controls':CONTROLS,
            'bounds':obj({'max_total_constructions':integer(1,100),'max_run_seconds':number(.001,600)})})


def study_id(study):
    return 'study:'+digest(study)


def main_capacity(study):
    experiment=study['experiment']
    if study['experiment_kind']=='ablation':
        return len(experiment['vary']['values'])*len(experiment['generation']['seeds'])
    return len(experiment['parents'])+sum(p['proposals'] for p in experiment['generation']['schedule'])


def control_profile(study,role,seed):
    require(role in study['random_controls'],'rôle de contrôle non demandé')
    profile=deepcopy(study['experiment']['base_profile'])
    profile.update(id=study['id']+'_'+role,version=study['version'],family='RANDOM')
    if role=='full_domain':
        profile['pool'].update(method='explicit',numbers=list(range(1,51)),stars=list(range(1,13)),
                               number_count=50,star_count=12)
    for key in profile['objectives']:
        if key!='minimize_overlap':profile['objectives'][key]=0
    profile['objectives']['minimize_overlap'].update(numbers=0,stars=0)
    profile['search'].update(method='random',seed=seed,candidate_count=1,candidates_per_step=1,
                             max_attempts=max(1000,profile['constraints']['grid_count']*100),
                             population_size=1,operators=[])
    validate_profile(profile)
    return profile


def validate_study(study):
    validate_schema(study,SCHEMA)
    require(all(0<len(study[key].strip())<=2000 for key in ('title','question')),'titre/question requis, 2000 caractères maximum')
    experiment=study['experiment'];kind=study['experiment_kind']
    (validate_ablation if kind=='ablation' else validate_evolution)(experiment)
    require(experiment['bounds']['max_run_seconds']<=study['bounds']['max_run_seconds'],
            'la limite de l’expérience principale doit rester dans la limite du wrapper')
    comparison=experiment['base_profile']['evaluation'];confirmation=experiment['confirmation']['evaluation']
    forbid={comparison['seed'],confirmation['seed'],experiment['base_profile']['pool']['seed']}
    if kind=='ablation':
        require(study['random_controls']['same_pool']['seeds']==experiment['generation']['seeds'],
                'ablation : RANDOM même pool exige exactement les graines communes de l’expérience')
    else:
        begin=experiment['generation']['seed'];count=sum(p['proposals'] for p in experiment['generation']['schedule'])
        forbid.update(range(begin,begin+count))
    for role,config in study['random_controls'].items():
        seeds=config['seeds'];require(len(set(seeds))==len(seeds),'graines RANDOM répétées dans '+role)
        require(not (set(seeds)&forbid),'graines RANDOM réutilisent pool, MC ou opérateur')
        for seed in seeds:control_profile(study,role,seed)
    control_count=sum(len(v['seeds']) for v in study['random_controls'].values())
    capacity=main_capacity(study)+control_count
    require(capacity<=study['bounds']['max_total_constructions'] and capacity<=100,'constructions au-delà du budget déclaré')
    m=experiment['base_profile']['constraints']['grid_count']
    require(capacity*m*comparison['batch_size']<=2000000,'comparaison : batch au-delà du plafond de travail')
    require((experiment['confirmation']['max_finalists']+control_count)*m*confirmation['batch_size']<=2000000,
            'confirmation : batch au-delà du plafond de travail')
    return study


def load_study(path):
    return validate_study(load_json(Path(path).read_bytes()))


def schema_document():
    from portfolio_study_contract import schema_document as ablation_schema
    from evolution.contract import schema_document as evolution_schema
    schema=deepcopy(SCHEMA)
    schema['properties']['experiment']={'oneOf':[ablation_schema(),evolution_schema()]}
    schema.update({'$schema':'https://json-schema.org/draft/2020-12/schema','$id':VERSION})
    return schema
