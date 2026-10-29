import tempfile, unittest
from pathlib import Path
from relay.research import Research


class SampleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.r = Research(Path(self.tmp.name))
        base = {'hypothesis': 'Which baselines hold under matched protocols?', 'provider': 'nebius', 'model': 'm', 'created': '2026-10-29T00:00:00Z',
                'status': 'review', 'revision': 1, 'tokens': 0, 'events': [], 'papers': [], 'suggestions': [], 'tex': '', 'bib': '', 'proposals': [], 'corrections': [], 'calls': []}
        self.sample = dict(base, id='5' * 16, studyKey='nebius-discovery-v1', execution=[{'id': 'n1'}])
        self.mine = dict(base, id='6' * 16)
        self.r.projects = [self.sample, self.mine]

    def tearDown(self): self.tmp.cleanup()

    def test_samples_lists_only_starter_investigations(self):
        ids = [p['id'] for p in self.r.samples()['projects']]
        self.assertEqual(ids, ['5' * 16])

    def test_branch_from_a_sample_is_the_users_own_project(self):
        from relay.research import Research as R
        child = dict(self.sample, id='7' * 16, parentProject=self.sample['id'])
        self.r.projects.append(child)
        self.assertNotIn('7' * 16, [p['id'] for p in self.r.samples()['projects']])
        self.assertIn(self.sample['id'], [p['id'] for p in self.r.samples()['projects']])

    def test_samples_are_never_listed_as_user_projects_by_id_filter(self):
        self.assertEqual(len(self.r.state(['5' * 16, '6' * 16])['projects']), 2)  # the server answers for ids; the browser decides ownership


if __name__ == '__main__': unittest.main()
