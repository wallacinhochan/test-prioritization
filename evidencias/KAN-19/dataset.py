"""Materializa entradas T1, treino sintético e oráculo T0 da KAN-19."""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parent / 'MUTACAO' / 'modelos'))
import piloto


def partition(position):
    if position <= max(piloto.TRAIN):
        return 'treino'
    if position <= piloto.VALIDATION:
        return 'validacao'
    return 'avaliacao'


def checked(path, expected):
    data = path.read_bytes()
    piloto.require(piloto.digest(data) == expected, f'Hash divergente: {path}')
    return data


def load_natural():
    source = BASE.parent / 'KAN-16'
    manifest = json.loads((source / 'resumo-lote.json').read_bytes())
    commits = list(piloto.records(checked(
        BASE.parent / 'KAN-10' / 'commits.csv', manifest['auditoria_sha256'])))
    index = {row['commit_sha']: row for row in commits}
    piloto.require(len(index) == len(commits) == 100 and
                   [int(row['position']) for row in commits] == list(range(1, 101)),
                   'Recorte KAN-10 inválido')
    runs = {}
    oracle = defaultdict(dict)
    for name in ('t0_runs.csv', 't0_results.csv'):
        for row in piloto.records(checked(source / 'local/lote' / name, manifest['sha256'][name])):
            sha = row['commit_sha']
            piloto.require(sha in index and row['scenario'] == 'T0', f'Linha T0 inválida: {sha}')
            pos = int(index[sha]['position'])
            if name == 't0_runs.csv':
                piloto.require(pos not in runs and row['run_status'] in
                               ('complete', 'incomplete', 'environment_error'),
                               f'Execução inválida em {pos}')
                runs[pos] = row['run_status']
            else:
                method = row['test_id']
                piloto.require(pos in runs and method and method not in oracle[pos] and
                               row['outcome'] in ('pass', 'fail', 'skip'),
                               f'Resultado inválido em {pos}/{method}')
                oracle[pos][method] = row
    return commits, runs, oracle, manifest


def history(position, methods, observations):
    """Diagnóstico de replay com disponibilidade hipotética após cada SHA."""
    prior = sorted(pos for pos in observations if pos < position)
    for method in methods:
        results = [(pos, observations[pos][method]) for pos in prior
                   if method in observations[pos] and
                   observations[pos][method]['outcome'] in ('pass', 'fail')]
        recent = [row for pos, row in results if pos >= position - 10]
        durations = [int(row['duration_ms']) for _, row in results if row['duration_ms'] != '']
        failures = sum(row['outcome'] == 'fail' for _, row in results)
        yield (
            method, len(recent), sum(row['outcome'] == 'fail' for row in recent) if recent else None,
            len(results), failures / len(results) if results else None,
            len(durations), sum(durations) / len(durations) if durations else None,
            '|'.join(str(pos) for pos, _ in results),
        )


def audit_history(position, methods, observations):
    rows = list(history(position, methods, observations))
    prefix = {pos: data for pos, data in observations.items() if pos < position}
    replacement = dict.fromkeys(methods, {'outcome': 'fail', 'duration_ms': '999999'})
    contaminated = prefix | dict.fromkeys(range(position, 101), replacement)
    piloto.require(rows == list(history(position, methods, prefix)) ==
                   list(history(position, methods, contaminated)),
                   f'Histórico depende do presente ou futuro em {position}')
    piloto.require(all(int(pos) < position for row in rows if row[-1]
                       for pos in row[-1].split('|')), f'Proveniência futura em {position}')
    return rows


def frozen_features(commits):
    features = {}
    selections = {}
    for position in (*piloto.DEVELOPMENT, piloto.FINAL):
        selection = piloto.frozen_selection(position)
        commit = commits[position - 1]
        piloto.require((selection['sha'], selection['pai']) ==
                       (commit['commit_sha'], commit['first_parent_sha']),
                       f'Seleção fora da revisão KAN-10: {position}')
        selections[position] = selection
        features[position] = [
            (position, selection['sha'], method, partition(position), *selection['methods'][method])
            for method in selection['selected']
        ]
    return features, selections


