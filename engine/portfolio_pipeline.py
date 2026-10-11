"""CLI locale : validate, generate, evaluate, compare, export, run.

Premier jalon 1.0 : candidats géométriques, RANDOM, preuves bornées et MC
final indépendant. Les archives de runs sont append-only, l'index est une
projection remplaçable. Aucun historique, achat ou déploiement.
"""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
import os
from pathlib import Path
import sys

from portfolio_contract import VERSION, load_profiles, resolve_pool, validate_grids
from portfolio_evaluation import evaluate_many, exact_analytics
from portfolio_geometry import portfolio_geometry
from portfolio_import import content_hash, digest, load_json, require
from portfolio_metrics import REGISTRY, metric_values
from portfolio_proof import proof_for
from portfolio_search import generate_candidates

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT/'configs/portfolios/milestone-v1.json'
CRITERIA = [{'metric_id':key,'direction':direction,'label':label} for key,direction,label in (
    ('portfolio.distinct_pairs@v1','max','Paires couvertes'),
    ('portfolio.distinct_triples@v1','max','Triplets couverts'),
    ('portfolio.number_frequency_sd@v1','min','Dispersion des occurrences'),
    ('portfolio.max_number_overlap@v1','min','Intersection maximale'))]


def read(path):
    return load_json(Path(path).read_bytes())


def write(path, data, immutable=False):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    payload=json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n'
    if path.exists() and immutable:
        require(read(path)==data,f'archive immuable déjà présente avec un autre contenu : {path}')
        return
    temp=path.with_name(path.name+f'.{os.getpid()}.tmp')
    try:
        with temp.open('w') as stream:
            stream.write(payload);stream.flush();os.fsync(stream.fileno())
        if immutable:
            try: os.link(temp,path)
            except FileExistsError: require(read(path)==data,f'collision d’archive immuable : {path}')
        else: os.replace(temp,path)
    finally:
        temp.unlink(missing_ok=True)


def signed(data):
    return {'payload':data,'sha256':digest(data)}


def read_signed(path):
    envelope=read(path)
    require(set(envelope)=={'payload','sha256'} and digest(envelope['payload'])==envelope['sha256'],f'empreinte de sauvegarde invalide : {path}')
    return envelope['payload']


def engine_sources():
    return {p.name:sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob('portfolio_*.py'))}


def pool_id(profile):
    n,s=resolve_pool(profile)
    return digest({'numbers':n,'stars':s})


def check_record(record):
    require(content_hash(record['grids'])==record['content_sha256'],'contenu portefeuille altéré')
    require(not validate_grids(record['grids'],record['constraint_profile']),'contraintes de portefeuille altérées')
    cert=record['certificate']
    require(cert['content_sha256']==record['content_sha256'],'preuve reliée à un autre contenu')
    if record['constraint_profile']['constraints']['conditional_guarantee'] is not None:
        require(cert.get('fulfilled') is True,'garantie obligatoire non prouvée')


