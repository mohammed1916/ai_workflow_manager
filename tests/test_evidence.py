import unittest
from relay.evidence import (html_to_text, cell_context, split_key, horizon_key, metric_definition_key, dataset_key, compare_pair,
                            compare, check_metric, supports, passages, repository_links, code_passages, is_proposed, dataset_splits, stated_splits, horizon_key, resolve_bare_pems)


def row(**kw):
    base = {'paper': 'A', 'title': 'Paper A', 'metric': 'm1', 'verified': True, 'method': 'GTS', 'dataset': 'METR-LA', 'datasetVersion': 'unknown',
            'split': '70/10/20', 'horizon': '60 minutes', 'aggregation': 'single horizon', 'preprocessing': 'unknown', 'metricDefinition': 'masked',
            'provenance': 'own', 'citedFrom': 'unknown', 'locator': 'Table 1', 'name': 'MAE', 'value': '3.41', 'unit': 'mph', 'direction': 'lower', 'quote': 'x'}
    base.update(kw); return base


class ParserTests(unittest.TestCase):
    def test_spans_become_aligned_grid_and_caption_labels_its_table(self):
        html = ('<p>Intro</p><figure><table><tr><td rowspan="2">Model</td><td colspan="2">PEMS04</td></tr><tr><td>MAE</td><td>RMSE</td></tr>'
                '<tr><td>AGCRN</td><td>19.83</td><td>32.26</td></tr></table><figcaption>Table 1: Overall performance.</figcaption></figure>')
        text = html_to_text(html)
        lines = text.split('\n')
        self.assertEqual(lines[1], 'Table 1: Overall performance.')
        self.assertIn('| Model | PEMS04 | PEMS04', text)
        self.assertIn('| Model | MAE | RMSE', text)
        cell = cell_context(text, '32.26', 'AGCRN', 'RMSE')
        self.assertEqual(cell['path'], 'AGCRN / PEMS04 / RMSE')
        self.assertTrue(cell['caption'].startswith('Table 1'))

    def test_transposed_table_cell_path(self):
        text = 'Table 1: Forecasting error (METR-LA).\n| | Metric | DCRNN | GTS\n| 60 min | MAE | 3.60 | 2.99\n| 60 min | RMSE | 7.59 | 5.85'
        cell = cell_context(text, '2.99', 'GTS', 'MAE', '60 min')
        self.assertEqual(cell['path'], '60 min / MAE / GTS')

    def test_inline_markup_does_not_split_numbers(self):
        self.assertIn('33.44', html_to_text('<table><tr><td><span class="u">3</span>3.44</td></tr></table>'))


class NormalizerTests(unittest.TestCase):
    def test_split_roles_and_ratios(self):
        self.assertEqual(split_key('70% of data is used for training, 20% are used for testing while the remaining 10% for validation'), (70, 10, 20))
        self.assertEqual(split_key('7:1:2'), (70, 10, 20))
        self.assertEqual(split_key('training set (70%), validation set (20%), and test set (10%)'), (70, 20, 10))
        self.assertIsNone(split_key('unknown'))

    def test_horizon_modes_and_documented_interval(self):
        self.assertEqual(horizon_key('Horizon 12', 'unknown', 'METR-LA')['minutes'], 60)
        self.assertEqual(horizon_key('12 steps', 'average over 12 horizons', 'PeMSD4')['mode'], 'average')
        self.assertEqual(horizon_key('60 minutes', 'mean of 10 runs', 'METR-LA')['mode'], 'single')  # run averaging is not horizon averaging
        self.assertIsNone(horizon_key('next 12 steps', 'unknown', 'PEMS04')['mode'])

    def test_run_counts_written_as_words_do_not_crash(self):
        from relay.evidence import runs_key
        self.assertEqual(runs_key('mean of ten runs'), ('mean', 10))
        self.assertEqual(runs_key('best of 5 runs'), ('best', 5))
        self.assertIsNone(runs_key('average over 12 horizons'))

    def test_metric_definitions_and_datasets(self):
        self.assertEqual(metric_definition_key('calculated in a manner slightly different from that used to report the official results'), 'nonstandard')
        self.assertEqual(metric_definition_key('missing values excluded'), 'masked')
        self.assertEqual(metric_definition_key('MAE with mae_thresh = None'), 'unmasked')
        self.assertEqual(dataset_key('PeMSD4'), dataset_key('PEMS04'))

    def test_supports_requires_numbers(self):
        self.assertTrue(supports('70/10/20', '70% for training, 10% for validation and 20% for testing'))
        self.assertFalse(supports('60/20/20', '70% for training, 10% for validation and 20% for testing'))


