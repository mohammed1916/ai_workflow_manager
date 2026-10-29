import copy
import unittest
from relay.protocol import contract
from relay.evidence import compare_pair, compare, check_metric, metric_key
from relay.research import validate_analysis


def vision(**changes):
    p = contract({'task':'classification','factors':[{'key':'resolution','label':'Input resolution'}]})
    r = dict(paper='a',title='Study',metric='m',verified=False,method='ViT',dataset='ImageNet-1K',datasetVersion='unknown',split='validation set',horizon='unknown',aggregation='unknown',metricDefinition='single-crop top-1 accuracy',provenance='own',citedFrom='unknown',locator='Table 1',name='Top-1 accuracy',value='80.0',unit='%',direction='higher',quote='ViT reports 80.0 accuracy.',protocol=p,factor_resolution='224 pixels',preprocessing='unknown')
    r.update(changes)
    return r

class ProtocolTests(unittest.TestCase):
    def test_classification_does_not_require_forecast_horizon(self):
        result=compare_pair(vision(),vision(paper='b',value='81.0'))
        self.assertEqual(result['outcome'],'comparable')
        self.assertEqual(result['favours'],'b')
        self.assertNotIn('horizon',[c['field'] for c in result['checks']])
    def test_resolution_conflict_is_not_hidden_by_unknown_horizon(self):
        self.assertEqual(compare_pair(vision(),vision(paper='b',factor_resolution='384 pixels'))['outcome'],'incompatible')
    def test_unknown_factor_stays_insufficient(self):
        self.assertEqual(compare_pair(vision(),vision(paper='b',factor_resolution='unknown'))['outcome'],'insufficient')
    def test_wording_difference_is_not_a_proven_mismatch(self):
        self.assertEqual(compare_pair(vision(),vision(paper='b',factor_resolution='224 by 224'))['outcome'],'insufficient')
    def test_top1_top5_error_and_unknown_are_not_paired(self):
        self.assertNotEqual(metric_key('top-1 accuracy'),metric_key('top-5 accuracy'))
        self.assertNotEqual(metric_key('top-1 error'),metric_key('top-1 accuracy'))
        a=vision(name='unknown'); b=vision(paper='b')
        self.assertEqual(compare([{'id':'a','metrics':[a]},{'id':'b','metrics':[b]}])['pairs'],[])
    def test_factor_requires_its_own_source_quote(self):
        m=vision(evidence={'factor_resolution':{'quote':'80.0 was reported at 384 pixels.'}})
        check_metric(m,'80.0 was reported at 384 pixels. ViT reports 80.0 accuracy.')
        self.assertEqual(m['factor_resolution'],'unknown')
    def test_named_partition_and_factor_survive_extraction(self):
        source='We evaluate on the validation set at 224 pixels. ViT reports 80.0 accuracy.'
        m=vision(evidence={'split':'validation set','factor_resolution':'224 pixels'})
        paper={'id':'a','protocol':m['protocol'],'evidence':source}
        validate_analysis(paper,{'metrics':[m]})
        self.assertEqual(paper['metrics'][0]['split'],'validation set')
        self.assertEqual(paper['metrics'][0]['factor_resolution'],'224 pixels')
        self.assertNotIn('horizon',paper['metrics'][0]['missing'])
    def test_general_contract_has_dynamic_fields_not_vision_presets(self):
        p=contract({'task':'general','factors':[{'key':'population','label':'Study population'}]})
        self.assertEqual(p['factors'][0]['key'],'factor_population')

    def test_factor_correction_changes_comparison_and_marks_claim_stale(self):
        import tempfile
        from pathlib import Path
        from relay.research import Research
        with tempfile.TemporaryDirectory() as d:
            r=Research(Path(d)); a,b=vision(id='m1'),vision(paper='b',id='m2',factor_resolution='384 pixels')
            for m in (a,b):
                m['evidence']={k:{'origin':'researcher','quote':'Verified source context.'} for k in ('dataset','method','split','metricDefinition','factor_resolution')}
            papers=[{'id':'a','title':'A','metrics':[a],'evidence':a['quote']},{'id':'b','title':'B','metrics':[b],'evidence':b['quote']}]
            p={'id':'p','papers':papers,'revision':1,'status':'review','events':[],'draft':{'relatedWork':[{'id':'claim','text':'Comparison claim','citations':['b']}],'comparisons':[]}}
            r.projects=[p]
            self.assertEqual(r.outcomes(p)[next(iter(r.outcomes(p)))]['outcome'],'incompatible')
            change=r.correct(p,papers[1],b,{'factor_resolution':'224 pixels'},'researcher review','Table caption states 224 pixels.')
            self.assertTrue(change['comparisonChanges'])
            self.assertEqual(change['comparisonChanges'][0]['after'],'comparable')
            self.assertTrue(p['draft']['relatedWork'][0]['stale'])

    def test_branch_reextract_calls_extraction_with_new_plan(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from relay.research import Research
        with tempfile.TemporaryDirectory() as d:
            r=Research(Path(d)); paper={'id':'a','title':'A','metrics':[vision()],'reviewed':True}
            p={'id':'p','papers':[paper],'revision':1,'status':'discovering','events':[],'proposals':[{}],'corrections':[{}]}
            r.projects=[p]
            with patch.object(r,'plan_protocol') as plan, patch.object(r,'assess') as extract, patch.object(r,'synthesize'):
                r.continue_branch(p,'extract')
            plan.assert_called_once_with(p); extract.assert_called_once_with(p,paper)
            self.assertFalse(paper['reviewed']); self.assertEqual(p['status'],'review')

    def test_tavily_initial_discovery_and_seed_only(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from relay.research import Research
        for seed_only in (False,True):
            with self.subTest(seed_only=seed_only), tempfile.TemporaryDirectory() as d:
                r=Research(Path(d)); paper={'id':'a','title':'Vision','metrics':[],'relevance':1}
                p={'id':'p','hypothesis':'Vision question','papers':[],'revision':1,'status':'discovering','events':[],'seedOnly':seed_only,'seeds':['2012.12877'] if seed_only else [],'queries':['vision transformers'],'protocol':vision()['protocol']}
                r.projects=[p]
                with patch.object(r,'plan_protocol'), patch.object(r,'cfg_for_id',return_value={'TAVILY_API_KEY':'test'}), patch('relay.research.tavily.search',return_value=[{'url':'https://arxiv.org/abs/2012.12877','location':'Vision'}]) as search, patch('relay.research.arxiv_paper',return_value=paper), patch('relay.research.discover',return_value=[]), patch('relay.research.enrich',side_effect=lambda p:p), patch.object(r,'store_source'), patch.object(r,'assess'), patch.object(r,'synthesize'):
                    r.run(p)
                self.assertEqual(search.call_count,0 if seed_only else 1)
                self.assertEqual(p['status'],'review')
                self.assertEqual(len(p['papers']),1)

    def test_new_contract_can_compare_within_one_paper_without_claiming_replication(self):
        a,b=vision(id='a'),vision(id='b',method='DeiT',value='81.0')
        pairs=compare([{'id':'p','metrics':[a,b]}])['pairs']
        self.assertEqual(len(pairs),1)
        self.assertEqual(pairs[0]['outcome'],'comparable')
        self.assertFalse(pairs[0]['independent'])

    def test_percent_suffix_and_trailing_table_separator_are_normalized(self):
        source='| Vision Transformer | 80.0'
        m=vision(value='80.0%',quote='| Vision Transformer | 80.0 |')
        p={'id':'p','protocol':m['protocol'],'evidence':source}
        validate_analysis(p,{'metrics':[m]})
        self.assertEqual(p['metrics'][0]['value'],'80.0')
        self.assertEqual(p['metrics'][0]['quote'],source)
