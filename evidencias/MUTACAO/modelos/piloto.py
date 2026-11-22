import argparse
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
PREFIX = BASE.relative_to(ROOT).as_posix()
T1 = '0d3cd01e68bf223eca124332f74d4486ae6bd6f7'
TRAIN = (15, 26, 42)
VALIDATION = 50
FINAL = 96
DEVELOPMENT = (*TRAIN, VALIDATION)
LABELS = ('induced_failure', 'pass', 'unknown')
FEATURES = ('distancia_rota', 'rota_ausente', 'arestas_lexicais',
            'classe_semente', 'comprimento_nome', 'quantidade_parametros',
            'classe_aninhada')
KNN = {'n_neighbors': 15, 'weights': 'uniform', 'algorithm': 'kd_tree',
       'metric': 'euclidean', 'n_jobs': 1}
FOREST = {'n_estimators': 200, 'min_samples_leaf': 5, 'max_features': 1.0,
          'random_state': 20261122, 'n_jobs': 1}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def records(data):
    return csv.DictReader(io.StringIO(data.decode('utf-8-sig'), newline=''))


def write_json(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2,
                                 allow_nan=False) + '\n').encode('utf-8'))


def write_csv(path, fields, rows):
    with path.open('w', encoding='utf-8', newline='') as output:
        writer = csv.writer(output, lineterminator='\n')
        writer.writerow(fields)
        writer.writerows(rows)


def ordinal(value):
    return value.encode('utf-16-be')


def features(test_id, test_class, decisions):
    route = decisions['rotas']
    current = test_class
    seen = set()
    lexical = 0
    while current in route and route[current] is not None:
        require(current not in seen, f'Ciclo em rota T1: {test_id}')
        seen.add(current)
        edge = route[current]
        lexical += edge['evidencia'] == 'fonte'
        current = edge['destino']
    missing = test_class not in route
    require(missing or current in decisions['sementes'], f'Rota sem semente: {test_id}')
    binary_class, method = test_id.split('#', 1)
    name, signature = method.split('(', 1)
    require(signature.endswith(')'), f'Assinatura T1 inválida: {test_id}')
    parameters = signature[:-1]
    return (len(seen), int(missing), lexical, int(test_class in decisions['sementes']),
            len(name), parameters.count(',') + 1 if parameters else 0,
            int('$' in binary_class))


def frozen_selection(position):
    t1_base = 'evidencias/MUTACAO/t1'
    revision = json.loads(git('show', f'{T1}:{t1_base}/revisoes.json'))[str(position)]
    directory = f'{t1_base}/congelado/{position}'
    manifest_bytes = git('show', f'{T1}:{directory}/manifesto.json')
    manifest = json.loads(manifest_bytes)
    sha = revision['sha']
    require((manifest['posicao'], manifest['sha'], manifest['pai']) ==
            (position, sha, revision['pai']), f'Manifesto T1 incompatível: {position}')
    inputs = {}
    for name in ('selection.csv', 'rankings.csv', 'decisoes.json'):
        inputs[name] = git('show', f'{T1}:{directory}/{name}')
        require(digest(inputs[name]) == manifest['saidas_sha256'][name],
                f'Hash T1 divergente: {position}/{name}')
    decisions = json.loads(inputs['decisoes.json'])
    methods = {}
    selected = []
    for row in records(inputs['selection.csv']):
        test_id = row['test_id']
        require(row['commit_sha'] == sha and row['scenario'] == 'T1'
                and test_id and test_id not in methods
                and row['selected'] in ('true', 'false'), f'Seleção T1 inválida: {position}')
        methods[test_id] = features(test_id, row['source_ref'].split('#', 1)[1], decisions)
        if row['selected'] == 'true':
            selected.append(test_id)
    selected.sort(key=ordinal)
    ranks = list(records(inputs['rankings.csv']))
    require(len(methods) == manifest['candidatos'] and
            len(ranks) == len(selected) == manifest['selecionados'] and
            all((row['commit_sha'], row['scenario'], row['test_id'], row['rank']) ==
                (sha, 'T1', test_id, str(rank))
                for rank, (row, test_id) in enumerate(zip(ranks, selected), 1)),
            f'Ranking T1 inválido: {position}')
    return {'sha': sha, 'pai': revision['pai'], 'methods': methods, 'selected': selected,
            'inventario_sha256': manifest['entradas_sha256']['metodos.tsv'],
            'manifesto_sha256': digest(manifest_bytes), 'arquivos': manifest['saidas_sha256']}


def aggregate(labels, mutations, methods):
    totals = {test_id: Counter() for test_id in methods}
    for (_, test_id), label in labels.items():
        totals[test_id][label] += 1
    for counts in totals.values():
        counts['ausente'] = len(mutations) - sum(counts.values())
    return totals


