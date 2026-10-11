"""Bounded mutation, geometric survival and crossover with fresh evaluations."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import fcntl
import json
from pathlib import Path
import random
import sys
import time
from uuid import uuid4

from portfolio_contract import validate_grids
from portfolio_evaluation import evaluate_many
from portfolio_import import content_hash, digest, require
from portfolio_pipeline import CRITERIA, ROOT, check_record, engine_sources, evaluate, make_record, pareto_ids, project, read, read_signed, signed, validate_graph, write
from portfolio_proof import proof_for
from portfolio_search import portfolio_score
from evolution.contract import CROSSOVER, MUTATIONS, SELECTION, VERSION, load_study, study_id, validate_study
from evolution.operators import construct_candidate, select_survivors

DEFAULT = ROOT/'configs/evolution/overlap-descendants-v1.json'


def event(**fields):
    print(json.dumps(fields,ensure_ascii=False),flush=True)


def source_signatures():
    """Do not broaden the already-signed portfolio_*.py source inventory."""
    engine=Path(__file__).resolve().parents[1]
    signatures=engine_sources()
    for path in sorted((engine/'evolution').glob('*.py')):
        signatures['evolution/'+path.name]=sha256(path.read_bytes()).hexdigest()
    schema=engine/'evolution/study.schema.json'
    signatures['evolution/study.schema.json']=sha256(schema.read_bytes()).hexdigest()
    signatures['evolve.py']=sha256((engine/'evolve.py').read_bytes()).hexdigest()
    return signatures


def frozen_parents(study):
    cached={};snapshots=[];profile=study['base_profile']
    generation=study['generation'];attempts=sum(s['proposals'] for s in generation['schedule'])
    future=set(range(generation['seed'],generation['seed']+attempts))
    for ref in study['parents']:
        path=ROOT/ref['source']
        if ref['source'] not in cached:
            require(sha256(path.read_bytes()).hexdigest()==ref['source_sha256'],'source parent modifiée : '+ref['source'])
            cached[ref['source']]=read(path)
        dataset=cached[ref['source']]
        rows=[p for p in dataset['profiles'] if p['id']==ref['id']]
        require(len(rows)==1,'parent absent ou ambigu : '+ref['id'])
        row=rows[0];check_record(row)
        require(row['content_sha256']==ref['content_sha256'],'contenu parent incompatible : '+ref['id'])
        require(not validate_grids(row['grids'],profile),'parent hors des contraintes physiques normalisées')
        require(row['pool_numbers']==profile['pool']['numbers'] and row['pool_stars']==profile['pool']['stars'],
                'parent : pools explicites incompatibles')
        seed=row['generation']['seed']
        require(seed not in {profile['evaluation']['seed'],study['confirmation']['evaluation']['seed']},'MC réutilise une graine parent')
        require(seed not in future,'graine opérateur réutilise une graine parent')
        snapshots.append({**ref,'grids':deepcopy(row['grids']),'generation_seed':seed,
                          'source_run_id':dataset.get('run_id'),'source_study_id':dataset.get('study',{}).get('id'),
                          'source_study_run_id':dataset.get('study_run',{}).get('id'),
                          'original_objectives':deepcopy(row['constraint_profile']['objectives'])})
    return snapshots


def initialize(study,run_dir):
    validate_study(study)
    write(run_dir/'study.json',study,immutable=True)
    inputs={'configuration':study,'engine_sources':source_signatures(),'parents':frozen_parents(study)}
    path=run_dir/'study-run.json'
    if path.exists():
        execution=read_signed(path)
        require(execution['inputs']==inputs,'étude, sources parent ou moteur modifiés : nouveau dossier requis')
    else:
        execution={'id':'study-run:'+str(uuid4()),'study_id':study_id(study),
                   'created_at':datetime.now(timezone.utc).isoformat(),'inputs':inputs}
        write(path,signed(execution),immutable=True)
    return execution


def _parent_records(study,execution,run_id):
    profile=study['base_profile'];records=[]
    for index,parent in enumerate(execution['inputs']['parents']):
        # A fresh content proof under the normalized physical contract; source
        # simulations and certificates are deliberately absent from the snapshot.
        proof=proof_for(parent['grids'],profile)
        if profile['constraints']['conditional_guarantee'] is not None:
            require(proof.get('fulfilled') is True,'garantie initiale obligatoire non prouvée')
        candidate={'grids':parent['grids'],'seed':parent['generation_seed'],'method':'source_parent',
                   'candidate_index':index,'score':None}
        record=make_record(profile,candidate,proof,run_id)
        record.update(id=f'{study["id"]}_parent{index+1:02d}',is_starting_parent=True,
                      study_id=execution['study_id'],study_run_id=execution['id'])
        record['generation'].update(operator='starting_portfolio',generation_index=0,
                                    source_record_id=parent['id'],source_content_sha256=parent['content_sha256'],
                                    source_dataset_sha256=parent['source_sha256'],
                                    parameters={'source':parent['source'],'source_run_id':parent['source_run_id'],
                                                'original_objectives':parent['original_objectives'],
                                                'objectives_normalized_to':profile['objectives']})
        record['lineage'].update(operator='starting_portfolio',parameters=record['generation']['parameters'])
        check_record(record);records.append(record)
    return records


def _check_generation(data,study,execution):
    require(data['signature']==digest(execution),'génération d’une autre exécution')
    require(len(data['proposals'])<=study['bounds']['max_proposals'],'checkpoint au-delà des propositions autorisées')
    require([p['index'] for p in data['proposals']]==list(range(len(data['proposals']))),'propositions checkpoint non consécutives')
    require(len({r['id'] for r in data['records']})==len(data['records']),'identifiants de candidats répétés')
    require(len({r['content_sha256'] for r in data['records']})==len(data['records']),'contenus checkpoint répétés')
    available={'portfolio:'+r['content_sha256'] for r in data['records']}
    for record in data['records']:
        check_record(record)
        require(set(record['lineage']['parent_ids'])<=available,'parent absent du checkpoint')
    require(set(data['population_ids'])<={r['id'] for r in data['records']},'survivant absent du checkpoint')


def generation(study,run_dir,execution,stop_after_proposals=None,stop_after_generations=None):
    for name,value in (('propositions',stop_after_proposals),('générations',stop_after_generations)):
        if value is not None:require(type(value) is int and value>=0,'arrêt '+name+' : entier positif ou zéro requis')
    complete=run_dir/'generation.json';checkpoint=run_dir/'generation-checkpoint.json'
    if complete.exists():
        data=read_signed(complete);_check_generation(data,study,execution);return data
    if checkpoint.exists():
        data=read_signed(checkpoint);_check_generation(data,study,execution)
    else:
        run_id='generation:'+digest(execution)
        records=_parent_records(study,execution,run_id)
        data={'schema':'aleaquant-generation-run-v1','signature':digest(execution),'run_id':run_id,
              'inputs':execution['inputs'],'created_at':execution['created_at'],'status':'generating',
              'study_execution_id':execution['id'],'records':records,'proposals':[],
              'generations':[],'population_ids':[r['id'] for r in records],
              'search_runs':[],'completed_profiles':[],'rejected_guarantees':[]}
        write(checkpoint,signed(data))
    started=time.monotonic();made=0;selected=0;offset=0
    profile=study['base_profile'];schedule=study['generation']['schedule'];seed_base=study['generation']['seed']
    def stop():
        return time.monotonic()-started>=study['bounds']['max_run_seconds']
    def interrupted():
        write(checkpoint,signed(data))
        event(phase='generation',status='interrupted',proposals=len(data['proposals']),
              completed_generations=len(data['generations']),accepted_children=sum(not r['is_starting_parent'] for r in data['records']))
        return data
    for gen_index,plan in enumerate(schedule,1):
        if len(data['generations'])>=gen_index:
            offset+=plan['proposals'];continue
        if (stop_after_generations is not None and selected>=stop_after_generations) or stop():return interrupted()
        population=[next(r for r in data['records'] if r['id']==rid) for rid in data['population_ids']]
        entrant_ids=[r['id'] for r in population]
        for local_index in range(plan['proposals']):
            index=offset+local_index
            if index<len(data['proposals']):continue
            if (stop_after_proposals is not None and made>=stop_after_proposals) or stop():return interrupted()
            rng=random.Random(seed_base+index)
            parents=rng.sample(population,2 if plan['phase']=='crossover' else 1)
            operator=CROSSOVER if plan['phase']=='crossover' else MUTATIONS[local_index%len(MUTATIONS)]
            proposal={'index':index,'generation_index':gen_index,'phase':plan['phase'],'operator':operator,
                      'seed':seed_base+index,'parent_ids':['portfolio:'+p['content_sha256'] for p in parents],
                      'parent_context_ids':[p['id'] for p in parents],'status':'rejected','reason':None}
            candidate=construct_candidate(operator,parents,profile,rng,index)
            if candidate is None:
                proposal['reason']='operator_proposal_rejected'
            else:
                grids=candidate['grids'];errors=validate_grids(grids,profile)
                content=content_hash(grids) if not errors else None
                if errors:
                    proposal.update(reason='invalid_constraints',violations=errors)
                elif content in {r['content_sha256'] for r in data['records']}:
                    proposal['reason']='duplicate_portfolio'
                else:
                    proof=proof_for(grids,profile)
                    if profile['constraints']['conditional_guarantee'] is not None and proof.get('fulfilled') is not True:
                        proposal['reason']='requested_guarantee_not_proved'
                        data['rejected_guarantees'].append(deepcopy(proposal))
                    else:
                        require(candidate['operator']==operator and candidate['parent_ids']==proposal['parent_ids'],'opérateur ou parents altérés')
                        birth={'grids':grids,'seed':proposal['seed'],'method':'evolution',
                               'candidate_index':index,'score':portfolio_score(grids,profile)}
                        record=make_record(profile,birth,proof,data['run_id'])
                        record.update(id=f'{study["id"]}_g{gen_index:02d}_p{local_index+1:02d}',is_starting_parent=False,
                                      study_id=execution['study_id'],study_run_id=execution['id'])
                        parameters={'operator':operator,'proposal_index':index,'metadata':candidate.get('metadata',{}),
                                    'parent_context_ids':proposal['parent_context_ids']}
                        record['generation'].update(operator=operator,generation_index=gen_index,
                                                    candidates_per_step=1,parameters=parameters)
                        record['lineage'].update(operator=operator,parent_ids=proposal['parent_ids'],parameters=parameters)
                        check_record(record);data['records'].append(record)
                        proposal.update(status='accepted',reason=None,record_id=record['id'],content_sha256=content)
            data['proposals'].append(proposal);made+=1
            write(checkpoint,signed(data));event(event='proposal',**proposal)
        accepted=[r for r in data['records'] if r['generation'].get('generation_index')==gen_index]
        entrants=population+accepted
        survivors=select_survivors(entrants,profile,study['generation']['population_size'])
        require(len(survivors)==study['generation']['population_size'],'sélection : population incomplète')
        require(len({r['id'] for r in survivors})==len(survivors) and {r['id'] for r in survivors}<={r['id'] for r in entrants},'sélection de survivants invalide')
        row={'generation_index':gen_index,'phase':plan['phase'],'proposal_count':plan['proposals'],
             'entrant_ids':[r['id'] for r in entrants],'parent_population_ids':entrant_ids,
             'accepted_ids':[r['id'] for r in accepted],
             'rejections':[p for p in data['proposals'] if p['generation_index']==gen_index and p['status']=='rejected'],
             'survivor_ids':[r['id'] for r in survivors],'selection_rule':SELECTION,'criteria':CRITERIA}
        data['generations'].append(row);data['population_ids']=row['survivor_ids'];selected+=1
        data['search_runs'].append({'profile_id':profile['id'],'generation_index':gen_index,'method':plan['phase'],
                                   'status':'complete','attempts':plan['proposals'],'accepted':len(accepted),
                                   'rejections':len(row['rejections']),'stopped_reason':None})
        write(checkpoint,signed(data));event(event='selection',**row)
        offset+=plan['proposals']
    data['status']='generated';data['evaluation_protocol']=profile['evaluation']
    require(len(data['proposals'])==sum(s['proposals'] for s in schedule),'plan de propositions incomplet')
    require(any(not r['is_starting_parent'] for r in data['records']),'recherche sans nouvel enfant : aucun résultat final')
    write(complete,signed(data),immutable=True);return data


def finalist_selection(study,records):
    children=[r for r in records if not r['is_starting_parent']]
    require(children,'aucun enfant à confirmer')
    survivors=select_survivors(children,study['base_profile'],min(len(children),study['confirmation']['max_finalists']))
    return {'rule':SELECTION,'selection_basis':'exact_geometry_only','criteria':CRITERIA,
            'finalist_ids':[r['id'] for r in survivors],'child_pareto_ids':pareto_ids(children)}


def confirm(study,run_dir,records,selection,stop_after=None):
    ids=set(selection['finalist_ids']);finalists=[r for r in records if r['id'] in ids]
    require(len(finalists)==len(ids),'finaliste absent')
    protocol={k:v for k,v in study['confirmation']['evaluation'].items() if k!='max_certificate_cases'}
    directory=run_dir/'evaluations'/('confirmation-'+digest(protocol)[:16])
    result=evaluate_many(finalists,protocol,directory,progress=lambda e:event(phase='confirmation',**e),stop_after_batches=stop_after)
    if result['status']=='complete':write(directory/'confirmation.json',signed(result),immutable=True)
    return result


def projection(study,run_dir,execution):
    generation_data=read_signed(run_dir/'generation.json');_check_generation(generation_data,study,execution)
    dataset=project(run_dir);records=dataset['profiles']
    selection=finalist_selection(study,records)
    require(read_signed(run_dir/'finalist-selection.json')==selection,'sélection finale altérée')
    protocol={k:v for k,v in study['confirmation']['evaluation'].items() if k!='max_certificate_cases'}
    path=run_dir/'evaluations'/('confirmation-'+digest(protocol)[:16])/'confirmation.json'
    require(path.exists(),'confirmation indépendante incomplète : aucun export final')
    confirmation=read_signed(path)
    require(confirmation['status']=='complete' and confirmation['protocol']==protocol,'confirmation invalide')
    comparison=read_signed(run_dir/read(run_dir/'latest-evaluation.json')['path'])
    require(comparison['protocol']['seed']!=protocol['seed'] and comparison['draw_stream_sha256']!=confirmation['draw_stream_sha256'],
            'échantillon de confirmation non indépendant')
    require(set(confirmation['results'])=={r['content_sha256'] for r in records if r['id'] in selection['finalist_ids']},'contenus de confirmation incompatibles')
    nodes=dataset['graph']['nodes'];edges=dataset['graph']['edges'];sid=execution['study_id'];rid=execution['id']
    survivor_ids=set(generation_data['population_ids']);finalist_ids=set(selection['finalist_ids'])
    for record in records:
        record['evaluation']['role']='comparison'
        record.update(is_survivor=record['id'] in survivor_ids,is_finalist=record['id'] in finalist_ids)
        gen_id=record['generation_run']['id'];portfolio_id='portfolio:'+record['content_sha256']
        edges.append({'type':'generated_in_study','source':gen_id,'target':rid})
        for parent in record['lineage']['parent_ids']:
            edges.append({'type':'derived_from','source':gen_id,'target':parent})
        if record['is_starting_parent']:
            ref=next(p for p in execution['inputs']['parents'] if p['content_sha256']==record['content_sha256'])
            ref_id='parent-reference:'+digest({k:ref[k] for k in ('id','source','source_sha256','content_sha256')})
            nodes.append({'id':ref_id,'type':'reference','data':{k:v for k,v in ref.items() if k!='grids'}})
            edges.append({'type':'uses_source_parent','source':gen_id,'target':ref_id})
        if record['is_finalist']:
            sim=confirmation['results'][record['content_sha256']]
            evaluation={'id':'evaluation:'+sim['evaluation_sha256'],'method':'monte_carlo','role':'confirmation',
                        'replayed':True,'content_sha256':record['content_sha256'],'draws':sim['draws'],'seed':sim['seed'],
                        'common_draws':True,'independent_of_generation':True,'independent_of_comparison':True,
                        'engine_version':confirmation['engine_version'],'environment':confirmation['environment'],
                        'source_sha256':confirmation['source_sha256'],'draw_stream_sha256':confirmation['draw_stream_sha256'],'protocol':protocol}
            record['confirmation']={'evaluation':evaluation,'simulation':sim}
            nodes.append({'id':evaluation['id'],'type':'evaluation_run','content_sha256':record['content_sha256'],'protocol':evaluation})
            edges.append({'type':'confirmed_by','source':portfolio_id,'target':evaluation['id']})
    nodes.extend([{'id':sid,'type':'study','data':study},{'id':rid,'type':'study_run','data':execution}])
    edges.append({'type':'executes_study','source':rid,'target':sid})
    for row in generation_data['generations']:
        select_id='selection:'+digest({'execution':rid,'selection':row})
        nodes.append({'id':select_id,'type':'selection_run','data':row})
        edges.append({'type':'selected_in_study','source':select_id,'target':rid})
        for record_id in row['entrant_ids']:
            record=next(r for r in records if r['id']==record_id)
            edges.append({'type':'considers','source':select_id,'target':'portfolio:'+record['content_sha256']})
    graph={'nodes':list({n['id']:n for n in nodes}.values()),'edges':list({digest(e):e for e in edges}.values())}
    validate_graph(graph)
    evolution={'population_size':study['generation']['population_size'],'schedule':study['generation']['schedule'],
               'generation_seed':study['generation']['seed'],'selection_rule':SELECTION,'criteria':CRITERIA,
               'completed_generations':len(generation_data['generations']),'proposal_count':len(generation_data['proposals']),
               'accepted_children':sum(not r['is_starting_parent'] for r in records),
               'rejected_proposals':sum(p['status']=='rejected' for p in generation_data['proposals']),
               'initial_parent_ids':[r['id'] for r in records if r['is_starting_parent']],
               'final_survivor_ids':generation_data['population_ids'],'generations':generation_data['generations'],
               'proposals':generation_data['proposals']}
    display={'id':sid,'run_id':rid,'config_id':study['id'],'version':study['version'],'title':study['title'],'question':study['question'],
             'metrics':study['metrics'],'fixed_parameters':{k:study['base_profile'][k] for k in ('game','pool','constraints','objectives')},
             'starting_points':study['parents'],'bounds':study['bounds'],'comparison':study['base_profile']['evaluation'],
             'confirmation':study['confirmation'],'generation':study['generation']}
    dataset.update(origin='local_evolution',engine_version=VERSION,study=display,study_definition=study,
                   study_run=execution,evolution=evolution,analysis=selection,graph=graph,
                   source={'date':execution['created_at'][:10],'type':'local_evolution','run_id':dataset['run_id'],
                           'study_id':sid,'study_run_id':rid},confirmation_protocol=protocol)
    dataset['limitations']=[
        'Démo bornée de mutations, sélection générationnelle et croisements ; aucune optimalité démontrée.',
        'Les cinq portefeuilles de départ conservent leurs contenus et identifiants sources ; leurs objectifs sont normalisés au profil commun de cette étude.',
        'Parents et enfants sont évalués ensemble sur de nouveaux tirages ; aucune performance MC importée ne sélectionne les parents, survivants ou finalistes.',
        'Chaque enfant repasse les contraintes et une preuve liée à son contenu ; aucune garantie parentale ne se transmet.',
        'Sélection sur quatre critères géométriques seulement ; la somme des intersections au carré est mesurée séparément.',
        'Confirmation indépendante sur de nouveaux tirages, limitée aux enfants finalistes géométriques.',
        'IC95 Wilson ponctuels ; aucune preuve de supériorité économique, remboursement ou prédiction.'
    ]
    return dataset


def publish(study,run_dir,execution,output):
    dataset=projection(study,run_dir,execution)
    archive=ROOT/'dist/data/portfolio_evolution_runs'/dataset['run_id'].split(':')[1]/'catalogue.json'
    write(archive,dataset,immutable=True);write(output,dataset)
    for record in dataset['profiles']:
        write(run_dir/'exports'/(record['id']+'.json'),record,immutable=True)
        csv='numbers;stars\n'+''.join(' '.join(map(str,g[0]))+';'+' '.join(map(str,g[1]))+'\n' for g in record['grids'])
        path=run_dir/'exports'/(record['id']+'.csv');path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():require(path.read_text()==csv,'export CSV existant différent')
        else:path.write_text(csv)
    index_path=ROOT/'dist/data/portfolio_evolutions.json';lock_path=ROOT/'runs/evolution/.index.lock';lock_path.parent.mkdir(parents=True,exist_ok=True)
    row={'id':execution['id'],'study_id':execution['study_id'],'config_id':study['id'],'title':study['title'],
         'url':'/data/portfolio_evolution_runs/'+dataset['run_id'].split(':')[1]+'/catalogue.json',
         'run_id':dataset['run_id'],'created_at':execution['created_at']}
    with lock_path.open('a+') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
        index=read(index_path) if index_path.exists() else {'schema':VERSION,'studies':[]}
        require(index.get('schema')==VERSION and isinstance(index.get('studies'),list),'index évolution invalide')
        previous=next((r for r in index['studies'] if r['id']==row['id']),None)
        if previous:require(previous==row,'index évolution incompatible')
        else:index['studies'].append(row)
        write(index_path,index)
    write(run_dir/'study-result.json',signed({'run_id':dataset['run_id'],'archive':str(archive),'evolution':dataset['evolution'],'analysis':dataset['analysis']}),immutable=True)
    event(phase='export',status='complete',output=str(output),archive=str(archive),run_id=dataset['run_id']);return dataset


def run(study,run_dir,stop_after_proposals=None,stop_after_generations=None,stop_after_comparison_batches=None,stop_after_confirmation_batches=None,output=None):
    run_dir=Path(run_dir);run_dir.mkdir(parents=True,exist_ok=True);started=time.monotonic()
    def timed_out():return time.monotonic()-started>=study['bounds']['max_run_seconds']
    with (run_dir/'.evolution.lock').open('a+') as lock:
        try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:raise ValueError('évolution déjà active dans ce dossier') from exc
        try:
            execution=initialize(study,run_dir)
            generated=generation(study,run_dir,execution,stop_after_proposals,stop_after_generations)
            if generated['status']!='generated':return {'status':generated['status'],'completed_proposals':len(generated['proposals'])}
            if timed_out():return {'status':'run_time_interrupted','phase':'generation'}
            result=evaluate(run_dir,stop_after_batches=stop_after_comparison_batches)
            if result['status']!='complete':return {'status':'comparison_interrupted','completed_draws':result['completed_draws']}
            if timed_out():return {'status':'run_time_interrupted','phase':'comparison'}
            records=project(run_dir)['profiles'];selection=finalist_selection(study,records)
            write(run_dir/'finalist-selection.json',signed(selection),immutable=True)
            event(phase='finalist_selection',**selection)
            result=confirm(study,run_dir,records,selection,stop_after_confirmation_batches)
            if result['status']!='complete':return {'status':'confirmation_interrupted','completed_draws':result['completed_draws']}
            if timed_out():return {'status':'run_time_interrupted','phase':'confirmation'}
            dataset=publish(study,run_dir,execution,output or ROOT/'dist/data/portfolio_evolution.json')
            return {'status':'complete','run_id':dataset['run_id']}
        finally:fcntl.flock(lock.fileno(),fcntl.LOCK_UN)


def status(run_dir):
    path=run_dir/'generation.json'
    if not path.exists():path=run_dir/'generation-checkpoint.json'
    data=read_signed(path);evaluations=[]
    for path in sorted(run_dir.glob('evaluations/*/checkpoint.json')):
        envelope=read(path);payload=envelope['payload']
        require(digest(payload)==envelope['checksum_sha256'],'checkpoint MC altéré')
        evaluations.append({'role':'confirmation' if path.parent.name.startswith('confirmation-') else 'comparison',
                            'status':payload['status'],'completed_draws':payload['completed_draws'],
                            'total_draws':payload['protocol']['draws'],'seed':payload['protocol']['seed']})
    result={'status':data['status'],'completed_proposals':len(data['proposals']),
            'completed_generations':len(data['generations']),
            'accepted_children':sum(not r['is_starting_parent'] for r in data['records']),
            'rejected_proposals':sum(p['status']=='rejected' for p in data['proposals']),
            'survivor_ids':data['population_ids'],'evaluations':evaluations}
    event(**result);return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['validate','run','status','export'])
    parser.add_argument('--study-config',type=Path,default=DEFAULT)
    parser.add_argument('--run-dir',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'dist/data/portfolio_evolution.json')
    parser.add_argument('--stop-after-proposals',type=int)
    parser.add_argument('--stop-after-generations',type=int)
    parser.add_argument('--stop-after-comparison-batches',type=int)
    parser.add_argument('--stop-after-confirmation-batches',type=int)
    args=parser.parse_args(argv)
    try:
        frozen=args.run_dir/'study.json' if args.run_dir else None
        study=load_study(frozen if args.command in ('status','export') and frozen and frozen.exists() else args.study_config)
        if args.command=='validate':
            parents=frozen_parents(study)
            event(status='valid',study_id=study_id(study),parents=len(parents),generations=len(study['generation']['schedule']),
                  proposals=sum(s['proposals'] for s in study['generation']['schedule']));return 0
        if args.run_dir is None:
            require(args.command=='run','status/export : --run-dir requis')
            stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            args.run_dir=ROOT/'runs/evolution'/study['id']/(stamp+'-'+str(uuid4())[:8])
        event(run_dir=str(args.run_dir))
        if args.command=='status':status(args.run_dir);return 0
        if args.command=='export':
            execution=initialize(study,args.run_dir);publish(study,args.run_dir,execution,args.output);return 0
        result=run(study,args.run_dir,args.stop_after_proposals,args.stop_after_generations,
                   args.stop_after_comparison_batches,args.stop_after_confirmation_batches,args.output)
        event(**result);return 0 if result['status']=='complete' else 2
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print('Évolution refusée : '+str(exc),file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
