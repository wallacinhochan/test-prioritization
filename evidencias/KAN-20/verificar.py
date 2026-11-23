"""Confere duas rodadas T2 contra a mesma publicação e registra a reprodução."""
import argparse

from ordenar import (BASE, OVERHEAD_FIELDS, RANK_FIELDS, Path, SCENARIO,
                     checked, isfinite, json, load_inputs, milliseconds, piloto)


def verify(run, inputs, expected):
    directory = BASE / 'local' / run
    manifest = json.loads((directory / 'manifesto.json').read_bytes())
    for key, value in expected.items():
        piloto.require(manifest[key] == value, f'{run}: manifesto divergente em {key}')
    hashes = manifest['sha256_saida']
    checked(directory / 'knn.joblib', hashes['knn.joblib'])
    ranks = piloto.records(checked(directory / 'rankings.csv', hashes['rankings.csv']))
    costs = piloto.records(checked(directory / 'overhead.csv', hashes['overhead.csv']))
    piloto.require(tuple(ranks.fieldnames) == RANK_FIELDS and
                   tuple(costs.fieldnames) == OVERHEAD_FIELDS, 'Cabeçalho inválido')
    source = f'evidencias/KAN-20/local/{run}/manifesto.json'
    tuples, overhead = [], []
    training = manifest['training']
    overhead.append((inputs[0][0], SCENARIO, 'training', 'measured',
                     milliseconds(training['duracao_ns']), f'{source}#training'))
    for sha, methods, _, t1 in inputs:
        order = []
        for rank in range(1, len(methods) + 1):
            row = next(ranks)
            score = float(row['score'])
            piloto.require((row['commit_sha'], row['scenario'], row['rank'], row['source_ref']) ==
                           (sha, SCENARIO, str(rank), f'{source}#modelo') and isfinite(score),
                           f'{run}: linha de ranking inválida em {sha}/{rank}')
            order.append((row['test_id'], score))
            tuples.append((sha, row['test_id'], rank, row['score']))
        items, scores = zip(*order)
        piloto.require(set(items) == set(methods) and
                       order == piloto.rank_scores(items, scores),
                       f'{run}: conjunto ou ordenação divergente em {sha}')
        elapsed = manifest['inference']['duracao_ns_por_sha'][sha]
        overhead.extend([
            (sha, SCENARIO, 'selection', *(t1[k] for k in OVERHEAD_FIELDS[3:])),
            (sha, SCENARIO, 'features', 'unknown', '', f'{source}#features'),
            (sha, SCENARIO, 'inference', 'measured', milliseconds(elapsed),
             f'{source}#inference'),
        ])
    piloto.require(next(ranks, None) is None and
                   [tuple(row[k] for k in OVERHEAD_FIELDS) for row in costs] == overhead,
                   f'{run}: linhas excedentes ou overhead divergente')
    return tuples, {
        'rodada': run, 'training_ns': training['duracao_ns'],
        'inference_ns_por_sha': manifest['inference']['duracao_ns_por_sha'],
        'sha256_saida': hashes,
    }, manifest


def main(args):
    piloto.require(args.first != args.second, 'Informe duas rodadas distintas')
    _, _, inputs, expected = load_inputs(args.train, args.features)
    first, evidence_a, manifest_a = verify(args.first, inputs, expected)
    second, evidence_b, manifest_b = verify(args.second, inputs, expected)
    piloto.require(first == second and manifest_a['modelo'] == manifest_b['modelo'] and
                   manifest_a['codigo_sha256'] == manifest_b['codigo_sha256'] and
                   manifest_a['ambiente'] == manifest_b['ambiente'],
                   'Scores, chaves, ordens ou condições divergentes entre rodadas')
    report = {**expected, 'linhas_ranking_reproduzidas': len(first),
              'modelo': manifest_a['modelo'], 'ambiente': manifest_a['ambiente'],
              'codigo_sha256': manifest_a['codigo_sha256'],
              'rodadas': [evidence_a, evidence_b]}
    piloto.write_json(args.report, report)
    print(f'{len(first)} linhas com chaves, postos e scores idênticos')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('first')
    parser.add_argument('second')
    parser.add_argument('--train', type=Path, required=True)
    parser.add_argument('--features', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    main(parser.parse_args())
