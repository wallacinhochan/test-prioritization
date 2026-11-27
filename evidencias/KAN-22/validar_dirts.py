"""Valida a KAN-22 sobre os artefatos imutaveis da expansao DIRTS."""
import argparse
import json
import platform
import re
from collections import Counter, defaultdict
from importlib.metadata import version
from pathlib import Path
from time import perf_counter_ns

from replay import (AVAILABILITY_FIELDS, BASE, FEATURES, KEYS, OVERHEAD_FIELDS, RANK_FIELDS,
                    SELECTION_FIELDS, digest, load_inputs, records, replay, require, write_csv,
                    write_json)
from piloto import git

LOTS = {
    'congelado-expansao-v1': 'ef577158bc012d87784bbfab1b9ccb4ee80cf812',
    'congelado-expansao-lote-02': '41a22e394de36512921bad82a4a28d029d8bb55f',
    'congelado-expansao-lote-03': 'ba7f204693007f18db648fdf16e34f52c62397f7',
}
FREEZE = 'a06d381c7a9e0fc896e7c5ae84d94a452eedc56a'
TRAINING = '1070e62788e9a180539c9df7ca10b65d48ee978c'
FROZEN = 'evidencias/KAN-19/expansao50-experimental-v1'
FEATURE_FIELDS = FEATURES[-3:]
CHECKPOINT = 50
HOLDOUT = 96
REFERENCE = 'evidencias/KAN-22/validacao-dirts.json'
T1_FIELDS = {'selection': SELECTION_FIELDS, 't1': RANK_FIELDS, 'overhead': OVERHEAD_FIELDS}


def blob(commit, path, sha256=None):
    data = git('show', f'{commit}:{path}')
    require(sha256 is None or digest(data) == sha256, f'Hash divergente: {commit}:{path}')
    return data


def signature(test_id):
    # Mesma politica expansao-direta/assinatura-v1 da KAN-19 dirts.py.
    match = re.fullmatch(r'([^#]+)#([^()]+)\(([^()]*)\)', test_id)
    require(match is not None, f'Identidade JUnit invalida: {test_id}')
    binary_class, name, parameters = match.groups()
    return len(name), parameters.count(',') + 1 if parameters else 0, int('$' in binary_class)


