import json
import secrets
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from relay.server import make_handler


class ResearchAPITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.store=SimpleNamespace(root=self.root,token=secrets.token_urlsafe(32))
        self.server=ThreadingHTTPServer(('127.0.0.1',0),lambda *a:None)
        self.port=self.server.server_address[1]
        self.server.RequestHandlerClass=make_handler(self.store,self.port)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.port}'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.temp.cleanup()
    def call(self,path,data=None,headers=None):
        req=urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,
                                  headers={'Content-Type':'application/json',**(headers or {})})
        try:
            with urllib.request.urlopen(req) as r:return r.status,r.read()
        except urllib.error.HTTPError as e:return e.code,e.read()
    def test_schema_covers_real_research_actions_without_legacy_workflows(self):
        code,body=self.call('/api/schema');self.assertEqual(code,200)
        endpoints=json.loads(body)['endpoints'];paths={e['path'] for e in endpoints}
        self.assertIn('/api/research/investigate',paths);self.assertIn('/api/desk/load',paths)
        self.assertNotIn('/api/runs',paths)
    def test_state_has_no_provider_secret_and_mutation_requires_token(self):
        code,body=self.call('/api/state');self.assertEqual(code,200);state=json.loads(body)
        self.assertEqual(state['token'],self.store.token);self.assertNotIn('NEBIUS_API_KEY',state)
        self.assertEqual(self.call('/api/desk/load',{})[0],403)
    def test_cross_origin_and_host_are_rejected(self):
        self.assertEqual(self.call('/api/state',headers={'Origin':'https://example.org'})[0],403)
        self.assertEqual(self.call('/api/state',headers={'Host':'evil.test'})[0],403)
        self.assertEqual(self.call('/api/schema',headers={'Sec-Fetch-Site':'cross-site'})[0],403)
    def test_removed_endpoints_cannot_run(self):
        for path in ['/api/runs','/api/approve','/api/clips','/api/reveal']:
            self.assertEqual(self.call(path,{},headers={'Authorization':'Bearer '+self.store.token})[0],404)
    def test_desk_is_readable_with_no_installed_example(self):
        code,body=self.call('/api/desk');self.assertEqual(code,200);d=json.loads(body)
        self.assertIsNone(d['featured']);self.assertEqual(d['evaluation']['runs'],[])
    def test_source_archive_excludes_credentials_and_private_state(self):
        from scripts.package_submission import build
        import zipfile
        path,_=build(self.root/'build.zip')
        with zipfile.ZipFile(path) as z:
            names=z.namelist()
            self.assertIn('README.md',names);self.assertIn('LICENSE',names)
            self.assertIn('data/research/discovery-study.json',names)
            self.assertNotIn('.env',names)
            self.assertFalse(any(n.startswith(('.relay/','docs/','extension/','workspace/')) for n in names))

    def test_source_endpoint_handles_unknown_project(self):
        self.assertEqual(self.call('/api/research/source?id=missing&paper=missing')[0],404)




    def test_comparison_api_filters_models_without_model_calls(self):
        from unittest.mock import patch
        from relay.research import Research
        from test_semantics import fixture
        research=Research(self.root)
        research.projects=[{'id':'saved','papers':fixture()}]
        with patch('relay.research.Research',return_value=research):
            self.server.RequestHandlerClass=make_handler(self.store,self.port)
        headers={'Authorization':'Bearer '+self.store.token}
        with patch.object(research,'llm',side_effect=AssertionError('Focus must not call a model')):
            code,body=self.call('/api/research/compare',{'id':'saved','methods':['e1','e2']},headers)
            self.assertEqual(code,200)
            self.assertEqual(len(json.loads(body)['pairs']),1)
            self.assertEqual(self.call('/api/research/compare',{'id':'saved','methods':'ViT'},headers)[0],400)
