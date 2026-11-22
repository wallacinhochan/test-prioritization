import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import piloto


class PilotoTest(unittest.TestCase):
    def test_denominator_excludes_unknowns_and_absences(self):
        mutations = ['a', 'b', 'c', 'd']
        labels = {('a', 'x'): 'induced_failure', ('b', 'x'): 'pass',
                  ('c', 'x'): 'unknown'}
        totals = piloto.aggregate(labels, mutations, ['x', 'y'])
        self.assertEqual(piloto.target(totals['x']), 0.5)
        self.assertIsNone(piloto.target(totals['y']))
        self.assertEqual(piloto.denominators(totals, totals), {
            'induced_failure': 1, 'pass': 1, 'unknown': 1, 'ausente': 5,
            'denominador': 2, 'metodos': 2, 'metodos_com_alvo': 1})

    def test_detection_with_gap_and_without_detection(self):
        order = ['a', 'b', 'c', 'd']
        labels = {('m', 'a'): 'pass', ('m', 'b'): 'unknown',
                  ('m', 'd'): 'induced_failure'}
        result = piloto.detection(order, 'm', labels)
        self.assertEqual(result['primeira_posicao_observada'], 4)
        self.assertEqual(result['primeira_posicao_possivel'], 2)
        self.assertEqual(result['lacunas_antes'], 2)
        self.assertEqual(piloto.detection(order[:3], 'm', labels)['estado'], 'indeterminado')
        self.assertEqual(piloto.detection(order[:1], 'm', labels)['estado'], 'sem_deteccao')

    def test_ordinal_ties_and_static_features(self):
        self.assertEqual(piloto.rank_scores(['z', 'A', 'a'], [0, 0, 1]),
                         [('a', 1.0), ('A', 0.0), ('z', 0.0)])
        decision = {'rotas': {'Class': {'destino': 'Seed', 'evidencia': 'fonte'},
                             'Seed': None}, 'sementes': {'Seed': 'src'}}
        self.assertEqual(piloto.features('Class$Nested#method(int,long)', 'Class', decision),
                         (1, 0, 1, 0, 6, 2, 1))

    def test_closed_replay_is_rejected_before_path_access(self):
        with patch.object(piloto, 'BASE', None):
            with self.assertRaisesRegex(ValueError, 'fechada'):
                piloto.load_replay(96, {})

    def test_final_publication_must_follow_freeze_before_reading(self):
        with patch.object(piloto, 'git', side_effect=[b'older\n', b'older\n']) as git:
            with self.assertRaisesRegex(ValueError, 'suceder'):
                piloto.load_replay(96, {}, after_freeze='freeze')
        self.assertEqual([call.args[0] for call in git.call_args_list], ['log', 'merge-base'])

    def test_final_summary_must_bind_to_exact_freeze(self):
        reads = [b'newer\n', b'freeze\n', b'{"congelamento_modelo": {"commit": "other"}}', b'{}']
        with patch.object(piloto, 'git', side_effect=reads) as git:
            with self.assertRaisesRegex(ValueError, 'outro congelamento'):
                piloto.load_replay(96, {}, after_freeze='freeze')
        self.assertEqual([call.args[0] for call in git.call_args_list],
                         ['log', 'merge-base', 'show', 'show'])

    def test_real_t1_inputs_are_integral(self):
        for pos, size in zip((*piloto.DEVELOPMENT, piloto.FINAL), (4647, 4648, 4653, 4653, 4659)):
            with self.subTest(pos=pos):
                selection = piloto.frozen_selection(pos)
                self.assertEqual(len(selection['selected']), size)
                self.assertGreater(len(set(selection['methods'].values())), 1)

    def test_models_freeze_and_verify_artifacts_before_final_replay(self):
        selection = piloto.frozen_selection(26)
        small = selection['selected'][:25]
        selection = {**selection, 'selected': small,
                     'methods': {test_id: selection['methods'][test_id] for test_id in small}}
        labels = {('m', test_id): ('induced_failure' if index == 0 else 'pass')
                  for index, test_id in enumerate(small)}
        totals = piloto.aggregate(labels, ['m'], small)
        stats = piloto.denominators(totals, small)

        def replay(position, _selection):
            self.assertIn(position, piloto.DEVELOPMENT)
            return {'estado': 'disponivel', 't1': stats}, (['m'], labels, totals)

        scratch = piloto.BASE / 'local'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temp:
            output = Path(temp)
            with (patch.object(piloto, 'frozen_selection', return_value=selection),
                  patch.object(piloto, 'load_replay', side_effect=replay),
                  patch.object(piloto, 'workspace', return_value=output),
                  patch('builtins.print')):
                piloto.freeze('run')
            rows = list(piloto.records((output / 'ranking-96.csv').read_bytes()))
            self.assertTrue((output / 'congelamento.json').is_file())
            self.assertFalse((output / 'deteccao-96.json').exists())
            for name in ('T1', 'KNN', 'RandomForest'):
                entries = [row for row in rows if row['ranking'] == name]
                self.assertEqual({row['test_id'] for row in entries}, set(small))
                self.assertEqual([int(row['rank']) for row in entries],
                                 list(range(1, len(small) + 1)))

            final_labels = {('m', small[0]): 'induced_failure'}
            final_totals = piloto.aggregate(final_labels, ['m'], small)
            final_stats = piloto.denominators(final_totals, small)
            final_replay = (['m'], final_labels, final_totals)
            manifest = (output / 'congelamento.json').read_bytes()
            commit = 'a' * 40

            def frozen_git(command, *args):
                if command == 'rev-parse':
                    return commit.encode()
                self.assertEqual(command, 'show')
                name = args[0].rsplit('/', 1)[1]
                if name == 'congelamento.json':
                    return manifest
                return (piloto.BASE / name).read_bytes()

            with (patch.object(piloto, 'git', side_effect=frozen_git),
                  patch.object(piloto, 'frozen_selection', return_value=selection),
                  patch.object(piloto, 'load_replay',
                               return_value=({'estado': 'disponivel', 't1': final_stats},
                                             final_replay)) as load_replay,
                  patch('builtins.print')):
                piloto.final(output.name, commit, 'synthetic fixture')
                ranking = output / 'ranking-96.csv'
                ranking.write_bytes(ranking.read_bytes() + b'\n')
                with self.assertRaisesRegex(ValueError, 'Artefato divergente'):
                    piloto.final(output.name, commit, 'synthetic fixture')
                load_replay.assert_called_once_with(96, selection, after_freeze=commit)
                result = json.loads((output / 'teste-final.json').read_bytes())
                self.assertFalse(result['teste_final']['suficiente'])
                self.assertEqual(len(result['deteccoes']), 3)
