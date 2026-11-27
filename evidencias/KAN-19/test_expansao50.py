import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from expansao50 import BASE, SHA, piloto, published, route_fields, run


class Expansao50Test(unittest.TestCase):
    def test_route_without_evidence(self):
        fields = route_fields({'classe_raiz': 'p.Test', 'estado_rota': 'sem_evidencia_rota',
                               'sementes_diretas': '', 'jdeps_evidencia': ''})
        self.assertEqual(fields, ('sem_evidencia_rota', None, None, None, None, '', ''))

    def test_exact_keys_and_reproduction(self):
        t1 = [r['test_id'] for r in piloto.records(published('rankings.csv'))
              if r['commit_sha'] == SHA]
        with TemporaryDirectory(dir=BASE) as temporary:
            runs = [Path(temporary) / name for name in ('a', 'b')]
            normalized = []
            feature_bytes = []
            for output in runs:
                run(output)
                report = json.loads((output / 'manifesto.json').read_bytes())
                self.assertEqual(report['estado'], 'teste_tecnico_fixture_sem_ranking_experimental')
                for name, expected in report['sha256_saida'].items():
                    self.assertEqual(piloto.digest((output / name).read_bytes()), expected)
                features = (output / 'features_inferencia.csv').read_bytes()
                feature_bytes.append(features)
                self.assertEqual([(row['commit_sha'], row['test_id']) for row in piloto.records(features)],
                                 [(SHA, method) for method in t1])
                ranks = list(piloto.records((output / 'rankings_fixture.csv').read_bytes()))
                self.assertEqual(len(ranks), 2 * len(t1))
                for scenario in ('T2', 'T3'):
                    rows = [row for row in ranks if row['scenario'] == scenario]
                    self.assertCountEqual([(row['commit_sha'], row['test_id']) for row in rows],
                                          [(SHA, method) for method in t1])
                    self.assertEqual([int(row['rank']) for row in rows], list(range(1, 417)))
                    self.assertEqual(rows, sorted(rows, key=lambda row: (
                        -float(row['score']), piloto.ordinal(row['test_id']))))
                normalized.append([tuple(row[key] for key in ('commit_sha', 'scenario', 'test_id',
                                                             'rank', 'score')) for row in ranks])
            self.assertEqual(*feature_bytes)
            self.assertEqual(*normalized)


if __name__ == '__main__':
    unittest.main()
