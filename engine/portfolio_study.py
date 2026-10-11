"""Validate/run/status/export configurable paired-seed portfolio studies.

The study freezes its configuration, saves each construction, compares on
common draws, chooses finalists by geometry only, then confirms on new draws.
"""
from copy import deepcopy
from datetime import datetime, timezone
import argparse
import fcntl
from pathlib import Path
import sys
import time
from uuid import uuid4

from portfolio_contract import validate_grids
from portfolio_evaluation import evaluate_many
from portfolio_import import content_hash, digest, require
from portfolio_pipeline import ROOT, check_record, comparisons, engine_sources, evaluate, make_record, project, read, read_signed, signed, validate_graph, write
from portfolio_proof import proof_for
from portfolio_search import generate_candidates
from portfolio_study_contract import VERSION, load_study, study_id, template_profiles

DEFAULT = ROOT/'configs/studies/minimize-overlap-20x15x5-v1.json'


def event(**fields):
    import json
    print(json.dumps(fields,ensure_ascii=False),flush=True)


def known_references(study):
    source=read(ROOT/'dist/data/portfolio_pipeline.json')
    available={p['id']:p for p in source['profiles']}
    for name in ('portfolio_search.json','portfolio_study.json'):
        current=ROOT/'dist/data'/name
        if current.exists():available.update({p['id']:p for p in read(current)['profiles']})
    out=[]
    for ref in study['references']:
        require(ref['id'] in available,'référence inconnue : '+ref['id'])
        p=available[ref['id']]
        require(content_hash(p['grids'])==ref['content_sha256'],'empreinte de référence incompatible : '+ref['id'])
        out.append({**ref,'role':'reference_only','source_archive_sha256':source['source']['archive_sha256'] if ref['id'] in {p['id'] for p in source['profiles']} else None})
    return out


def initialize(study,run_dir):
    definition=run_dir/'study.json';identity=run_dir/'study-run.json'
    write(definition,study,immutable=True)
    inputs={'configuration':study,'engine_sources':engine_sources(),'references':known_references(study)}
    if identity.exists():
        execution=read_signed(identity)
        require(execution['inputs']==inputs,'étude ou code modifiés : choisir un nouveau dossier de run')
    else:
        execution={'id':'study-run:'+str(uuid4()),'study_id':study_id(study),
                   'created_at':datetime.now(timezone.utc).isoformat(),'inputs':inputs}
        write(identity,signed(execution),immutable=True)
    return execution


def generation(study,run_dir,execution,stop_after=None):
    if stop_after is not None:require(type(stop_after) is int and stop_after>=0,'arrêt construction : entier positif ou zéro requis')
    complete=run_dir/'generation.json';checkpoint=run_dir/'generation-checkpoint.json'
    signature=digest(execution)
    if complete.exists():
        data=read_signed(complete);require(data['signature']==signature,'génération d’une autre étude')
        for p in data['records']:check_record(p)
        return data
    if checkpoint.exists():
        data=read_signed(checkpoint);require(data['signature']==signature,'checkpoint d’une autre étude')
        for p in data['records']:check_record(p)
    else:
        data={'schema':'aleaquant-generation-run-v1','run_id':'generation:'+signature,'signature':signature,
              'inputs':execution['inputs'],'study_execution_id':execution['id'],
              'records':[],'search_runs':[],'completed_profiles':[],
              'created_at':execution['created_at'],'status':'generating','rejected_guarantees':[]}
    templates=template_profiles(study);started=time.monotonic();made=0
    total=len(templates)*len(study['generation']['seeds'])
    for seed in study['generation']['seeds']:
        for template,weight in zip(templates,study['vary']['values']):
            key=template['id']+f'_s{seed}'
            if key in data['completed_profiles']:continue
            if ((stop_after is not None and made>=stop_after) or
                time.monotonic()-started>=study['bounds']['max_run_seconds']):
                write(checkpoint,signed(data));event(phase='generation',status='interrupted',completed=len(data['completed_profiles']),total=total)
                return data
            profile=deepcopy(template);profile['search']['seed']=seed
            result=generate_candidates(profile)
            require(len(result['candidates'])<=1,'une construction par réglage/graine requise')
            search={'profile_id':template['id'],'weight':weight,'seed':seed,
                    **{k:result[k] for k in ('status','attempts','rejections','stopped_reason')}}
            if not result['candidates']:
                data['status']='search_exhausted';data['failed_search']=search
                write(checkpoint,signed(data));event(phase='generation',**search)
                return data
            candidate=result['candidates'][0]
            require(candidate['seed']==seed,'graine commune non respectée')
            require(not validate_grids(candidate['grids'],profile),'construction invalide')
            proof=proof_for(candidate['grids'],profile)
            if profile['constraints']['conditional_guarantee'] is not None:
                require(proof.get('fulfilled') is True,'garantie obligatoire non prouvée : étude non achevée')
            record=make_record(profile,candidate,proof,data['run_id'])
            record.update(id=key,profile_object=deepcopy(template),config_sha256=digest(template),
                          study_factor={'weight':weight,'seed':seed},
                          study_id=execution['study_id'],study_run_id=execution['id'])
            record['generation']['profile_seed_override']=seed
            record['generation']['study_run_id']=execution['id']
            check_record(record);data['records'].append(record)
            data['completed_profiles'].append(key);data['search_runs'].append({**search,'accepted':1})
            made+=1;write(checkpoint,signed(data))
            event(phase='generation',completed=len(data['completed_profiles']),total=total,weight=weight,seed=seed,attempts=result['attempts'])
    data['status']='generated';data.pop('failed_search',None)
    data['evaluation_protocol']=study['base_profile']['evaluation']
    require(len(data['records'])==total,'plan d’étude incomplet')
    write(complete,signed(data),immutable=True)
    return data


