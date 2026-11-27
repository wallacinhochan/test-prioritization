import unittest

from auditar_treino_expansao import PUBLICATION, prepare


class AuditTest(unittest.TestCase):
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
