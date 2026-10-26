import copy, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from relay.research import Research
from relay.core import RelayError

class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.r=Research(self.root)
        self.p={'id':'a'*16,'hypothesis':'Do graph models outperform attention models?','provider':'ollama','model':'gpt-oss:120b','created':'2026-10-26T00:00:00Z','status':'review','revision':1,'tokens':40,'events':[],
                'papers':[{'id':'W1','title':'A paper','authors':[],'year':2024,'url':'https://example.org','evidence':'Original evidence','abstract':'Original abstract','metrics':[],'reviewed':True}],
                'suggestions':[],'tex':'Original manuscript','bib':'Original bibliography','draftReviewed':True,'compile':{'ok':True,'hash':'0'*16}}
        self.r.projects=[self.p];self.node=self.r.checkpoint(self.p,'retrieval','Retrieved evidence')
    def tearDown(self): self.tmp.cleanup()
    def branch(self,**extra):return self.r.branch({'id':self.p['id'],'node':self.node['id'],**extra})
    def test_checkpoint_is_immutable_and_branches_old_state(self):
        self.p['tex']='Later manuscript';self.p['papers'][0]['evidence']='Later evidence';self.p['revision']=2
        self.r.checkpoint(self.p,'edit','Later edit')
        child=self.r.get(self.branch()['id'])
        self.assertEqual(child['tex'],'Original manuscript');self.assertEqual(child['papers'][0]['evidence'],'Original evidence')
        self.assertEqual(self.p['tex'],'Later manuscript');self.assertEqual(child['parentNode'],self.node['id'])
    def test_copy_has_no_network_call_and_no_parent_changes(self):
        before=copy.deepcopy(self.p)
        with patch('relay.executions.models',side_effect=AssertionError('No network for snapshot')): child=self.r.get(self.branch()['id'])
        child['papers'][0]['title']='Changed only in branch'
        self.assertEqual(self.p,before);self.assertEqual(child['tokens'],0);self.assertEqual(child['inheritedTokens'],40)
        self.assertNotIn('compile',child);self.assertFalse(child['draftReviewed'])
    def test_changed_hypothesis_invalidates_fit_and_draft(self):
        child=self.r.get(self.branch(hypothesis='Can forecasting remain robust to sensor outages?')['id'])
        self.assertEqual(child['tex'],'');self.assertTrue(child['papers'][0]['assessmentStale']);self.assertEqual(self.p['tex'],'Original manuscript')
    def test_tampered_checkpoint_is_blocked(self):
        path=self.root/'.relay/checkpoints'/self.p['id']/(self.node['id']+'.json');path.write_text('{}')
        with self.assertRaises(RelayError) as e:self.branch()
        self.assertEqual(e.exception.code,'CHECKPOINT_CHANGED');self.assertEqual(len(self.r.projects),1)
    def test_unknown_node_and_traversal_are_rejected(self):
        with self.assertRaises(RelayError):self.r.get_checkpoint(self.p['id'],'../../state')
        with self.assertRaises(RelayError):self.r.get_checkpoint('../state',self.node['id'])
    def test_checkpoint_inspection_excludes_full_evidence(self):
        view=self.r.inspect_checkpoint(self.p['id'],self.node['id'])
        self.assertNotIn('evidence',view['snapshot']['papers'][0])
        self.assertEqual(self.r.get_checkpoint(self.p['id'],self.node['id'])[1]['papers'][0]['evidence'],'Original evidence')
    def test_unsupported_continuation_is_rejected(self):
        with self.assertRaises(RelayError):self.branch(next='shell')
        self.assertEqual(len(self.r.projects),1)
    def test_changed_hypothesis_cannot_reuse_old_fit_for_draft(self):
        with patch('relay.executions.models',return_value={'models':['gpt-oss:120b']}):
            with self.assertRaises(RelayError) as e:self.branch(next='draft',hypothesis='Can forecasting remain robust to sensor outages?')
        self.assertEqual(e.exception.code,'REASSESS_REQUIRED')
    def test_network_failure_does_not_create_partial_branch(self):
        with patch('relay.executions.models',side_effect=RelayError('PROVIDER_ERROR','Unavailable')):
            with self.assertRaises(RelayError):self.branch(next='synthesize')
        self.assertEqual(len(self.r.projects),1)
    def test_restart_preserves_graph_and_branches(self):
        child=self.r.get(self.branch()['id']);count=len(self.p['execution']);r=Research(self.root)
        self.assertEqual(len(r.get(self.p['id'])['execution']),count);self.assertEqual(r.get(child['id'])['parentNode'],self.node['id'])
    def test_failed_continuation_records_failure_and_allows_fork(self):
        child=self.r.get(self.branch()['id'])
        with patch.object(self.r,'synthesize',side_effect=ValueError('Controlled test failure')):self.r.continue_branch(child,'synthesize')
        self.assertEqual(child['status'],'error');self.assertEqual(child['execution'][-1]['status'],'failed')
        sibling=self.r.branch({'id':child['id'],'node':child['execution'][0]['id']})
        self.assertEqual(self.r.get(sibling['id'])['status'],'review')
    def test_legacy_migration_records_only_known_state(self):
        p=copy.deepcopy(self.p);p.pop('execution');self.r.projects=[p];self.r.save()
        r=Research(self.root);self.assertEqual(len(r.projects[0]['execution']),1);self.assertEqual(r.projects[0]['execution'][0]['kind'],'import')

if __name__=='__main__':unittest.main()
