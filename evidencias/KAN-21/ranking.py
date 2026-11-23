import argparse
import json
import math
import platform
import sys
from collections import Counter
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter_ns

BASE = Path(__file__).resolve().parent
PILOT = BASE.parent / 'MUTACAO' / 'modelos'
sys.path.insert(0, str(PILOT))
from piloto import (FEATURES, FOREST, ROOT, TRAIN, digest, git, ordinal,
                    rank_scores, records, require, write_csv, write_json)

PUBLICATION = '92aff717b2521317966e8e4076afb79a77aa0287'
SCENARIO = 'T3'
RANK_FIELDS = ('commit_sha', 'scenario', 'test_id', 'rank', 'score', 'source_ref')
OVERHEAD_FIELDS = ('commit_sha', 'scenario', 'phase', 'measurement_status',
                   'duration_ms', 'source_ref')


def published(path):
    return git('show', f'{PUBLICATION}:evidencias/{path}')


def verified(path, sha256):
    data = path.read_bytes()
    require(digest(data) == sha256, f'SHA-256 divergente: {path}')
    return data


def key(row):
    return row['commit_sha'], row['test_id']


def vector(row):
    return [int(row[name]) for name in FEATURES]


def load_inputs(training_path, inference_path):
    train_meta = json.loads(published('KAN-19/resumo.json'))
    inference_meta = json.loads(published('KAN-19/resumo_principal.json'))
    selection_meta = json.loads(published('KAN-18/verificacao.json'))
    commits = {int(row['position']): row['commit_sha']
               for row in records(published('KAN-10/commits.csv'))}
    for metadata in (train_meta, inference_meta):
        require(tuple(metadata['features_modelo']) == FEATURES, 'Ordem de features divergente.')

    inputs = {}
    rows = {}
    for path, name, metadata in (
        (training_path, 'treino_sintetico.csv', train_meta),
        (inference_path, 'features_inferencia.csv', inference_meta),
    ):
        sha256 = metadata['sha256_saida'][name]
        reader = records(verified(path, sha256))
        require(tuple(field for field in reader.fieldnames if field in FEATURES) == FEATURES,
                f'Colunas de features divergentes: {path}')
        rows[name] = list(reader)
        require(len({key(row) for row in rows[name]}) == len(rows[name]),
                f'Chave SHA × test_id repetida: {path}')
        inputs[name] = {'path': str(path), 'sha256': sha256, 'rows': len(rows[name])}

    training = rows['treino_sintetico.csv']
    require({int(row['position']) for row in training} == set(TRAIN)
            and all(row['commit_sha'] == commits[int(row['position'])]
                    and row['partition'] == 'treino' for row in training),
            'Posições, SHAs ou partição de treino divergentes.')
    training = [row for row in training if row['target_synthetic'] != '']
    require(len(training) == train_meta['linhas_treino'], 'Contagem de alvos divergente.')
    training.sort(key=lambda row: (int(row['position']), ordinal(row['test_id'])))

    inference = {}
    for row in rows['features_inferencia.csv']:
        inference.setdefault(int(row['position']), []).append(row)
    require(set(inference) == {entry['posicao'] for entry in selection_meta},
            'A cobertura das features diverge da seleção formal.')
    coverage = []
    selection_costs = {}
    for entry in sorted(selection_meta, key=lambda item: item['posicao']):
        position, sha = entry['posicao'], entry['sha']
        require(sha == commits[position], f'SHA formal divergente: {position}')
        directory = BASE.parent / 'KAN-18' / 'local' / 'selecao' / sha
        hashes = entry['saidas_sha256']
        ranking = list(records(verified(directory / 'rankings.csv', hashes['rankings.csv'])))
        grouped = inference[position]
        require([key(row) for row in grouped] == [key(row) for row in ranking]
                and len(ranking) == entry['selecionados']
                and all(row['commit_sha'] == sha and row['scenario'] == 'T1'
                        and int(row['rank']) == rank
                        for rank, row in enumerate(ranking, 1)),
                f'População ou ordem T1 divergente: {position}')
        eligible = position > max(TRAIN)
        coverage.append({
            'position': position, 'commit_sha': sha, 't1_rows': len(grouped),
            't1_ranking_sha256': hashes['rankings.csv'],
            'status': 'ranked' if eligible else 'sem_ranking_por_anterioridade',
        })
        if eligible:
            cost, = records(verified(directory / 'overhead.csv', hashes['overhead.csv']))
            require((cost['commit_sha'], cost['scenario'], cost['phase']) == (sha, 'T1', 'selection'),
                    f'Overhead T1 incompatível: {position}')
            selection_costs[position] = cost
    return training, inference, coverage, selection_costs, inputs, commits


def rank_revision(model, sha, rows, source_ref):
    start = perf_counter_ns()
    candidates = [row['test_id'] for row in rows]
    scores = model.predict([vector(row) for row in rows])
    ranking = [(sha, SCENARIO, test_id, rank, score, source_ref)
               for rank, (test_id, score) in enumerate(rank_scores(candidates, scores), 1)]
    elapsed = perf_counter_ns() - start
    require(len(ranking) == len(rows) and {row[2] for row in ranking} == set(candidates)
            and all(math.isfinite(row[4]) for row in ranking), f'Ranking inválido: {sha}')
    return ranking, elapsed