def load_replay(position, selection, *, after_freeze=None):
    require(position in DEVELOPMENT or (position == FINAL and after_freeze),
            'A posição 96 está fechada para leitura.')
    base = BASE.parent / 'mutantes'
    public = (base / f'pos-{position}').relative_to(ROOT).as_posix()
    summary_ref = f'{public}/resumo.json'
    publication = git('log', '-1', '--format=%H', '--', summary_ref).decode().strip()
    if not publication:
        return {'estado': 'resumo_indisponivel'}, None
    if after_freeze:
        common_base = git('merge-base', publication, after_freeze).decode().strip()
        require(publication != after_freeze and common_base == after_freeze,
                'A publicação final deve suceder o congelamento.')
    summary_bytes = git('show', f'{publication}:{summary_ref}')
    summary = json.loads(summary_bytes)
    sha = selection['sha']
    relative = f'local/{position}/rotulos.csv'
    require((summary['posicao'], summary['sha'], summary['rotulos']) ==
            (position, sha, relative), f'Resumo incompatível: {position}')
    label_path = base / relative
    if not label_path.is_file():
        return {'estado': 'dados_indisponiveis', 'publicacao_commit': publication,
                'resumo_sha256': digest(summary_bytes)}, None
    manifest_bytes = git('show', f'{publication}:{public}/manifesto.json')
    label_bytes = label_path.read_bytes()
    require(digest(manifest_bytes) == summary['manifesto_sha256']
            and digest(label_bytes) == summary['rotulos_sha256']
            and summary['inventario_sha256'] == selection['inventario_sha256'],
            f'Proveniência divergente: {position}')
    manifest = json.loads(manifest_bytes)
    mutations = [item['mutation_id'] for item in manifest['selecionados']]
    require((manifest['sha'], manifest['pai'], manifest['protocolo']) ==
            (sha, selection['pai'], 'tp-mutation-v1')
            and 1 <= len(mutations) <= 4 and all(mutations)
            and len(set(mutations)) == len(mutations), f'Manifesto incompatível: {position}')
    labels = {}
    counts = Counter()
    for row in records(label_bytes):
        key = (row['mutation_id'], row['test_id'])
        label = row['label']
        require(row['sha'] == sha and key[0] in mutations and key[1] in selection['methods']
                and key not in labels and label in LABELS, f'Chave ou rótulo inválido: {position}/{key}')
        if label != 'unknown':
            require(row['controle'] == 'pass' and row['replay'] ==
                    ('fail' if label == 'induced_failure' else 'pass'),
                    f'Observação conhecida sem evidência: {position}/{key}')
        labels[key] = label
        counts[label] += 1
    require(all(counts[label] == summary['contagens'][label] for label in LABELS),
            f'Contagens divergentes: {position}')
    gate = all(summary[key] is True for key in
               ('equivalencia_controle', 'repeticao_coincidente', 'restauracao'))
    totals = aggregate(labels, mutations, selection['methods'])
    report = {'estado': 'disponivel' if gate else 'gate_insuficiente', 'sha': sha,
              'publicacao_commit': publication,
              'resumo_sha256': digest(summary_bytes), 'manifesto_sha256': digest(manifest_bytes),
              'rotulos_sha256': digest(label_bytes), 'publicador_gate_aprovado': summary['gate_aprovado'],
              'variantes': len(mutations), 't0': denominators(totals, totals),
              't1': denominators(totals, selection['selected'])}
    return report, (mutations, labels, totals) if gate else None


def denominators(totals, methods):
    counts = Counter()
    for test_id in methods:
        counts.update(totals[test_id])
    summary = {label: counts[label] for label in (*LABELS, 'ausente')}
    summary['denominador'] = counts['induced_failure'] + counts['pass']
    summary['metodos'] = len(methods)
    summary['metodos_com_alvo'] = sum(target(totals[test_id]) is not None for test_id in methods)
    return summary


def target(counts):
    known = counts['induced_failure'] + counts['pass']
    return counts['induced_failure'] / known if known else None


def sufficiency(reports, positions):
    counts = Counter(dict.fromkeys((*LABELS, 'ausente', 'denominador',
                                    'metodos', 'metodos_com_alvo'), 0))
    for pos in positions:
        if 't1' in reports[pos]:
            counts.update(reports[pos]['t1'])
    return {**counts, 'posicoes': list(positions), 'suficiente':
            all(reports[pos]['estado'] == 'disponivel' for pos in positions)
            and counts['induced_failure'] > 0 and counts['pass'] > 0}