class CompareTests(unittest.TestCase):
    def test_matching_context_is_comparable(self):
        r = compare_pair(row(), row(paper='B', title='Paper B', method='Graph WaveNet', value='3.53'))
        self.assertEqual(r['outcome'], 'comparable'); self.assertEqual(r['favours'], 'a'); self.assertAlmostEqual(r['relative'], 3.4, 1)

    def test_missing_context_is_insufficient_not_incompatible(self):
        r = compare_pair(row(), row(paper='B', split='unknown'))
        self.assertEqual(r['outcome'], 'insufficient'); self.assertIn('split is unknown', r['explanation'][0]); self.assertIsNone(r['favours'])

    def test_conflicts_are_explained(self):
        r = compare_pair(row(), row(paper='B', horizon='15 minutes'))
        self.assertEqual(r['outcome'], 'incompatible'); self.assertIn('different horizons', r['explanation'][0])
        r = compare_pair(row(horizon='12 steps', aggregation='average over 12 horizons'), row(paper='B', horizon='60 minutes'))
        self.assertIn('aggregation', r['explanation'][0])

    def test_nonstandard_metric_conflicts_even_when_other_side_is_unknown(self):
        r = compare_pair(row(metricDefinition='computed in a manner different from the official DCRNN results'), row(paper='B', metricDefinition='unknown'))
        self.assertEqual(r['outcome'], 'incompatible')

    def test_unknown_metric_definition_is_a_caveat(self):
        r = compare_pair(row(), row(paper='B', metricDefinition='unknown'))
        self.assertEqual(r['outcome'], 'comparable'); self.assertTrue(r['caveats'])

    def test_cited_copy_is_not_independent(self):
        r = compare_pair(row(method='DCRNN', value='3.60'), row(paper='B', method='DCRNN', value='3.60', provenance='cited'))
        self.assertFalse(r['independent'])

    def test_compare_skips_same_paper_and_counts_other_datasets(self):
        a = {'id': 'A', 'title': 'A', 'metrics': [dict(row(), id='1'), dict(row(value='2.0'), id='2')]}
        b = {'id': 'B', 'title': 'B', 'metrics': [dict(row(dataset='PEMS-BAY'), id='3'), dict(row(value='3.5'), id='4')]}
        result = compare([a, b])
        self.assertEqual(result['summary']['differentDataset'], 2)
        self.assertTrue(all(x['a']['paper'] != x['b']['paper'] for x in result['pairs']))