def run(training_path, inference_path, output):
    requirements = PILOT / 'requirements.txt'
    require(requirements.read_bytes() == published('MUTACAO/modelos/requirements.txt')
            and (PILOT / 'piloto.py').read_bytes() == published('MUTACAO/modelos/piloto.py'),
            'Código ou dependências do piloto divergentes da publicação.')
    versions = {}
    for line in requirements.read_text(encoding='utf-8').splitlines():
        name, expected = line.split('==')
        versions[name] = version(name)
        require(versions[name] == expected, f'{name}: versão esperada {expected}')

    from joblib import dump
    from sklearn.ensemble import RandomForestRegressor

    training, inference, coverage, costs, inputs, commits = load_inputs(training_path, inference_path)
    x_train = [vector(row) for row in training]
    y_train = [float(row['target_synthetic']) for row in training]
    model = RandomForestRegressor(**FOREST)
    start = perf_counter_ns()
    model.fit(x_train, y_train)
    fit_ns = perf_counter_ns() - start

    reference = output.relative_to(ROOT).as_posix() + '/manifesto.json'
    rankings = []
    first_sha = commits[min(costs)]
    overhead = [(first_sha, SCENARIO, 'training', 'measured', fit_ns / 1_000_000,
                 reference + '#training')]
    timings = {}
    for position, cost in costs.items():
        sha = commits[position]
        rows, elapsed = rank_revision(model, sha, inference[position], reference)
        rankings.extend(rows)
        timings[str(position)] = elapsed
        overhead.extend([
            (sha, SCENARIO, 'selection', cost['measurement_status'], cost['duration_ms'],
             cost['source_ref']),
            (sha, SCENARIO, 'features', 'unknown', '', reference + '#features'),
            (sha, SCENARIO, 'inference', 'measured', elapsed / 1_000_000,
             reference + '#inference'),
        ])

    manifest = {
        'scenario': SCENARIO, 'publication': PUBLICATION, 'inputs': inputs,
        'features': {
            'columns': FEATURES,
            'availability': 'Vetores estáticos KAN-19 materializados após descoberta e seleção T1.',
            'measurement': 'Extração dos vetores sem medida publicada. Conversão incluída em inference.',
        },
        'training': {
            'cut_position': max(TRAIN), 'cut_sha': commits[max(TRAIN)],
            'positions': {position: commits[position] for position in TRAIN},
            'rows_by_position': dict(Counter(row['position'] for row in training)),
            'available_from_position': min(costs), 'available_from_sha': first_sha,
            'fit_ns': fit_ns,
            'availability': 'Alvos sintéticos KAN-19 congelados antes da inferência no replay.',
        },
        'inference': {
            'positions': list(costs), 'elapsed_ns': timings,
            'interval': 'Conversão dos vetores disponíveis, predict, ordenação e construção das linhas.',
        },
        'iteration': {
            'training': 'position crescente, test_id ordinal UTF-16 crescente',
            'inference': 'position crescente, ordem de entrada do ranking T1',
            'output': 'position crescente, score decrescente, test_id ordinal UTF-16 crescente',
        },
        'coverage': coverage, 'estimator': type(model).__name__, 'parameters': model.get_params(),
        'environment': {
            'python': platform.python_version(), 'platform': platform.platform(),
            'machine': platform.machine(), 'packages': versions,
            'clock': 'perf_counter_ns', 'csv_unit': 'ms',
            'process': 'Um processo por execução, n_jobs=1, cache não controlado.',
        },
        'code_sha256': digest(Path(__file__).read_bytes()),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as temporary:
        stage = Path(temporary) / 'publication'
        stage.mkdir()
        write_csv(stage / 'rankings.csv', RANK_FIELDS, rankings)
        write_csv(stage / 'overhead.csv', OVERHEAD_FIELDS, overhead)
        dump(model, stage / 'RandomForest.joblib')
        manifest['output_sha256'] = {path.name: digest(path.read_bytes()) for path in sorted(stage.iterdir())}
        write_json(stage / 'manifesto.json', manifest)
        stage.rename(output)


def main():
    parser = argparse.ArgumentParser(description='Gera o ranking T3 do replay inicial da KAN-21.')
    parser.add_argument('run', help='Nome novo sob local/')
    parser.add_argument('--treino', type=Path, required=True)
    parser.add_argument('--inferencia', type=Path, required=True)
    args = parser.parse_args()
    if Path(args.run).name != args.run or args.run in ('', '.', '..'):
        parser.error('Use um nome simples para a execução.')
    output = BASE / 'local' / args.run
    if output.exists():
        parser.error(f'O destino já existe: {output}')
    run(args.treino, args.inferencia, output)


if __name__ == '__main__':
    main()