def generate(config, run_dir, include_references=False):
    profiles=load_profiles(config)
    run_dir=Path(run_dir)
    inputs={'configuration':read(config),'engine_sources':engine_sources(),
            'references_sha256':sha256((ROOT/'dist/data/portfolio_pipeline.json').read_bytes()).hexdigest() if include_references else None}
    signature=digest(inputs)
    completed_path=run_dir/'generation.json';progress_path=run_dir/'generation-checkpoint.json'
    if completed_path.exists():
        data=read_signed(completed_path)
        require(data['signature']==signature,'ce dossier contient une génération différente ; choisir un nouveau dossier de run')
        for record in data['records']: check_record(record)
        return data
    if progress_path.exists():
        data=read_signed(progress_path)
        require(data['signature']==signature,'checkpoint génération incompatible')
        for record in data['records']:check_record(record)
    else:
        data={'schema':'aleaquant-generation-run-v1','run_id':'generation:'+signature,
              'signature':signature,'inputs':inputs,'records':[],'search_runs':[],
              'completed_profiles':[],'created_at':datetime.now(timezone.utc).isoformat(),
              'status':'generating','rejected_guarantees':[]}
    for profile in profiles:
        if profile['id'] in data['completed_profiles']:continue
        result=generate_candidates(profile)
        accepted=0
        for candidate in result['candidates']:
            certificate=proof_for(candidate['grids'],profile)
            if profile['constraints']['conditional_guarantee'] and certificate.get('fulfilled') is not True:
                data['rejected_guarantees'].append({'profile_id':profile['id'],'content_sha256':content_hash(candidate['grids']),'reason':'requested_guarantee_not_proved'})
                continue
            data['records'].append(make_record(profile,candidate,certificate,data['run_id']))
            accepted+=1
        data['search_runs'].append({'profile_id':profile['id'],'status':result['status'] if accepted else 'search_exhausted',
                                   'accepted':accepted,**{k:result[k] for k in ('attempts','rejections','stopped_reason')}})
        data['completed_profiles'].append(profile['id'])
        write(progress_path,signed(data))
        print(f"Génération {profile['id']} : {accepted} candidat(s), {result['attempts']} propositions, {result['status']}",flush=True)
    if include_references and 'ZIP_REFERENCES' not in data['completed_profiles']:
        archive=read(ROOT/'dist/data/portfolio_pipeline.json')
        archived_config=read(ROOT/'prototypes/portfolio-pipeline/source-20261009/profiles.json')
        for old in archive['profiles']:
            profile=deepcopy(next(p for p in profiles if p['id']==old['id']+'_v1'))
            profile['id']='reference_'+old['id']
            candidate={'grids':old['grids'],'seed':old['generation']['seed'],'method':'reference_import','candidate_index':0,'score':None}
            record=make_record(profile,candidate,proof_for(old['grids'],profile),data['run_id'])
            record['profile_object']={'schema_version':'0.1','pool_seed':archived_config['pool_seed'],
                                      'profile':next(p for p in archived_config['profiles'] if p['id']==old['id'])}
            record['config_sha256']=digest(record['profile_object'])
            record['generation']['source_archive_sha256']=archive['source']['archive_sha256']
            record['generation']['source_engine_sha256']=old['evaluation']['source_engine_sha256']
            record['generation']['pool_seed']=old['generation']['pool_seed']
            record['generation']['candidates_per_step']=old['generation']['candidates_per_step']
            record['generation']['parameters']=record['profile_object']
            record['lineage']['parameters']=record['profile_object']
            record['origin']='reference_import'
            data['records'].append(record)
        data['completed_profiles'].append('ZIP_REFERENCES')
        write(progress_path,signed(data))
    seeds={r['generation']['seed'] for r in data['records']}
    require(profiles[0]['evaluation']['seed'] not in seeds,'évaluation : graine de génération réutilisée')
    data['status']='generated';data['evaluation_protocol']=profiles[0]['evaluation']
    write(completed_path,signed(data),immutable=True)
    return data


def make_record(profile,candidate,certificate,run_id):
    grids=sorted([[sorted(g[0]),sorted(g[1])] for g in candidate['grids']])
    geometry=portfolio_geometry(grids,50);nums,stars=resolve_pool(profile)
    idx=candidate['candidate_index']+1
    generation={'method':candidate['method'],'seed':candidate['seed'],'pool_seed':profile['pool']['seed'],
                'candidates_per_step':profile['search']['candidates_per_step'],
                'candidate_index':candidate['candidate_index'],'score':candidate['score'],
                'operator':'reference_import' if candidate['method']=='reference_import' else 'initial_generation',
                'parameters':profile['search'],'run_id':run_id}
    return {'id':profile['id']+f'_c{idx:02d}','family':profile['family'],'display_family':profile['family'],
            'profile_version':profile['version'],'profile_object':profile,'constraint_profile':profile,
            'config_sha256':digest(profile),'content_sha256':content_hash(grids),
            'pool_id':pool_id(profile),'pool_numbers':nums,'pool_stars':stars,'grids':grids,
            'game_id':'euromillions','rule_id':profile['game']['rule_id'],'format_id':'5of50+2of12',
            'grid_count':len(grids),'budget_eur':len(grids)*2.5,'budget_actual_eur':len(grids)*2.5,
            'budget_max_eur':profile['constraints']['budget_max_eur'],'unit_price_eur':2.5,
            'geometry':geometry,'metric_values':metric_values(grids,geometry),
            'certificate':certificate,'proof':certificate,'generation':generation,
            'generation_run':{'id':'generation-candidate:'+digest({'run':run_id,'profile':digest(profile),'seed':candidate['seed'],'content':content_hash(grids)}),
                              'parent_run_id':run_id,'method':candidate['method'],'seed':candidate['seed']},
            'lineage':{'parent_ids':[],'operator':generation['operator'],'parameters':profile['search'],'seed':candidate['seed']},
            'origin':'local_pipeline','state':'feasible','state_scope':'validated_constraints'}


