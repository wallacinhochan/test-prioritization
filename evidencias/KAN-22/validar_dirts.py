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

LOTS_03 = {
    'congelado-expansao-v1': 'ef577158bc012d87784bbfab1b9ccb4ee80cf812',
    'congelado-expansao-lote-02': '41a22e394de36512921bad82a4a28d029d8bb55f',
    'congelado-expansao-lote-03': 'ba7f204693007f18db648fdf16e34f52c62397f7',
}
LOT_04_COMMIT = '767f08b6dc2fe203d925bd9f97883028c3af551d'
LOT_04_MANIFEST_SHA256 = '0dffd291d16d20966f7cce60c87eea621c6d9cfe94757daf017d1fc346da19b8'
LOTS_04 = {
    **LOTS_03,
    'congelado-expansao-lote-04': LOT_04_COMMIT,
}
LOTS = LOTS_04
FREEZE = 'a06d381c7a9e0fc896e7c5ae84d94a452eedc56a'
TRAINING = '1070e62788e9a180539c9df7ca10b65d48ee978c'
FROZEN = 'evidencias/KAN-19/expansao50-experimental-v1'
FEATURE_FIELDS = FEATURES[-3:]
CHECKPOINT = 50
HOLDOUT = 96
REFERENCE_03 = 'evidencias/KAN-22/validacao-dirts.json'
REFERENCE_04 = 'evidencias/KAN-22/validacao-dirts-lote-04.json'
REFERENCE = REFERENCE_04
PROFILES = {
    '03': {
        'lots': LOTS_03,
        'reference': REFERENCE_03,
        'report_name': 'validacao-dirts.json',
        'expected_ranked': [(64, 26), (75, 7), (100, 4663)],
        'first_ranked_position': 64,
    },
    '04': {
        'lots': LOTS_04,
        'reference': REFERENCE_04,
        'report_name': 'validacao-dirts-lote-04.json',
        'expected_ranked': [(58, 75), (59, 75), (60, 241), (64, 26), (75, 7), (100, 4663)],
        'first_ranked_position': 58,
    },
}
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


def prepare(work, profile='04'):
    require(profile in PROFILES, f'Perfil de lotes desconhecido: {profile}')
    spec = PROFILES[profile]
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
    seen_all_positions = set()
    lot_manifests = {}
    availability_table = None
    for lot, commit in spec['lots'].items():
        bundle = f'evidencias/KAN-18/{lot}'
        expected_manifest_sha = (audit['manifestos_t1_sha256'][commit]
                                 if commit in audit['manifestos_t1_sha256']
                                 else LOT_04_MANIFEST_SHA256)
        raw = blob(commit, f'{bundle}/manifesto.json', expected_manifest_sha)
        manifest = json.loads(raw)
        require(manifest['seletor'] == 'dirts-expansao-direta-reuso/1.0.0' and
                manifest['contrato'] == '0.1.0' and not manifest['holdout']['rotulos_lidos'],
                f'Variante ou holdout T1 incompativel: {lot}')
        if lot == 'congelado-expansao-lote-04':
            base_commit = LOTS_03['congelado-expansao-v1']
            require(manifest['publicacao_base'] == base_commit and
                    manifest['manifesto_base_sha256'] == lot_manifests[base_commit] and
                    manifest['manifestos_lotes_anteriores_sha256'] == {
                        LOTS_03['congelado-expansao-lote-02']: lot_manifests[LOTS_03['congelado-expansao-lote-02']],
                        LOTS_03['congelado-expansao-lote-03']: lot_manifests[LOTS_03['congelado-expansao-lote-03']],
                    },
                    'Linhagem criptografica do lote 04 divergente')
        lot_manifests[commit] = digest(raw)
        hashes = manifest['saidas_sha256']
        if raw_commits is None:
            raw_commits = blob(commit, f'{bundle}/commits.csv', hashes['commits.csv'])
            commits = {int(r['commit_order']): r['commit_sha'] for r in records(raw_commits)}
        lot_positions = {r['posicao'] for r in manifest['revisoes'].values()}
        require(not (seen_all_positions & lot_positions), f'Sobreposicao de posicoes no lote: {lot}')
        seen_all_positions |= lot_positions
        for aux_name in ('cobertura.csv', 'rotas.csv', 'disponibilidade.csv'):
            if aux_name in hashes:
                aux_data = blob(commit, f'{bundle}/{aux_name}', hashes[aux_name])
                if aux_name == 'disponibilidade.csv':
                    availability_table = list(records(aux_data))
        sources['selection_lots'][lot] = {
            'commit': commit, 'manifest_sha256': lot_manifests[commit],
            'seen_positions': sorted(p for p in lot_positions if p != HOLDOUT),
        }
        for name, filename in [('selection', 'selection.csv'), ('t1', 'rankings.csv'),
                               ('overhead', 'overhead.csv')]:
            data = blob(commit, f'{bundle}/{filename}', hashes[filename])
            # O lote misto e verificado byte a byte. A posicao 96 e descartada antes do uso.
            tables[name].extend(r for r in records(data) if r['commit_sha'] != commits[HOLDOUT])

    if availability_table is not None:
        frozen_in_table = {int(r['posicao']) for r in availability_table
                           if r['estado_selecao'] == 'congelado'}
        require(len(availability_table) == len(commits) and frozen_in_table == seen_all_positions,
                'Disponibilidade consolidada do lote 04 diverge dos lotes carregados')
        cost_by_sha = {r['commit_sha']: r for r in tables['overhead']}
        for row in availability_table:
            pos = int(row['posicao'])
            if row['estado_selecao'] == 'congelado' and pos != HOLDOUT:
                require(cost_by_sha[row['sha']]['measurement_status'] == row['estado_custo_t1'],
                        f'Estado de custo T1 divergente na posicao {pos}')

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