def detection(order, mutation, labels):
    counts = Counter()
    first = first_gap = gaps_before = None
    for rank, test_id in enumerate(order, 1):
        label = labels.get((mutation, test_id), 'ausente')
        if label in ('unknown', 'ausente') and first_gap is None:
            first_gap = rank
        if label == 'induced_failure' and first is None:
            first = rank
            gaps_before = counts['unknown'] + counts['ausente']
        counts[label] += 1
    possible = min((rank for rank in (first, first_gap) if rank is not None), default=None)
    return {'estado': ('detectado' if first is not None else
                       'indeterminado' if first_gap is not None else 'sem_deteccao'),
            'primeira_posicao_observada': first,
            'primeira_posicao_possivel': possible, 'lacunas_antes': gaps_before,
            **{label: counts[label] for label in (*LABELS, 'ausente')}}


def rank_scores(selected, scores):
    return sorted(zip(selected, map(float, scores)),
                  key=lambda pair: (-pair[1], ordinal(pair[0])))


def evaluate(position, selection, replay, orders):
    mutations, labels, _ = replay
    require(all(len(order) == len(selection['selected']) and
                set(order) == set(selection['selected']) for order in orders.values()),
            'Ordens de avaliação incompatíveis com T1.')
    return [{'posicao': position, 'sha': selection['sha'], 'mutation_id': mutation,
             'ranking': name, **detection(order, mutation, labels)}
            for mutation in mutations for name, order in orders.items()]


def workspace(run):
    require(run and Path(run).name == run and run not in ('.', '..') and ':' not in run,
            'Use um nome simples para a execução.')
    output = BASE / 'local' / run
    output.mkdir(parents=True, exist_ok=False)
    return output


def write_targets(output, selection, totals):
    selected = set(selection['selected'])
    write_csv(output, ('sha', 'test_id', 'selecionado_t1', *LABELS, 'ausente',
                       'denominador', 'alvo'),
              ((selection['sha'], test_id, int(test_id in selected),
                *(totals[test_id][label] for label in (*LABELS, 'ausente')),
                totals[test_id]['induced_failure'] + totals[test_id]['pass'],
                target(totals[test_id]))
               for test_id in sorted(totals, key=ordinal)))


def development(run):
    selections = {pos: frozen_selection(pos) for pos in DEVELOPMENT}
    reports, replays = {}, {}
    output = workspace(run)
    for pos, selection in selections.items():
        reports[pos], replays[pos] = load_replay(pos, selection)
        if replays[pos]:
            write_targets(output / f'alvos-{pos}.csv', selection, replays[pos][2])
    report = {'versao': 1, 'natureza': 'mutacao_sintetica', 't1_commit': T1,
              'python': sys.version, 'posicoes': reports,
              'treino': sufficiency(reports, TRAIN),
              'validacao': sufficiency(reports, (VALIDATION,))}
    report['artefatos_sha256'] = {path.name: digest(path.read_bytes())
                                  for path in sorted(output.glob('alvos-*.csv'))}
    write_json(output / 'diagnostico.json', report)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return output, report, selections, replays


def freeze(run):
    output, report, selections, replays = development(run)
    require(report['treino']['suficiente'] and report['validacao']['suficiente'],
            'Treino ou validação insuficiente. Consulte diagnostico.json.')
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[name] = '1'
    from importlib.metadata import version

    import joblib
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.neighbors import KNeighborsRegressor
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    # A ordem de inserção é fixa, inclusive para vizinhos com distâncias empatadas.
    x_train, y_train = [], []
    for pos in TRAIN:
        selection = selections[pos]
        for test_id in selection['selected']:
            value = target(replays[pos][2][test_id])
            if value is not None:
                x_train.append(selection['methods'][test_id])
                y_train.append(value)
    require(len(y_train) >= KNN['n_neighbors'], 'Treino menor que k.')
    models = {
        'KNN': make_pipeline(StandardScaler(), KNeighborsRegressor(**KNN)),
        'RandomForest': RandomForestRegressor(**FOREST),
    }
    for name, model in models.items():
        model.fit(x_train, y_train)
        joblib.dump(model, output / f'{name}.joblib', compress=3)

    # A posição final entra somente pelo Git congelado de entradas pré-execução.
    selections[FINAL] = frozen_selection(FINAL)
    for pos in (*DEVELOPMENT, FINAL):
        selection = selections[pos]
        selected = selection['selected']
        x = [selection['methods'][test_id] for test_id in selected]
        write_csv(output / f'features-{pos}.csv', ('sha', 'test_id', *FEATURES),
                  ((selection['sha'], test_id, *row) for test_id, row in zip(selected, x)))
        ranked = {'T1': list(zip(selected, [None] * len(selected)))}
        for name, model in models.items():
            ranked[name] = rank_scores(selected, model.predict(x))
        write_csv(output / f'ranking-{pos}.csv', ('sha', 'ranking', 'rank', 'test_id', 'score'),
                  ((selection['sha'], name, rank, test_id, score)
                   for name, rows in ranked.items()
                   for rank, (test_id, score) in enumerate(rows, 1)))
        if pos in replays:
            write_json(output / f'deteccao-{pos}.json', evaluate(
                pos, selection, replays[pos],
                {name: [test_id for test_id, _ in rows] for name, rows in ranked.items()}))
    manifest = {'versao': 1, 'natureza': 'mutacao_sintetica', 't1_commit': T1,
                'codigo_commit': git('rev-parse', 'HEAD').decode().strip(),
                'python': sys.version, 'bibliotecas': {name: version(name) for name in
                    ('scikit-learn', 'numpy', 'scipy', 'joblib', 'threadpoolctl')},
                'codigo_sha256': {name: digest((BASE / name).read_bytes())
                                  for name in ('piloto.py', 'requirements.txt')},
                'caracteristicas': FEATURES, 'historico': 'nenhum',
                'parametros': {'KNN': KNN, 'RandomForest': FOREST},
                'pre_processamento': {'KNN': 'StandardScaler no treino', 'RandomForest': 'nenhum'},
                'treino': report['treino'], 'validacao': report['validacao'],
                'entradas_t1': {pos: {name: selection[name] for name in
                                     ('sha', 'manifesto_sha256', 'arquivos')}
                                for pos, selection in selections.items()},
                'artefatos_sha256': {path.name: digest(path.read_bytes())
                                      for path in sorted(output.iterdir())}}
    write_json(output / 'congelamento.json', manifest)


