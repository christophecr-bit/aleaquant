"""Bounded real studies with RANDOM controls and only 65 common MC draws."""
from contextlib import redirect_stdout
from copy import deepcopy
from hashlib import sha256
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'engine'))
import portfolio_pipeline as shared
import portfolio_study as ablation
from evolution import pipeline as evolution
from controlled import pipeline as runner
from controlled.contract import control_profile,load_study,validate_study
from controlled.comparison import qualify_controls
from portfolio_contract import validate_grids
from portfolio_proof import proof_for
from portfolio_search import generate_candidates


class ControlledPipelineTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.directory=Path(temporary.name);self.site=self.directory/'site';(self.site/'dist/data').mkdir(parents=True)
        (self.site/'dist/metrics.json').write_bytes((ROOT/'dist/metrics.json').read_bytes())
        shared.write(self.site/'dist/data/portfolio_pipeline.json',{'profiles':[],'source':{'archive_sha256':'a'*64}})
        self.study=json.loads((ROOT/'configs/controlled/overlap-random-v1.json').read_text())
        self.study.update(id='mini_controlled',title='Petite étude contrôlée',question='Comparer dix graines et témoins RANDOM ?')
        experiment=self.study['experiment'];experiment.update(id='mini_ablation',title='Petite ablation',question='Effet de deux poids ?')
        p=experiment['base_profile'];p['pool'].update(numbers=list(range(1,10)),stars=[1,2,3,4],number_count=9,star_count=4,seed=91)
        p['constraints'].update(grid_count=3,budget_max_eur=7.5,conditional_guarantee=None)
        p['search'].update(seed=101,max_attempts=3600,max_seconds=5)
        p['evaluation'].update(draws=65,seed=901,batch_size=16,max_seconds=5,max_certificate_cases=1000)
        experiment['vary']['values']=[0,1.4];experiment['generation'].update(seeds=list(range(101,111)),repetitions=10)
        experiment['bounds'].update(max_constructions=20,max_run_seconds=10)
        experiment['confirmation'].update(max_finalists=2,evaluation=deepcopy(p['evaluation']))
        experiment['confirmation']['evaluation']['seed']=902;experiment['references']=[]
        self.study['random_controls']={role:{'seeds':list(range(101,111))} for role in ('same_pool','full_domain')}
        self.study['bounds'].update(max_total_constructions=40,max_run_seconds=10)
        self.run_dir=self.directory/'run-a';self.output=self.site/'dist/data/portfolio_study.json'
        for module in (shared,ablation,evolution,runner):
            change=patch.object(module,'ROOT',self.site);change.start();self.addCleanup(change.stop)
        validate_study(self.study)

    def run_study(self,run_dir=None,study=None,**options):
        with redirect_stdout(io.StringIO()):
            return runner.run(study or self.study,run_dir or self.run_dir,output=self.output,**options)

    def unpublished(self):
        self.assertFalse(self.output.exists());self.assertFalse((self.site/'dist/data/portfolio_studies.json').exists())

    def test_registered_single_configs_are_valid_and_frozen_engines_are_unmodified(self):
        for kind,name,count in [('ablation','overlap-random-v1.json',60),('evolution','evolution-random-v1.json',49)]:
            config=ROOT/'configs/controlled'/name;study=load_study(config)
            self.assertEqual(study['experiment_kind'],kind);self.assertEqual(study['bounds']['max_total_constructions'],count)
            result=subprocess.run([sys.executable,str(ROOT/'engine/study.py'),'validate','--study-config',str(config)],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout)['controls'],20)
        self.assertTrue(all(not k.startswith('controlled/') for k in shared.engine_sources()))
        sources=runner.source_signatures();self.assertIn('controlled/study.schema.json',sources);self.assertIn('study.py',sources)
        self.unpublished()

    def test_contract_refuses_mismatched_seeds_protocols_bounds_and_unknown_controls(self):
        changes=[(('random_controls','same_pool','seeds'),list(range(201,211))),
                 (('random_controls','same_pool','seeds'),[101]*10),
                 (('random_controls','full_domain','seeds'),list(range(895,905))),
                 (('bounds','max_total_constructions'),39),(('bounds','max_run_seconds'),601),
                 (('experiment','base_profile','evaluation','seed'),101),
                 (('experiment','confirmation','evaluation','seed'),901)]
        for path,value in changes:
            bad=deepcopy(self.study);cursor=bad
            for part in path[:-1]:cursor=cursor[part]
            cursor[path[-1]]=value
            with self.subTest(path=path),self.assertRaises(ValueError):validate_study(bad)
        bad=deepcopy(self.study);bad['random_controls']['same_pool']['method']='greedy'
        with self.assertRaises(ValueError):validate_study(bad)
        bad=deepcopy(self.study);bad['random_controls']['extra']={'seeds':list(range(101,111))}
        with self.assertRaises(ValueError):validate_study(bad)

    def test_main_controls_and_both_mc_roles_resume_before_publication(self):
        partial=self.run_study(stop_after_main=2);self.assertEqual(partial['status'],'main_generating');self.unpublished()
        partial=self.run_study(stop_after_controls=3);self.assertEqual(partial['status'],'controls_generating')
        self.assertEqual(partial['completed_controls'],3);self.unpublished()
        checkpoint=shared.read_signed(self.run_dir/'generation-checkpoint.json');saved=deepcopy(checkpoint['records'])
        partial=self.run_study(stop_after_comparison_batches=1);self.assertEqual(partial['status'],'comparison_interrupted')
        self.assertEqual(partial['completed_draws'],16);self.unpublished()
        generation=shared.read_signed(self.run_dir/'generation.json')
        self.assertEqual(generation['records'][:len(saved)],saved);self.assertEqual(len(generation['records']),40)
        partial=self.run_study(stop_after_confirmation_batches=1);self.assertEqual(partial['status'],'confirmation_interrupted')
        self.assertEqual(partial['completed_draws'],16);self.unpublished()
        with self.assertRaises(ValueError):runner.projection(self.study,self.run_dir,shared.read_signed(self.run_dir/'study-run.json'))
        result=self.run_study();self.assertEqual(result['status'],'complete')
        dataset=shared.read(self.output);self.assertEqual(dataset['analysis']['record_count'],20)
        self.assertEqual(dataset['origin'],'local_study');self.assertEqual(len(dataset['profiles']),40)
        self.assert_dataset(dataset)
        original=self.output.read_bytes();again=self.run_study();self.assertEqual(result['run_id'],again['run_id'])
        self.assertEqual(original,self.output.read_bytes())

    def assert_dataset(self,dataset):
        controlled=dataset['controlled'];main,controls=runner.split_records(dataset['profiles'])
        self.assertEqual(len(controls),20);self.assertEqual(len(controlled['roles']['same_pool']),10)
        self.assertEqual(len(controlled['roles']['full_domain']),10)
        self.assertEqual(controlled['qualification']['status'],'qualified')
        self.assertTrue(set(dataset['analysis']['finalist_ids']).isdisjoint(controlled['control_record_ids']))
        streams=set();confirmation_streams=set()
        for record in dataset['profiles']:
            self.assertEqual(validate_grids(record['grids'],record['constraint_profile']),[])
            self.assertEqual(record['certificate']['content_sha256'],record['content_sha256'])
            self.assertEqual(record['evaluation']['role'],'comparison');self.assertEqual(record['simulation']['draws'],65)
            streams.add(record['evaluation']['draw_stream_sha256'])
            if 'reference_benchmark' in record:
                meta=record['reference_benchmark'];expected=control_profile(self.study,meta['role'],meta['generation_seed'])
                self.assertEqual(record['constraint_profile'],expected);self.assertEqual(record['generation']['method'],'random')
                self.assertEqual(record['generation']['seed'],meta['generation_seed']);self.assertFalse(meta['selection_eligible'])
                self.assertFalse(record['is_finalist']);self.assertFalse(record['is_survivor']);self.assertEqual(record['lineage']['parent_ids'],[])
                self.assertEqual(record['confirmation_role'],'reference');self.assertIn('confirmation',record)
                self.assertEqual(record['confirmation']['simulation']['draws'],65)
            if 'confirmation' in record:
                self.assertEqual(record['confirmation']['evaluation']['seed'],902)
                confirmation_streams.add(record['confirmation']['evaluation']['draw_stream_sha256'])
        self.assertEqual(len(streams),1);self.assertEqual(len(confirmation_streams),1);self.assertTrue(streams.isdisjoint(confirmation_streams))
        shared.validate_graph(dataset['graph'])

    def test_resume_refuses_changed_wrapper_sources_and_tampered_random_profile(self):
        self.run_study(stop_after_controls=1)
        with patch.object(runner,'source_signatures',return_value={'changed.py':'a'*64}),self.assertRaises(ValueError):self.run_study()
        checkpoint=self.run_dir/'generation-checkpoint.json';data=shared.read_signed(checkpoint)
        control=runner.split_records(data['records'])[1][0];control['constraint_profile']['family']='BALANCED'
        shared.write(checkpoint,shared.signed(data))
        with self.assertRaises(ValueError):self.run_study()
        self.unpublished()

    def test_same_pool_only_is_valid_and_does_not_invent_full_domain_controls(self):
        study=deepcopy(self.study);study['random_controls'].pop('full_domain')
        study['bounds']['max_total_constructions']=30;validate_study(study)
        result=self.run_study(study=study);self.assertEqual(result['status'],'complete')
        dataset=shared.read(self.output);self.assertEqual(set(dataset['controlled']['roles']),{'same_pool'})
        self.assertEqual(len(dataset['profiles']),30)

    def test_full_domain_may_use_an_independent_declared_seed_set(self):
        study=deepcopy(self.study);study['random_controls']['full_domain']['seeds']=list(range(201,211))
        validate_study(study);result=self.run_study(study=study)
        self.assertEqual(result['status'],'complete');dataset=shared.read(self.output)
        self.assertFalse(dataset['reference_benchmark']['full_domain']['pool_effect']['paired'])
        self.assertEqual(dataset['reference_benchmark']['full_domain']['pool_effect']['rows'],[])

    def miniature_evolution(self):
        study=json.loads((ROOT/'configs/controlled/evolution-random-v1.json').read_text())
        study.update(id='mini_evolution_controls',title='Petite évolution contrôlée',question='Descendants et RANDOM ?')
        exp=study['experiment'];p=deepcopy(self.study['experiment']['base_profile']);p['search']['seed']=701;exp['base_profile']=p
        exp.update(id='mini_evolution',title='Petite évolution',question='Mutations puis croisement ?')
        exp['generation'].update(seed=701,population_size=2,schedule=[{'phase':'mutation','proposals':3},{'phase':'crossover','proposals':2}])
        exp['bounds'].update(max_proposals=5,max_run_seconds=10)
        exp['confirmation'].update(max_finalists=2,evaluation=deepcopy(self.study['experiment']['confirmation']['evaluation']))
        source_records=[]
        for index,seed in enumerate((601,602)):
            parent_profile=deepcopy(p);parent_profile['search']['seed']=seed
            candidate=generate_candidates(parent_profile)['candidates'][0]
            record=shared.make_record(parent_profile,candidate,proof_for(candidate['grids'],parent_profile),'source-run')
            record['id']='parent'+str(index);source_records.append(record)
        path=self.site/'dist/data/parents.json';shared.write(path,{'profiles':source_records,'run_id':'source-run'})
        exp['parents']=[{'source':'dist/data/parents.json','source_sha256':sha256(path.read_bytes()).hexdigest(),'id':r['id'],'content_sha256':r['content_sha256']} for r in source_records]
        study['random_controls']={role:{'seeds':list(range(801,811))} for role in ('same_pool','full_domain')}
        study['bounds'].update(max_total_constructions=27,max_run_seconds=10);validate_study(study);return study

    def test_evolution_controls_are_never_parents_survivors_or_finalists(self):
        study=self.miniature_evolution();result=self.run_study(study=study);self.assertEqual(result['status'],'complete')
        dataset=shared.read(self.output);self.assertEqual(dataset['origin'],'local_evolution')
        main,controls=runner.split_records(dataset['profiles']);control_ids={r['id'] for r in controls}
        control_nodes={'portfolio:'+r['content_sha256'] for r in controls}
        self.assertEqual(len(controls),20);self.assertTrue(any(not r['is_starting_parent'] for r in main))
        for record in main:self.assertTrue(set(record['lineage']['parent_ids']).isdisjoint(control_nodes))
        for row in dataset['evolution']['generations']:
            self.assertTrue(set(row['entrant_ids']).isdisjoint(control_ids));self.assertTrue(set(row['survivor_ids']).isdisjoint(control_ids))
        self.assertTrue(set(dataset['analysis']['finalist_ids']).isdisjoint(control_ids))
        shared.validate_graph(dataset['graph'])

    def test_evolution_control_seeds_must_not_reuse_parent_seeds(self):
        study=self.miniature_evolution();study['random_controls']['same_pool']['seeds'][0]=601
        validate_study(study)
        with self.assertRaises(ValueError):self.run_study(study=study)
        self.unpublished()

    def test_old_monte_carlo_mixed_into_a_control_is_refused(self):
        result=self.run_study();self.assertEqual(result['status'],'complete')
        dataset=shared.read(self.output);main,controls=runner.split_records(dataset['profiles'])
        bad=deepcopy(controls);bad[0]['evaluation']['draw_stream_sha256']='a'*64
        qualification=qualify_controls(main,bad,'ablation',require_full_domain=True)
        self.assertEqual(qualification['status'],'refused')

    def test_random_pool_method_and_protocol_mismatch_are_refused(self):
        self.run_study();dataset=shared.read(self.output);main,controls=runner.split_records(dataset['profiles'])
        for alteration in ('pool','method','protocol'):
            bad=deepcopy(controls)
            if alteration=='pool':bad[0]['pool_numbers']=list(range(1,51))
            elif alteration=='method':bad[0]['generation']['method']='prototype_greedy'
            else:bad[0]['evaluation']['protocol']['seed']=903
            with self.subTest(alteration=alteration):
                qualification=qualify_controls(main,bad,'ablation',require_full_domain=True)
                self.assertEqual(qualification['status'],'refused')

    def test_unproved_random_guarantee_stops_without_retry_or_seed_selection(self):
        study=deepcopy(self.study)
        study['experiment']['base_profile']['constraints']['conditional_guarantee']={
            'pool_good_numbers':5,'pool_good_stars':2,'condition_mode':'exactly',
            'required_numbers':0,'required_stars':0,'threshold_mode':'at_least'}
        study['random_controls'].pop('full_domain');study['bounds']['max_total_constructions']=30
        def refused(grids,profile):
            proof=proof_for(grids,profile);proof['fulfilled']=False;return proof
        with patch.object(runner,'proof_for',side_effect=refused) as prove:
            result=self.run_study(study=study)
        self.assertEqual(result['status'],'control_guarantee_refused');self.assertEqual(prove.call_count,1)
        checkpoint=shared.read_signed(self.run_dir/'generation-checkpoint.json')
        self.assertEqual(checkpoint['completed_controls'],[])
        self.assertEqual(checkpoint['failed_control']['seed'],101)
        self.assertEqual(len(checkpoint['rejected_guarantees']),1);self.unpublished()

    def test_repeat_execution_preserves_old_archive_with_new_run_identity(self):
        study=self.miniature_evolution();first=self.run_study(study=study)
        archive=self.site/'dist/data/portfolio_evolution_runs'/first['run_id'].split(':')[1]/'catalogue.json'
        saved=archive.read_bytes();second=self.run_study(run_dir=self.directory/'run-b',study=study)
        self.assertNotEqual(first['run_id'],second['run_id']);self.assertEqual(archive.read_bytes(),saved)
        index=shared.read(self.site/'dist/data/portfolio_evolutions.json');self.assertEqual(len(index['studies']),2)


if __name__=='__main__':unittest.main()
