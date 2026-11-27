"""Valida features e rankings técnicos na revisão 50 do T1 congelado."""
import argparse
import json
import platform
import re
from collections import Counter
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter_ns

from dirts import (BASE, COST_FIELDS, FEATURES, KEYS, RANK_FIELDS, KNeighborsRegressor,
                   RandomForestRegressor, StandardScaler, fixture, make_pipeline, piloto,
                   rank, vector)

PUBLICATION = 'ef577158bc012d87784bbfab1b9ccb4ee80cf812'
BUNDLE = 'evidencias/KAN-18/congelado-expansao-v1'
POSITION = 50
SHA = 'f24c027ff83b90beab2ec28696721200abb4f9e9'
POLICY = 'expansao-direta/assinatura-v1'
AUDIT_FIELDS = ('estado_rota', 'distancia_rota', 'rota_ausente', 'arestas_lexicais',
                'classe_semente', 'sementes_diretas', 'jdeps_evidencia')


def route_fields(route):
    state = route['estado_rota']
    direct = state == 'direta_jdeps'
    piloto.require(
        state in ('direta_jdeps', 'sem_evidencia_rota')
        and (bool(route['sementes_diretas']) == direct)
        and (not direct or re.fullmatch(r'[0-9a-f]{64}', route['jdeps_evidencia'])),
        f'Evidência de rota inválida: {route["classe_raiz"]}')
    return (state, 1 if direct else None, 0 if direct else None, None, None,
            route['sementes_diretas'], route['jdeps_evidencia'])


def published(name):
    return piloto.git('show', f'{PUBLICATION}:{BUNDLE}/{name}')


def set_hash(ids):
    return piloto.digest(''.join(f'{test_id}\n' for test_id in sorted(ids)).encode())


def frozen_input():
    raw = published('manifesto.json')
    manifest = json.loads(raw)
    tables = {}
    for name, sha256 in manifest['saidas_sha256'].items():
        data = published(name)
        piloto.require(piloto.digest(data) == sha256, f'Hash divergente: {name}')
        tables[name] = list(piloto.records(data))
    revision = manifest['revisoes']['posicao-050']
    coverage = {int(row['posicao']): row for row in tables['cobertura.csv']}
    piloto.require((revision['posicao'], revision['sha'], revision['holdout']) ==
                   (POSITION, SHA, False) and
                   (coverage[POSITION]['sha'], coverage[POSITION]['pai'],
                    coverage[POSITION]['holdout']) == (SHA, revision['pai'], 'false'),
                   'Identidade da revisão incompatível')
    reference = f'{BUNDLE}/manifesto.json#posicao-050'
    ranks = [r for r in tables['rankings.csv'] if r['commit_sha'] == SHA]
    ids = [r['test_id'] for r in ranks]
    selections = [r for r in tables['selection.csv'] if r['commit_sha'] == SHA]
    candidates = {r['test_id'] for r in selections}
    piloto.require(len(candidates) == len(selections) == revision['candidatos'] and
                   set_hash(candidates) == revision['sha256_conjuntos']['t0'] and
                   all((r['scenario'], r['source_ref']) == ('T1', reference)
                       and r['selected'] in ('true', 'false') for r in selections),
                   'Seleção T1 inválida')
    piloto.require(
        len(ids) == len(set(ids)) == revision['selecionados'] == 416
        and set(ids) == {r['test_id'] for r in selections if r['selected'] == 'true'}
        and set_hash(ids) == revision['sha256_conjuntos']['t1']
        and ids == sorted(ids, key=piloto.ordinal)
        and all((r['scenario'], r['rank'], r['score'], r['source_ref']) ==
                ('T1', str(i), '', reference) for i, r in enumerate(ranks, 1)),
        'Ranking T1 inválido')
    route_rows = [r for r in tables['rotas.csv'] if r['commit_sha'] == SHA]
    routes = {r['classe_raiz']: r for r in route_rows}
    piloto.require(len(routes) == len(route_rows) and set(routes) == {root(t) for t in ids},
                   'Rotas incompatíveis com a população selecionada')
    costs = [r for r in tables['overhead.csv'] if r['commit_sha'] == SHA]
    piloto.require(len(costs) == 1 and
                   tuple(costs[0].values()) == (SHA, 'T1', 'selection', 'measured', '78575', reference),
                   'Custo T1 incompatível')
    return ids, routes, costs[0], revision, coverage, piloto.digest(raw)


def root(test_id):
    return test_id.split('#', 1)[0].split('$', 1)[0]