def evaluate(run_dir, seed=None, draws=None, stop_after_batches=None):
    data=read_signed(Path(run_dir)/'generation.json')
    for record in data['records']:check_record(record)
    protocol={k:v for k,v in data['evaluation_protocol'].items() if k!='max_certificate_cases'}
    if seed is not None:protocol['seed']=seed
    if draws is not None:protocol['draws']=draws
    forbidden={r['generation']['seed'] for r in data['records']}|{r['generation']['pool_seed'] for r in data['records']}
    require(protocol['seed'] not in forbidden,'graine MC doit être distincte de génération et pool')
    evaluation_dir=Path(run_dir)/'evaluations'/digest(protocol)[:16]
    unique_records=list({r['content_sha256']:r for r in data['records']}.values())
    result=evaluate_many(unique_records,protocol,evaluation_dir,
                         progress=lambda event:print(json.dumps(event,ensure_ascii=False),flush=True),
                         stop_after_batches=stop_after_batches)
    if result['status']=='complete':
        evaluation={'generation_signature':data['signature'],**result}
        write(evaluation_dir/'evaluation.json',signed(evaluation),immutable=True)
        write(Path(run_dir)/'latest-evaluation.json',{'path':str(evaluation_dir.relative_to(run_dir))+'/evaluation.json'})
    return result


def pareto_ids(records):
    def dominates(a,b):
        av=[a['metric_values'][c['metric_id']] for c in CRITERIA]
        bv=[b['metric_values'][c['metric_id']] for c in CRITERIA]
        if None in av or None in bv:return False
        better=[x>=y if c['direction']=='max' else x<=y for x,y,c in zip(av,bv,CRITERIA)]
        strict=[x>y if c['direction']=='max' else x<y for x,y,c in zip(av,bv,CRITERIA)]
        return all(better) and any(strict)
    return [b['id'] for b in records if not any(dominates(a,b) for a in records if a['content_sha256']!=b['content_sha256'])]


def comparisons(records):
    out={}
    for protocol in ('same_pool','different_pools'):
        groups={}
        for p in records:
            key=(p['budget_actual_eur'],p['grid_count'],p['pool_id'] if protocol=='same_pool' else None)
            groups.setdefault(key,[]).append(p)
        out[protocol]=[{'id':protocol+':'+digest(key),'pool_id':key[2],'budget_eur':key[0],'grid_count':key[1],
                        'profile_ids':[p['id'] for p in group],
                        'random_reference_available':any(p['family']=='RANDOM' for p in group),
                        'pareto_ids':pareto_ids(group),'criteria':CRITERIA,
                        'distinct_content_count':len({p['content_sha256'] for p in group})} for key,group in groups.items()]
    return out


def validate_graph(graph):
    nodes={n['id']:n for n in graph['nodes']}
    require(len(nodes)==len(graph['nodes']),'graphe : identifiants répétés')
    outgoing={key:[] for key in nodes}
    for edge in graph['edges']:
        require(edge['source'] in nodes and edge['target'] in nodes,'graphe : lien sans nœud')
        outgoing[edge['source']].append(edge['target'])
    active=set();visited=set()
    def visit(node):
        require(node not in active,'graphe : cycle de filiation')
        if node in visited:return
        active.add(node)
        for child in outgoing[node]:visit(child)
        active.remove(node);visited.add(node)
    for node in nodes:visit(node)