def confirm(study,run_dir,records,analysis,stop_after=None):
    ids=set(analysis['finalist_ids'])
    finalists=[p for p in records if p['id'] in ids]
    require(len(finalists)==len(ids),'finaliste absent de la génération')
    unique=list({p['content_sha256']:p for p in finalists}.values())
    require(0<len(unique)<=study['confirmation']['max_finalists'],'nombre de finalistes incompatible')
    protocol={k:v for k,v in study['confirmation']['evaluation'].items() if k!='max_certificate_cases'}
    directory=run_dir/'evaluations'/('confirmation-'+digest(protocol)[:16])
    result=evaluate_many(unique,protocol,directory,
                         progress=lambda e:event(phase='confirmation',**e),stop_after_batches=stop_after)
    if result['status']=='complete':write(directory/'confirmation.json',signed(result),immutable=True)
    return result


def display_study(study,execution):
    p=study['base_profile']
    fixed={k:deepcopy(p[k]) for k in ('game','pool','constraints','objectives','search')}
    fixed['objectives']['minimize_overlap'].pop('numbers')
    fixed['search'].pop('seed')
    return {'id':execution['study_id'],'config_id':study['id'],'version':study['version'],
            'run_id':execution['id'],'title':study['title'],'question':study['question'],
            'fixed_parameters':fixed,
            'axis':{'parameter':study['vary']['parameter'],'values':study['vary']['values']},
            'repetitions':study['generation']['repetitions'],'seeds':study['generation']['seeds'],
            'bounds':study['bounds'],'comparison':p['evaluation'],
            'comparison_method':study['comparison']['method'],
            'metrics':study['comparison']['metrics'],
            'starting_points':{'base_profile_id':p['id'],'references':study['references']},
            'confirmation':{**study['confirmation']['evaluation'],'selection_rule':study['confirmation']['selection'],
                            'max_finalists':study['confirmation']['max_finalists']}}