def final(run, commit, release):
    require(release.strip(), 'Registre a referência da liberação coordenada.')
    require(commit == git('rev-parse', f'{commit}^{{commit}}').decode().strip(),
            'Informe o SHA completo do commit de congelamento.')
    local = BASE / 'local' / run
    manifest_bytes = git('show', f'{commit}:{PREFIX}/congelamento.json')
    require(manifest_bytes == (local / 'congelamento.json').read_bytes(),
            'O congelamento local diverge do Git.')
    manifest = json.loads(manifest_bytes)
    require(manifest['versao'] == 1 and manifest['t1_commit'] == T1
            and manifest['treino']['suficiente'] and manifest['validacao']['suficiente'],
            'Congelamento incompatível.')
    for name, expected in manifest['codigo_sha256'].items():
        require(digest(git('show', f'{commit}:{PREFIX}/{name}')) ==
                digest((BASE / name).read_bytes()) == expected, f'Código divergente: {name}')
    for name, expected in manifest['artefatos_sha256'].items():
        require(digest((local / name).read_bytes()) == expected, f'Artefato divergente: {name}')
    selection = frozen_selection(FINAL)
    orders = {name: [] for name in ('T1', 'KNN', 'RandomForest')}
    for row in records((local / f'ranking-{FINAL}.csv').read_bytes()):
        order = orders[row['ranking']]
        require(row['sha'] == selection['sha'] and int(row['rank']) == len(order) + 1,
                'Posto ou SHA inválido no ranking final.')
        order.append(row['test_id'])
    require(orders['T1'] == selection['selected'] and all(
        len(order) == len(orders['T1']) and set(order) == set(orders['T1'])
        for order in orders.values()), 'Ranking final diverge do conjunto T1.')
    report, replay = load_replay(FINAL, selection, after_freeze=commit)
    adequate = sufficiency({FINAL: report}, (FINAL,))
    result = {'natureza': 'mutacao_sintetica', 'congelamento': commit, 'liberacao': release,
              'posicao': report, 'teste_final': adequate,
              'deteccoes': evaluate(FINAL, selection, replay, orders) if replay else []}
    if replay:
        targets = local / f'alvos-{FINAL}.csv'
        write_targets(targets, selection, replay[2])
        result['alvos_sha256'] = digest(targets.read_bytes())
    write_json(local / 'teste-final.json', result)
    print(json.dumps(result, ensure_ascii=True, indent=2))


def main():
    parser = argparse.ArgumentParser(description='Dataset e ranking do piloto de mutação.')
    parser.add_argument('etapa', choices=('diagnostico', 'congelar', 'final'))
    parser.add_argument('execucao')
    parser.add_argument('--commit')
    parser.add_argument('--liberacao')
    args = parser.parse_args()
    try:
        if args.etapa == 'diagnostico':
            development(args.execucao)
        elif args.etapa == 'congelar':
            freeze(args.execucao)
        else:
            require(args.commit and args.liberacao, 'Informe --commit e --liberacao.')
            require(args.execucao and Path(args.execucao).name == args.execucao
                    and args.execucao not in ('.', '..') and ':' not in args.execucao,
                    'Use um nome simples para a execução.')
            final(args.execucao, args.commit, args.liberacao)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
