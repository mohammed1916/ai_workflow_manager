import copy, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from relay.research import Research, claim_status, controls, manuscript
from relay.research import compare
from relay.core import RelayError

SOURCE_A = ('Experiments. We use 70% of data for training, 10% for validation and 20% for testing. Missing values are excluded.\n'
            'Table 2: Results on METR-LA.\n| Model | 60 min\n| Model | MAE\n| Graph WaveNet | 3.53')
SOURCE_B = ('Setup. The datasets are split into a training set (70%), validation set (20%), and test set (10%).\n'
            'Table 3: Multi-step results on METR-LA.\n| Model | Horizon 12\n| Model | MAE\n| MTGNN | 3.49\nThe code is available at https://github.com/nnzhan/MTGNN.')


def metric(**kw):
    m = {'id': kw.pop('id'), 'name': 'MAE', 'value': '3.53', 'unit': 'mph', 'direction': 'lower', 'method': 'Graph WaveNet', 'dataset': 'METR-LA', 'datasetVersion': 'unknown',
         'split': '70/10/20', 'horizon': '60 minutes', 'aggregation': 'single horizon', 'preprocessing': 'unknown', 'metricDefinition': 'masked', 'provenance': 'own',
         'citedFrom': 'unknown', 'locator': 'Table 2', 'quote': '| Graph WaveNet | 3.53', 'verified': True, 'evidence': {}, 'history': []}
    m.update(kw); return m


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name); self.r = Research(self.root)
        a = {'id': 'WA', 'title': 'Graph WaveNet', 'authors': ['A'], 'year': 2019, 'url': 'https://example.org/a', 'abstract': '', 'evidence': SOURCE_A, 'evidenceKind': 'test', 'reviewed': True,
             'metrics': [metric(id='ma')]}
        b = {'id': 'WB', 'title': 'MTGNN', 'authors': ['B'], 'year': 2020, 'url': 'https://example.org/b', 'abstract': '', 'evidence': SOURCE_B, 'evidenceKind': 'test', 'reviewed': True,
             'metrics': [metric(id='mb', method='MTGNN', value='3.49', split='70/20/10', horizon='60 minutes (horizon 12)', metricDefinition='unknown', locator='Table 3', quote='| MTGNN | 3.49')]}
        self.p = {'id': 'b' * 16, 'hypothesis': 'Which METR-LA baselines can be compared at 60 minutes?', 'provider': 'nebius', 'model': 'test-model', 'created': '2026-10-26T00:00:00Z',
                  'status': 'review', 'revision': 1, 'tokens': 0, 'events': [], 'papers': [a, b], 'suggestions': [], 'tex': '', 'bib': '', 'proposals': [], 'corrections': [], 'calls': []}
        self.r.projects = [self.p]; self.r.checkpoint(self.p, 'retrieval', 'Retrieved')

    def test_structured_draft_amendment_keeps_agent_attribution_and_invalidates_pdf(self):
        self.p['compile']={'ok':True,'hash':'old'}
        d={'abstract':'Proposed study; no experiments performed.','study':'Use one shared protocol.',
           'relatedWork':[{'text':'Graph WaveNet reports experimental results.','citations':['WA']}], 'comparisons':[]}
        self.r.update({'id':self.p['id'],'revision':1,'action':'amend-draft','actor':'agent','draft':d,'note':'Checked the source table and protocol.'})
        self.assertNotIn('compile',self.p);self.assertFalse(self.p['draftReviewed'])
        self.assertEqual(self.p['draftEdits'][-1]['actor'],'agent');self.assertIn('Graph WaveNet',self.p['tex'])
        snapshot=self.r.get_checkpoint(self.p['id'],self.p['execution'][-1]['id'])[1]
        self.assertEqual(snapshot['draftEdits'][-1]['actor'],'agent')

    def test_invalid_manuscript_citations_do_not_overwrite_saved_draft(self):
        self.p['tex']='Preserved'
        with self.assertRaises(ValueError):
            self.r.update({'id':self.p['id'],'revision':1,'action':'amend-draft','draft':{'abstract':'A','relatedWork':[{'text':'Claim','citations':['fake']}]},'note':'Checked source.'})
        self.assertEqual(self.p['tex'],'Preserved');self.assertEqual(self.p['revision'],1)

    def tearDown(self): self.tmp.cleanup()

    def pair(self): return compare(self.p['papers'])['pairs'][0]


    def test_researcher_correction_requires_reason_and_reports_no_change(self):
        with self.assertRaises(RelayError) as e:
            self.r.update({'id': self.p['id'], 'revision': self.p['revision'], 'action': 'correct', 'paper': 'WB', 'metric': 'mb', 'field': 'split', 'value': '70/10/20', 'note': ''})
        self.assertEqual(e.exception.code, 'NOTE_REQUIRED')
        with self.assertRaises(RelayError) as e:
            self.r.update({'id': self.p['id'], 'revision': self.p['revision'], 'action': 'correct', 'paper': 'WB', 'metric': 'mb', 'field': 'value', 'value': '1', 'note': 'checked table'})
        self.assertEqual(e.exception.code, 'INVALID_FIELD')
        self.r.update({'id': self.p['id'], 'revision': self.p['revision'], 'action': 'correct', 'paper': 'WB', 'metric': 'mb', 'field': 'split', 'value': '70/10/20', 'note': 'Matches the DCRNN split the paper says it follows.'})
        m = self.p['papers'][1]['metrics'][0]
        self.assertEqual(m['history'][-1]['before'], '70/20/10'); self.assertEqual(m['evidence']['split']['origin'], 'researcher')

    def test_proposal_that_restates_current_value_is_dropped(self):
        answer = {'proposals': [{'field': 'split', 'value': '70/20/10', 'passage': 'P1', 'quote': 'training set (70%), validation set (20%), and test set (10%)', 'explanation': 'same'}]}
        with patch.object(self.r, 'llm', return_value=answer):
            self.r.run_investigation(self.p, [('WB', 'mb', ['split'])], False, None)
        self.assertEqual(self.p['proposals'], [])

    def test_rejected_proposal_changes_nothing(self):
        self.p['proposals'] = [{'id': 'p2', 'paper': 'WB', 'metric': 'mb', 'field': 'split', 'value': '70/10/20', 'quote': 'q', 'origin': 'paper', 'location': '', 'url': '', 'explanation': '', 'status': 'pending'}]
        self.r.update({'id': self.p['id'], 'revision': self.p['revision'], 'action': 'proposal', 'proposal': 'p2', 'decision': 'reject'})
        self.assertEqual(self.p['papers'][1]['metrics'][0]['split'], '70/20/10'); self.assertEqual(self.p['corrections'], [])

    def test_investigation_keeps_only_quotes_copied_from_passages(self):
        answer = {'proposals': [{'field': 'split', 'value': '70/20/10', 'passage': 'P1', 'quote': 'training set (70%), validation set (20%), and test set (10%)', 'explanation': 'stated'},
                                {'field': 'split', 'value': '70/10/20', 'passage': 'P1', 'quote': 'we use a 7:1:2 split', 'explanation': 'invented'}], 'unresolved': []}
        self.p['papers'][1]['metrics'][0]['split'] = 'unknown'
        with patch.object(self.r, 'llm', return_value=answer):
            self.r.run_investigation(self.p, [('WB', 'mb', ['split'])], False, None)
        self.assertEqual(len(self.p['proposals']), 1); self.assertEqual(self.p['proposals'][0]['value'], '70/20/10')
        self.assertEqual(self.p['status'], 'review'); self.assertEqual(self.p['execution'][-1]['kind'], 'investigation')

    def test_regeneration_rewrites_only_stale_paragraphs(self):
        from test_semantics import fixture
        generic=fixture()
        for old,new in zip(self.p['papers'],generic):old['metrics']=new['metrics']
        pid = self.pair()['id']
        self.p['draft'] = {'abstract': 'A', 'study': 'S', 'pairTable': [], 'relatedWork': [{'id': 'rw1', 'text': 'Kept paragraph.', 'citations': ['WA']}],
                           'comparisons': [{'id': 'cmp1', 'text': 'Old claim.', 'pairs': [pid], 'citations': ['WA', 'WB'], 'stale': True, 'staleReason': 'changed'}]}
        self.p['corrections'] = [{'id': 'c1', 'status': 'stale', 'result': 'MTGNN', 'changes': [], 'comparisonChanges': []}]
        with patch.object(self.r, 'llm', return_value={'paragraphs': [{'id': 'cmp1', 'text': 'New grounded claim.', 'pairs': [pid], 'citations': ['WA', 'WB']}, {'id': 'rw1', 'text': 'Should not replace.'}]}):
            self.r.rewrite(self.p)
        self.assertEqual(self.p['draft']['relatedWork'][0]['text'], 'Kept paragraph.')
        self.assertEqual(self.p['draft']['comparisons'][0]['text'], 'New grounded claim.'); self.assertEqual(self.p['draft']['comparisons'][0]['previous'], 'Old claim.')
        self.assertEqual(self.p['corrections'][0]['status'], 'regenerated'); self.assertIn('Evidence assessment', self.p['tex'])

    def test_draft_drops_citations_outside_reviewed_set(self):
        d = {'abstract': 'A', 'study': 'S', 'relatedWork': [{'text': 'Keeps valid.', 'citations': ['WA', 'arXiv999']}, {'text': 'Only invalid.', 'citations': ['nope']}], 'comparisons': []}
        self.r.check_draft(d, self.p['papers'], [])
        self.assertEqual([i['citations'] for i in d['relatedWork']], [['WA']])
        with self.assertRaises(ValueError): self.r.check_draft({'abstract': 'A', 'relatedWork': [{'text': 'x', 'citations': ['nope']}]}, self.p['papers'], [])



    def test_provider_retry_and_json_repair_are_recorded(self):
        from relay.core import RelayError as E
        busy = E('PROVIDER_ERROR', 'HTTP 503'); busy.provider_status = 503
        responses = [busy, ('not json', {'total_tokens': 5}), ('{"ok": 1}', {'total_tokens': 7})]
        def fake(*a, **k):
            r = responses.pop(0)
            if isinstance(r, Exception): raise r
            return r
        with patch('relay.research.complete', side_effect=fake), patch('relay.research.time.sleep'):
            self.assertEqual(self.r.llm(self.p, 'sys', {}, 'test'), {'ok': 1})
        call = self.p['calls'][-1]
        self.assertEqual(call['attempts'], 3); self.assertTrue(call['repaired']); self.assertEqual(call['totalTokens'], 12); self.assertTrue(call['ok'])

    def test_permanent_provider_error_is_not_retried(self):
        from relay.core import RelayError as E
        denied = E('PROVIDER_ERROR', 'HTTP 401'); denied.provider_status = 401
        with patch('relay.research.complete', side_effect=denied):
            with self.assertRaises(E): self.r.llm(self.p, 'sys', {}, 'test')
        self.assertEqual(self.p['calls'][-1]['attempts'], 1); self.assertFalse(self.p['calls'][-1]['ok'])


    def test_source_store_is_content_addressed(self):
        paper = {'_full': 'Full text ' * 10000}
        self.r.store_source(paper)
        self.assertEqual(self.r.source(paper), 'Full text ' * 10000); self.assertEqual(len(paper['evidence']), 65000)
        (self.root / '.relay/sources' / (paper['sourceRef'] + '.txt')).write_text('tampered')
        self.assertEqual(self.r.source(paper), paper['evidence'])


if __name__ == '__main__': unittest.main()
