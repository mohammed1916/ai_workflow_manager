import json, tempfile, unittest, zipfile, time
from pathlib import Path
from unittest.mock import patch
from relay.core import RelayError
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
