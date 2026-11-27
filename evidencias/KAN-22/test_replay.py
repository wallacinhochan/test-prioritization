import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from replay import (AVAILABILITY_FIELDS, FEATURES, KEYS, OVERHEAD_FIELDS, RANK_FIELDS,
                    SELECTION_FIELDS, load_inputs, replay, write_csv)


def sha(pos):
    return f'{pos:040x}'


class ExpandingWindowTest(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.paths = {}

        self.freeze('commits', KEYS[:2], [(p, sha(p)) for p in range(1, 52)])
        self.freeze('train', (*KEYS, *FEATURES, 'partition', 'target_synthetic'), [
            (p, sha(p), f'Test#{i}', *([p] * len(FEATURES)), 'treino', target)
            for p, target in [(9, 0), (10, ''), (11, 1), (12, 1), (30, 1), (50, 1)]
            for i in range(15)
        ])
        self.freeze('availability', AVAILABILITY_FIELDS, [
            (sha(p), released, f'fixture-{p}')
            for p, released in [(9, 9), (10, 10), (11, 11), (12, 21), (30, 31)]
        ])
        positions = (10, 11, 12, 21, 31, 42)
        self.freeze('selection', SELECTION_FIELDS, [
            (sha(p), 'T1', method, selected, reason, 'selecao-fixture')
            for p in positions for method, selected, reason in [
                ('Test#B', 'true', 'dependency'), ('Test#A', 'true', 'fallback'),
                ('Test#C', 'false', 'no_dependency')
            ]
        ])
        self.freeze('t1', RANK_FIELDS, [
            (sha(p), 'T1', method, rank, '', 'ranking-fixture')
            for p in positions for rank, method in enumerate(('Test#B', 'Test#A'), 1)
        ])
        self.freeze('overhead', OVERHEAD_FIELDS, [
            (sha(p), 'T1', 'selection', 'measured', '1.25', 'tempo-fixture')
            for p in (*positions, 51)
        ])
        self.freeze('features', (*KEYS, *FEATURES), [
            (p, sha(p), method, *([9] * len(FEATURES)))
            for p in positions for method in ('Test#B', 'Test#A')
        ])

    def freeze(self, name, fields, rows):
        path = self.directory / (name + '.csv')
        write_csv(path, fields, rows)
        self.paths[name] = path

    def result(self):
        commits, labels, availability, features, costs, _ = load_inputs(self.paths)
        return replay(commits, labels, availability, features, costs, 'manifesto.json')

    def test_strict_cut_expansion_and_reuse_without_labels(self):
        ranks, overhead, windows, coverage, fits = self.result()
        self.assertEqual([w['decision_position'] for w in windows], [11, 21, 31, 41, 51])
        self.assertEqual([w['eligible_rows'] for w in windows], [15, 30, 45, 60, 60])
        self.assertEqual([w['status'] for w in windows], ['fit'] * 4 + ['no_new_labels'])
        self.assertEqual(
            [{int(s['origin_position']) for s in w['eligible_sources']} for w in windows],
            [{9}, {9, 11}, {9, 11, 12}, {9, 11, 12, 30}, {9, 11, 12, 30}],
        )
        self.assertEqual(len(fits), 4)
        self.assertEqual(coverage[9]['status'], 'no_model')
        self.assertEqual(coverage[50]['status'], 'empty_t1')
        self.assertEqual(coverage[50]['model_window'], 'janela-40')
        self.assertEqual({r[0] for r in ranks}, {sha(p) for p in (11, 12, 21, 31, 42)})
        self.assertTrue(all(r[4] == 0 for r in ranks if r[0] == sha(11)))
        for p in (11, 12, 21, 31, 42):
            for scenario in ('T2', 'T3'):
                self.assertEqual([(r[2], r[3]) for r in ranks if r[:2] == (sha(p), scenario)],
                                 [('Test#A', 1), ('Test#B', 2)])
        training = [r for r in overhead if r[2] == 'training']
        self.assertEqual({r[0] for r in training}, {sha(p) for p in (11, 21, 31, 42)})
        self.assertEqual(len(training), 8)
        self.assertEqual(len({r[:3] for r in overhead}), len(overhead))
        self.assertTrue(all(r[3:] == ('measured', '1.25', 'tempo-fixture')
                            for r in overhead if r[2] == 'selection'))

    def test_waits_for_enough_observable_labels(self):
        self.freeze('availability', AVAILABILITY_FIELDS, [(sha(9), 11, 'aprovacao')])
        ranks, _, windows, coverage, _ = self.result()
        self.assertEqual(windows[0]['status'], 'insufficient_labels')
        self.assertEqual(windows[1]['status'], 'fit')
        self.assertEqual(coverage[10]['status'], 'no_model')
        self.assertNotIn(sha(11), {r[0] for r in ranks})

    def test_rejects_selection_mismatch(self):
        self.freeze('t1', RANK_FIELDS, [(sha(10), 'T1', 'Test#C', 1, '', 'fixture')])
        with self.assertRaisesRegex(ValueError, 'Populacao ou ordem T1 divergente'):
            load_inputs(self.paths)

    def test_rejects_duplicate_and_wrong_order(self):
        for methods in [('Test#B', 'Test#B'), ('Test#A', 'Test#B')]:
            with self.subTest(methods=methods):
                self.freeze('features', (*KEYS, *FEATURES), [
                    (p, sha(p), method, *([9] * len(FEATURES)))
                    for p in (10, 11, 12, 21, 31, 42) for method in methods
                ])
                with self.assertRaisesRegex(ValueError, 'Populacao ou ordem T1 divergente'):
                    load_inputs(self.paths)

    def test_rejects_current_outcome_as_an_inference_column(self):
        self.freeze('features', (*KEYS, *FEATURES, 'target_synthetic'), [])
        with self.assertRaisesRegex(ValueError, 'Cabecalho invalido'):
            load_inputs(self.paths)

    def test_cli_exports_contract_and_window_provenance(self):
        name = 'test-' + uuid4().hex
        script = Path(__file__).with_name('replay.py')
        command = [sys.executable, '-B', str(script), name]
        for key, path in self.paths.items():
            command.extend(('--' + key, str(path)))
        output = subprocess.check_output(command, text=True)
        directory = Path(output.strip())
        try:
            manifest = json.loads((directory / 'manifesto.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['cadence'], 10)
            self.assertEqual(len(manifest['inputs']), 7)
            self.assertEqual(len(manifest['output_sha256']), 10)
            for filename, fields in [('rankings.csv', RANK_FIELDS),
                                     ('overhead.csv', OVERHEAD_FIELDS)]:
                with (directory / filename).open(newline='', encoding='utf-8') as stream:
                    reader = csv.DictReader(stream)
                    self.assertEqual(tuple(reader.fieldnames), fields)
                    self.assertTrue(list(reader))
        finally:
            for path in directory.iterdir():
                path.unlink()
            directory.rmdir()


if __name__ == '__main__':
    unittest.main()
