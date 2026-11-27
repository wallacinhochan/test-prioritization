import json
import os
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from dirts import BASE, FEATURES, load_revision, piloto, run, vector


class DirtsTest(unittest.TestCase):
    def test_vector(self):
        self.assertEqual(vector('p.Test$Nested#check(int,java.lang.String[])'), (5, 2, 1))
        self.assertEqual(vector('p.Test#check()'), (5, 0, 0))
        with self.assertRaises(ValueError):
            vector('p.Test#check')

    @unittest.skipUnless(os.environ.get('KAN18_DIRTS'), 'Requer KAN18_DIRTS')
    def test_publication_and_reproduction(self):
        local = Path(os.environ['KAN18_DIRTS'])
        publication = json.loads((BASE.parent / 'KAN-18' / 'verificacao-dirts.json').read_bytes())
        recorte = (BASE.parent / 'KAN-10' / 'commits.csv').read_bytes()
        commits = {int(row['position']): row for row in piloto.records(recorte)}
        with TemporaryDirectory(dir=BASE) as tmp:
            tmp = Path(tmp)
            outputs = [tmp / suffix for suffix in ('a', 'b')]
            for output in outputs:
                run(local, output)
            self.assertEqual(*(path.joinpath('features_inferencia.csv').read_bytes() for path in outputs))
            normalized = []
            for output in outputs:
                features = list(piloto.records((output / 'features_inferencia.csv').read_bytes()))
                ranks = list(piloto.records((output / 'rankings.csv').read_bytes()))
                report = json.loads((output / 'manifesto.json').read_bytes())
                self.assertEqual(report['estado'], 'provisorio_fixture')
                for name, expected in report['sha256_saida'].items():
                    self.assertEqual(piloto.digest((output / name).read_bytes()), expected)
                for reference in publication['revisoes']:
                    sha = reference['sha']
                    t1 = list(piloto.records((local / 'selecao' / sha / 'rankings.csv').read_bytes()))
                    methods = [row['test_id'] for row in t1]
                    actual = [row for row in features if row['commit_sha'] == sha]
                    self.assertEqual([row['test_id'] for row in actual], methods)
                    self.assertEqual(tuple(actual[0])[-3:], FEATURES)
                    for scenario in ('T2', 'T3'):
                        rows = [r for r in ranks if (r['commit_sha'], r['scenario']) == (sha, scenario)]
                        self.assertEqual(len(rows), len(methods))
                        self.assertEqual({row['test_id'] for row in rows}, set(methods))
                        self.assertEqual([int(row['rank']) for row in rows],
                                         list(range(1, len(methods) + 1)))
                        self.assertEqual(rows, sorted(rows, key=lambda row: (
                            -float(row['score']), piloto.ordinal(row['test_id']))))
                normalized.append([tuple(value for key, value in row.items() if key != 'source_ref')
                                   for row in ranks])
            self.assertEqual(*normalized)

            reference = publication['revisoes'][0]
            sha = reference['sha']
            tampered = tmp / 'tampered'
            target = tampered / 'selecao' / sha
            shutil.copytree(local / 'selecao' / sha, target)
            with (target / 'rankings.csv').open('ab') as stream:
                stream.write(b'\n')
            with self.assertRaises(ValueError):
                load_revision(tampered, publication, reference, commits[reference['posicao']],
                              piloto.digest(recorte))


if __name__ == '__main__':
    unittest.main()
