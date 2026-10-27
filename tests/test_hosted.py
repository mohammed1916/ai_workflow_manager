import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from relay.core import read_config, RelayError
from relay.providers import with_key
from relay.research import Research


class HostedTests(unittest.TestCase):
    def test_hosted_mode_ignores_server_keys(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {'RELAY_HOSTED': '1', 'NEBIUS_API_KEY': 'server-secret', 'OLLAMA_TEST_API_KEY': 'o'}):
            cfg = read_config(Path(d))
            self.assertNotIn('NEBIUS_API_KEY', cfg); self.assertNotIn('OLLAMA_TEST_API_KEY', cfg)

    def test_local_mode_still_reads_server_keys(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {'RELAY_HOSTED': '0', 'NEBIUS_API_KEY': 'local'}):
            self.assertEqual(read_config(Path(d))['NEBIUS_API_KEY'], 'local')

    def test_visitor_key_overlays_without_mutating_base(self):
        base = {'NEBIUS_API_KEY': ''}
        out = with_key(base, 'nebius', 'visitor-key')
        self.assertEqual(out['NEBIUS_API_KEY'], 'visitor-key'); self.assertEqual(base['NEBIUS_API_KEY'], '')
        self.assertIs(with_key(base, 'nebius', None), base)

    def test_visitor_key_never_reaches_disk(self):
        secret = 'visitor-secret-9f3a7c'
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); r = Research(root)
            p = {'id': 'k' * 16, 'hypothesis': 'Does the key stay in memory?', 'provider': 'nebius', 'model': 'm', 'created': '2026-10-27T00:00:00Z',
                 'status': 'review', 'revision': 1, 'tokens': 0, 'events': [], 'papers': [], 'suggestions': [], 'tex': '', 'bib': '', 'proposals': [], 'corrections': [], 'calls': []}
            r.projects = [p]; r.set_key(p['id'], 'nebius', secret)
            r.checkpoint(p, 'retrieval', 'Retrieved')  # status is review, so the key is released here
            self.assertNotIn(p['id'], r.keys)
            r.set_key(p['id'], 'nebius', secret)
            self.assertEqual(r.cfg_for_id(p['id'])['NEBIUS_API_KEY'], secret)
            r.checkpoint(p, 'input', 'busy', )  # still review: released again
            for f in root.rglob('*'):
                if f.is_file(): self.assertNotIn(secret, f.read_text(errors='ignore'), str(f))

    def test_busy_project_keeps_key_until_work_ends(self):
        with tempfile.TemporaryDirectory() as d:
            r = Research(Path(d))
            p = {'id': 'b' * 16, 'hypothesis': 'Busy project keeps key', 'provider': 'nebius', 'model': 'm', 'created': '2026-10-27T00:00:00Z',
                 'status': 'discovering', 'revision': 1, 'tokens': 0, 'events': [], 'papers': [], 'suggestions': [], 'tex': '', 'bib': '', 'proposals': [], 'corrections': [], 'calls': []}
            r.projects = [p]; r.set_key(p['id'], 'nebius', 'k1'); r.checkpoint(p, 'x', 'busy step')
            self.assertIn(p['id'], r.keys)

    def test_compile_is_refused_when_hosted(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {'RELAY_HOSTED': '1'}):
            r = Research(Path(d))
            r.projects = [{'id': 'c' * 16, 'revision': 1, 'tex': 'x', 'bib': ''}]
            with self.assertRaises(RelayError) as e:
                r.compile({'id': 'c' * 16, 'revision': 1})
            self.assertEqual(e.exception.code, 'COMPILE_LOCAL_ONLY')


if __name__ == '__main__': unittest.main()
