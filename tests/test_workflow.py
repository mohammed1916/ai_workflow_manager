import copy, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from relay.research import Research, claim_status, controls, manuscript
from relay.evidence import compare
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

    def test_text_split_conflict_then_accepted_code_evidence_makes_comparison_comparable(self):
        self.assertEqual(self.pair()['outcome'], 'incompatible')
        self.p['draft'] = {'abstract': 'A', 'study': 'S', 'relatedWork': [{'id': 'rw1', 'text': 'MTGNN reports results.', 'citations': ['WB']}],
                           'comparisons': [{'id': 'cmp1', 'text': 'The MTGNN and Graph WaveNet numbers cannot be compared.', 'pairs': [self.pair()['id']], 'citations': ['WA', 'WB']}], 'pairTable': []}
        self.p['proposals'] = [{'id': 'prop1', 'paper': 'WB', 'metric': 'mb', 'field': 'split', 'value': '70/10/20', 'quote': 'num_test = round(num_samples * 0.2)\nnum_train = round(num_samples * 0.7)',
                                'origin': 'repository', 'location': 'generate_training_data.py@abc', 'url': 'https://github.com/nnzhan/MTGNN', 'explanation': 'Code uses 70/10/20.', 'status': 'pending'}]
        result = self.r.update({'id': self.p['id'], 'revision': self.p['revision'], 'action': 'proposal', 'proposal': 'prop1', 'decision': 'accept'})
        correction = self.p['corrections'][0]
        self.assertEqual(result['correction'], correction['id'])
        self.assertEqual(self.p['papers'][1]['metrics'][0]['split'], '70/10/20')
        self.assertEqual(self.p['papers'][1]['metrics'][0]['checks']['support']['split'], 'repository')
        self.assertEqual(correction['comparisonChanges'][0]['before'], 'incompatible'); self.assertEqual(correction['comparisonChanges'][0]['after'], 'comparable')
        self.assertEqual({c['id'] for c in correction['staleClaims']}, {'rw1', 'cmp1'})
        self.assertTrue(self.p['draft']['comparisons'][0]['stale']); self.assertEqual(self.pair()['outcome'], 'comparable')
        # The pre-correction state remains available as an independent branch.
        branch = self.r.get(self.r.branch({'id': self.p['id'], 'node': correction['beforeNode'], 'name': 'Before correction'})['id'])
        self.assertEqual(branch['papers'][1]['metrics'][0]['split'], '70/20/10')
        self.assertEqual(compare(branch['papers'])['pairs'][0]['outcome'], 'incompatible')

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

    def test_claim_status_requires_comparable_pair_for_superiority(self):
        pairs = {x['id']: x for x in compare(self.p['papers'])['pairs']}
        pid = next(iter(pairs))
        self.assertEqual(claim_status('MTGNN outperforms Graph WaveNet.', [pid], pairs), 'unsupported')
        self.assertEqual(claim_status('MTGNN outperforms Graph WaveNet.', [], pairs), 'unsupported')
        self.assertEqual(claim_status('The MTGNN authors report that it outperforms prior work.', [], pairs), 'attributed')
        self.assertEqual(claim_status('Both use METR-LA.', [pid], pairs), 'descriptive')

    def test_manuscript_includes_outcome_table_and_controls(self):
        pairs = compare(self.p['papers'])['pairs']
        d = {'abstract': 'A', 'study': 'S', 'relatedWork': [{'text': 'R', 'citations': ['WA']}], 'comparisons': [{'text': 'C & D', 'citations': ['WA', 'WB']}],
             'pairTable': self.r.pair_table(pairs), 'controls': controls(pairs)}
        tex, bib = manuscript(self.p, d)
        self.assertIn(r'\section{Evidence assessment}', tex); self.assertIn('incompatible', tex); self.assertIn('Controls required', tex); self.assertIn(r'C \& D', tex)

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

    def test_targeted_check_reads_appendix_and_makes_original_value_incompatible(self):
        from relay.research import target_context
        source = ('We use a temporal 70/10/20 split for training, validation, and testing.\nTable 1: Forecasting error (METR-LA).\n| | Metric | Graph WaveNet | GTS\n| 60 min | MAE | 3.53 | 2.99\n'
                  'Appendix D Updates of Tables 1, 2, and 3\nOur implementation calculated the evaluation metrics MAE/RMSE/MAPE in a manner slightly different from that used to report the results of DCRNN in the official publication.')
        seen = {}
        def ask(system, payload, kind):
            seen.update(payload)
            return {'method': 'GTS', 'name': 'MAE', 'value': '2.99', 'direction': 'lower', 'dataset': 'METR-LA', 'split': '70/10/20', 'horizon': '60 minutes', 'aggregation': 'single horizon',
                    'metricDefinition': 'calculated in a manner slightly different from that used to report the official DCRNN results', 'provenance': 'own', 'locator': 'Table 1', 'quote': '2.99',
                    'evidence': {'metricDefinition': 'calculated the evaluation metrics MAE/RMSE/MAPE in a manner slightly different from that used to report the results of DCRNN in the official publication'}}
        m = target_context(ask, 'WG', 'GTS', source, '2.99')
        self.assertEqual(seen['cell']['path'], '60 min / MAE / GTS'); self.assertTrue(any('Appendix' in x['location'] or 'manner' in x['text'] for x in seen['passages']))
        self.assertEqual(m['quote'], '| 60 min | MAE | 3.53 | 2.99'); self.assertEqual(m['checks']['support']['metricDefinition'], 'quoted')
        paper = {'id': 'WG', 'title': 'GTS', 'metrics': [m]}
        pair = compare([self.p['papers'][0], paper])['pairs'][0]
        self.assertEqual(pair['outcome'], 'incompatible'); self.assertIn('computed differently', pair['explanation'][0])
        with self.assertRaises(RelayError): target_context(ask, 'WG', 'GTS', source, '9.99')

    def test_source_store_is_content_addressed(self):
        paper = {'_full': 'Full text ' * 10000}
        self.r.store_source(paper)
        self.assertEqual(self.r.source(paper), 'Full text ' * 10000); self.assertEqual(len(paper['evidence']), 65000)
        (self.root / '.relay/sources' / (paper['sourceRef'] + '.txt')).write_text('tampered')
        self.assertEqual(self.r.source(paper), paper['evidence'])


if __name__ == '__main__': unittest.main()
