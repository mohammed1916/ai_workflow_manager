import tempfile, unittest
from pathlib import Path
from relay.research import Research
from relay.core import RelayError


class PortabilityTests(unittest.TestCase):
    def project(self, pid='a' * 16):
        return {'id': pid, 'hypothesis': 'Do the reported baselines hold under matched protocols?', 'provider': 'nebius', 'model': 'm',
                'created': '2026-10-27T00:00:00Z', 'status': 'review', 'revision': 3, 'tokens': 5, 'events': [], 'papers': [{'id': 'W1', 'title': 'A', 'metrics': [], 'reviewed': True, 'evidence': 'Full source text of paper one.'}],
                'suggestions': [], 'tex': '', 'bib': '', 'proposals': [], 'corrections': [], 'calls': []}

    def test_round_trip_restores_project_and_source_text(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            a = Research(Path(d1)); p = self.project(); a.projects = [p]; a.checkpoint(p, 'x', 'saved')
            doc = a.export_project(p['id'])
            self.assertNotIn('keys', doc['project']); self.assertEqual(doc['project']['papers'][0]['evidence'], 'Full source text of paper one.')
            b = Research(Path(d2))
            self.assertEqual(b.import_project(doc), {'ok': True, 'existing': False})
            restored = b.get(p['id'])
            self.assertTrue(restored['papers'][0]['evidence'].startswith('Full'))
            self.assertEqual(b.source(restored['papers'][0]), 'Full source text of paper one.')
            self.assertEqual(b.import_project(doc)['existing'], True)  # importing twice never overwrites

    def test_busy_project_is_restored_as_interrupted_and_bad_files_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            b = Research(Path(d)); p = self.project('b' * 16); p['status'] = 'discovering'
            b.import_project({'format': 'relay-research/1', 'project': p})
            self.assertEqual(b.get('b' * 16)['status'], 'interrupted')
            for bad in ({}, {'format': 'x', 'project': p}, {'format': 'relay-research/1', 'project': dict(p, id='../../etc')}):
                with self.assertRaises(RelayError): b.import_project(bad)


if __name__ == '__main__': unittest.main()