def export(output):
    commits, runs, oracle, manifest = load_natural()
    features, selections = frozen_features(commits)
    observations = {pos: rows for pos, rows in oracle.items() if runs[pos] == 'complete'}
    predictors = ('position', 'commit_sha', 'test_id', 'partition', *piloto.FEATURES)
    piloto.write_csv(output / 'features_t1.csv', predictors,
                     (row for rows in features.values() for row in rows))

    replay_reports = {}
    train = []
    for pos in piloto.TRAIN:
        report, replay = piloto.load_replay(pos, selections[pos])
        replay_reports[pos] = report
        if replay is None:
            continue
        _, _, totals = replay
        for row in features[pos]:
            counts = totals[row[2]]
            target = piloto.target(counts)
            if target is not None:
                train.append((*row, target, *(counts[k] for k in (*piloto.LABELS, 'ausente'))))
    piloto.write_csv(output / 'treino_sintetico.csv',
                     (*predictors, 'target_synthetic', *piloto.LABELS, 'ausente'), train)

    natural = []
    retrospective = []
    coverage = []
    for pos, commit in enumerate(commits, 1):
        sha = commit['commit_sha']
        rows = oracle.get(pos, {})
        selected = {row[2] for row in features.get(pos, [])}
        outcomes = Counter(row['outcome'] for row in rows.values())
        coverage.append((pos, sha, partition(pos), commit['eligibility_status'],
                         runs.get(pos, 'sem_t0'), len(rows), outcomes['pass'], outcomes['fail'],
                         outcomes['skip'], sum(bool(row['duration_ms']) for row in rows.values()),
                         len(selected) if pos in selections else None,
                         len(selected.intersection(rows)) if pos in selections else None))
        for method, row in sorted(rows.items()):
            # Uma falha de teste exige atribuição antes de virar positivo natural.
            natural.append((pos, sha, method, partition(pos), runs[pos], row['outcome'],
                            0 if runs[pos] == 'complete' and row['outcome'] == 'pass' else None,
                            row['duration_ms'], row['execution_order'], row['source_ref']))
        if pos in selections:
            methods = [row[2] for row in features[pos]]
            retrospective.extend((pos, sha, *row) for row in audit_history(pos, methods, observations))
    piloto.write_csv(output / 'oraculo_t0.csv',
                     ('position', 'commit_sha', 'test_id', 'partition', 'run_status', 'outcome',
                      'target_natural', 'duration_ms', 'execution_order', 'source_ref'), natural)
    piloto.write_csv(output / 'historico_replay.csv',
                     ('position', 'commit_sha', 'test_id', 'recent_observed', 'recent_failures',
                      'past_observed', 'past_failure_rate', 'past_measured', 'past_mean_ms',
                      'source_positions'), retrospective)
    piloto.write_csv(output / 'cobertura.csv',
                     ('position', 'commit_sha', 'partition', 'eligibility_kan10', 't0_status',
                      't0_methods', 'pass', 'fail', 'skip', 'duration_known',
                      't1_selected', 't1_with_t0'), coverage)

    diagnostics = {}
    for pos in selections:
        audit = [row for row in retrospective if row[0] == pos]
        diagnostics[pos] = {
            't1': len(features[pos]),
            't1_com_t0': coverage[pos - 1][-1],
            'historico_recente': sum(row[4] is not None for row in audit),
            'taxa_historica': sum(row[6] is not None for row in audit),
            'duracao_historica': sum(row[8] is not None for row in audit),
        }
    return {
        'protocolo': 'kan19-v1',
        'codigo': {path.name: piloto.digest(path.read_bytes().replace(b'\r\n', b'\n')) for path in
                   (Path(__file__), Path(piloto.__file__))},
        'sha256_entrada': {'commits.csv': manifest['auditoria_sha256'],
                           **{name: manifest['sha256'][name] for name in
                              ('t0_runs.csv', 't0_results.csv')}},
        't1_commit': piloto.T1,
        't1_manifestos': {pos: sel['manifesto_sha256'] for pos, sel in selections.items()},
        'features_modelo': piloto.FEATURES,
        't0_completo': sorted(pos for pos in runs if runs[pos] == 'complete'),
        'linhas_t0': len(natural),
        'falhas_t0': sum(row[5] == 'fail' for row in natural),
        'positivos_naturais_confirmados': sum(row[6] == 1 for row in natural),
        'linhas_t1': sum(map(len, features.values())),
        'linhas_treino': len(train),
        'alvos_sinteticos_positivos': sum(row[len(predictors)] > 0 for row in train),
        'replays_treino': replay_reports,
        'auditoria_historico': diagnostics,
        'verificacao_temporal': 'prefixo e substituicao de todos os resultados a partir do alvo',
        'sha256_saida': {path.name: piloto.digest(path.read_bytes())
                         for path in sorted(output.glob('*.csv'))},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('execucao', help='Nome novo sob evidencias/KAN-19/local')
    args = parser.parse_args()
    if (not args.execucao.isascii() or not args.execucao[0:1].isalnum() or
            not all(c.isalnum() or c in '-_' for c in args.execucao)):
        parser.error('Use um nome com letras ASCII, números, hífen ou sublinhado')
    output = BASE / 'local' / args.execucao
    output.mkdir(parents=True)
    piloto.write_json(output / 'resumo.json', export(output))


if __name__ == '__main__':
    main()
