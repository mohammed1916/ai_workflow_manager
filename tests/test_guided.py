import tempfile, threading, time, unittest
from pathlib import Path
from unittest.mock import patch
from relay.research import Research
from relay.guided import table_inventory,RunStopped
from relay.core import RelayError

SOURCE='Setup common to both arms.\nTable 1: Outcomes\n| Method | Accuracy |\n| A | 82 |\n| B | 85 |\nFollowing explanation.\n'
class GuidedTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.r=Research(Path(self.temp.name))
        self.p={'id':'a'*16,'status':'review','revision':1,'events':[],'papers':[{'id':'P','title':'Trial','evidence':SOURCE,'metrics':[]}],'calls':[],'provider':'nebius','model':'test','protocol':{'version':3},'tokens':0}
        self.r.projects=[self.p]
    def tearDown(self):self.temp.cleanup()
    def test_scan_retains_source_addresses_without_inference(self):
        with patch.object(self.r,'llm',side_effect=AssertionError('No model call')):self.r.guided_scan({'id':self.p['id']})
        t=self.p['papers'][0]['tables'][0]
        self.assertEqual(t['caption'],'Table 1: Outcomes');self.assertEqual(t['rows'][1]['id'],'L4');self.assertEqual(self.p['status'],'select_tables')
    def test_stop_preserves_results_and_blocks_followup_calls(self):
        entered=threading.Event();release=threading.Event();self.p['status']='discovering'
        self.p['papers'][0]['metrics']=[{'id':'saved'}]
        def provider(*args,**kwargs):entered.set();release.wait(3);return {'ok':True}
        def run():self.r.llm(self.p,'test',{});self.r.llm(self.p,'must not run',{})
        with patch('relay.research.model_call',side_effect=provider) as call:
            t=self.r.launch(self.p,run);self.assertTrue(entered.wait(1));self.r.stop({'id':self.p['id']})
            self.assertEqual(self.p['status'],'stopping');release.set();t.join(2)
            self.assertEqual(call.call_count,1);self.assertEqual(self.p['status'],'stopped');self.assertEqual(self.p['papers'][0]['metrics'][0]['id'],'saved')
    def test_stop_does_not_affect_another_project(self):
        other={'id':'b'*16,'status':'discovering','calls':[]};self.r.projects.append(other);self.p['status']='discovering'
        self.r.stop({'id':self.p['id']});self.r.check_running(other)
        with self.assertRaises(RunStopped):self.r.check_running(self.p)
    def test_budget_prevents_another_provider_call(self):
        self.p['runBudget']={'deadline':time.time()+60,'startCalls':0,'maxCalls':1};self.p['calls']=[{}]
        with patch('relay.research.model_call') as model:
            with self.assertRaises(RunStopped):self.r.llm(self.p,'test',{})
            model.assert_not_called()
    def test_invalid_source_excerpt_cannot_start(self):
        with self.assertRaises(RelayError):self.r.guided_extract({'id':self.p['id'],'revision':1,'selections':[{'paper':'P','excerpt':'Invented evidence not in this paper'}]})
        self.assertEqual(self.p['status'],'review')
    def test_selection_only_supplies_checked_rows_plus_headers_context(self):
        table=table_inventory(SOURCE)[0]
        with patch.object(self.r,'launch') as launch:
            self.r.guided_extract({'id':self.p['id'],'revision':1,'selections':[{'paper':'P','table':table['id'],'rows':['L5']}]})
        lines=launch.call_args.args[2][1][0][1]
        # Header context is always supplied; row addresses remain original.
        self.assertIn('L5',[l['id'] for l in lines]);self.assertEqual(self.p['status'],'discovering')
    def test_unknown_row_rejected(self):
        table=table_inventory(SOURCE)[0]
        with self.assertRaises(RelayError):self.r.guided_extract({'id':self.p['id'],'revision':1,'selections':[{'paper':'P','table':table['id'],'rows':['L999']}]})
    def test_no_tables_is_not_fabricated(self):self.assertEqual(table_inventory('A paper without a structured table.'),[])

    def test_stop_prevents_json_repair_request(self):
        from relay.research import model_call
        calls=[]
        def provider(*args,**kwargs):
            calls.append(1);self.p['stopRequested']=True
            return 'invalid JSON',{'total_tokens':3}
        with patch('relay.research.complete',side_effect=provider):
            with self.assertRaises(RunStopped):model_call({},'nebius','test','system',{},check_running=lambda:self.r.check_running(self.p))
        self.assertEqual(len(calls),1)
    def test_schema_error_is_explicit_not_silently_reinterpreted(self):
        from relay.guided import schema_errors
        protocol={'factors':[{'key':'factor_condition'}]}
        self.assertTrue(schema_errors({'metrics':[{'evidence':{'factor_condition':{'quote':'Q','value':'V'}}}]},protocol))
        self.assertEqual(schema_errors({'metrics':[{'factor_condition':'unknown','evidence':{}}]},protocol),[])
    def test_selected_pair_scope_rejects_stale_or_unknown_pairs(self):
        self.p['protocol']['entities']=[]
        with self.assertRaises(RelayError):self.r.assess_comparisons({'id':self.p['id'],'revision':1,'pairs':['fabricated'],'limit':1})
        self.assertEqual(self.p['status'],'review')

    def test_context_address_preserves_math_without_domain_alias(self):
        from relay.extraction import ground_output,indexed_lines
        source='| group | B\\uparrow384 |\n| treatment | 84.5 |\n'
        raw={'metrics':[{'value':'84.5','valueLocation':{'line':'L2','column':2},'factor_group':'B','fieldLocations':{'factor_group':{'line':'L1','column':2}}}]}
        grounded=ground_output(raw,indexed_lines(source))['metrics'][0]
        self.assertEqual(grounded['evidence']['factor_group'],r'B\uparrow384')
        raw['metrics'][0]['fieldLocations']['factor_group']['column']=999
        self.assertEqual(ground_output(raw,indexed_lines(source))['metrics'][0]['evidence']['factor_group'],'')

    def test_source_identity_does_not_depend_on_generated_label(self):
        from relay.research import metric_id
        a={'sourceAddress':{'source':'hash','line':'L10','column':2},'value':'82','method':'Treatment'}
        b={**a,'method':'Treatment (group 1)'}
        self.assertEqual(metric_id('paper',a),metric_id('paper',b))
        b['sourceAddress']={**b['sourceAddress'],'column':3}
        self.assertNotEqual(metric_id('paper',a),metric_id('paper',b))
