import json, tempfile, unittest, zipfile, time
from pathlib import Path
from unittest.mock import patch
from relay.core import Store, validate_plan, RelayError
from relay.analysis import profile_csv
from relay.providers import models, complete, settings

class ProviderTests(unittest.TestCase):
 def test_key_precedence(self):
  self.assertEqual(settings({'OLLAMA_TEST_API_KEY':'test','OLLAMA_API_KEY':'normal'},'ollama')['key'],'test')
 def test_catalog_uses_native_api(self):
  with patch('relay.providers.request',return_value={'models':[{'name':'gpt-oss:120b'},{'name':'gpt-oss:20b'}]}) as request:
   result=models({'OLLAMA_TEST_API_KEY':'private'},'ollama')
  self.assertEqual(request.call_args.args[1],'/api/tags');self.assertEqual(len(result['models']),2);self.assertNotIn('private',json.dumps(result))
 def test_native_response_and_usage(self):
  with patch('relay.providers.request',return_value={'message':{'content':'{}'},'prompt_eval_count':20,'eval_count':30}) as request:
   content,usage=complete({'OLLAMA_TEST_API_KEY':'test'},'ollama','gpt-oss:120b',[])
  self.assertEqual(usage['total_tokens'],50);self.assertEqual(content,'{}');self.assertFalse(request.call_args.args[2]['stream'])
 def test_provider_credentials_do_not_cross(self):
  self.assertEqual(settings({'NEBIUS_API_KEY':'n','OLLAMA_TEST_API_KEY':'o'},'nebius')['key'],'n')
  self.assertEqual(settings({'NEBIUS_API_KEY':'n','OLLAMA_TEST_API_KEY':'o'},'ollama')['key'],'o')
 def test_unknown_provider(self):
  with self.assertRaises(RelayError):settings({},'unknown')

class ComplexTests(unittest.TestCase):
 def test_csv_calculations(self):
  p=profile_csv('Name,Value\na,10\nb,20\nc,\n')
  self.assertEqual(p['rows'],3);self.assertEqual(p['columns']['Value']['sum'],30);self.assertEqual(p['columns']['Value']['missing'],1)
 def test_invalid_csv(self):
  for data in ('a,a\n1,2','a,b\n1,2,3'):
   with self.assertRaises(ValueError):profile_csv(data)
 def test_archive_forward_reference_denied(self):
  with self.assertRaises(RelayError):validate_plan({'title':'Bad','steps':[{'kind':'create_archive','title':'Zip','filename':'x.zip','files':['later.md']}]})
 def test_archive_path_denied(self):
  with self.assertRaises(RelayError):validate_plan({'title':'Bad','steps':[{'kind':'write_file','title':'Write','filename':'a.md','content':'a'},{'kind':'create_archive','title':'Zip','filename':'../x.zip','files':['a.md']}]})
 def test_real_archive_matches_human_edit(self):
  with tempfile.TemporaryDirectory() as folder:
   store=Store(Path(folder));(store.inbox/'a.md').write_text('source')
   run=store.create('Package notes',['file:a.md'],'demo')
   for _ in range(300):
    if run['status']=='review' and not store.active:break
    time.sleep(.01)
   run['plan']['steps'].append({'kind':'create_archive','title':'Package outputs','filename':'kit.zip','files':['research-brief.md','sources.json']})
   store.edit(run['id'],1,0,'human final version')
   store.approve(run['id'],2)
   for _ in range(300):
    if run['status'] in ('complete','failed'):break
    time.sleep(.01)
   self.assertEqual(run['status'],'complete',run.get('error'))
   with zipfile.ZipFile(store.outbox/run['id']/'kit.zip') as z:self.assertEqual(z.read('research-brief.md'),b'human final version')
