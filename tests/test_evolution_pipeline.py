"""Small real evolution runs; production parents and MC never run here."""
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
from portfolio_contract import validate_grids
from portfolio_import import content_hash,digest
from portfolio_proof import proof_for
from portfolio_search import generate_candidates
from evolution import pipeline as runner
from evolution.contract import load_study,validate_study

REGISTERED=ROOT/'configs/evolution/overlap-descendants-v1.json'


class EvolutionPipelineTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.directory=Path(temp.name);self.site=self.directory/'site'
        (self.site/'dist/data').mkdir(parents=True)
        (self.site/'dist/metrics.json').write_bytes((ROOT/'dist/metrics.json').read_bytes())
        self.study=json.loads(REGISTERED.read_text());self.study.update(id='mini_evolution',title='Petite évolution',question='Deux générations bornées ?')
        p=self.study['base_profile']
        p['pool'].update(numbers=list(range(1,10)),stars=[1,2,3,4],number_count=9,star_count=4,seed=91)
        p['constraints'].update(grid_count=3,budget_max_eur=7.5,conditional_guarantee=None)
        p['search'].update(seed=701,max_attempts=3600,max_seconds=5)
        p['evaluation'].update(draws=65,seed=901,batch_size=16,max_seconds=5,max_certificate_cases=1000)
        self.study['confirmation'].update(max_finalists=2,evaluation=deepcopy(p['evaluation']))
        self.study['confirmation']['evaluation']['seed']=902
        self.study['generation'].update(seed=701,population_size=2,schedule=[{'phase':'mutation','proposals':3},{'phase':'crossover','proposals':2}])
        self.study['bounds'].update(max_proposals=5,max_run_seconds=10)
        records=[]
        for i,seed in enumerate((601,602)):
            source_profile=deepcopy(p);source_profile['search']['seed']=seed
            candidate=generate_candidates(source_profile)['candidates'][0]
            record=shared.make_record(source_profile,candidate,proof_for(candidate['grids'],source_profile),'source-run')
            record['id']='source_parent_'+str(i);record['is_finalist']=True;records.append(record)
        path=self.site/'dist/data/parents.json'
        shared.write(path,{'run_id':'source-run','profiles':records,'study':{'id':'source-study'},'study_run':{'id':'source-study-run'}})
        self.study['parents']=[{'source':'dist/data/parents.json','source_sha256':sha256(path.read_bytes()).hexdigest(),
                               'id':r['id'],'content_sha256':r['content_sha256']} for r in records]
        validate_study(self.study)
        self.config=self.directory/'configuration.json';self.config.write_text(json.dumps(self.study))
        self.run_dir=self.directory/'run-a';self.output=self.site/'dist/data/portfolio_evolution.json'
        for module in (shared,runner):
            root_patch=patch.object(module,'ROOT',self.site);root_patch.start();self.addCleanup(root_patch.stop)

    def run_evolution(self,run_dir=None,**options):
        with redirect_stdout(io.StringIO()):
            return runner.run(self.study,run_dir or self.run_dir,output=self.output,**options)

    def assert_unpublished(self):
        self.assertFalse(self.output.exists())
        self.assertFalse((self.site/'dist/data/portfolio_evolution_runs').exists())
        self.assertFalse((self.site/'dist/data/portfolio_evolutions.json').exists())

    def test_registered_config_has_frozen_five_parents_and_declared_order(self):
        registered=load_study(REGISTERED)
        self.assertEqual(registered['generation']['population_size'],5)
        self.assertEqual([s['phase'] for s in registered['generation']['schedule']],['mutation','mutation','crossover'])
        self.assertEqual(sum(s['proposals'] for s in registered['generation']['schedule']),24)
        self.assertTrue(all('/portfolio_study_runs/' in p['source'] for p in registered['parents']))
        result=subprocess.run([sys.executable,str(ROOT/'engine/evolve.py'),'validate','--study-config',str(REGISTERED)],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['proposals'],24)
        self.assert_unpublished()

    def test_contract_refuses_unknown_operators_mixed_order_seeds_and_budgets(self):
        changes=[(('schema_version',),'1.0'),(('generation','selection'),'monte_carlo'),
                 (('generation','population_size'),3),(('generation','seed'),901),
                 (('bounds','max_proposals'),4),(('bounds','max_run_seconds'),601),
                 (('confirmation','evaluation','seed'),901),(('parents',0,'source'),'../private.json'),
                 (('base_profile','constraints','budget_max_eur'),7.49),
                 (('metrics',),['portfolio.jackpot_probability@v1'])]
        for path,value in changes:
            bad=deepcopy(self.study);cursor=bad
            for part in path[:-1]:cursor=cursor[part]
            cursor[path[-1]]=value
            with self.subTest(path=path),self.assertRaises(ValueError):validate_study(bad)
        bad=deepcopy(self.study);bad['generation']['schedule'].reverse()
        with self.assertRaises(ValueError):validate_study(bad)
        bad=deepcopy(self.study);bad['parents'][1]['content_sha256']=bad['parents'][0]['content_sha256']
        with self.assertRaises(ValueError):validate_study(bad)
        self.assert_unpublished()

    def test_proposals_generations_and_mc_resume_without_early_publication(self):
        partial=self.run_evolution(stop_after_proposals=1)
        self.assertEqual(partial['status'],'generating');self.assertEqual(partial['completed_proposals'],1)
        checkpoint=shared.read_signed(self.run_dir/'generation-checkpoint.json')
        frozen_records=deepcopy(checkpoint['records']);self.assert_unpublished()
        partial=self.run_evolution(stop_after_generations=1)
        self.assertEqual(partial['status'],'generating')
        checkpoint=shared.read_signed(self.run_dir/'generation-checkpoint.json')
        self.assertEqual(len(checkpoint['generations']),1)
        self.assertEqual(checkpoint['records'][:len(frozen_records)],frozen_records)
        self.assert_unpublished()
        partial=self.run_evolution(stop_after_comparison_batches=1)
        self.assertEqual(partial['status'],'comparison_interrupted');self.assertEqual(partial['completed_draws'],16)
        generation=shared.read_signed(self.run_dir/'generation.json')
        self.assertEqual(len(generation['proposals']),5);self.assertEqual(len(generation['generations']),2)
        self.assert_unpublished()
        partial=self.run_evolution(stop_after_confirmation_batches=1)
        self.assertEqual(partial['status'],'confirmation_interrupted');self.assertEqual(partial['completed_draws'],16)
        self.assert_unpublished()
        with self.assertRaises(ValueError):runner.projection(self.study,self.run_dir,shared.read_signed(self.run_dir/'study-run.json'))
        result=self.run_evolution();self.assertEqual(result['status'],'complete')
        dataset=shared.read(self.output);self.assert_dataset(dataset)
        original=self.output.read_bytes();rerun=self.run_evolution()
        self.assertEqual(rerun['run_id'],result['run_id']);self.assertEqual(self.output.read_bytes(),original)
        execution=shared.read_signed(self.run_dir/'study-run.json')
        with redirect_stdout(io.StringIO()):runner.publish(self.study,self.run_dir,execution,self.output)
        self.assertEqual(self.output.read_bytes(),original)

    def assert_dataset(self,dataset):
        self.assertEqual(dataset['origin'],'local_evolution')
        self.assertEqual(dataset['evolution']['proposal_count'],5)
        self.assertEqual(dataset['evolution']['completed_generations'],2)
        self.assertEqual(dataset['evolution']['population_size'],2)
        self.assertGreater(dataset['evolution']['accepted_children'],0)
        available={'portfolio:'+p['content_sha256'] for p in dataset['profiles']}
        children=[p for p in dataset['profiles'] if not p['is_starting_parent']]
        self.assertTrue(children)
        comparison_streams=set();confirmation_streams=set()
        for record in dataset['profiles']:
            self.assertEqual(validate_grids(record['grids'],self.study['base_profile']),[])
            self.assertEqual(record['content_sha256'],content_hash(record['grids']))
            self.assertEqual(record['certificate']['content_sha256'],record['content_sha256'])
            self.assertEqual(record['certificate'],proof_for(record['grids'],self.study['base_profile']))
            self.assertEqual(record['evaluation']['role'],'comparison')
            self.assertEqual(record['evaluation']['seed'],901);self.assertEqual(record['simulation']['draws'],65)
            comparison_streams.add(record['evaluation']['draw_stream_sha256'])
            self.assertLessEqual(set(record['lineage']['parent_ids']),available)
            self.assertNotIn('portfolio:'+record['content_sha256'],record['lineage']['parent_ids'])
            if not record['is_starting_parent']:
                self.assertIn(record['generation']['operator'],('replace_number_v1','swap_numbers_v1','replace_grid_v1','grid_crossover_v1'))
                self.assertTrue(record['lineage']['parent_ids'])
            if record['is_finalist']:
                self.assertFalse(record['is_starting_parent'])
                self.assertEqual(record['confirmation']['evaluation']['role'],'confirmation')
                self.assertEqual(record['confirmation']['evaluation']['seed'],902)
                self.assertEqual(record['confirmation']['simulation']['draws'],65)
                confirmation_streams.add(record['confirmation']['evaluation']['draw_stream_sha256'])
            else:self.assertNotIn('confirmation',record)
        self.assertEqual(len(comparison_streams),1);self.assertEqual(len(confirmation_streams),1)
        self.assertTrue(comparison_streams.isdisjoint(confirmation_streams))
        shared.validate_graph(dataset['graph'])
        self.assertTrue(any(e['type']=='derived_from' for e in dataset['graph']['edges']))
        self.assertEqual(len([n for n in dataset['graph']['nodes'] if n['type']=='selection_run']),2)
        self.assertEqual(dataset['analysis']['selection_basis'],'exact_geometry_only')

    def test_changed_configuration_sources_and_parents_refuse_resume(self):
        self.run_evolution(stop_after_proposals=1)
        with patch.object(runner,'source_signatures',return_value={'altered.py':'a'*64}),self.assertRaises(ValueError):self.run_evolution()
        bad=deepcopy(self.study);bad['title']='Autre étude'
        with self.assertRaises(ValueError):
            with redirect_stdout(io.StringIO()):runner.run(bad,self.run_dir,output=self.output)
        parents=self.site/'dist/data/parents.json';parents.write_text(parents.read_text()+' ')
        with self.assertRaises(ValueError):self.run_evolution()
        self.assert_unpublished()

    def test_new_execution_preserves_archive_and_changes_run_identity(self):
        first=self.run_evolution();first_dataset=shared.read(self.output)
        archive=self.site/'dist/data/portfolio_evolution_runs'/first['run_id'].split(':')[1]/'catalogue.json'
        saved=archive.read_bytes()
        second=self.run_evolution(self.directory/'run-b')
        self.assertNotEqual(first['run_id'],second['run_id'])
        self.assertNotEqual(first_dataset['study_run']['id'],shared.read(self.output)['study_run']['id'])
        self.assertEqual(archive.read_bytes(),saved)
        index=shared.read(self.site/'dist/data/portfolio_evolutions.json')
        self.assertEqual(len(index['studies']),2)

    def test_child_guarantee_is_recomputed_and_never_inherited(self):
        with patch.object(runner,'proof_for',wraps=proof_for) as prove:
            self.run_evolution(stop_after_comparison_batches=1)
        generation=shared.read_signed(self.run_dir/'generation.json')
        self.assertEqual(prove.call_count,len(generation['records']))
        for record in generation['records']:
            self.assertEqual(record['certificate']['content_sha256'],record['content_sha256'])

    def test_unproved_mandatory_child_guarantee_rejects_birth_and_prevents_final_export(self):
        self.study['base_profile']['constraints']['conditional_guarantee']={
            'pool_good_numbers':5,'pool_good_stars':2,'condition_mode':'exactly',
            'required_numbers':0,'required_stars':0,'threshold_mode':'at_least'}
        calls=0
        def refused_child(grids,profile):
            nonlocal calls
            calls+=1;proof=proof_for(grids,profile)
            if calls>2:proof['fulfilled']=False
            return proof
        with patch.object(runner,'proof_for',side_effect=refused_child),self.assertRaises(ValueError):
            self.run_evolution()
        checkpoint=shared.read_signed(self.run_dir/'generation-checkpoint.json')
        self.assertEqual(len(checkpoint['records']),2)
        self.assertTrue(checkpoint['rejected_guarantees'])
        self.assertTrue(all(p['reason']=='requested_guarantee_not_proved' for p in checkpoint['rejected_guarantees']))
        self.assert_unpublished()


if __name__=='__main__':unittest.main()
