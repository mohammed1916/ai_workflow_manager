import copy
import unittest
from relay.legacy_matching import match_condition, resolution
from relay.protocol import contract, enforce_scope
from relay.evidence import compare, compare_pair, html_to_text, row
from test_protocol import vision

class MatchingTests(unittest.TestCase):
    def test_duplicate_partition_uses_existing_evidence_once(self):
        a,b=vision(),vision(method='DeiT')
        for m in (a,b):
            m['protocol']['factors'].append({'key':'factor_evaluation_partition','label':'Evaluation partition'})
            m['factor_evaluation_partition']='unknown'
        result=compare_pair(row({'id':'a'},a),row({'id':'b'},b))
        self.assertEqual(result['outcome'],'comparable')
        self.assertNotIn('factor_evaluation_partition',[c['field'] for c in result['checks']])
    def test_alias_can_supply_partition_but_not_overwrite_contradiction(self):
        m=vision(split='unknown');m['protocol']['factors'].append({'key':'factor_evaluation_partition','label':'Evaluation partition'})
        m['factor_evaluation_partition']='validation'
        self.assertEqual(row({'id':'p'},m)['split'],'validation')
        self.assertEqual(m['split'],'unknown')
        m['split']='test'
        self.assertTrue(row({'id':'p'},m)['partitionConflict'])
    def test_plan_deduplicates_semantic_conditions(self):
        p=contract({'task':'classification','factors':[{'key':'evaluation_partition','label':'Evaluation partition'},{'key':'input_size','label':'Input resolution'},{'key':'image_resolution','label':'Image resolution'}]})
        self.assertEqual(len(p['factors']),1)
    def test_rounded_capacities_are_unresolved_not_equal_or_incompatible(self):
        for a,b in [('22M','22.1M'),('86M','86.6M'),('86M','87M')]:
            self.assertEqual(match_condition('factor_capacity','Model capacity',a,b)[0],'missing')
        self.assertEqual(match_condition('factor_capacity','Model capacity','22M','86M')[0],'conflict')
    def test_capacity_unit_conversion(self):
        self.assertEqual(match_condition('factor_capacity','Parameters','1000M','1 billion')[0],'match')
    def test_resolution_formats_and_ambiguous_legacy(self):
        self.assertEqual(resolution('384^{2}'),(384,384))
        self.assertEqual(resolution('384²'),(384,384))
        self.assertEqual(match_condition('resolution','Input resolution','384²','384×384')[0],'match')
        self.assertEqual(match_condition('resolution','Input resolution','3842','224')[0],'missing')
        self.assertEqual(match_condition('resolution','Input resolution','3842','3842')[0],'missing')
    def test_math_parser_preserves_superscript_and_archives_legacy(self):
        markup='<table><tr><td>ViT</td><td><math alttext="384^{2}"><msup><mn>384</mn><mn>2</mn></msup></math></td></tr></table>'
        self.assertIn('384^{2}',html_to_text(markup))
        self.assertIn('3842',html_to_text(markup,preserve_math=False))
        self.assertIn('224^(2)',html_to_text('<p>224<sup>2</sup> pixels</p>'))
    def test_redundant_metric_description_but_not_single_crop_equivalence(self):
        a=vision(metricDefinition='top-1 accuracy');b=vision(metricDefinition='top-1 accuracy on ImageNet-1K validation set')
        self.assertEqual(compare_pair(a,b)['outcome'],'comparable')
        self.assertEqual(compare_pair(vision(metricDefinition='single-crop top-1 accuracy'),b)['outcome'],'insufficient')
    def test_historical_focus_uses_exact_labels(self):
        metrics=[vision(id='a',method='ViT-B/16'),vision(id='b',method='DeiT-B'),vision(id='c',method='DeiT-S'),vision(id='d',method='SP-ViT')]
        r=compare([{'id':'p','metrics':metrics}],methods=['ViT-B/16','DeiT-B'])
        self.assertEqual(len(r['pairs']),1)
        self.assertEqual(r['summary']['outsideScope'],5)
    def test_non_distilled_restriction_is_enforced_without_guessing(self):
        a,b=vision(),vision(method='DeiT')
        for m in (a,b):
            m['protocol']['direction']='Compare non-distilled models only.'
            enforce_scope(m['protocol'])
            m['factor_distillation']='unknown'
        self.assertEqual(compare_pair(a,b)['outcome'],'insufficient')
        for m in (a,b):m['factor_distillation']='no distillation'
        self.assertEqual(compare_pair(a,b)['outcome'],'comparable')
        b['factor_distillation']='hard distillation'
        self.assertEqual(compare_pair(a,b)['outcome'],'incompatible')
    def test_reported_resolution_and_rounding_no_longer_false_conflict(self):
        # Regression from the user's export. Unknown pretraining is intentionally retained.
        a,b=vision(method='DeiT-S',factor_resolution='224×224'),vision(method='DeiT-S [38]',factor_resolution='unknown')
        for m,v in ((a,'22M'),(b,'22.1M')):
            m['protocol']['factors'] += [{'key':'factor_capacity','label':'Model capacity'},{'key':'factor_pretraining','label':'Pretraining data'}]
            m['factor_capacity']=v;m['factor_pretraining']='unknown'
        pair=compare_pair(a,b)
        self.assertEqual(pair['outcome'],'insufficient')
        self.assertFalse(any(c['status']=='conflict' for c in pair['checks']))

    def test_focused_investigation_passes_user_direction_to_model(self):
        import json,tempfile
        from pathlib import Path
        from unittest.mock import patch
        from test_tavily import TavilyTests
        captured=[]
        def complete(cfg,provider,model,messages,**kw):
            captured.append(json.loads(messages[1]['content']))
            return json.dumps({'proposals':[],'unresolved':[]}),{'total_tokens':1}
        with tempfile.TemporaryDirectory() as d:
            r,p=TavilyTests().project(Path(d))
            p['papers'][0]['evidence'] += ' Results are averaged over 3 runs with different random seeds.'
            r.keys[p['id']]={}
            with patch('relay.research.complete',side_effect=complete),patch('relay.research.tavily.search',return_value=[]):
                r.run_investigation(p,[('a1','m1',['aggregation'])],False,None,'Inspect repeated runs; do not change the metric.')
            self.assertTrue(captured)
            self.assertEqual(captured[0]['researcherDirection'],'Inspect repeated runs; do not change the metric.')
            self.assertEqual(captured[0]['fields'],['aggregation'])
            self.assertEqual(p['status'],'review')
    def test_superscript_is_not_extracted_from_navigation(self):
        text=html_to_text('<nav><math alttext="123^{2}"><mn>123</mn></math></nav><p>Evidence</p>')
        self.assertEqual(text,'Evidence')

    def test_separating_distilled_groups_does_not_exclude_one_group(self):
        from relay.legacy_matching import non_distilled_requested
        self.assertFalse(non_distilled_requested({'question':'Separate distilled from non-distilled models.'}))
        self.assertTrue(non_distilled_requested({'direction':'Compare non-distilled DeiT and ViT results.'}))