def prepare(work):
    manifest_raw = blob(FREEZE, f'{FROZEN}/manifesto.json')
    frozen = json.loads(manifest_raw)
    audit = frozen['treino']['auditoria']
    require(tuple(frozen['features_modelo']) == FEATURE_FIELDS and
            frozen['politica_features'] == 'expansao-direta/assinatura-v1' and
            frozen['posicao'] == CHECKPOINT and audit['publicacao_pacote'] == TRAINING,
            'Manifesto de treino incompativel')
    files = {}
    sources = {'training_package': TRAINING, 'training_checksums_sha256': audit['checksums_sha256'],
               'ranking_freeze': FREEZE, 'ranking_freeze_manifest_sha256': digest(manifest_raw),
               'selection_lots': {}}

    def materialize(name, fields, rows):
        files[name] = work / f'{name}.csv'
        write_csv(files[name], fields, rows)

    tables = defaultdict(list)
    raw_commits = None
    for lot, commit in LOTS.items():
        bundle = f'evidencias/KAN-18/{lot}'
        raw = blob(commit, f'{bundle}/manifesto.json', audit['manifestos_t1_sha256'][commit])
        manifest = json.loads(raw)
        hashes = manifest['saidas_sha256']
        if raw_commits is None:
            raw_commits = blob(commit, f'{bundle}/commits.csv', hashes['commits.csv'])
            commits = {int(r['commit_order']): r['commit_sha'] for r in records(raw_commits)}
        sources['selection_lots'][lot] = {
            'commit': commit, 'manifest_sha256': digest(raw),
            'seen_positions': sorted(r['posicao'] for r in manifest['revisoes'].values()
                                     if r['posicao'] != HOLDOUT),
        }
        for name, filename in [('selection', 'selection.csv'), ('t1', 'rankings.csv'),
                               ('overhead', 'overhead.csv')]:
            data = blob(commit, f'{bundle}/{filename}', hashes[filename])
            # O lote misto e verificado byte a byte. A posicao 96 e descartada antes do uso.
            tables[name].extend(r for r in records(data) if r['commit_sha'] != commits[HOLDOUT])

    materialize('commits', KEYS[:2], sorted(commits.items()))
    (work.parent / 'commits.csv').write_bytes(raw_commits)
    for name, fields in T1_FIELDS.items():
        materialize(name, fields, (tuple(r[field] for field in fields) for r in tables[name]))

    training_raw = blob(FREEZE, f'{FROZEN}/treino_sintetico.csv',
                        frozen['sha256_saida']['treino_sintetico.csv'])
    training = list(records(training_raw))
    known = Counter(int(r['position']) for r in training)
    selected = {(r['commit_sha'], r['test_id']) for r in tables['selection']
                if r['selected'] == 'true'}
    require(known == {15: 318, 26: 53, 42: 153} and
            sum(float(r['target_synthetic']) > 0 for r in training) == 181 and
            all((r['commit_sha'], r['test_id']) in selected and
                tuple(int(r[f]) for f in FEATURE_FIELDS) == signature(r['test_id'])
                for r in training), 'Treino incompatível com os lotes T1')
    train_fields = (*KEYS, *FEATURE_FIELDS, 'partition', 'target_synthetic')
    materialize('train', train_fields, (tuple(r.get(f, 'treino') for f in train_fields)
                                       for r in training))

    positions = {sha: pos for pos, sha in commits.items()}
    rows_by_sha = defaultdict(list)
    for row in tables['t1']:
        rows_by_sha[row['commit_sha']].append(row)
    features, feature_time = [], {}
    for sha, rows in rows_by_sha.items():
        ordered = sorted(rows, key=lambda r: int(r['rank']))
        start = perf_counter_ns()
        features.extend((positions[sha], sha, row['test_id'], *signature(row['test_id']))
                        for row in ordered)
        feature_time[sha] = perf_counter_ns() - start
    raw = blob(FREEZE, f'{FROZEN}/features_inferencia.csv',
               frozen['sha256_saida']['features_inferencia.csv'])
    expected = [tuple(r.values()) for r in records(raw)]
    actual = [tuple(map(str, r)) for r in features if r[0] == CHECKPOINT]
    require(actual == expected and len(actual) == 416, 'Vetores divergentes na revisao 50')
    materialize('features', (*KEYS, *FEATURE_FIELDS), features)

    frozen_ranks = blob(FREEZE, f'{FROZEN}/rankings.csv',
                        frozen['sha256_saida']['rankings.csv'])
    expected_methods = {r[2] for r in actual}
    by_scenario = defaultdict(list)
    for row in records(frozen_ranks):
        require(row['commit_sha'] == commits[CHECKPOINT], 'SHA divergente no ranking congelado')
        by_scenario[row['scenario']].append(row)
    require(set(by_scenario) == {'T2', 'T3'} and
            all({r['test_id'] for r in rows} == expected_methods and
                [int(r['rank']) for r in rows] == list(range(1, len(expected_methods) + 1))
                for rows in by_scenario.values()), 'Ranking congelado divergente de T1')

    release_ref = f'{FROZEN}/manifesto.json@{FREEZE}#treino'
    materialize('availability', AVAILABILITY_FIELDS,
                [(commits[pos], CHECKPOINT, release_ref) for pos in sorted(known)])
    sources['training_rows'] = dict(known)
    sources['training_positive_rows'] = 181
    sources['training_sha256'] = digest(training_raw)
    sources['reference_features_50_sha256'] = digest(raw)
    sources['reference_rankings_50_sha256'] = digest(frozen_ranks)
    return files, sources, tables, feature_time