class CheckTests(unittest.TestCase):
    source = 'Experiments. We use 70% of data for training, 10% for validation and 20% for testing.\nTable 4: Corrected error (METR-LA).\n| | Metric | GTS\n| 60 min | MAE | 3.41'

    def test_unsupported_field_is_demoted_and_kept_for_review(self):
        m = {'method': 'GTS', 'name': 'MAE', 'value': '3.41', 'quote': '| 60 min | MAE | 3.41', 'dataset': 'METR-LA', 'split': '60/20/20', 'horizon': '60 minutes',
             'aggregation': 'unknown', 'preprocessing': 'unknown', 'metricDefinition': 'unknown', 'provenance': 'cited', 'datasetVersion': 'unknown', 'citedFrom': 'unknown', 'evidence': {}}
        check_metric(m, self.source)
        # The paper states one split, so the stated value replaces the model's claim, which stays visible.
        self.assertEqual(m['split'], '70/10/20'); self.assertEqual(m['checks']['support']['split'], 'document')
        self.assertEqual(m['rejected']['split']['value'], '60/20/20'); self.assertIn('states 70/10/20', m['rejected']['split']['reason'])
        self.assertEqual(m['provenance'], 'unknown')  # cited without a supporting quote
        self.assertEqual(m['checks']['cell']['path'], '60 min / MAE / GTS'); self.assertTrue(m['checks']['cell']['ok'])

    def test_unstated_split_stays_unknown_and_generic_provenance_is_rejected(self):
        source = 'Table 4: Corrected error (METR-LA).\n| | Metric | GTS\n| 60 min | MAE | 3.41\nBaselines. We compare against several widely used baselines.'
        m = {'method': 'GTS', 'name': 'MAE', 'value': '3.41', 'quote': '| 60 min | MAE | 3.41', 'dataset': 'METR-LA', 'split': '70/10/20', 'horizon': 'unknown',
             'aggregation': 'unknown', 'preprocessing': 'unknown', 'metricDefinition': 'unknown', 'provenance': 'reproduced', 'datasetVersion': 'unknown', 'citedFrom': 'unknown',
             'evidence': {'provenance': {'quote': 'Baselines. We compare against several widely used baselines.', 'origin': 'paper'}}}
        check_metric(m, source)
        self.assertEqual(m['split'], 'unknown'); self.assertEqual(m['provenance'], 'unknown')
        self.assertEqual(m['checks']['cell']['horizonLabel'], '60 min')

    def test_marker_legend_makes_value_cited_and_unstated_average_is_rejected(self):
        source = ('Table 1: Overall performance; results with * are reported performance in the paper used the same datasets.\n| Model | PeMSD4\n| Model | MAE\n'
                  '| STSGCN [11] | 21.19*\n| AGCRN (ours) | 19.83')
        m = {'method': 'STSGCN', 'name': 'MAE', 'value': '21.19', 'quote': '| STSGCN [11] | 21.19*', 'dataset': 'PeMSD4', 'split': 'unknown', 'horizon': '12 steps',
             'aggregation': 'average over 12 horizons', 'preprocessing': 'unknown', 'metricDefinition': 'unknown', 'provenance': 'reproduced', 'datasetVersion': 'unknown', 'citedFrom': 'unknown', 'evidence': {}}
        check_metric(m, source)
        self.assertEqual(m['provenance'], 'cited'); self.assertIn('* are reported', m['evidence']['provenance']['quote'])
        self.assertEqual(m['aggregation'], 'unknown'); self.assertIn('aggregation', m['rejected'])
        m2 = dict(m, aggregation='average over 12 horizons', evidence={'aggregation': {'quote': 'results with * are reported performance in the paper', 'origin': 'paper'}}, provenance='own')
        check_metric(m2, source)
        self.assertEqual(m2['aggregation'], 'unknown'); self.assertIn('averaged over horizons', m2['rejected']['aggregation']['reason'])

    def test_different_single_horizons_are_counted_not_listed(self):
        a = {'id': 'A', 'title': 'A', 'metrics': [dict(row(), id='1')]}
        b = {'id': 'B', 'title': 'B', 'metrics': [dict(row(horizon='15 minutes'), id='2'), dict(row(horizon='12 steps', aggregation='average over 12 horizons'), id='3')]}
        result = compare([a, b])
        self.assertEqual(result['summary']['differentHorizon'], 1); self.assertEqual(len(result['pairs']), 1)
        self.assertIn('aggregation', result['pairs'][0]['explanation'][0])

    def test_correction_note_flags_original_table_but_not_the_correction(self):
        source = ('Table 1: Forecasting error (METR-LA).\n| | Metric | GTS\n| 60 min | MAE | 2.99\n'
                  'Appendix D Updates of Tables 1, 2, and 3\nIt was brought to our attention that this version calculated the evaluation metrics in a manner slightly different from the official results. We updated Tables 1, 2, and 3 by correcting the calculations. See Tables 4, 5, and 6.\n'
                  'Table 4: (Correction of Table 1) Forecasting error (METR-LA).\n| | Metric | GTS\n| 60 min | MAE | 3.41')
        base = {'method': 'GTS', 'name': 'MAE', 'dataset': 'METR-LA', 'split': 'unknown', 'horizon': '60 minutes', 'aggregation': 'unknown', 'preprocessing': 'unknown',
                'metricDefinition': 'unknown', 'provenance': 'own', 'datasetVersion': 'unknown', 'citedFrom': 'unknown', 'evidence': {}}
        original = dict(base, value='2.99', quote='| 60 min | MAE | 2.99'); corrected = dict(base, value='3.41', quote='| 60 min | MAE | 3.41')
        check_metric(original, source); check_metric(corrected, source)
        self.assertEqual(metric_definition_key(original['metricDefinition']), 'nonstandard'); self.assertTrue(original['superseded'])
        self.assertIn('manner slightly different', original['evidence']['metricDefinition']['quote'])
        self.assertEqual(corrected['metricDefinition'], 'unknown'); self.assertNotIn('superseded', corrected)

    def test_proposal_detection_ignores_non_method_listings_and_finds_acronym_after_ie(self):
        gmac = ('We present the training time and inference time of STGCN, DCRNN, Graph WaveNet, and GMAN on the PeMS dataset in Table 2. '
                'In this paper, we propose a graph multi-attention network (GMAN) to predict traffic conditions.')
        self.assertFalse(is_proposed('Graph WaveNet', gmac, 'GMAN: A Graph Multi-Attention Network'))
        self.assertTrue(is_proposed('GMAN', gmac, 'GMAN: A Graph Multi-Attention Network'))
        stid = ('Instead, we propose a simple yet effective baseline for MTS forecasting by attaching spatial and temporal identity information, i.e., STID. '
                'We compare against several widely used baselines such as AGCRN.')
        self.assertTrue(is_proposed('STID', stid, 'Spatial-Temporal Identity'))
        self.assertFalse(is_proposed('AGCRN', stid, 'Spatial-Temporal Identity'))

    def test_multi_ratio_sentence_is_scoped_to_named_dataset(self):
        text = ('The ratio of training, validation, and test sets for the PEMS-BAY dataset is 7 : 1 : 2, while the ratio for other datasets is 6 : 2 : 2.\n'
                'We aim to predict 12 steps on all datasets.')
        self.assertEqual(dataset_splits(text, 'PEMS-BAY'), [(70, 10, 20)])
        self.assertEqual(dataset_splits(text, 'PEMS04'), [])
        self.assertEqual(stated_splits(text), [(70, 10, 20), (60, 20, 20)])

    def test_average_horizon_span_uses_longest_horizon_and_bare_pems_is_resolved(self):
        self.assertEqual(horizon_key('average over 12 horizons (each horizon = 5 minutes; range 5–60 minutes)', 'average over 12 horizons', 'PeMSD4')['minutes'], 60)
        self.assertEqual(resolve_bare_pems('The PeMS dataset contains 6 months of data recorded by 325 traffic sensors.', 'PeMS'), 'PEMS-BAY')
        self.assertIsNone(resolve_bare_pems('The PeMS dataset is described below.', 'PeMS'))

    def test_unknown_metric_name_is_missing_not_conflicting_and_recovered_from_column(self):
        a = {'paper': 'A', 'title': 'A', 'metric': 'm1', 'verified': True, 'method': 'DCRNN', 'dataset': 'PEMS04', 'split': '60/20/20', 'horizon': '60 minutes',
             'aggregation': 'single horizon', 'metricDefinition': 'masked', 'provenance': 'cited', 'name': 'unknown', 'value': '21.22', 'direction': 'lower', 'quote': 'x', 'citedFrom': 'unknown', 'datasetVersion': 'unknown', 'preprocessing': 'unknown', 'locator': 'Table 1', 'unit': 'unknown'}
        b = dict(a, paper='B', title='B', name='MAE', value='21.5', provenance='own', method='AGCRN')
        self.assertEqual(compare_pair(a, b)['outcome'], 'insufficient')
        source = 'Table 1: Performance.\n| Model | PeMSD4\n| Model | MAE\n| DCRNN [2] | 21.22'
        m = {'method': 'DCRNN', 'name': 'unknown', 'value': '21.22', 'quote': '| DCRNN [2] | 21.22', 'dataset': 'PeMSD4', 'split': 'unknown', 'horizon': 'unknown',
             'aggregation': 'unknown', 'preprocessing': 'unknown', 'metricDefinition': 'unknown', 'provenance': 'unknown', 'datasetVersion': 'unknown', 'citedFrom': 'unknown', 'evidence': {}}
        check_metric(m, source)
        self.assertEqual(m['name'], 'MAE')

    def test_dataset_name_in_metric_field_is_rejected_and_recovered_from_column(self):
        source = 'Table 1: Performance.\n| Model | PeMSD4\n| Model | MAE\n| AGCRN | 19.83'
        m = {'method': 'AGCRN', 'name': 'PeMSD4', 'value': '19.83', 'quote': '| AGCRN | 19.83', 'dataset': 'PeMSD4', 'split': 'unknown', 'horizon': 'unknown',
             'aggregation': 'unknown', 'preprocessing': 'unknown', 'metricDefinition': 'unknown', 'provenance': 'unknown', 'datasetVersion': 'unknown', 'citedFrom': 'unknown', 'evidence': {}}
        check_metric(m, source)
        self.assertEqual(m['name'], 'MAE'); self.assertIn('name', m['rejected'])

    def test_unknown_dataset_recovered_from_table_column_then_resolved_by_sensor_count(self):
        source = ('The PeMS dataset contains 6 months of data recorded by 325 traffic sensors.\nTable 1: Performance comparison.\n'
                  '| | PeMS | PeMS\n| Model | 1 hour | MAE\n| GMAN | 1.86')
        m = {'method': 'GMAN', 'name': 'MAE', 'value': '1.86', 'quote': '| GMAN | 1.86', 'dataset': 'unknown', 'split': 'unknown', 'horizon': '1 hour',
             'aggregation': 'unknown', 'preprocessing': 'unknown', 'metricDefinition': 'unknown', 'provenance': 'own', 'datasetVersion': 'unknown', 'citedFrom': 'unknown', 'evidence': {}}
        check_metric(m, source)
        self.assertEqual(m['dataset'], 'PEMS-BAY')

    def test_passages_and_repository_links(self):
        text = 'Intro.\n4.1 Setup\nThe datasets are split with 70% for training.\nThe code is available at https://github.com/owner/repo.\nSee issues at https://github.com/other/thing/issues for details.'
        self.assertTrue(passages(text, ['split'])[0]['text'].startswith('The datasets are split'))
        links = repository_links(text)
        self.assertEqual(links[0]['url'], 'https://github.com/owner/repo'); self.assertTrue(links[0]['own']); self.assertFalse(links[1]['own'])
        code = code_passages([{'path': 'conf.yaml', 'sha': 'a' * 40, 'url': 'u', 'text': 'x\nval_ratio = 0.2\ntest_ratio = 0.2\ny'}], ['split'])
        self.assertIn('val_ratio', code[0]['text']); self.assertIn('conf.yaml@aaaaaaaaaa', code[0]['location'])


if __name__ == '__main__': unittest.main()
