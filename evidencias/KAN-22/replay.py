"""Replay T2/T3 com treinamento em janela expansiva."""
import argparse
import math
import platform
import re
import sys
from collections import Counter, defaultdict
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter_ns

BASE = Path(__file__).resolve().parent
EVIDENCE = BASE.parent
sys.path.insert(0, str(EVIDENCE / 'KAN-21'))
from ranking import (FEATURES, FOREST, OVERHEAD_FIELDS, RANK_FIELDS, ROOT, digest,
                     ordinal, rank_revision, records, require, vector, write_csv, write_json)
from piloto import KNN

KEYS = ('position', 'commit_sha', 'test_id')
SELECTION_FIELDS = ('commit_sha', 'scenario', 'test_id', 'selected', 'selection_reason',
                    'source_ref')
AVAILABILITY_FIELDS = ('commit_sha', 'available_position', 'source_ref')


def load_inputs(paths):
    provenance = {}

    def read(name, fields=None):
        path = paths[name]
        data = path.read_bytes()
        provenance[name] = {'path': str(path.resolve()), 'sha256': digest(data)}
        reader = records(data)
        header = reader.fieldnames or []
        require(len(header) == len(set(header)) and
                (fields is None or tuple(header) == fields), f'Cabecalho invalido: {path}')
        rows = list(reader)
        require(all(None not in row and None not in row.values() for row in rows),
                f'Linha CSV incompleta ou excedente: {path}')
        return header, rows

    _, commits_rows = read('commits')
    commits = {int(row['position']): row['commit_sha'] for row in commits_rows}
    positions = {sha: pos for pos, sha in commits.items()}
    require(len(commits) == len(positions) == len(commits_rows) and
            set(commits) == set(range(1, len(commits) + 1)) and
            all(re.fullmatch(r'[a-f0-9]{40}', sha) for sha in positions),
            'Cronologia invalida: use posicoes contiguas e SHAs unicos')

    _, releases = read('availability', AVAILABILITY_FIELDS)
    availability = {}
    for row in releases:
        sha = row['commit_sha']
        released = int(row['available_position'])
        require(sha in positions and sha not in availability and released >= positions[sha]
                and row['source_ref'], f'Disponibilidade invalida: {sha}')
        availability[sha] = row

    header, training = read('train')
    require(set((*KEYS, 'partition', 'target_synthetic')) <= set(header) and
            tuple(name for name in header if name in FEATURES) == FEATURES,
            'Colunas de treino incompativeis com KAN-19')
    labeled, seen = [], set()
    for row in training:
        pos = int(row['position'])
        sha, method = row['commit_sha'], row['test_id']
        key = sha, method
        require(commits.get(pos) == sha and method and key not in seen and
                row['partition'] == 'treino', f'Linha de treino invalida: {key}')
        seen.add(key)
        if row['target_synthetic'] and sha in availability:
            target = float(row['target_synthetic'])
            require(0 <= target <= 1, f'Alvo invalido: {key}')
            labeled.append((pos, int(availability[sha]['available_position']), row))

    _, selection = read('selection', SELECTION_FIELDS)
    _, baseline = read('t1', RANK_FIELDS)
    _, costs = read('overhead', OVERHEAD_FIELDS)
    _, features = read('features', (*KEYS, *FEATURES))
    by_sha, t1, selected, overhead = defaultdict(list), defaultdict(list), defaultdict(set), {}
    seen = set()
    reasons = {'dependency': 'true', 'fallback': 'true', 'no_dependency': 'false'}
    for row in selection:
        sha, method = row['commit_sha'], row['test_id']
        key = sha, method
        require(sha in positions and method and key not in seen and row['scenario'] == 'T1'
                and reasons.get(row['selection_reason']) == row['selected']
                and row['source_ref'], f'Selecao T1 invalida: {key}')
        seen.add(key)
        methods = selected[sha]
        if row['selected'] == 'true':
            methods.add(method)
    for row in baseline:
        sha = row['commit_sha']
        require(sha in positions and row['scenario'] == 'T1' and row['test_id']
                and not row['score'] and row['source_ref'], f'Ranking T1 invalido: {sha}')
        t1[sha].append(row)
    for row in costs:
        sha = row['commit_sha']
        status, duration = row['measurement_status'], row['duration_ms']
        require(sha in positions and sha not in overhead and row['scenario'] == 'T1'
                and row['phase'] == 'selection' and row['source_ref']
                and ((status == 'unknown' and not duration)
                     or (status == 'measured' and duration and math.isfinite(float(duration))
                         and float(duration) >= 0)), f'Overhead T1 invalido: {sha}')
        overhead[sha] = row
    for row in features:
        sha = row['commit_sha']
        require(positions.get(sha) == int(row['position']), f'Feature de outro SHA: {sha}')
        by_sha[sha].append(row)

    require(set(selected) | set(t1) | set(by_sha) <= set(overhead),
            'Entrada T1 sem overhead de selecao')
    for sha in overhead:
        ordered = sorted(t1[sha], key=lambda row: int(row['rank']))
        methods = [row['test_id'] for row in ordered]
        require([int(row['rank']) for row in ordered] == list(range(1, len(methods) + 1))
                and len(methods) == len(set(methods)) and set(methods) == selected[sha]
                and methods == [row['test_id'] for row in by_sha[sha]],
                f'Populacao ou ordem T1 divergente: {sha}')
    return commits, labeled, availability, by_sha, overhead, provenance


def estimators():
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.neighbors import KNeighborsRegressor
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    return {
        'T2': make_pipeline(StandardScaler(), KNeighborsRegressor(**KNN)),
        'T3': RandomForestRegressor(**FOREST),
    }