def run(output, *, training=None, training_audit=None):
    ids, routes, selection, revision, coverage, publication_hash = frozen_input()
    start = perf_counter_ns()
    features = [(POSITION, SHA, test_id, *vector(test_id)) for test_id in ids]
    audit = [(*row[:3], *route_fields(routes[root(row[2])])) for row in features]
    extraction = perf_counter_ns() - start
    route_counts = Counter(row[3] for row in audit)
    piloto.require(route_counts == revision['rotas_por_metodo'], 'Cobertura de rotas divergente')

    technical = training is None
    if technical:
        x_train, y_train = fixture()
        training_info = {
            'origem': 'fixture interno com alvos artificiais', 'linhas': len(x_train),
            'balanceamento': False, 'janela_experimental': [15, 26, 42],
            'cobertura_janela': {p: {k: coverage[p][k] for k in ('estado_selecao', 'selecionados')}
                                 for p in (15, 26, 42)},
        }
    else:
        piloto.require(training_audit['treino']['suficiente'], 'Treino experimental insuficiente')
        x_train = [row[3:-1] for row in training]
        y_train = [row[-1] for row in training]
        training_info = {'origem': 'replay sintético versionado', 'balanceamento': False,
                         'auditoria': training_audit}
    models = {
        'T2': make_pipeline(StandardScaler(), KNeighborsRegressor(**piloto.KNN)),
        'T3': RandomForestRegressor(**piloto.FOREST),
    }
    source = output.relative_to(BASE.parent.parent).as_posix() + '/manifesto.json'
    rankings, costs, timings = [], [], {}
    for scenario, model in models.items():
        start = perf_counter_ns()
        model.fit(x_train, y_train)
        fit = perf_counter_ns() - start
        lines, inference = rank(model, SHA, scenario, features, source)
        rankings.extend(lines)
        timings[scenario] = {'fit_ns': fit, 'inference_ns': inference}
        costs.extend([
            (SHA, scenario, 'selection', *(selection[key] for key in COST_FIELDS[3:])),
            (SHA, scenario, 'features', 'measured', extraction / 1e6, source),
            (SHA, scenario, 'training', 'measured', fit / 1e6, source),
            (SHA, scenario, 'inference', 'measured', inference / 1e6, source),
        ])
    report = {
        'estado': ('teste_tecnico_fixture_sem_ranking_experimental' if technical else
                   'ranking_experimental_congelado_sem_avaliacao'),
        'posicao': POSITION, 'sha': SHA, 'selecionados': len(ids),
        'publicacao_t1': PUBLICATION, 'manifesto_t1_sha256': publication_hash,
        'conjunto_t1_sha256': set_hash(ids),
        'politica_features': POLICY, 'features_modelo': FEATURES, 'rotas_por_metodo': route_counts,
        'treino': training_info,
        'tempos': {'extracao_compartilhada_ns': extraction, 'modelos': timings},
        'escopo': {
            'selection': 'herdado da publicação T1',
            'features': 'construção dos vetores e auditoria de rotas em memória, uma vez por SHA',
            'training': 'fit com vetores e alvos em memória',
            'inference': 'matriz, predict, ordenação e construção das linhas em memória',
            'excluido_das_medicoes_locais': 'I/O, hashes, verificações, descoberta JUnit e jdeps',
        },
        'ambiente': {'python': platform.python_version(), 'host': platform.platform(),
                     'scikit-learn': version('scikit-learn')},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as temporary:
        stage = Path(temporary) / 'artefatos'
        stage.mkdir()
        piloto.write_csv(stage / 'features_inferencia.csv', (*KEYS, *FEATURES), features)
        piloto.write_csv(stage / 'auditoria_rotas.csv', (*KEYS, *AUDIT_FIELDS), audit)
        suffix = '_fixture' if technical else ''
        piloto.write_csv(stage / f'rankings{suffix}.csv', RANK_FIELDS, rankings)
        piloto.write_csv(stage / f'overhead{suffix}.csv', COST_FIELDS, costs)
        if not technical:
            piloto.write_csv(stage / 'treino_sintetico.csv', (*KEYS, *FEATURES, 'target_synthetic'),
                             training)
        report['sha256_saida'] = {path.name: piloto.digest(path.read_bytes())
                                  for path in sorted(stage.iterdir())}
        piloto.write_json(stage / 'manifesto.json', report)
        stage.rename(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rodada')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.rodada):
        parser.error('Identificador de rodada inválido')
    output = BASE / 'local' / f'expansao50-{args.rodada}'
    if output.exists():
        parser.error(f'Destino já existe: {output}')
    run(output)
    print(output)


if __name__ == '__main__':
    main()
