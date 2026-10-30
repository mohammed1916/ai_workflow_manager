import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from relay.desk import load_study, overview, evaluation
from relay.research import Research
from relay.core import RelayError

ROOT=Path(__file__).resolve().parents[1]

class SavedStudyTests(unittest.TestCase):
    def test_real_evaluation_records_ignore_apple_resource_sidecars(self):
        result=evaluation(ROOT)
        self.assertGreater(len(result['runs']),0)
        self.assertEqual(result['runs'][-1]['split'],'heldout')

    def test_import_preserves_live_provenance_and_real_checkpoints(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);shutil.copytree(ROOT/'data',root/'data');(root/'eval/.cache').mkdir(parents=True)
            data=json.loads((root/'data/research/after-correction.json').read_text())
            for p in data['papers']:
                cached=ROOT/'eval/.cache'/(p['arxiv']+'.html')
                if not cached.exists():self.skipTest('Local source cache not available; import retrieves public sources on first use')
                shutil.copyfile(cached,root/'eval/.cache'/cached.name)
            r=Research(root);result=load_study(root,r);p=r.get(result['id'])
            self.assertEqual(p['provider'],'nebius');self.assertEqual(len(p['execution']),2)
            self.assertEqual(len(p['calls']),len(data['calls']));self.assertFalse(p['draftReviewed'])
            self.assertTrue(all(x.get('reviewActor')=='agent' for x in p['papers'] if x['reviewed']))
            for n in p['execution']:r.get_checkpoint(p['id'],n['id'])
            before=copy.deepcopy(p);self.assertFalse(load_study(root,r)['loaded']);self.assertEqual(before,p)
            branch=r.branch({'id':p['id'],'node':p['execution'][0]['id'],'next':'snapshot','name':'Before correction'})
            self.assertEqual(r.get(branch['id'])['parentProject'],p['id'])
            self.assertGreater(len(r.source(p['papers'][0])),3000)
            self.assertTrue(p['tex']);self.assertTrue(p['bib'])
            self.assertEqual(overview(root,r)['featured']['id'],p['id'])
    def test_changed_source_refuses_import_without_changing_projects(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);shutil.copytree(ROOT/'data',root/'data');(root/'eval/.cache').mkdir(parents=True)
            d=json.loads((root/'data/research/after-correction.json').read_text())
            (root/'eval/.cache'/(d['papers'][0]['arxiv']+'.html')).write_text('<p>Changed source</p>')
            r=Research(root)
            with self.assertRaises(RelayError) as e:load_study(root,r)
            self.assertEqual(e.exception.code,'SOURCE_CHANGED');self.assertEqual(r.projects,[])

    def test_guided_recording_loads_without_inference_and_preserves_checkpoints(self):
        from relay.desk import load_validation
        from relay.research import compare
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'data/research').mkdir(parents=True)
            shutil.copyfile(ROOT/'data/research/guided-study.json',root/'data/research/guided-study.json')
            r=Research(root)
            with patch.object(r,'llm',side_effect=AssertionError('Recorded opening must not call inference')):
                result=load_validation(root,r,'guided-study.json')
            p=r.get(result['id']);summary=compare(p['papers'],assessments=p['comparisonAssessments'])['summary']
            self.assertEqual(summary,overview(root,r)['guidedStudy']['summary'])
            self.assertGreaterEqual(summary['comparable'],2)
            self.assertTrue(all(not m.get('verified') for paper in p['papers'] for m in paper['metrics']))
            for node in p['execution']:r.get_checkpoint(p['id'],node['id'])
            self.assertTrue(load_validation(root,r,'guided-study.json')['existing'])
    def test_parallel_recording_preserves_receipts_and_uncertainty(self):
        from relay.desk import load_validation
        from relay.research import compare
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'data/research').mkdir(parents=True)
            shutil.copyfile(ROOT/'data/research/parallel-study.json',root/'data/research/parallel-study.json')
            r=Research(root)
            with patch.object(r,'llm',side_effect=AssertionError('No inference on recorded open')):
                result=load_validation(root,r,'parallel-study.json')
            p=r.get(result['id'])
            self.assertEqual(sum(len(x['metrics']) for x in p['papers']),12)
            self.assertEqual(compare(p['papers'],assessments=p['comparisonAssessments'])['summary'],overview(root,r)['parallelStudy']['summary'])
            self.assertEqual(len(p['paperWorkers']),2)
            self.assertTrue(all(w['status']=='returned' for w in p['paperWorkers'].values()))
            for node in p['execution']:r.get_checkpoint(p['id'],node['id'])
            self.assertTrue(load_validation(root,r,'parallel-study.json')['existing'])
