import json, os, tempfile, unittest, urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch
from relay import tavily
from relay.core import RelayError, read_config
from relay.research import Research, INVESTIGATE

SECRET = 'tvly-secret-7c41e9d2'
WEB_URL = 'https://example.org/protocol'
WEB_TEXT = 'Results are averaged over 3 runs with different random seeds.'


class FakeResponse:
    def __init__(self, body): self.body = body
    def read(self, n=None): return self.body
    def __enter__(self): return self
    def __exit__(self, *a): return False


def fake_complete(cfg, provider, model, messages, max_tokens=8000, timeout=90):
    """Stands in for the model: proposes the aggregation from any web passage it is shown."""
    system = messages[0]['content']
    if INVESTIGATE[:60] in system:
        payload = json.loads(messages[1]['content'])
        for x in payload['passages']:
            if x['origin'] == 'web':
                return json.dumps({'proposals': [{'field': 'aggregation', 'value': 'mean over 3 runs', 'passage': x['id'], 'quote': WEB_TEXT,
                                                  'explanation': 'The web page states the runs are averaged.'}], 'unresolved': []}), {'total_tokens': 10}
        return json.dumps({'proposals': [], 'unresolved': [{'field': 'aggregation', 'reason': 'not stated'}]}), {'total_tokens': 5}
    return json.dumps({}), {'total_tokens': 1}


