"""Ajusta KNN no treino sintético publicado e ordena o T1 formal posterior."""
import argparse
import json
import platform
import re
import sys
from collections import Counter
from importlib.metadata import version
from math import isfinite
from pathlib import Path
from tempfile import TemporaryDirectory
from time import get_clock_info, perf_counter_ns

import joblib
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

BASE = Path(__file__).resolve().parent
EVIDENCE = BASE.parent
ROOT = EVIDENCE.parent
PILOT = EVIDENCE / 'MUTACAO' / 'modelos'
sys.path.insert(0, str(EVIDENCE / 'KAN-19'))
from dataset import checked, piloto

PUBLICATION = '92aff717b2521317966e8e4076afb79a77aa0287'
SCENARIO = 'T2'
KEYS = ('position', 'commit_sha', 'test_id')
RANK_FIELDS = ('commit_sha', 'scenario', 'test_id', 'rank', 'score', 'source_ref')
OVERHEAD_FIELDS = ('commit_sha', 'scenario', 'phase', 'measurement_status',
                   'duration_ms', 'source_ref')
TRAIN_CSV = 'treino_sintetico.csv'
FEATURE_CSV = 'features_inferencia.csv'


def published(relative):
    return json.loads(piloto.git('show', f'{PUBLICATION}:evidencias/{relative}'))


def load_inputs(train_path, feature_path):
    training = published('KAN-19/resumo.json')
    formal = published('KAN-19/resumo_principal.json')
    for summary in (training, formal):
        piloto.require(tuple(summary['features_modelo']) == piloto.FEATURES,
                       'Ordem de features divergente da referência')
    hashes = {name: summary['sha256_saida'][name]
              for name, summary in ((TRAIN_CSV, training), (FEATURE_CSV, formal))}
    train_rows = piloto.records(checked(train_path, hashes[TRAIN_CSV]))
    feature_rows = piloto.records(checked(feature_path, hashes[FEATURE_CSV]))
    piloto.require(tuple(feature_rows.fieldnames) == (*KEYS, *piloto.FEATURES) and
                   tuple(train_rows.fieldnames[4:11]) == piloto.FEATURES,
                   'Colunas preditivas fora da ordem publicada')

    train_shas = {str(pos): training['replays_treino'][str(pos)]['sha'] for pos in piloto.TRAIN}
    vectors, targets, seen = [], [], set()
    counts = Counter()
    for row in train_rows:
        pos, sha, method = (row[key] for key in KEYS)
        target = float(row['target_synthetic'])
        piloto.require(train_shas.get(pos) == sha and row['partition'] == 'treino' and
                       (sha, method) not in seen and 0 <= target <= 1,
                       f'Linha de treino inválida: {pos}/{method}')
        seen.add((sha, method))
        counts[pos] += 1
        vectors.append(tuple(int(row[name]) for name in piloto.FEATURES))
        targets.append(target)
    piloto.require(counts.keys() == train_shas.keys() and
                   len(targets) == training['linhas_treino'] and
                   sum(target > 0 for target in targets) == training['alvos_sinteticos_positivos'],
                   'Cobertura de treino divergente da publicação')

    by_position = {pos: [] for pos in formal['selecao']}
    for row in feature_rows:
        by_position[row['position']].append(row)

    selection = {str(entry['posicao']): entry for entry in published('KAN-18/verificacao.json')}
    coverage, inputs = [], []
    for pos, reference in sorted(formal['selecao'].items(), key=lambda item: int(item[0])):
        sha = reference['sha']
        directory = (ROOT / reference['manifesto_ref']).parent
        baseline = list(piloto.records(checked(directory / 'rankings.csv',
                                              reference['ranking_sha256'])))
        rows = by_position[pos]
        methods = [row['test_id'] for row in rows]
        piloto.require(len(methods) == len(set(methods)) == len(baseline) ==
                       selection[pos]['selecionados'] and
                       all((rank['commit_sha'], rank['scenario'], rank['test_id'], rank['rank']) ==
                           (sha, 'T1', row['test_id'], str(index)) and row['commit_sha'] == sha
                           for index, (rank, row) in enumerate(zip(baseline, rows), 1)),
                       f'Chaves ou ordem divergentes de T1: {pos}')
        eligible = int(pos) > max(piloto.TRAIN)
        coverage.append({'posicao': int(pos), 'sha': sha, 'linhas_t1': len(methods),
                         'ranking_t1_sha256': reference['ranking_sha256'],
                         'estado': 'ranking' if eligible else 'sem_ranking_anterioridade'})
        if eligible:
            overhead_hash = selection[pos]['saidas_sha256']['overhead.csv']
            overhead, = piloto.records(checked(directory / 'overhead.csv', overhead_hash))
            piloto.require(tuple(overhead[key] for key in OVERHEAD_FIELDS[:3]) ==
                           (sha, 'T1', 'selection'), f'Overhead T1 inválido: {pos}')
            coverage[-1]['overhead_t1_sha256'] = overhead_hash
            inputs.append((sha, methods, rows, overhead))
    return vectors, targets, inputs, {
        'publicacao': PUBLICATION,
        'sha256_entrada': hashes,
        'features_modelo': list(piloto.FEATURES),
        'treino': [{'posicao': pos, 'sha': train_shas[str(pos)], 'linhas': counts[str(pos)]}
                   for pos in piloto.TRAIN],
        'alvos_positivos': sum(target > 0 for target in targets),
        'corte_inclusivo_treino': max(piloto.TRAIN),
        'cobertura': coverage,
        'demais_posicoes': 'sem T1 formal e sem vetores de inferência na publicação',
        'ordem_treino': 'ordem física do CSV de treino, preservada no fit',
        'ordem_inferencia': 'posição crescente e ordem T1 dentro do SHA, antes do predict',
        'ordem_ranking': 'score decrescente, test_id crescente em unidades UTF-16 ordinais',
    }


