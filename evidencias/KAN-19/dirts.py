"""Materialização e ranking técnico provisório da publicação DIRTS."""
import argparse
import json
import math
import platform
import re
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter_ns

from sklearn.ensemble import RandomForestRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from principal import BASE, KAN18, KEYS, checked, load_selection, piloto

FEATURES = piloto.FEATURES[-3:]
REFERENCE_ROOT = f'{KAN18}/local/dirts'
RANK_FIELDS = ('commit_sha', 'scenario', 'test_id', 'rank', 'score', 'source_ref')
COST_FIELDS = ('commit_sha', 'scenario', 'phase', 'measurement_status', 'duration_ms',
               'source_ref')


def vector(test_id):
    match = re.fullmatch(r'([^#]+)#([^()]+)\(([^()]*)\)', test_id)
    piloto.require(match is not None, f'Identidade inválida: {test_id}')
    binary_class, name, parameters = match.groups()
    return len(name), parameters.count(',') + 1 if parameters else 0, int('$' in binary_class)


def load_revision(local, publication, reference, commit, recorte_hash):
    sha = commit['commit_sha']
    directory = local / 'selecao' / sha
    manifest = json.loads((directory / 'manifesto.json').read_bytes())
    expected = {name: reference[name] for name in (
        'posicao', 'sha', 'pai', 'imagem', 'candidatos', 'selecionados', 'fallback', 'saidas_sha256')}
    expected.update(seletor=publication['seletor'], ferramenta={
        'nome': 'DIRTS', 'versao': '1.0', 'commit': publication['dirts_commit']})
    piloto.require(manifest['codigo_sha256']['seletor'] == reference['seletor_sha256']
                   and manifest['entradas_sha256']['metodos.tsv'] == reference['metodos_sha256'],
                   f'Proveniência DIRTS divergente: {sha}')
    rows, _, lineage = load_selection(
        expected, commit, recorte_hash, local=local, reference_root=REFERENCE_ROOT,
        extract=lambda *_: ())
    costs = list(piloto.records(checked(directory / 'overhead.csv',
                                       reference['saidas_sha256']['overhead.csv'])))
    piloto.require(len(costs) == 1 and tuple(costs[0]) == COST_FIELDS, f'Overhead inválido: {sha}')
    cost = costs[0]
    piloto.require((cost['commit_sha'], cost['scenario'], cost['phase'],
                    cost['measurement_status'], cost['duration_ms'], cost['source_ref']) ==
                   (sha, 'T1', 'selection', 'measured', str(manifest['custo']['ms']),
                    f'{REFERENCE_ROOT}/selecao/{sha}/manifesto.json#custo'),
                   f'Custo de seleção divergente: {sha}')
    start = perf_counter_ns()
    features = [(*row, *vector(row[2])) for row in rows]
    return features, perf_counter_ns() - start, cost, lineage


def fixture():
    # Identidades e alvos fabricados, independentes dos SHAs do estudo.
    methods = [f'fixture.Test{"$Nested" if i % 2 else ""}#test{"X" * i}'
               f'({"int" if i % 3 else ""})' for i in range(16)]
    return [vector(method) for method in methods], [float(i % 3 == 0) for i in range(16)]


def rank(model, sha, scenario, rows, reference):
    start = perf_counter_ns()
    methods = [row[2] for row in rows]
    scores = model.predict([row[3:] for row in rows]) if rows else []
    lines = [(sha, scenario, method, index, score, reference)
             for index, (method, score) in enumerate(piloto.rank_scores(methods, scores), 1)]
    elapsed = perf_counter_ns() - start
    piloto.require(len(lines) == len(rows) and {row[2] for row in lines} == set(methods)
                   and all(math.isfinite(row[4]) for row in lines),
                   f'Ranking incompatível com T1: {sha}/{scenario}')
    return lines, elapsed


