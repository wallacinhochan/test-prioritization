import argparse
import csv
import json
import math
from io import StringIO

from ranking import (BASE, OVERHEAD_FIELDS, RANK_FIELDS, SCENARIO, digest, ordinal,
                     published, records, require, verified, write_json)


def check_run(directory):
    manifest = json.loads((directory / 'manifesto.json').read_bytes())
    artifacts = {name: verified(directory / name, sha256)
                 for name, sha256 in manifest['output_sha256'].items()}
    ranking = records(artifacts['rankings.csv'])
    overhead = records(artifacts['overhead.csv'])
    require(tuple(ranking.fieldnames) == RANK_FIELDS
            and tuple(overhead.fieldnames) == OVERHEAD_FIELDS, 'Cabeçalho KAN-15 divergente.')
    ranking = list(ranking)
    overhead = list(overhead)
    formal = json.loads(published('KAN-18/verificacao.json'))
    expected_positions = [entry['posicao'] for entry in formal if entry['posicao'] > 42]
    require(expected_positions == manifest['inference']['positions'], 'Cobertura incompatível.')
    require([entry['position'] for entry in manifest['coverage']
             if entry['status'] == 'sem_ranking_por_anterioridade'] == [1, 2, 26],
            'Cobertura anterior ao corte incompatível.')
    expected_order = []
    expected_phases = set()
    for entry in sorted(formal, key=lambda item: item['posicao']):
        position, sha = entry['posicao'], entry['sha']
        if position not in expected_positions:
            continue
        t1_dir = BASE.parent / 'KAN-18' / 'local' / 'selecao' / sha
        hashes = entry['saidas_sha256']
        t1 = list(records(verified(t1_dir / 'rankings.csv', hashes['rankings.csv'])))
        group = [row for row in ranking if row['commit_sha'] == sha]
        scores = [float(row['score']) for row in group]
        require(len(group) == len(t1) and {row['test_id'] for row in group}
                == {row['test_id'] for row in t1}, f'Chaves T3 divergentes: {position}')
        require(all(math.isfinite(score) for score in scores)
                and [int(row['rank']) for row in group] == list(range(1, len(t1) + 1))
                and [(-score, ordinal(row['test_id'])) for score, row in zip(scores, group)]
                == sorted((-score, ordinal(row['test_id'])) for score, row in zip(scores, group)),
                f'Postos ou escores inválidos: {position}')
        expected_order.extend(group)
        expected_phases.update((sha, phase) for phase in ('selection', 'features', 'inference'))
        t1_cost, = records(verified(t1_dir / 'overhead.csv', hashes['overhead.csv']))
        t3_cost, = (row for row in overhead if row['commit_sha'] == sha and row['phase'] == 'selection')
        require(all(t1_cost[field] == t3_cost[field] for field in OVERHEAD_FIELDS if field != 'scenario'),
                f'Custo compartilhado incompatível: {position}')

    training = manifest['training']
    expected_phases.add((training['available_from_sha'], 'training'))
    require(expected_order == ranking and {row['scenario'] for row in ranking} == {SCENARIO},
            'Ordem de exportação ou cenário divergente.')
    require({(row['commit_sha'], row['phase']) for row in overhead} == expected_phases
            and len(overhead) == len(expected_phases)
            and {row['scenario'] for row in overhead} == {SCENARIO}, 'Fases T3 divergentes.')
    durations = {training['available_from_sha']: training['fit_ns']}
    inference_ns = {entry['commit_sha']: manifest['inference']['elapsed_ns'][str(entry['position'])]
                    for entry in manifest['coverage'] if entry['position'] in expected_positions}
    for row in overhead:
        sha, phase = row['commit_sha'], row['phase']
        if phase == 'features':
            require(row['measurement_status'] == 'unknown' and row['duration_ms'] == '',
                    'A extração de features deve manter custo desconhecido.')
        if phase in ('training', 'inference'):
            elapsed = (durations if phase == 'training' else inference_ns)[sha]
            require(row['measurement_status'] == 'measured'
                    and float(row['duration_ms']) == elapsed / 1_000_000 and elapsed > 0,
                    f'Medição inválida: {phase} em {sha}')

    comparison = StringIO(newline='')
    writer = csv.DictWriter(comparison, RANK_FIELDS[:-1], extrasaction='ignore', lineterminator='\n')
    writer.writeheader()
    writer.writerows(ranking)
    return manifest, comparison.getvalue().encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description='Verifica duas execuções T3 da KAN-21.')
    parser.add_argument('first')
    parser.add_argument('second')
    parser.add_argument('--resumo', help='Nome do resumo, sob local/')
    args = parser.parse_args()
    require(args.first != args.second, 'Indique duas execuções distintas.')
    names = (args.first, args.second)
    checked = [check_run(BASE / 'local' / name) for name in names]
    (first, ranking_a), (second, ranking_b) = checked
    require(ranking_a == ranking_b, 'Rankings ou escores divergentes.')
    fields = ('publication', 'inputs', 'coverage', 'estimator', 'parameters',
              'environment', 'code_sha256', 'features', 'iteration')
    require(all(first[field] == second[field] for field in fields),
            'Configuração ou insumos divergentes entre execuções.')
    summary = {field: first[field] for field in fields}
    summary['ranking_without_source_ref_sha256'] = digest(ranking_a)
    summary['runs'] = {name: {field: manifest[field] for field in
                             ('training', 'inference', 'output_sha256')}
                       for name, (manifest, _) in zip(names, checked)}
    if args.resumo:
        write_json(BASE / 'local' / args.resumo, summary)
    print('Chaves, cobertura, postos, escores e overhead verificados nas duas execuções.')


if __name__ == '__main__':
    main()
