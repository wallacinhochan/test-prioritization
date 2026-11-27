import csv
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import validar_dirts as vd


HOLDOUT_SHA = '5454931eb735deb59e9b671fd8a14cd4c14d8272'
POS_58_SHA = 'c04469163d86bdd10f4aa409c1a694c87c467d2a'
POS_59_SHA = '7b77ea4cfb73399e0dde72a8ab7742a2da5796d0'
POS_60_SHA = '21e65f8b312c6608b554e4f551315fb0651c3277'


class ValidarDirtsLot04Test(unittest.TestCase):
    def test_lot_04_reproducible_and_matches_versioned_report(self):
        versioned = json.loads(
            (vd.BASE / 'validacao-dirts-lote-04.json').read_text(encoding='utf-8')
        )
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_a = root / 'a'
            out_b = root / 'b'
            rep_a = vd.validate(out_a, profile='04')
            rep_b = vd.validate(out_b, profile='04')

            for artifact in ('commits.csv', 'selection.csv', 'rankings.csv'):
                self.assertEqual(rep_a['output_sha256'][artifact], rep_b['output_sha256'][artifact])
                self.assertEqual(
                    rep_a['output_sha256'][artifact], versioned['output_sha256'][artifact]
                )

            self.assertEqual(
                rep_a['coverage_counts'],
                {'missing_t1': 82, 'no_model': 11, 'ranked': 6, 'excluded_holdout': 1},
            )
            self.assertEqual(
                rep_a['ranked_selection_cost_positions'],
                {'measured': [58, 59, 60], 'unknown': [64, 75, 100]},
            )
            self.assertEqual(rep_a['release']['historical_ranking_rows'], 0)
            self.assertEqual(
                set(rep_a['sources']['selection_lots']),
                {
                    'congelado-expansao-v1',
                    'congelado-expansao-lote-02',
                    'congelado-expansao-lote-03',
                    'congelado-expansao-lote-04',
                },
            )

            # Holdout 96 não entra em nenhuma tabela materializada de consumo
            for filename in ('selection.csv', 'rankings.csv', 'overhead.csv'):
                with (out_a / filename).open(encoding='utf-8', newline='') as fh:
                    shas = {row['commit_sha'] for row in csv.DictReader(fh)}
                self.assertNotIn(HOLDOUT_SHA, shas)

            # Custos medidos em 58-60 e treinamento atribuído uma vez por cenário na pos 58
            with (out_a / 'overhead.csv').open(encoding='utf-8', newline='') as fh:
                overhead_rows = list(csv.DictReader(fh))
            training_rows = [r for r in overhead_rows if r['phase'] == 'training']
            self.assertEqual(len(training_rows), 2)
            self.assertEqual({r['scenario'] for r in training_rows}, {'T2', 'T3'})
            self.assertEqual({r['commit_sha'] for r in training_rows}, {POS_58_SHA})

            expected_sel = {POS_58_SHA: '520303', POS_59_SHA: '148021', POS_60_SHA: '151683'}
            for sha, expected_ms in expected_sel.items():
                for scenario in ('T1', 'T2', 'T3'):
                    matches = [
                        r for r in overhead_rows
                        if r['commit_sha'] == sha
                        and r['scenario'] == scenario
                        and r['phase'] == 'selection'
                    ]
                    self.assertEqual(len(matches), 1)
                    self.assertEqual(matches[0]['measurement_status'], 'measured')
                    self.assertEqual(matches[0]['duration_ms'], expected_ms)
                for scenario in ('T2', 'T3'):
                    for phase in ('features', 'inference'):
                        matches = [
                            r for r in overhead_rows
                            if r['commit_sha'] == sha
                            and r['scenario'] == scenario
                            and r['phase'] == phase
                        ]
                        self.assertEqual(len(matches), 1)
                        self.assertEqual(matches[0]['measurement_status'], 'measured')

    def test_lot_03_profile_preserves_historical_selection_and_coverage(self):
        hist = json.loads((vd.BASE / 'validacao-dirts.json').read_text(encoding='utf-8'))
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / 'lote03'
            rep = vd.validate(out, profile='03')
            self.assertEqual(rep['coverage_counts'], hist['coverage_counts'])
            for artifact in ('commits.csv', 'selection.csv', 'rankings.csv'):
                self.assertEqual(rep['output_sha256'][artifact], hist['output_sha256'][artifact])
            self.assertEqual(
                rep['ranked_selection_cost_positions'],
                {'measured': [], 'unknown': [64, 75, 100]},
            )


if __name__ == '__main__':
    unittest.main()