def run(args):
    piloto.require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.run),
                   'Use um identificador de execução alfanumérico, com hífen ou sublinhado')
    local = BASE / 'local'
    output = local / args.run
    piloto.require(not output.exists(), f'Destino já existe: {output}')
    expected = dict(line.split('==') for line in (PILOT / 'requirements.txt').read_text().splitlines())
    versions = {name: version(name) for name in expected}
    piloto.require(versions == expected and platform.python_version() == '3.12.14',
                   f'Use CPython 3.12.14 e as versões do piloto: {expected}')

    vectors, targets, inputs, manifest = load_inputs(args.train, args.features)
    source = f'{output.relative_to(ROOT).as_posix()}/manifesto.json'
    model = make_pipeline(StandardScaler(), KNeighborsRegressor(**piloto.KNN))
    start = perf_counter_ns()
    model.fit(vectors, targets)
    training_ns = perf_counter_ns() - start
    overhead_rows = [(inputs[0][0], SCENARIO, 'training', 'measured',
                      milliseconds(training_ns), f'{source}#training')]
    ranking_rows, inference_ns = [], {}
    for sha, methods, rows, t1 in inputs:
        start = perf_counter_ns()
        features = [tuple(int(row[name]) for name in piloto.FEATURES) for row in rows]
        scores = model.predict(features)
        ranked = piloto.rank_scores(methods, scores)
        lines = [(sha, SCENARIO, method, rank, score, f'{source}#modelo')
                 for rank, (method, score) in enumerate(ranked, 1)]
        inference_ns[sha] = perf_counter_ns() - start
        piloto.require(len(scores) == len(lines) == len(methods) and
                       all(isfinite(line[4]) for line in lines),
                       f'Escore ausente ou não finito: {sha}')
        ranking_rows.extend(lines)
        overhead_rows.extend([
            (sha, SCENARIO, 'selection', *(t1[k] for k in OVERHEAD_FIELDS[3:])),
            (sha, SCENARIO, 'features', 'unknown', '', f'{source}#features'),
            (sha, SCENARIO, 'inference', 'measured', milliseconds(inference_ns[sha]),
             f'{source}#inference'),
        ])

    manifest.update({
        'scenario': SCENARIO,
        'modelo': {'preprocessamento': model.steps[0][1].get_params(),
                   'knn': model.steps[1][1].get_params(),
                   'artefato': 'knn.joblib'},
        'ambiente': {'python': sys.version, 'bibliotecas': versions,
                     'plataforma': platform.platform(), 'arquitetura': platform.machine(),
                     'processador': platform.processor(),
                     'cache': 'processo novo por rodada; cache do SO não controlado'},
        'relogio': {'implementacao': get_clock_info('perf_counter').implementation,
                   'unidade_bruta': 'ns', 'unidade_csv': 'ms'},
        'training': {'sha_disponibilidade': inputs[0][0], 'duracao_ns': training_ns,
                     'janela': 'fit do pipeline com vetores e alvos em memória'},
        'features': {'estado': 'unknown', 'motivo': 'vetores entregues prontos pela KAN-19',
                     'disponibilidade': 'vetores estáticos pré-execução no replay'},
        'inference': {'duracao_ns_por_sha': inference_ns,
                      'janela': 'conversão dos vetores disponíveis, predict com escalonamento, '
                                'ordenação e construção das linhas; sem I/O'},
        'disponibilidade_treino': 'rótulos sintéticos congelados antes do replay posterior',
        'arquivos_locais': {TRAIN_CSV: str(args.train.resolve()),
                           FEATURE_CSV: str(args.features.resolve())},
        'codigo_sha256': {path.name: piloto.digest(path.read_bytes())
                          for path in (Path(__file__), PILOT / 'piloto.py')},
    })
    local.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix=f'.{args.run}-', dir=local) as temp:
        stage = Path(temp) / 'artefatos'
        stage.mkdir()
        piloto.write_csv(stage / 'rankings.csv', RANK_FIELDS, ranking_rows)
        piloto.write_csv(stage / 'overhead.csv', OVERHEAD_FIELDS, overhead_rows)
        joblib.dump(model, stage / 'knn.joblib')
        manifest['sha256_saida'] = {path.name: piloto.digest(path.read_bytes())
                                    for path in sorted(stage.iterdir())}
        piloto.write_json(stage / 'manifesto.json', manifest)
        stage.rename(output)
    print(output)


def milliseconds(ns):
    return f'{ns // 1_000_000}.{ns % 1_000_000:06d}'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', help='Novo diretório sob local/')
    parser.add_argument('--train', type=Path, required=True)
    parser.add_argument('--features', type=Path, required=True)
    run(parser.parse_args())
