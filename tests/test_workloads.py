import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from relay import semantics
from relay.core import RelayError
from relay.limits import count,take
from relay.research import Research, compare, validate_analysis
from test_semantics import fixture,assessment

class WorkloadTests(unittest.TestCase):
    def test_custom_and_all_are_not_silently_capped(self):
        rows=list(range(501))
        self.assertEqual(len(take(rows,100,12,'count')),100)
        self.assertEqual(len(take(rows,'all',12,'count')),501)
        for value in (0,-2,True,1.5,'10'):
            with self.assertRaises(RelayError):count(value,12,'count')
    def test_contract_keeps_more_than_six_entities_and_eight_criteria(self):
        p=semantics.contract({'entities':[{'label':str(i),'definition':'Defined intervention'} for i in range(10)],'factors':[{'key':f'f{i}','label':str(i),'rule':'Same context'} for i in range(15)]})
        self.assertEqual(len(p['entities']),10);self.assertEqual(len(p['factors']),15)
    def test_all_extraction_preserves_more_than_twelve_valid_results(self):
        p=fixture()[0];m=p['metrics'][0]
        rows=[dict(copy.deepcopy(m),method=f'Group {i}') for i in range(20)]
        validate_analysis(p,{'metrics':rows},m['quote'])
        self.assertEqual(len(p['metrics']),20)
        self.assertIn('Extract all relevant results',semantics.extraction_system(p['protocol'],'all'))
        self.assertIn('Extract up to 25',semantics.extraction_system(p['protocol'],25))
    def test_all_comparisons_runs_every_pending_pair_in_small_calls(self):
        with tempfile.TemporaryDirectory() as d:
            r=Research(Path(d));papers=fixture()
            for p in papers:p['metrics']=[dict(copy.deepcopy(p['metrics'][0]),id=str(i)) for i in range(5)]
            p={'id':'x','papers':papers,'protocol':papers[0]['protocol'],'revision':1,'model':'test','comparisonLimit':'all'}
            batches=[]
            def ask(project,system,payload,*args):
                batches.append(len(payload['pairs']))
                return {'assessments':[dict(assessment(pair),pair=pair['id']) for pair in payload['pairs']]}
            with patch.object(r,'llm',side_effect=ask),patch.object(r,'event'),patch.object(r,'checkpoint'):
                r.audit_comparisons(p)
            self.assertEqual(sum(batches),25);self.assertLessEqual(max(batches),3)
    def test_saved_old_evidence_requires_migration_not_old_comparison(self):
        old=[{'id':'old','metrics':[{'id':'1','method':'A','value':'1','protocol':{}},{'id':'2','method':'B','value':'2','protocol':{}}]}]
        original=copy.deepcopy(old);result=compare(old)
        self.assertTrue(result['requiresContract']);self.assertEqual(result['pairs'],[]);self.assertEqual(old,original)
    def test_correction_invalidates_generic_assessment_and_draft_without_auto_approval(self):
        with tempfile.TemporaryDirectory() as d:
            r=Research(Path(d));papers=fixture();pair=semantics.candidate_pairs(papers)[1][0]
            record=semantics.validate_assessment(pair,assessment(pair),'test');record['reviewed']=True
            p={'id':'a'*16,'papers':papers,'protocol':papers[0]['protocol'],'revision':1,'status':'review','events':[],
               'comparisonAssessments':{pair['id']:record},'draft':{'comparisons':[{'id':'claim','text':'Comparison conclusion','pairs':[pair['id']],'citations':['p1']}]}}
            r.projects=[p]
            with patch.object(r,'source',return_value=papers[0]['metrics'][0]['quote']),patch.object(r,'checkpoint',return_value={'id':'before'}):
                correction=r.correct(p,papers[0],papers[0]['metrics'][0],{'factor_population':'children'},'researcher correction','Verified new source context')
            self.assertEqual(correction['comparisonChanges'][0]['after'],'insufficient')
            self.assertTrue(p['draft']['comparisons'][0]['stale'])
            self.assertTrue(r.outcomes(p)[pair['id']]['stale'])
    def test_start_persists_custom_scope_and_does_not_truncate_seed_list(self):
        with tempfile.TemporaryDirectory() as d:
            r=Research(Path(d))
            with patch('relay.research.models',return_value={'models':['test']}),patch('relay.research.threading.Thread'),patch.object(r,'checkpoint'):
                result=r.start({'hypothesis':'Compare these interventions under matched conditions','provider':'nebius','model':'test','seeds':[f'2401.{i:05d}' for i in range(20)],'paperLimit':'all','resultLimit':25,'comparisonLimit':'all'})
            p=r.get(result['id'])
            self.assertEqual(len(p['seeds']),20)
            self.assertEqual((p['paperLimit'],p['resultLimit'],p['comparisonLimit']),('all',25,'all'))
    def test_all_selected_fields_are_batched_not_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            r=Research(Path(d));papers=fixture();protocol=papers[0]['protocol']
            protocol['factors']=[{'key':f'factor_f{i}','label':str(i),'role':'match','rule':'Match'} for i in range(17)]
            m=papers[0]['metrics'][0];m['protocol']=protocol
            p={'id':'x','papers':papers,'protocol':protocol,'revision':1,'status':'review'};r.projects=[p]
            fields=[f['key'] for f in protocol['factors']]
            with patch.object(r,'launch') as thread,patch.object(r,'checkpoint'):
                r.investigate({'id':'x','revision':1,'targets':[{'paper':papers[0]['id'],'metric':m['id'],'fields':fields}]})
            targets=thread.call_args.args[2][1]
            self.assertEqual([f for _,_,batch in targets for f in batch],fields)
            self.assertLessEqual(max(len(batch) for _,_,batch in targets),6)
    def test_custom_discovery_fetches_more_than_one_page(self):
        import json
        from relay.research import discover
        pages=[{'results':[{'id':f'https://openalex.org/W{i}','display_name':str(i)} for i in range(start,start+200)]} for start in (0,200)]
        with patch('relay.research.fetch',side_effect=[json.dumps(p) for p in pages]) as fetch:
            papers=discover('a research question',250)
        self.assertEqual(len(papers),250);self.assertEqual(fetch.call_count,2)
        self.assertIn('page=2',fetch.call_args.args[0]);self.assertIn('per-page=200',fetch.call_args.args[0])