def project(run_dir):
    run_dir=Path(run_dir);generation=read_signed(run_dir/'generation.json')
    pointer=read(run_dir/'latest-evaluation.json');relative=Path(pointer['path'])
    require(not relative.is_absolute() and '..' not in relative.parts,'chemin évaluation hors du run')
    evaluation=read_signed(run_dir/relative)
    require(evaluation['generation_signature']==generation['signature'] and evaluation['status']=='complete','évaluation incomplète ou autre génération')
    records=deepcopy(generation['records']);nodes={};edges=[]
    for p in records:
        check_record(p)
        content=p['content_sha256'];sim=evaluation['results'][content]
        p['simulation']=sim;p['exact']=exact_analytics(p['grids'])
        p['metric_values']=metric_values(p['grids'],portfolio_geometry(p['grids'],50),sim)
        p['metric_values']['portfolio.jackpot_probability@v1']=p['exact']['jackpot_probability']
        protocol=evaluation['protocol']
        evaluation_id='evaluation:'+sim['evaluation_sha256']
        p['evaluation']={'id':evaluation_id,'method':'monte_carlo','replayed':True,'reproduces_archive':False,
                         'content_sha256':content,'draws':sim['draws'],'seed':sim['seed'],'common_draws':True,
                         'engine_version':evaluation['engine_version'],'environment':evaluation['environment'],
                         'source_sha256':evaluation['source_sha256'],'draw_stream_sha256':evaluation['draw_stream_sha256'],
                         'protocol':protocol,'source_generation_signature':generation['signature']}
        p['state']='certified' if p['certificate']['method']=='exhaustive_enumeration' else 'evaluated'
        p['state_scope']='conditional_guarantee' if p['state']=='certified' else 'local_monte_carlo'
        portfolio_id='portfolio:'+content;profile_id='profile:'+digest(p['profile_object']);gen_id=p['generation_run']['id']
        p['lineage'].update(profile_node_id=profile_id,portfolio_node_id=portfolio_id)
        for node in ({'id':profile_id,'type':'profile','data':p['profile_object']},
                     {'id':gen_id,'type':'generation_run','data':p['generation'],'parent_ids':p['lineage']['parent_ids']},
                     {'id':portfolio_id,'type':'portfolio','content_sha256':content},
                     {'id':evaluation_id,'type':'evaluation_run','content_sha256':content,'protocol':p['evaluation']}):nodes[node['id']]=node
        edges.extend([{'type':'generated_from','source':gen_id,'target':profile_id},
                      {'type':'generated_by','source':portfolio_id,'target':gen_id},
                      {'type':'evaluated_by','source':portfolio_id,'target':evaluation_id}])
        if p['certificate']['method']=='exhaustive_enumeration':
            proof_id=p['certificate']['id'];nodes[proof_id]={'id':proof_id,'type':'guarantee_proof','data':p['certificate']}
            edges.append({'type':'proves','source':proof_id,'target':portfolio_id})
    graph={'nodes':list(nodes.values()),'edges':list({digest(e):e for e in edges}.values())};validate_graph(graph)
    comp=comparisons(records)
    current=read(ROOT/'dist/metrics.json')
    run_id='run:'+digest({'generation':generation['signature'],'evaluation':evaluation['signature']})
    return {'schema':'aleaquant-portfolio-pipeline-v1','contract_version':'1.0','origin':'local_pipeline','engine_version':VERSION,
            'run_id':run_id,'source':{'date':generation['created_at'][:10],'type':'local_pipeline','run_id':run_id},
            'verification_environment':evaluation['environment'],'configuration_sha256':digest(generation['inputs']['configuration']),
            'engine_sources':generation['inputs']['engine_sources'],'profiles':records,
            'cohorts':comp['different_pools'],'comparisons':comp,'graph':graph,'metric_registry':REGISTRY,
            'metric_source':{'path':'metrics.json','sha256':sha256((ROOT/'dist/metrics.json').read_bytes()).hexdigest(),
                             'definitions_count':len(current),'grid_definitions_count':sum(m.get('group')!='portfolio' for m in current),
                             'portfolio_evaluator':'engine/portfolio_geometry.py','portfolio_definitions':'docs/PORTFOLIO-PIPELINE.md'},
            'search_runs':generation['search_runs'],'states':['draft','invalid','feasible','evaluated','certified','search_exhausted','proven_infeasible'],
            'limitations':[f'MC exploratoire indépendant de la sélection géométrique, {evaluation["completed_draws"]} tirages ; IC95 ponctuels, sans correction de multiplicité.',
                           'Compromis non dominés sur quatre métriques géométriques seulement ; aucune optimalité ni classement économique.',
                           'Une preuve conditionnelle est liée au contenu et au pool ; aucune garantie ne se transmet à un descendant.',
                           'Les alias et références d’un même contenu partagent leur EvaluationRun, sans compter comme répétitions indépendantes.',
                           'Unicité porte sur les contenus concrets du graphe ; la liste conserve les contextes de profils et de génération.',
                           'Mutation, sélection évolutionnaire et croisement sont refusés en version1.0 et restent l’étape suivante.'],
            'exclusions':['montants de gain','remboursement de mise','Étoile+','My Million','historique et prédiction']}