def projection(study,run_dir,execution):
    from portfolio_study_analysis import analyze_study
    dataset=project(run_dir);records=dataset['profiles']
    analysis=analyze_study(records,max_finalists=study['confirmation']['max_finalists'])
    protocol={k:v for k,v in study['confirmation']['evaluation'].items() if k!='max_certificate_cases'}
    path=run_dir/'evaluations'/('confirmation-'+digest(protocol)[:16])/'confirmation.json'
    require(path.exists(),'confirmation indépendante non achevée : aucun export final')
    confirmation=read_signed(path)
    require(confirmation['status']=='complete' and confirmation['protocol']==protocol,'confirmation invalide')
    analysis=analyze_study(records,max_finalists=study['confirmation']['max_finalists'],confirmation=confirmation['results'])
    ids=set(analysis['finalist_ids']);nodes=dataset['graph']['nodes'];edges=dataset['graph']['edges']
    for p in records:
        p['evaluation']['role']='comparison';p['is_finalist']=p['id'] in ids
        if p['is_finalist']:
            sim=confirmation['results'][p['content_sha256']]
            evaluation={'id':'evaluation:'+sim['evaluation_sha256'],'method':'monte_carlo','role':'confirmation',
                        'replayed':True,'content_sha256':p['content_sha256'],'draws':sim['draws'],'seed':sim['seed'],
                        'common_draws':True,'independent_of_generation':True,'independent_of_comparison':True,
                        'engine_version':confirmation['engine_version'],'environment':confirmation['environment'],
                        'source_sha256':confirmation['source_sha256'],'draw_stream_sha256':confirmation['draw_stream_sha256'],
                        'protocol':protocol}
            p['confirmation']={'evaluation':evaluation,'simulation':sim}
            nodes.append({'id':evaluation['id'],'type':'evaluation_run','content_sha256':p['content_sha256'],'protocol':evaluation})
            edges.append({'type':'confirmed_by','source':'portfolio:'+p['content_sha256'],'target':evaluation['id']})
    sid=execution['study_id'];rid=execution['id']
    nodes.extend([{'id':sid,'type':'study','data':study},{'id':rid,'type':'study_run','data':execution}])
    edges.append({'type':'executes_study','source':rid,'target':sid})
    for p in records:
        edges.extend([{'type':'generated_in_study','source':p['generation_run']['id'],'target':rid},
                      {'type':'uses_profile_version','source':sid,'target':p['lineage']['profile_node_id']}])
    for ref in execution['inputs']['references']:
        ref_id='reference:'+digest(ref)
        nodes.append({'id':ref_id,'type':'reference','data':ref})
        edges.append({'type':'uses_reference','source':sid,'target':ref_id})
    graph={'nodes':list({n['id']:n for n in nodes}.values()),'edges':list({digest(e):e for e in edges}.values())}
    validate_graph(graph)
    dataset.update(origin='local_study',study=display_study(study,execution),study_definition=study,
                   study_run=execution,analysis=analysis,graph=graph,
                   source={'date':execution['created_at'][:10],'type':'local_study','run_id':dataset['run_id'],
                           'study_id':sid,'study_run_id':rid},
                   confirmation_protocol=confirmation['protocol'])
    dataset['limitations']=[
        'Étude appariée : seul le poids de minimize_overlap.numbers varie ; pools, autres poids, budget et fenêtre de propositions restent fixes.',
        f'{study["generation"]["repetitions"]} graines ne sont pas autant de tirages ni de pools indépendants. Les mêmes graines servent aux {len(study["vary"]["values"])} réglages ; comparaison par différences appariées.',
        'Finalistes choisis sur la géométrie exacte uniquement, avec diversité de poids et plafond déclaré ; le front global complet reste enregistré.',
        'MC de comparaison et MC de confirmation utilisent des graines et des ensembles de tirages distincts. Chaque rôle conserve ses compteurs et empreintes.',
        'Les IC95 Wilson sont ponctuels, sans correction de multiplicité ; les IC de probabilités marginales ne sont pas des IC de différences entre portefeuilles.',
        'Aucune preuve de supériorité économique, de remboursement ni d’optimalité. Les garanties restent conditionnelles et liées au contenu.',
        'Cette étude ne réalise pas encore mutations, sélection générationnelle ni croisements.'
    ]
    return dataset


def publish_study(study,run_dir,execution,output):
    dataset=projection(study,run_dir,execution)
    archive=ROOT/'dist/data/portfolio_study_runs'/dataset['run_id'].split(':')[1]/'catalogue.json'
    write(archive,dataset,immutable=True);write(output,dataset)
    for p in dataset['profiles']:
        write(run_dir/'exports'/(p['id']+'.json'),p,immutable=True)
        csv='numbers;stars\n'+''.join(' '.join(map(str,g[0]))+';'+' '.join(map(str,g[1]))+'\n' for g in p['grids'])
        file=run_dir/'exports'/(p['id']+'.csv');file.parent.mkdir(parents=True,exist_ok=True)
        if file.exists():require(file.read_text()==csv,'export de grilles existant différent')
        else:file.write_text(csv)
    index_path=ROOT/'dist/data/portfolio_studies.json'
    row={'id':execution['id'],'study_id':execution['study_id'],'config_id':study['id'],'title':study['title'],
         'url':'/data/portfolio_study_runs/'+dataset['run_id'].split(':')[1]+'/catalogue.json',
         'run_id':dataset['run_id'],'created_at':execution['created_at']}
    lock_path=ROOT/'runs/studies/.index.lock';lock_path.parent.mkdir(parents=True,exist_ok=True)
    with lock_path.open('a+') as index_lock:
        fcntl.flock(index_lock.fileno(),fcntl.LOCK_EX)
        index=read(index_path) if index_path.exists() else {'schema':VERSION,'studies':[]}
        require(index.get('schema')==VERSION and isinstance(index.get('studies'),list),'index d’étude invalide')
        existing=next((r for r in index['studies'] if r['id']==row['id']),None)
        if existing:require(existing==row,'index d’étude existant incompatible')
        else:index['studies'].append(row)
        write(index_path,index)
    write(run_dir/'study-result.json',signed({'run_id':dataset['run_id'],'archive':str(archive),
                                            'contexts':len(dataset['profiles']),
                                            'contents':len({p['content_sha256'] for p in dataset['profiles']}),
                                            'analysis':dataset['analysis']}),immutable=True)
    event(phase='export',status='complete',run_id=dataset['run_id'],study_run_id=execution['id'],output=str(output),archive=str(archive))
    return dataset