def run(local, output):
    publication_bytes = (BASE.parent / 'KAN-18' / 'verificacao-dirts.json').read_bytes()
    publication = json.loads(publication_bytes)
    recorte = (BASE.parent / 'KAN-10' / 'commits.csv').read_bytes()
    recorte_hash = piloto.digest(recorte)
    commits = {int(row['position']): row for row in piloto.records(recorte)}
    revisions = {}
    for reference in sorted(publication['revisoes'], key=lambda row: row['posicao']):
        position = reference['posicao']
        piloto.require(position not in revisions, f'Posição duplicada: {position}')
        revisions[position] = load_revision(local, publication, reference, commits[position], recorte_hash)

    models = {
        'T2': make_pipeline(StandardScaler(), KNeighborsRegressor(**piloto.KNN)),
        'T3': RandomForestRegressor(**piloto.FOREST),
    }
    x_train, y_train = fixture()
    source = f'{output.relative_to(BASE.parent.parent).as_posix()}/manifesto.json'
    rankings, costs = [], []
    timings = {}
    first_sha = commits[min(revisions)]['commit_sha']
    for scenario, model in models.items():
        start = perf_counter_ns()
        model.fit(x_train, y_train)
        fit = perf_counter_ns() - start
        costs.append((first_sha, scenario, 'training', 'measured', fit / 1e6, source))
        timings[scenario] = {'fit_ns': fit, 'inference_ns': {}}
        for position, (rows, extraction, t1, _) in revisions.items():
            sha = commits[position]['commit_sha']
            ranked, elapsed = rank(model, sha, scenario, rows, source)
            rankings.extend(ranked)
            timings[scenario]['inference_ns'][sha] = elapsed
            costs.extend([
                (sha, scenario, 'selection', *(t1[key] for key in COST_FIELDS[3:])),
                (sha, scenario, 'features', 'measured', extraction / 1e6, source),
                (sha, scenario, 'inference', 'measured', elapsed / 1e6, source),
            ])

    report = {
        'estado': 'provisorio_fixture',
        'features': FEATURES,
        'treino': {'origem': 'fixture interno com alvos artificiais', 'linhas': len(x_train)},
        'ambiente': {'python': platform.python_version(), 'host': platform.platform(),
                     'bibliotecas': {name: version(name) for name in
                                     ('scikit-learn', 'numpy', 'scipy', 'joblib', 'threadpoolctl')}},
        'publicacao_dirts_sha256': piloto.digest(publication_bytes),
        'recorte_sha256': recorte_hash,
        'codigo_sha256': {path.name: piloto.digest(path.read_bytes()) for path in
                          (Path(__file__), BASE / 'principal.py', Path(piloto.__file__))},
        'escopo': {
            'selection': 'medição original KAN-18, herdada por cenário',
            'features': 'vetor e linha a partir de identidade em memória, uma extração comum por SHA',
            'inference': 'matriz em memória, predict, ordenação e linhas por SHA',
            'training': 'fit com fixture em memória',
            'excluido_de_features_inference_training': 'I/O, hashes, verificações e descoberta JUnit',
        },
        'revisoes': {position: {**lineage, 'selecionados': len(rows), 'extraction_ns': extraction}
                     for position, (rows, extraction, _, lineage) in revisions.items()},
        'modelos': timings,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as temporary:
        stage = Path(temporary) / 'artefatos'
        stage.mkdir()
        piloto.write_csv(stage / 'features_inferencia.csv', (*KEYS, *FEATURES),
                         (row for rows, *_ in revisions.values() for row in rows))
        piloto.write_csv(stage / 'rankings.csv', RANK_FIELDS, rankings)
        piloto.write_csv(stage / 'overhead.csv', COST_FIELDS, costs)
        report['sha256_saida'] = {path.name: piloto.digest(path.read_bytes())
                                  for path in sorted(stage.iterdir())}
        piloto.write_json(stage / 'manifesto.json', report)
        stage.rename(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rodada')
    parser.add_argument('--kan18-local', type=Path, default=BASE.parent / 'KAN-18' / 'local' / 'dirts')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.rodada):
        parser.error('Identificador de rodada inválido')
    output = BASE / 'local' / f'dirts-provisorio-{args.rodada}'
    if output.exists():
        parser.error(f'Destino já existe: {output}')
    run(args.kan18_local, output)
    print(output)


if __name__ == '__main__':
    main()
