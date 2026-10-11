"""Generate an experiment and RANDOM controls, then evaluate them together."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import fcntl
import json
from pathlib import Path
import sys
import time
from uuid import uuid4

import portfolio_study as ablation
from evolution import pipeline as evolution
from portfolio_contract import validate_grids
from portfolio_evaluation import evaluate_many
from portfolio_import import content_hash, digest, require
from portfolio_pipeline import ROOT, check_record, evaluate, make_record, project, read, read_signed, signed, validate_graph, write
from portfolio_proof import proof_for
from portfolio_search import generate_candidates
from portfolio_study_analysis import analyze_study
from controlled.contract import VERSION, control_profile, load_study, main_capacity, study_id, validate_study
from controlled.comparison import benchmark, qualify_controls

DEFAULT=ROOT/'configs/controlled/overlap-random-v1.json'


def event(**fields):
    print(json.dumps(fields,ensure_ascii=False),flush=True)


def source_signatures():
    sources=evolution.source_signatures()
    engine=Path(__file__).resolve().parents[1]
    for path in sorted((engine/'controlled').iterdir()):
        if path.suffix in ('.py','.json'):sources['controlled/'+path.name]=sha256(path.read_bytes()).hexdigest()
    sources['study.py']=sha256((engine/'study.py').read_bytes()).hexdigest()
    return sources


def main_module(study):
    return ablation if study['experiment_kind']=='ablation' else evolution


def check_parent_control_seeds(study,parents):
    parent_seeds={p['generation_seed'] for p in parents}
    require(not (parent_seeds&{s for c in study['random_controls'].values() for s in c['seeds']}),
            'RANDOM réutilise une graine parent')


def initialize(study,run_dir):
    validate_study(study);write(run_dir/'study.json',study,immutable=True)
    main_dir=run_dir/'main';main_dir.mkdir(parents=True,exist_ok=True)
    main_execution=main_module(study).initialize(study['experiment'],main_dir)
    if study['experiment_kind']=='evolution':
        check_parent_control_seeds(study,main_execution['inputs']['parents'])
    inputs={'configuration':study,'engine_sources':source_signatures(),'main_execution':main_execution}
    path=run_dir/'study-run.json'
    if path.exists():
        execution=read_signed(path);require(execution['inputs']==inputs,'configuration, sources ou moteur modifiés : nouveau dossier requis')
    else:
        execution={'id':'study-run:'+str(uuid4()),'study_id':study_id(study),
                   'created_at':datetime.now(timezone.utc).isoformat(),'inputs':inputs}
        write(path,signed(execution),immutable=True)
    return execution


def split_records(records):
    return ([r for r in records if 'reference_benchmark' not in r],
            [r for r in records if 'reference_benchmark' in r])


def _check_generation(data,study,execution):
    require(data['signature']==digest(execution),'génération d’une autre exécution')
    main_records,controls=split_records(data['records'])
    require(len(data['records'])<=study['bounds']['max_total_constructions'],'checkpoint au-delà des constructions autorisées')
    require(len({r['id'] for r in data['records']})==len(data['records']),'identifiants répétés')
    for record in data['records']:check_record(record)
    expected={role+'_'+str(seed):(role,seed) for role,c in study['random_controls'].items() for seed in c['seeds']}
    require(len(data['completed_controls'])==len(controls) and len(set(data['completed_controls']))==len(controls),'checkpoint RANDOM répété ou incomplet')
    for record in controls:
        meta=record['reference_benchmark'];key=meta['role']+'_'+str(meta['generation_seed'])
        require(key in expected and key in data['completed_controls'],'contrôle non planifié')
        profile=control_profile(study,meta['role'],meta['generation_seed'])
        require(record['constraint_profile']==profile and record['profile_object']==profile,'profil RANDOM altéré')
        require(record['generation']['method']=='random' and record['generation']['seed']==meta['generation_seed'],'générateur RANDOM altéré')
        require(meta['selection_eligible'] is False and record['lineage']['parent_ids']==[],'contrôle utilisé comme opérateur ou parent')
    return main_records,controls


def generation(study,run_dir,execution,stop_after_main=None,stop_after_controls=None):
    for value in (stop_after_main,stop_after_controls):
        if value is not None:require(type(value) is int and value>=0,'arrêt construction : entier positif ou zéro requis')
    complete=run_dir/'generation.json';checkpoint=run_dir/'generation-checkpoint.json'
    if complete.exists():
        data=read_signed(complete);_check_generation(data,study,execution);return data
    module=main_module(study);experiment=study['experiment'];main_dir=run_dir/'main'
    inner=execution['inputs']['main_execution'];started=time.monotonic()
    if study['experiment_kind']=='ablation':
        original=module.generation(experiment,main_dir,inner,stop_after_main)
    else:
        original=module.generation(experiment,main_dir,inner,stop_after_proposals=stop_after_main)
    if original['status']!='generated':
        return {'status':'main_'+original['status'],'records':original['records'],'completed_controls':[]}
    if checkpoint.exists():
        data=read_signed(checkpoint);_check_generation(data,study,execution)
        require(data['main_generation_signature']==original['signature'],'expérience principale différente')
    else:
        records=deepcopy(original['records'])
        for record in records:
            record.update(study_id=execution['study_id'],study_run_id=execution['id'])
            record['generation'].update(controlled_study_run_id=execution['id'],main_study_run_id=inner['id'])
        data={'schema':'aleaquant-generation-run-v1','signature':digest(execution),
              'run_id':'generation:'+digest(execution),'inputs':execution['inputs'],
              'created_at':execution['created_at'],'status':'controls_generating','records':records,
              'main_generation_signature':original['signature'],'main_record_ids':[r['id'] for r in records],
              'completed_controls':[],'completed_profiles':[],'search_runs':deepcopy(original['search_runs']),
              'rejected_guarantees':[]}
        write(checkpoint,signed(data))
    made=0
    for role,config in study['random_controls'].items():
        for seed in config['seeds']:
            key=role+'_'+str(seed)
            if key in data['completed_controls']:continue
            if ((stop_after_controls is not None and made>=stop_after_controls) or
                time.monotonic()-started>=study['bounds']['max_run_seconds']):
                write(checkpoint,signed(data));event(phase='controls',status='interrupted',completed=len(data['completed_controls']))
                return data
            profile=control_profile(study,role,seed);result=generate_candidates(profile)
            require(len(result['candidates'])<=1,'un contrôle untargeted par graine requis')
            search={'profile_id':profile['id'],'reference_role':role,'seed':seed,
                    **{k:result[k] for k in ('status','attempts','rejections','stopped_reason')}}
            if not result['candidates']:
                data.update(status='control_search_exhausted',failed_control=search)
                write(checkpoint,signed(data));return data
            candidate=result['candidates'][0];require(candidate['seed']==seed,'graine RANDOM commune non respectée')
            require(not validate_grids(candidate['grids'],profile),'contrôle RANDOM invalide')
            proof=proof_for(candidate['grids'],profile)
            if profile['constraints']['conditional_guarantee'] is not None and proof.get('fulfilled') is not True:
                data.update(status='control_guarantee_refused',failed_control=search)
                data['rejected_guarantees'].append({'role':role,'seed':seed,'content_sha256':content_hash(candidate['grids']),
                                                    'reason':'requested_guarantee_not_proved'})
                write(checkpoint,signed(data));return data
            record=make_record(profile,candidate,proof,data['run_id'])
            record.update(id=study['id']+'_'+key,study_id=execution['study_id'],study_run_id=execution['id'],
                          reference_benchmark={'role':role,'generation_seed':seed,'selection_eligible':False},
                          is_starting_parent=False,is_survivor=False,is_finalist=False,confirmation_role='reference')
            record['generation'].update(operator='random_control',controlled_study_run_id=execution['id'])
            record['lineage']['operator']='random_control'
            check_record(record);data['records'].append(record);data['completed_controls'].append(key)
            data['search_runs'].append({**search,'accepted':1});made+=1
            data['status']='controls_generating';data.pop('failed_control',None)
            write(checkpoint,signed(data));event(phase='control_generation',role=role,seed=seed,completed=len(data['completed_controls']),attempts=result['attempts'])
    main_records,controls=_check_generation(data,study,execution)
    qualification=qualify_controls(main_records,controls,study['experiment_kind'],require_evaluation=False,
                                  require_full_domain='full_domain' in study['random_controls'])
    require(qualification['status']=='qualified','témoins RANDOM non qualifiés : '+json.dumps(qualification,ensure_ascii=False))
    data.update(status='generated',evaluation_protocol=experiment['base_profile']['evaluation'],control_qualification=qualification)
    write(complete,signed(data),immutable=True);return data


def selection(study,records):
    main_records,controls=split_records(records);experiment=study['experiment']
    if study['experiment_kind']=='ablation':
        analysis=analyze_study(main_records,max_finalists=experiment['confirmation']['max_finalists'])
        main_ids=analysis['finalist_ids']
    else:
        analysis=evolution.finalist_selection(experiment,main_records);main_ids=analysis['finalist_ids']
    require(not (set(main_ids)&{r['id'] for r in controls}),'contrôle présent parmi les finalistes')
    return {'selection_basis':'exact_geometry_only','main_finalist_ids':main_ids,
            'control_ids':[r['id'] for r in controls],
            'confirmation_ids':main_ids+[r['id'] for r in controls]}


def confirm(study,run_dir,records,selected,stop_after=None):
    ids=set(selected['confirmation_ids']);confirmed=[r for r in records if r['id'] in ids]
    require(len(confirmed)==len(ids),'contenu à confirmer absent')
    unique=list({r['content_sha256']:r for r in confirmed}.values())
    protocol={k:v for k,v in study['experiment']['confirmation']['evaluation'].items() if k!='max_certificate_cases'}
    directory=run_dir/'evaluations'/('confirmation-'+digest(protocol)[:16])
    result=evaluate_many(unique,protocol,directory,progress=lambda e:event(phase='confirmation',**e),stop_after_batches=stop_after)
    if result['status']=='complete':write(directory/'confirmation.json',signed(result),immutable=True)
    return result


def _main_projection(study,run_dir,execution,comparison,confirmation,selected):
    """Views of the common evaluations, never independently simulated main MC."""
    main_dir=run_dir/'main';original=read_signed(main_dir/'generation.json')
    contents={r['content_sha256'] for r in original['records']}
    compare=deepcopy(comparison);compare['results']={h:v for h,v in comparison['results'].items() if h in contents}
    compare['generation_signature']=original['signature']
    directory=main_dir/'evaluations'/('controlled-comparison-'+digest(comparison['protocol'])[:16])
    write(directory/'evaluation.json',signed(compare),immutable=True)
    write(main_dir/'latest-evaluation.json',{'path':str((directory/'evaluation.json').relative_to(main_dir))})
    finalists={r['content_sha256'] for r in original['records'] if r['id'] in selected['main_finalist_ids']}
    confirmed=deepcopy(confirmation);confirmed['results']={h:v for h,v in confirmation['results'].items() if h in finalists}
    directory=main_dir/'evaluations'/('confirmation-'+digest(confirmation['protocol'])[:16])
    write(directory/'confirmation.json',signed(confirmed),immutable=True)
    if study['experiment_kind']=='evolution':
        main_selection=evolution.finalist_selection(study['experiment'],original['records'])
        write(main_dir/'finalist-selection.json',signed(main_selection),immutable=True)
    return main_module(study).projection(study['experiment'],main_dir,execution['inputs']['main_execution'])


def projection(study,run_dir,execution):
    data=read_signed(run_dir/'generation.json');_check_generation(data,study,execution)
    dataset=project(run_dir);records=dataset['profiles'];selected=selection(study,records)
    require(read_signed(run_dir/'finalist-selection.json')==selected,'sélection finale différente')
    comparison=read_signed(run_dir/read(run_dir/'latest-evaluation.json')['path'])
    protocol={k:v for k,v in study['experiment']['confirmation']['evaluation'].items() if k!='max_certificate_cases'}
    path=run_dir/'evaluations'/('confirmation-'+digest(protocol)[:16])/'confirmation.json'
    require(path.exists(),'confirmation principale et témoins incomplète : aucun export final')
    confirmation=read_signed(path)
    require(confirmation['status']=='complete' and confirmation['protocol']==protocol,'confirmation incompatible')
    require(comparison['protocol']['seed']!=protocol['seed'] and comparison['draw_stream_sha256']!=confirmation['draw_stream_sha256'],
            'confirmation non indépendante de la comparaison')
    expected={r['content_sha256'] for r in records if r['id'] in selected['confirmation_ids']}
    require(set(confirmation['results'])==expected,'contenus de confirmation manquants ou supplémentaires')
    main_dataset=_main_projection(study,run_dir,execution,comparison,confirmation,selected)
    originals={r['id']:r for r in main_dataset['profiles']};nodes=dataset['graph']['nodes']+main_dataset['graph']['nodes']
    edges=dataset['graph']['edges']+main_dataset['graph']['edges'];sid=execution['study_id'];rid=execution['id']
    for record in records:
        record['evaluation']['role']='comparison'
        record['evaluation']['source_generation_signature']=data['signature']
        nodes.append({'id':record['evaluation']['id'],'type':'evaluation_run','content_sha256':record['content_sha256'],'protocol':record['evaluation']})
        if record['id'] in originals:
            original=originals[record['id']]
            for key in ('is_finalist','is_survivor','is_starting_parent'):
                if key in original:record[key]=original[key]
        record['is_finalist']=record['id'] in selected['main_finalist_ids']
        if record['id'] in selected['confirmation_ids']:
            sim=confirmation['results'][record['content_sha256']]
            evaluation={'id':'evaluation:'+sim['evaluation_sha256'],'method':'monte_carlo','role':'confirmation',
                        'replayed':True,'content_sha256':record['content_sha256'],'draws':sim['draws'],'seed':sim['seed'],
                        'common_draws':True,'independent_of_generation':True,'independent_of_comparison':True,
                        'engine_version':confirmation['engine_version'],'environment':confirmation['environment'],
                        'source_sha256':confirmation['source_sha256'],'draw_stream_sha256':confirmation['draw_stream_sha256'],
                        'source_generation_signature':data['signature'],'protocol':protocol}
            record['confirmation_role']='reference' if 'reference_benchmark' in record else 'finalist'
            if 'reference_benchmark' in record:evaluation['benchmark_role']=record['reference_benchmark']['role']
            record['confirmation']={'evaluation':evaluation,'simulation':sim}
            nodes.append({'id':evaluation['id'],'type':'evaluation_run','content_sha256':record['content_sha256'],'protocol':evaluation})
            edges.append({'type':'confirmed_by','source':'portfolio:'+record['content_sha256'],'target':evaluation['id']})
        edges.append({'type':'generated_in_controlled_study','source':record['generation_run']['id'],'target':rid})
    nodes.extend([{'id':sid,'type':'study','data':study},{'id':rid,'type':'study_run','data':execution}])
    edges.extend([{'type':'executes_study','source':rid,'target':sid},
                  {'type':'contains_experiment','source':sid,'target':main_dataset['study']['id']}])
    graph={'nodes':list({n['id']:n for n in nodes}.values()),'edges':list({digest(e):e for e in edges}.values())}
    validate_graph(graph)
    main_records,controls=split_records(records)
    qualification=qualify_controls(main_records,controls,study['experiment_kind'],require_full_domain='full_domain' in study['random_controls'],
                                  expected_protocol=comparison['protocol'],expected_generation_signature=data['signature'])
    require(qualification['status']=='qualified','évaluations RANDOM non qualifiées : '+json.dumps(qualification,ensure_ascii=False))
    benchmarks=benchmark(main_records,controls,study['experiment_kind'],main_analysis=main_dataset['analysis'],
                         require_full_domain='full_domain' in study['random_controls'],expected_protocol=comparison['protocol'],
                         expected_confirmation_protocol=protocol,expected_generation_signature=data['signature'])
    display=deepcopy(main_dataset['study'])
    display.update(id=sid,run_id=rid,config_id=study['id'],version=study['version'],title=study['title'],question=study['question'],
                   controlled_bounds=study['bounds'],random_controls=study['random_controls'])
    controlled={'version':VERSION,'experiment_kind':study['experiment_kind'],'main_record_ids':[r['id'] for r in main_records],
                'control_record_ids':[r['id'] for r in controls],
                'roles':{role:[r['id'] for r in controls if r['reference_benchmark']['role']==role] for role in study['random_controls']},
                'main_study_id':main_dataset['study']['id'],'main_study_run_id':execution['inputs']['main_execution']['id'],
                'study_run_id':rid,'bounds':study['bounds'],'qualification':qualification}
    origin='local_study' if study['experiment_kind']=='ablation' else 'local_evolution'
    dataset.update(origin=origin,engine_version=VERSION,study=display,study_definition=study,experiment_definition=study['experiment'],
                   study_run=execution,controlled=controlled,reference_benchmark=benchmarks,analysis=main_dataset['analysis'],graph=graph,
                   source={'date':execution['created_at'][:10],'type':origin,'run_id':dataset['run_id'],'study_id':sid,'study_run_id':rid},
                   confirmation_protocol=protocol,limitations=main_dataset['limitations']+[
                       'Témoins RANDOM générés sans objectif ni choix de graine sur MC : dix au même pool et, si demandé, dix sur le domaine complet.',
                       'Les témoins ne participent à aucune sélection ; chacun est confirmé sans classement sur un nouvel ensemble commun de tirages.',
                       'Comparaisons RANDOM descriptives ; les différences appariées ne constituent pas des IC ni une preuve de supériorité.',
                       'Le domaine complet constitue un protocole de comparaison distinct du même pool.'
                   ])
    if study['experiment_kind']=='evolution':dataset['evolution']=main_dataset['evolution']
    return dataset


def publish(study,run_dir,execution,output):
    dataset=projection(study,run_dir,execution)
    ablation_kind=study['experiment_kind']=='ablation'
    folder='portfolio_study_runs' if ablation_kind else 'portfolio_evolution_runs'
    archive=ROOT/'dist/data'/folder/dataset['run_id'].split(':')[1]/'catalogue.json'
    write(archive,dataset,immutable=True);write(output,dataset)
    for record in dataset['profiles']:
        write(run_dir/'exports'/(record['id']+'.json'),record,immutable=True)
        csv='numbers;stars\n'+''.join(' '.join(map(str,g[0]))+';'+' '.join(map(str,g[1]))+'\n' for g in record['grids'])
        path=run_dir/'exports'/(record['id']+'.csv');path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():require(path.read_text()==csv,'export CSV existant différent')
        else:path.write_text(csv)
    index_path=ROOT/'dist/data'/('portfolio_studies.json' if ablation_kind else 'portfolio_evolutions.json')
    schema='aleaquant-study-1.0' if ablation_kind else 'aleaquant-evolution-study-1.0'
    lock_path=ROOT/'runs'/('studies' if ablation_kind else 'evolution')/'.index.lock';lock_path.parent.mkdir(parents=True,exist_ok=True)
    row={'id':execution['id'],'study_id':execution['study_id'],'config_id':study['id'],'title':study['title'],
         'url':'/data/'+folder+'/'+dataset['run_id'].split(':')[1]+'/catalogue.json','run_id':dataset['run_id'],'created_at':execution['created_at']}
    with lock_path.open('a+') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
        index=read(index_path) if index_path.exists() else {'schema':schema,'studies':[]}
        require(index.get('schema')==schema and isinstance(index.get('studies'),list),'index étude invalide')
        existing=next((r for r in index['studies'] if r['id']==row['id']),None)
        if existing:require(existing==row,'index existant incompatible')
        else:index['studies'].append(row)
        write(index_path,index)
    write(run_dir/'study-result.json',signed({'run_id':dataset['run_id'],'archive':str(archive),'controlled':dataset['controlled']}),immutable=True)
    event(phase='export',status='complete',output=str(output),archive=str(archive),run_id=dataset['run_id']);return dataset


def run(study,run_dir,stop_after_main=None,stop_after_controls=None,stop_after_comparison_batches=None,stop_after_confirmation_batches=None,output=None):
    run_dir=Path(run_dir);run_dir.mkdir(parents=True,exist_ok=True);started=time.monotonic()
    def expired():return time.monotonic()-started>=study['bounds']['max_run_seconds']
    with (run_dir/'.controlled.lock').open('a+') as lock:
        try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:raise ValueError('étude contrôlée déjà active dans ce dossier') from exc
        try:
            execution=initialize(study,run_dir);generated=generation(study,run_dir,execution,stop_after_main,stop_after_controls)
            if generated['status']!='generated':return {'status':generated['status'],'completed_main':len(split_records(generated['records'])[0]),'completed_controls':len(generated['completed_controls'])}
            selected=selection(study,generated['records']);write(run_dir/'finalist-selection.json',signed(selected),immutable=True)
            if expired():return {'status':'run_time_interrupted','phase':'generation'}
            result=evaluate(run_dir,stop_after_batches=stop_after_comparison_batches)
            if result['status']!='complete':return {'status':'comparison_interrupted','completed_draws':result['completed_draws']}
            if expired():return {'status':'run_time_interrupted','phase':'comparison'}
            records=project(run_dir)['profiles'];main_records,controls=split_records(records)
            for record in records:record['evaluation']['role']='comparison'
            qualification=qualify_controls(main_records,controls,study['experiment_kind'],
                                          require_full_domain='full_domain' in study['random_controls'],expected_protocol=result['protocol'],
                                          expected_generation_signature=generated['signature'])
            require(qualification['status']=='qualified','MC commun non qualifié : '+json.dumps(qualification,ensure_ascii=False))
            confirmed=confirm(study,run_dir,records,selected,stop_after_confirmation_batches)
            if confirmed['status']!='complete':return {'status':'confirmation_interrupted','completed_draws':confirmed['completed_draws']}
            if expired():return {'status':'run_time_interrupted','phase':'confirmation'}
            if output is None:output=ROOT/'dist/data'/('portfolio_study.json' if study['experiment_kind']=='ablation' else 'portfolio_evolution.json')
            dataset=publish(study,run_dir,execution,output);return {'status':'complete','run_id':dataset['run_id']}
        finally:fcntl.flock(lock.fileno(),fcntl.LOCK_UN)


def status(run_dir):
    path=run_dir/'generation.json'
    if not path.exists():path=run_dir/'generation-checkpoint.json'
    if path.exists():
        data=read_signed(path);main_records,controls=split_records(data['records'])
        result={'status':data['status'],'completed_main':len(main_records),'completed_controls':len(controls)}
    else:
        path=run_dir/'main/generation-checkpoint.json';data=read_signed(path)
        result={'status':'main_'+data['status'],'completed_main':len(data['records']),'completed_controls':0}
        if 'proposals' in data:result['completed_main_proposals']=len(data['proposals'])
    evaluations=[]
    for path in sorted(run_dir.glob('evaluations/*/checkpoint.json')):
        envelope=read(path);payload=envelope['payload'];require(digest(payload)==envelope['checksum_sha256'],'checkpoint MC altéré')
        evaluations.append({'role':'confirmation' if path.parent.name.startswith('confirmation-') else 'comparison',
                            'status':payload['status'],'completed_draws':payload['completed_draws'],
                            'total_draws':payload['protocol']['draws'],'seed':payload['protocol']['seed']})
    result['evaluations']=evaluations;event(**result);return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['validate','run','status','export'])
    parser.add_argument('--study-config',type=Path,default=DEFAULT);parser.add_argument('--run-dir',type=Path);parser.add_argument('--output',type=Path)
    parser.add_argument('--stop-after-main',type=int);parser.add_argument('--stop-after-controls',type=int)
    parser.add_argument('--stop-after-comparison-batches',type=int);parser.add_argument('--stop-after-confirmation-batches',type=int)
    args=parser.parse_args(argv)
    try:
        frozen=args.run_dir/'study.json' if args.run_dir else None
        study=load_study(frozen if args.command in ('status','export') and frozen and frozen.exists() else args.study_config)
        if args.command=='validate':
            if study['experiment_kind']=='evolution':
                check_parent_control_seeds(study,evolution.frozen_parents(study['experiment']))
            else:ablation.known_references(study['experiment'])
            event(status='valid',study_id=study_id(study),main_maximum=main_capacity(study),
                  controls=sum(len(c['seeds']) for c in study['random_controls'].values()));return 0
        if args.run_dir is None:
            require(args.command=='run','status/export : --run-dir requis')
            stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            args.run_dir=ROOT/'runs/controlled'/study['id']/(stamp+'-'+str(uuid4())[:8])
        event(run_dir=str(args.run_dir))
        if args.command=='status':status(args.run_dir);return 0
        if args.command=='export':
            execution=initialize(study,args.run_dir)
            output=args.output or ROOT/'dist/data'/('portfolio_study.json' if study['experiment_kind']=='ablation' else 'portfolio_evolution.json')
            publish(study,args.run_dir,execution,output);return 0
        result=run(study,args.run_dir,args.stop_after_main,args.stop_after_controls,args.stop_after_comparison_batches,args.stop_after_confirmation_batches,args.output)
        event(**result);return 0 if result['status']=='complete' else 2
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print('Étude contrôlée refusée : '+str(exc),file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