def run(study,run_dir,stop_after_constructions=None,stop_after_comparison_batches=None,stop_after_confirmation_batches=None,output=None):
    run_dir=Path(run_dir);run_dir.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    def timed_out():
        return time.monotonic()-started>=study['bounds']['max_run_seconds']
    with (run_dir/'.study.lock').open('a+') as lock:
        try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:raise ValueError('étude déjà active dans ce dossier') from exc
        try:
            execution=initialize(study,run_dir)
            data=generation(study,run_dir,execution,stop_after_constructions)
            if data['status']!='generated':return {'status':data['status'],'completed_constructions':len(data['records'])}
            if timed_out():return {'status':'run_time_interrupted','completed_constructions':len(data['records'])}
            event(phase='comparison',draws=study['base_profile']['evaluation']['draws'],seed=study['base_profile']['evaluation']['seed'])
            result=evaluate(run_dir,stop_after_batches=stop_after_comparison_batches)
            if result['status']!='complete':return {'status':'comparison_interrupted','completed_draws':result['completed_draws']}
            if timed_out():return {'status':'run_time_interrupted','phase':'comparison'}
            from portfolio_study_analysis import analyze_study
            records=project(run_dir)['profiles']
            analysis=analyze_study(records,max_finalists=study['confirmation']['max_finalists'])
            write(run_dir/'finalist-selection.json',signed(analysis['finalist_selection']),immutable=True)
            event(phase='selection',finalists=len(analysis['finalist_ids']),rule=study['confirmation']['selection'])
            confirmed=confirm(study,run_dir,records,analysis,stop_after_confirmation_batches)
            if confirmed['status']!='complete':return {'status':'confirmation_interrupted','completed_draws':confirmed['completed_draws']}
            if timed_out():return {'status':'run_time_interrupted','phase':'confirmation'}
            dataset=publish_study(study,run_dir,execution,output or ROOT/'dist/data/portfolio_study.json')
            return {'status':'complete','run_id':dataset['run_id']}
        finally:fcntl.flock(lock.fileno(),fcntl.LOCK_UN)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['validate','run','status','export'])
    parser.add_argument('--study-config',type=Path,default=DEFAULT)
    parser.add_argument('--run-dir',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'dist/data/portfolio_study.json')
    parser.add_argument('--stop-after-constructions',type=int)
    parser.add_argument('--stop-after-comparison-batches',type=int)
    parser.add_argument('--stop-after-confirmation-batches',type=int)
    args=parser.parse_args(argv)
    try:
        frozen=args.run_dir/'study.json' if args.run_dir else None
        study=load_study(frozen if args.command in ('status','export') and frozen and frozen.exists() else args.study_config)
        if args.command=='validate':
            event(status='valid',study_id=study_id(study),profiles=len(study['vary']['values']),
                  repetitions=study['generation']['repetitions'],constructions=len(study['vary']['values'])*len(study['generation']['seeds']))
            return 0
        if args.run_dir is None:
            require(args.command=='run','status/export : --run-dir requis')
            stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            args.run_dir=ROOT/'runs/studies'/study['id']/(stamp+'-'+str(uuid4())[:8])
        event(run_dir=str(args.run_dir))
        if args.command=='status':
            file=args.run_dir/'generation.json'
            if not file.exists():file=args.run_dir/'generation-checkpoint.json'
            data=read_signed(file)
            evaluations=[]
            for file in sorted(args.run_dir.glob('evaluations/*/checkpoint.json')):
                envelope=read(file);payload=envelope['payload']
                require(digest(payload)==envelope['checksum_sha256'],'checkpoint évaluation altéré')
                evaluations.append({'role':'confirmation' if file.parent.name.startswith('confirmation-') else 'comparison',
                                    'status':payload['status'],'completed_draws':payload['completed_draws'],
                                    'total_draws':payload['protocol']['draws'],'seed':payload['protocol']['seed']})
            event(status=data['status'],completed_constructions=len(data['records']),evaluations=evaluations)
            return 0
        if args.command=='export':
            execution=initialize(study,args.run_dir);publish_study(study,args.run_dir,execution,args.output);return 0
        result=run(study,args.run_dir,args.stop_after_constructions,args.stop_after_comparison_batches,
                   args.stop_after_confirmation_batches,args.output)
        event(**result);return 0 if result['status']=='complete' else 2
    except (ValueError,KeyError,TypeError,OSError) as error:
        print(f'Étude refusée : {error}',file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