class TavilyTests(unittest.TestCase):
    def project(self, root):
        r = Research(root)
        metric = {'id': 'm1', 'name': 'MAE', 'value': '18.2', 'method': 'Graph', 'dataset': 'PEMS04', 'quote': 'On PEMS04, the test MAE is 18.2 at 60 minutes.', 'missing': ['aggregation']}
        paper = {'id': 'a1', 'title': 'Graph forecasts', 'evidence': 'On PEMS04, the test MAE is 18.2 at 60 minutes.', 'metrics': [metric], 'url': 'https://example.org/paper'}
        p = {'id': 'a' * 16, 'hypothesis': 'Does the protocol match?', 'provider': 'nebius', 'model': 'm', 'created': '2026-10-27T00:00:00Z', 'status': 'investigating',
             'revision': 1, 'tokens': 0, 'events': [], 'papers': [paper], 'suggestions': [], 'tex': '', 'bib': '', 'proposals': [], 'corrections': [], 'calls': []}
        r.projects = [p]
        return r, p

    def run_flow(self, r, p, search_result=None):
        results = search_result if search_result is not None else [{'id': 'W1', 'origin': 'web', 'location': 'Protocol', 'url': WEB_URL, 'text': WEB_TEXT}]
        with patch('relay.research.complete', side_effect=fake_complete), patch('relay.tavily.search', return_value=results) as search:
            r.run_investigation(p, [('a1', 'm1', ['aggregation'])], False, None)
        return search

    def test_search_parses_passages_and_truncates(self):
        body = json.dumps({'results': [{'url': WEB_URL, 'title': 'T' * 120, 'content': 'x' * 5000, 'score': 0.9},
                                       {'url': '', 'title': 'no url', 'content': 'skipped'}]}).encode()
        with patch('relay.tavily.urllib.request.urlopen', return_value=FakeResponse(body)) as opened:
            out = tavily.search(SECRET, 'query text')
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0], {'id': 'W1', 'origin': 'web', 'location': 'T' * 90, 'url': WEB_URL, 'text': 'x' * 3000})
        req = opened.call_args[0][0]
        self.assertEqual(req.get_header('Authorization'), 'Bearer ' + SECRET)
        self.assertEqual(json.loads(req.data), {'query': 'query text', 'max_results': 4})

    def test_search_returns_empty_list_for_no_results(self):
        with patch('relay.tavily.urllib.request.urlopen', return_value=FakeResponse(b'{"results": []}')):
            self.assertEqual(tavily.search(SECRET, 'q'), [])

    def test_http_error_is_a_relay_error_without_the_key(self):
        err = urllib.error.HTTPError('https://api.tavily.com/search', 401, 'Unauthorized', {}, None)
        with patch('relay.tavily.urllib.request.urlopen', side_effect=err):
            with self.assertRaises(RelayError) as cm:
                tavily.search(SECRET, 'q')
        self.assertEqual(cm.exception.code, 'TAVILY_ERROR')
        self.assertNotIn(SECRET, str(cm.exception))

    def test_without_key_no_search_and_one_hint(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {'TAVILY_API_KEY': ''}):
            r, p = self.project(Path(d))
            p['papers'][0]['metrics'][0]['missing'] = ['aggregation']
            with patch('relay.research.complete', side_effect=fake_complete), patch('relay.tavily.search') as search:
                r.run_investigation(p, [('a1', 'm1', ['aggregation', 'split'])], False, None)
            search.assert_not_called()
            hints = [e['message'] for e in p['events'] if 'Tavily key' in e['message']]
            self.assertEqual(hints, ['Add a Tavily key in Model settings to let Relay search the web for missing protocol details.'])

    def test_with_key_missing_field_gets_web_passage_and_proposal(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {'TAVILY_API_KEY': ''}):
            r, p = self.project(Path(d))
            r.set_key(p['id'], 'tavily', SECRET)
            search = self.run_flow(r, p)
            search.assert_called_once()
            self.assertEqual(search.call_args[0][0], SECRET)
            self.assertIn('evaluation protocol', search.call_args[0][1])
            self.assertLessEqual(len(search.call_args[0][1]), 300)
            props = p['proposals']
            self.assertEqual(len(props), 1)
            self.assertEqual(props[0]['field'], 'aggregation')
            self.assertEqual(props[0]['origin'], 'web')
            self.assertEqual(props[0]['url'], WEB_URL)
            self.assertEqual(props[0]['quote'], WEB_TEXT)
            inv = [n for n in p['execution'] if n['kind'] == 'investigation'][-1]
            self.assertEqual(inv['details']['web']['results'], 1)
            self.assertNotIn(SECRET, json.dumps(inv))

    def test_start_path_holds_key_in_memory_only(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {'TAVILY_API_KEY': ''}), \
                patch('relay.research.models', return_value={'models': ['m']}), patch('relay.research.threading.Thread') as thread:
            r = Research(Path(d))
            pid = r.start({'hypothesis': 'Does the protocol match?', 'provider': 'nebius', 'model': 'm', 'tavilyKey': SECRET})['id']
            self.assertEqual(r.keys[pid]['TAVILY_API_KEY'], SECRET)
            self.assertNotIn('tavilyKey', [k for p in r.projects for k in p])
            self.assertNotIn(SECRET, json.dumps(r.projects))
            thread.assert_called_once()

    def test_search_failure_continues_without_web(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {'TAVILY_API_KEY': ''}):
            r, p = self.project(Path(d))
            r.set_key(p['id'], 'tavily', SECRET)
            with patch('relay.research.complete', side_effect=fake_complete), \
                    patch('relay.tavily.search', side_effect=RelayError('TAVILY_ERROR', 'Tavily returned HTTP 401. Check the key and usage limits.', 502)):
                r.run_investigation(p, [('a1', 'm1', ['aggregation'])], False, None)
            self.assertEqual(p['proposals'], [])
            self.assertTrue(any(e['message'].startswith('Web search failed; continuing with the paper and code.') for e in p['events']))
            self.assertEqual(p['status'], 'review')

    def test_key_never_reaches_disk_or_events(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {'TAVILY_API_KEY': ''}):
            root = Path(d); r, p = self.project(root)
            r.set_key(p['id'], 'tavily', SECRET)
            self.run_flow(r, p)
            r.save()
            files = [f for f in root.rglob('*') if f.is_file()]
            self.assertTrue(any('checkpoints' in str(f) for f in files))
            for f in files:
                self.assertNotIn(SECRET, f.read_text(errors='ignore'), str(f))
            self.assertNotIn(SECRET, json.dumps(p))

    def test_hosted_mode_strips_tavily_key(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {'RELAY_HOSTED': '1', 'TAVILY_API_KEY': 'server-tavily'}):
            self.assertNotIn('TAVILY_API_KEY', read_config(Path(d)))


if __name__ == '__main__': unittest.main()
