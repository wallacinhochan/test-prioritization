import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from auditar_treino_expansao import BASE, LOT_03, PUBLICATION, piloto, prepare, run
from expansao50 import SHA, frozen_input


class AuditTest(unittest.TestCase):
    def test_complete_window_and_frozen_rankings(self):
        report, training = prepare(LOT_03)
        self.assertEqual(report['treino'], {
            'linhas': 524, 'alvos_positivos': 181, 'fracao_positivos': '181/524', 'suficiente': True,
        })
        self.assertEqual([row['intersecao']['metodos'] for row in report['revisoes'].values()],
                         [318, 56, 153])
        frozen = BASE / 'expansao50-experimental-v1'
        ids, *_ = frozen_input()
        manifest = json.loads((frozen / 'manifesto.json').read_bytes())
        self.assertEqual(manifest['treino']['auditoria'], report)
        for name, expected in manifest['sha256_saida'].items():
            self.assertEqual(piloto.digest((frozen / name).read_bytes()), expected)
        with TemporaryDirectory(dir=BASE) as temporary:
            repeated = Path(temporary) / 'repeated'
            run(repeated, training=training, training_audit=report)
            for name in ('treino_sintetico.csv', 'features_inferencia.csv', 'auditoria_rotas.csv'):
                self.assertEqual((repeated / name).read_bytes(), (frozen / name).read_bytes())
            rows = []
            for directory in (frozen, repeated):
                ranks = list(piloto.records((directory / 'rankings.csv').read_bytes()))
                self.assertEqual(len(ranks), 832)
                for scenario in ('T2', 'T3'):
                    subset = [r for r in ranks if r['scenario'] == scenario]
                    self.assertCountEqual([(r['commit_sha'], r['test_id']) for r in subset],
                                          [(SHA, method) for method in ids])
                    self.assertEqual([int(r['rank']) for r in subset], list(range(1, 417)))
                    self.assertEqual(subset, sorted(subset, key=lambda r: (
                        -float(r['score']), piloto.ordinal(r['test_id']))))
                rows.append([tuple(value for key, value in r.items() if key != 'source_ref')
                             for r in ranks])
            self.assertEqual(*rows)

    def test_versioned_replay_and_incomplete_window(self):
        report, rows = prepare(PUBLICATION)
        revisions = report['revisoes']
        self.assertEqual([r['pacote']['alvos_positivos'] for r in revisions.values()],
                         [185, 10, 15])
        self.assertEqual(revisions['15']['estado_t1'], 'indisponivel')
        self.assertEqual(revisions['42']['estado_t1'], 'indisponivel')
        self.assertEqual(revisions['26']['intersecao'], {
            'metodos': 56, 'alvos_conhecidos': 53, 'alvos_positivos': 9, 'alvos_zero': 44,
            'induced_failure': 11, 'pass': 201, 'unknown': 12, 'ausente': 0,
        })
        self.assertEqual(len({(row[1], row[2]) for row in rows}), 53)
        self.assertEqual({row[0] for row in rows}, {26})
        self.assertFalse(report['treino']['suficiente'])
