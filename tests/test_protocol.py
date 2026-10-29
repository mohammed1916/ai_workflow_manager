import unittest
from test_semantics import fixture

def vision(): return fixture()[0]["metrics"][0]

class ProtocolIntegrationTests(unittest.TestCase):
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