def validate(output, profile='04'):
    require(profile in PROFILES, f'Perfil de lotes desconhecido: {profile}')
    spec = PROFILES[profile]
    reference = spec['reference']
    work = output / 'entradas'
    work.mkdir(parents=True)
    files, sources, tables, feature_time = prepare(work, profile=profile)
    commits, labels, releases, features, costs, inputs = load_inputs(files, FEATURE_FIELDS)
    historical = replay(commits, [], {}, features, costs, reference,
                        feature_fields=FEATURE_FIELDS)
    require(not historical[0] and not historical[1] and not historical[4],
            'O replay historico deve ficar sem ajustes e rankings')

    ranks, overhead, windows, coverage, fits = replay(
        commits, labels, releases, features, costs, reference, feature_fields=FEATURE_FIELDS)
    require([w['decision_position'] for w in windows] == list(range(11, 100, 10)) and
            [w['eligible_rows'] for w in windows] == [0] * 4 + [524] * 5 and
            [w['status'] for w in windows] ==
            ['insufficient_labels'] * 4 + ['fit'] + ['no_new_labels'] * 4 and
            list(fits) == ['janela-50'], 'Cadencia ou corte de liberacao divergente')
    rank_counts = Counter((r[0], r[1]) for r in ranks)
    require(rank_counts == {(commits[p], scenario): n for p, n in spec['expected_ranked']
                            for scenario in ('T2', 'T3')}, 'Cobertura de rankings divergente')
    first_pos = spec['first_ranked_position']
    require(all(row[0] == commits[first_pos] for row in overhead if row[2] == 'training') and
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
            if costs[entry['commit_sha']]['measurement_status'] == 'measured':
                entry['selection_ms'] = int(costs[entry['commit_sha']]['duration_ms'])
    for index, (sha, scenario, phase, *_) in enumerate(overhead):
        if phase == 'features':
            overhead[index] = (sha, scenario, phase, 'measured', feature_time[sha] / 1_000_000,
                               reference + '#coverage')

    write_csv(output / 'rankings.csv', RANK_FIELDS,
              [tuple(row[f] for f in RANK_FIELDS) for row in tables['t1']] + ranks)
    write_csv(output / 'overhead.csv', OVERHEAD_FIELDS,
              [tuple(row[f] for f in OVERHEAD_FIELDS) for row in tables['overhead']] + overhead)
    write_csv(output / 'selection.csv', SELECTION_FIELDS,
              (tuple(row[f] for f in SELECTION_FIELDS) for row in tables['selection']))
    ranked_entries = [r for r in coverage if r['status'] == 'ranked']
    report = {
        'data_kind': 'technical_synthetic_replay', 'contract_version': '0.1.0',
        'cadence': 10, 'features': FEATURE_FIELDS, 'sources': sources,
        'release': {'kind': 'experimental_checkpoint', 'position': CHECKPOINT,
                    'historical_position': None, 'source_ref': next(iter(releases.values()))['source_ref'],
                    'historical_ranking_rows': len(historical[0])},
        'input_sha256': {name: item['sha256'] for name, item in inputs.items()},
        'window_log': windows, 'coverage': coverage,
        'coverage_counts': dict(Counter(r['status'] for r in coverage)),
        'ranked_selection_cost_positions': {
            'measured': [r['position'] for r in ranked_entries
                         if r['selection_measurement_status'] == 'measured'],
            'unknown': [r['position'] for r in ranked_entries
                        if r['selection_measurement_status'] == 'unknown'],
        },
        'output_sha256': {name: digest((output / name).read_bytes())
                          for name in ('commits.csv', 'selection.csv', 'rankings.csv', 'overhead.csv')},
        'environment': {'python': platform.python_version(), 'scikit-learn': version('scikit-learn'),
                        'clock': 'perf_counter_ns', 'cache': 'uncontrolled'},
    }
    write_json(output / spec['report_name'], report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', help='Novo diretorio sob local/')
    parser.add_argument('--ate-lote', choices=sorted(PROFILES), default='04',
                        help='Ultimo lote congelado T1 a incluir (padrao: 04)')
    args = parser.parse_args()
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.run), 'Nome de rodada invalido')
    validate(BASE / 'local' / args.run, profile=args.ate_lote)