def publish(run_dir,output):
    dataset=project(run_dir)
    archive=ROOT/'dist/data/portfolio_runs'/dataset['run_id'].split(':')[1]/'catalogue.json'
    write(archive,dataset,immutable=True)
    # An index is a projection, while immutable run and evaluation archives remain.
    write(output,dataset)
    exports=Path(run_dir)/'exports'
    for p in dataset['profiles']:
        write(exports/(p['id']+'.json'),p,immutable=True)
        csv='numbers;stars\n'+''.join(' '.join(map(str,g[0]))+';'+' '.join(map(str,g[1]))+'\n' for g in p['grids'])
        file=exports/(p['id']+'.csv')
        if file.exists():require(file.read_text()==csv,'export de grilles existant différent')
        else:file.parent.mkdir(parents=True,exist_ok=True);file.write_text(csv)
    return dataset


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['validate','generate','evaluate','compare','export','run'])
    parser.add_argument('--config',type=Path,default=DEFAULT_CONFIG)
    parser.add_argument('--run-dir',type=Path,default=ROOT/'runs/portfolios/milestone-20261009')
    parser.add_argument('--include-references',action='store_true')
    parser.add_argument('--seed',type=int);parser.add_argument('--draws',type=int)
    parser.add_argument('--stop-after-batches',type=int,help='arrêt court et reprenable du MC')
    parser.add_argument('--output',type=Path,default=ROOT/'dist/data/portfolio_search.json')
    args=parser.parse_args(argv)
    try:
        if args.command=='validate':
            ps=load_profiles(args.config)
            print(json.dumps({'status':'valid','profiles':len(ps),'budgets':sorted({p['constraints']['budget_max_eur'] for p in ps}),'evaluation_draws':ps[0]['evaluation']['draws']},ensure_ascii=False));return 0
        if args.command in ('generate','run'):
            data=generate(args.config,args.run_dir,args.include_references)
            print(f"Génération sauvegardée : {len(data['records'])} contextes, {len({p['content_sha256'] for p in data['records']})} contenus distincts",flush=True)
        if args.command in ('evaluate','run'):
            result=evaluate(args.run_dir,args.seed,args.draws,args.stop_after_batches)
            print(f"MC {result['status']} : {result['completed_draws']} tirages",flush=True)
            if result['status']!='complete':return 2
        if args.command=='compare':
            dataset=project(args.run_dir);write(args.run_dir/'comparison.json',dataset['comparisons'])
            print(json.dumps(dataset['comparisons'],ensure_ascii=False));return 0
        if args.command in ('export','run'):
            data=publish(args.run_dir,args.output)
            print(f"Atlas : {args.output} ; {len(data['profiles'])} fiches ; run {data['run_id']}")
        return 0
    except (ValueError,KeyError,TypeError,OSError) as error:
        print(f'Pipeline refusé : {error}',file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
