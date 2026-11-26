"""Testes de invariantes do balanceamento. Rodar com:
    python -m unittest test_balanceamento -v --  (de dentro da pasta dos dois arquivos)
Defina DADOS=<pasta dados> ou deixe o padrão do repositório."""
import os
import unittest
from pathlib import Path

import numpy as np

import comparar_balanceamento as cb

DADOS = os.environ.get('DADOS', 'evidencias/MUTACAO/modelos/entrega-replay/dados')


class TestBalanceamento(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.metodos, cls.obs = cb.carregar(DADOS)
        cls.treino, cls.valid = cb.particionar(cls.metodos)

    def test_contagens_originais(self):
        self.assertEqual((self.treino.alvo == 0).sum(), 13705)
        self.assertEqual((self.treino.alvo > 0).sum(), 210)

    def test_validacao_so_pos_50(self):
        self.assertEqual(set(self.valid.posicao), {50})
        self.assertEqual(set(self.treino.posicao), {15, 26, 42})

    def test_baseline_inalterado(self):
        out, w, _ = cb.balancear(self.treino, 'baseline')
        self.assertTrue(out.equals(self.treino))
        self.assertTrue((w == 1).all())

    def test_ponderacao_nao_altera_linhas(self):
        out, w, cfg = cb.balancear(self.treino, 'ponderacao')
        self.assertTrue(out.equals(self.treino))
        self.assertTrue((w[out.alvo > 0] > 1).all() and (w[out.alvo == 0] == 1).all())

    def test_oversampling_com_reposicao_e_sem_perder_zeros(self):
        out, _, cfg = cb.balancear(self.treino, 'oversampling')
        self.assertEqual(cfg['depois']['zeros'], 13705)
        self.assertGreater(cfg['depois']['positivos'], 210)
        # só linhas já existentes no treino
        self.assertTrue(set(out.test_id + out.sha).issubset(set(self.treino.test_id + self.treino.sha)))

    def test_undersampling_preserva_positivos_sem_reposicao(self):
        out, _, cfg = cb.balancear(self.treino, 'undersampling')
        self.assertEqual(cfg['depois']['positivos'], 210)
        self.assertLess(cfg['depois']['zeros'], 13705)
        zeros = out[out.alvo == 0]
        self.assertFalse(zeros.duplicated(['sha', 'test_id']).any())

    def test_alvo_continuo_preservado(self):
        for e in cb.ESTRATEGIAS:
            out, _, _ = cb.balancear(self.treino, e)
            pos = out[out.alvo > 0].alvo
            self.assertTrue(((pos > 0) & (pos <= 1)).all())
            self.assertGreater(pos.nunique(), 1)  # não virou binário

    def test_reprodutibilidade(self):
        for e in cb.ESTRATEGIAS:
            a = cb.balancear(self.treino, e)[0]
            b = cb.balancear(self.treino, e)[0]
            self.assertTrue(a.equals(b), e)

    def test_nao_vaza_validacao(self):
        for e in cb.ESTRATEGIAS:
            out, _, _ = cb.balancear(self.treino, e)
            self.assertFalse(set(out.sha) & set(self.valid.sha))

    def test_ranking_completo_e_mesmo_conjunto(self):
        ids = None
        for e in cb.ESTRATEGIAS:
            r, _ = cb.treinar_e_ranquear(self.treino, self.valid, e)
            self.assertEqual(len(r), len(self.valid))
            self.assertEqual(r.test_id.nunique(), len(r))
            if ids is None:
                ids = set(r.test_id)
            self.assertEqual(set(r.test_id), ids)
            # ordem: escore desc, desempate por test_id
            ok = all((a > b) or (a == b and x < y) for a, b, x, y in zip(
                r.escore, r.escore[1:], r.test_id, r.test_id[1:]))
            self.assertTrue(ok, e)

    def test_features_sem_vazamento(self):
        self.assertEqual(len(cb.FEATURES), 7)
        for proibida in ('alvo', 'induced_failure', 'pass', 'unknown', 'ausente',
                         'duracao_intacto_ms', 'duracao_ms'):
            self.assertNotIn(proibida, cb.FEATURES)


if __name__ == '__main__':
    unittest.main()