def validate(output):
    work = output / 'entradas'
    work.mkdir(parents=True)
    files, sources, tables, feature_time = prepare(work)
    commits, labels, releases, features, costs, inputs = load_inputs(files, FEATURE_FIELDS)
    historical = replay(commits, [], {}, features, costs, REFERENCE,
                        feature_fields=FEATURE_FIELDS)
    require(not historical[0] and not historical[1] and not historical[4],
            'O replay historico deve ficar sem ajustes e rankings')

    ranks, overhead, windows, coverage, fits = replay(
        commits, labels, releases, features, costs, REFERENCE, feature_fields=FEATURE_FIELDS)
    require([w['decision_position'] for w in windows] == list(range(11, 100, 10)) and
            [w['eligible_rows'] for w in windows] == [0] * 4 + [524] * 5 and
            [w['status'] for w in windows] ==
            ['insufficient_labels'] * 4 + ['fit'] + ['no_new_labels'] * 4 and
            list(fits) == ['janela-50'], 'Cadencia ou corte de liberacao divergente')
    rank_counts = Counter((r[0], r[1]) for r in ranks)
    require(rank_counts == {(commits[p], scenario): n for p, n in [(64, 26), (75, 7), (100, 4663)]
                            for scenario in ('T2', 'T3')}, 'Cobertura de rankings divergente')
    require(all(row[0] == commits[64] for row in overhead if row[2] == 'training') and
            sum(row[2] == 'training' for row in overhead) == 2, 'Atribuicao de treino divergente')

    expected = defaultdict(set)
    for row in tables['t1']:
        expected[row['commit_sha']].add(row['test_id'])
    for key in rank_counts:
        rows = [r for r in ranks if r[:2] == key]
        require({r[2] for r in rows} == expected[key[0]] and
                [r[3] for r in rows] == list(range(1, len(rows) + 1)),
                f'Populacao KAN-15 invalida: {key}')

    for entry, hist in zip(coverage, historical[3]):
        entry['historical_status'] = hist['status']
        if entry['position'] == HOLDOUT:
            entry.update(status='excluded_holdout', historical_status='excluded_holdout')
        if entry['status'] == 'ranked':
            entry['feature_ns'] = feature_time[entry['commit_sha']]
            entry['selection_measurement_status'] = costs[entry['commit_sha']]['measurement_status']
    for index, (sha, scenario, phase, *_) in enumerate(overhead):
        if phase == 'features':
            overhead[index] = (sha, scenario, phase, 'measured', feature_time[sha] / 1_000_000,
                               REFERENCE + '#coverage')

    write_csv(output / 'rankings.csv', RANK_FIELDS,
              [tuple(row[f] for f in RANK_FIELDS) for row in tables['t1']] + ranks)
    write_csv(output / 'overhead.csv', OVERHEAD_FIELDS,
              [tuple(row[f] for f in OVERHEAD_FIELDS) for row in tables['overhead']] + overhead)
    write_csv(output / 'selection.csv', SELECTION_FIELDS,
              (tuple(row[f] for f in SELECTION_FIELDS) for row in tables['selection']))
    report = {
        'data_kind': 'technical_synthetic_replay', 'contract_version': '0.1.0',
        'cadence': 10, 'features': FEATURE_FIELDS, 'sources': sources,
        'release': {'kind': 'experimental_checkpoint', 'position': CHECKPOINT,
                    'historical_position': None, 'source_ref': next(iter(releases.values()))['source_ref'],
                    'historical_ranking_rows': len(historical[0])},
        'input_sha256': {name: item['sha256'] for name, item in inputs.items()},
        'window_log': windows, 'coverage': coverage,
        'coverage_counts': dict(Counter(r['status'] for r in coverage)),
        'output_sha256': {name: digest((output / name).read_bytes())
                          for name in ('commits.csv', 'selection.csv', 'rankings.csv', 'overhead.csv')},
        'environment': {'python': platform.python_version(), 'scikit-learn': version('scikit-learn'),
                        'clock': 'perf_counter_ns', 'cache': 'uncontrolled'},
    }
    write_json(output / 'validacao-dirts.json', report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', help='Novo diretorio sob local/')
    args = parser.parse_args()
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.run), 'Nome de rodada invalido')
    validate(BASE / 'local' / args.run)