def replay(commits, labeled, availability, features, costs, reference, cadence=10,
           make_models=estimators):
    require(cadence > 0, 'Cadencia deve ser positiva')
    rankings, overhead, windows, coverage, fits = [], [], [], [], {}
    active = None
    for pos, sha in sorted(commits.items()):
        if pos > 1 and (pos - 1) % cadence == 0:
            eligible = [row for origin, release, row in labeled if origin < pos and release < pos]
            counts = Counter(row['commit_sha'] for row in eligible)
            window_id = f'janela-{pos - 1}'
            previous_count = active['training_rows'] if active else 0
            window = {
                'id': window_id, 'cut_position': pos - 1, 'cut_sha': commits[pos - 1],
                'decision_position': pos, 'decision_sha': sha, 'eligible_rows': len(eligible),
                'new_rows': len(eligible) - previous_count,
                'eligible_sources': [
                    {**availability[source], 'origin_position': int(next_row['position']),
                     'rows': counts[source]}
                    for source, next_row in {row['commit_sha']: row for row in eligible}.items()
                ],
            }
            windows.append(window)
            if len(eligible) < KNN['n_neighbors']:
                window['status'] = 'insufficient_labels'
            elif len(eligible) == previous_count:
                window['status'] = 'no_new_labels'
            else:
                models = make_models()
                fit_ns = {}
                for scenario, model in models.items():
                    rows = eligible
                    if scenario == 'T3':
                        rows = sorted(rows, key=lambda row: (int(row['position']),
                                                             ordinal(row['test_id'])))
                    x = [vector(row) for row in rows]
                    y = [float(row['target_synthetic']) for row in rows]
                    start = perf_counter_ns()
                    model.fit(x, y)
                    fit_ns[scenario] = perf_counter_ns() - start
                window.update(status='fit', fit_ns=fit_ns, training_rows=len(eligible),
                              first_ranked_sha=None, first_ranked_position=None,
                              models={scenario: f'{window_id}-{scenario}.joblib'
                                      for scenario in models})
                fits[window_id] = models
                active = window
            window['active_model_window'] = active['id'] if active else None

        entry = {'position': pos, 'commit_sha': sha, 't1_rows': len(features.get(sha, ())),
                 'model_window': active['id'] if active else None}
        coverage.append(entry)
        if sha not in costs:
            entry['status'] = 'missing_t1'
        elif not features[sha]:
            entry['status'] = 'empty_t1'
        elif active is None:
            entry['status'] = 'no_model'
        else:
            entry['status'] = 'ranked'
            entry['inference_ns'] = {}
            source = f'{reference}#{active["id"]}'
            first_use = active['first_ranked_sha'] is None
            if first_use:
                active.update(first_ranked_sha=sha, first_ranked_position=pos)
            cost = costs[sha]
            for scenario, model in fits[active['id']].items():
                rows, elapsed = rank_revision(model, sha, features[sha], source)
                rankings.extend((r[0], scenario, *r[2:]) for r in rows)
                entry['inference_ns'][scenario] = elapsed
                overhead.extend([
                    (sha, scenario, 'selection', *(cost[key] for key in OVERHEAD_FIELDS[3:])),
                    (sha, scenario, 'features', 'unknown', '', reference + '#features'),
                    (sha, scenario, 'inference', 'measured', elapsed / 1_000_000, source),
                ])
                if first_use:
                    overhead.append((sha, scenario, 'training', 'measured',
                                     active['fit_ns'][scenario] / 1_000_000, source))
    return rankings, overhead, windows, coverage, fits


def run(args):
    from joblib import dump

    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.run), 'Nome de rodada invalido')
    output = BASE / 'local' / args.run
    require(not output.exists(), f'Destino ja existe: {output}')
    names = ('commits', 'train', 'availability', 'features', 'selection', 't1', 'overhead')
    commits, labeled, availability, features, costs, inputs = load_inputs(
        {name: getattr(args, name) for name in names})
    reference = output.relative_to(ROOT).as_posix() + '/manifesto.json'
    rankings, overhead, windows, coverage, fits = replay(
        commits, labeled, availability, features, costs, reference, args.cadence)
    manifest = {
        'cadence': args.cadence, 'inputs': inputs, 'features': FEATURES,
        'knn': KNN, 'forest': FOREST, 'windows': windows, 'coverage': coverage,
        'environment': {'python': platform.python_version(), 'platform': platform.platform(),
                        'scikit-learn': version('scikit-learn'), 'joblib': version('joblib'),
                        'clock': 'perf_counter_ns', 'cache': 'uncontrolled'},
        'code_sha256': {path.relative_to(ROOT).as_posix(): digest(path.read_bytes())
                        for path in (Path(__file__).resolve(), EVIDENCE / 'KAN-21/ranking.py',
                                     EVIDENCE / 'MUTACAO/modelos/piloto.py')},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as temp:
        stage = Path(temp) / 'publication'
        stage.mkdir()
        write_csv(stage / 'rankings.csv', RANK_FIELDS, rankings)
        write_csv(stage / 'overhead.csv', OVERHEAD_FIELDS, overhead)
        for window_id, models in fits.items():
            for scenario, model in models.items():
                dump(model, stage / f'{window_id}-{scenario}.joblib')
        manifest['output_sha256'] = {path.name: digest(path.read_bytes())
                                     for path in sorted(stage.iterdir())}
        write_json(stage / 'manifesto.json', manifest)
        stage.rename(output)
    print(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run')
    parser.add_argument('--cadence', type=int, default=10)
    for field in ('commits', 'train', 'availability', 'features', 'selection', 't1', 'overhead'):
        parser.add_argument('--' + field, type=Path, required=True)
    run(parser.parse_args())
