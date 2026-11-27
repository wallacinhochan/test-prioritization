"""Audita e prepara o treino sintético por SHA e test_id para o T1 de expansão."""
import argparse
import json
import re
from collections import Counter
from fractions import Fraction

from expansao50 import BASE, BUNDLE, FEATURES, PUBLICATION, piloto, run, set_hash, vector

PACKAGE_COMMIT = '1070e62788e9a180539c9df7ca10b65d48ee978c'
PACKAGE = 'evidencias/MUTACAO/modelos/entrega-replay'
LOT_02 = '41a22e394de36512921bad82a4a28d029d8bb55f'
LOT_03 = 'ba7f204693007f18db648fdf16e34f52c62397f7'
POSITIONS = (15, 26, 42)
LABELS = (*piloto.LABELS, 'ausente')


def blob(commit, path):
    return piloto.git('show', f'{commit}:{path}')


def package_rows():
    index = blob(PACKAGE_COMMIT, f'{PACKAGE}/SHA256SUMS')
    files = {}
    for line in index.decode().splitlines():
        digest, name = line.split()
        data = blob(PACKAGE_COMMIT, f'{PACKAGE}/{name}')
        piloto.require(piloto.digest(data) == digest, f'Checksum divergente: {name}')
        files[name] = data
    provenance = json.loads(files['dados/proveniencia.json'])
    piloto.require(provenance['t1_commit'] == piloto.T1 and
                   provenance['natureza'] == 'mutacao_sintetica' and
                   all(piloto.digest(files[f'dados/{name}']) == digest
                       for name, digest in provenance['arquivos_sha256'].items()),
                   'Proveniência do pacote divergente')
    return provenance, list(piloto.records(files['dados/metodos.csv'])), list(
        piloto.records(files['dados/observacoes.csv'])), piloto.digest(index)


def replay_methods(position, source, methods, observations, *, partition='treino'):
    original = piloto.frozen_selection(position)
    sha = original['sha']
    base = f'evidencias/MUTACAO/mutantes/pos-{position}'
    replay_manifest = blob(PACKAGE_COMMIT, f'{base}/manifesto.json')
    summary = json.loads(blob(PACKAGE_COMMIT, f'{base}/resumo.json'))
    manifest = json.loads(replay_manifest)
    mutations = {item['mutation_id'] for item in manifest['selecionados']}
    piloto.require(source['particao'] == partition and source['sha'] == sha == summary['sha'] ==
                   manifest['sha'] and original['pai'] == manifest['pai'] and
                   source['manifesto_sha256'] == summary['manifesto_sha256'] ==
                   piloto.digest(replay_manifest) and
                   original['inventario_sha256'] == summary['inventario_sha256'] and
                   source['contagens_no_git'] == summary['contagens'] and
                   all(summary[key] is True for key in ('gate_aprovado', 'equivalencia_controle',
                                                       'repeticao_coincidente', 'restauracao')),
                   f'Proveniência do replay incompatível: {position}')
    by_id = {}
    for row in methods:
        method = row['test_id']
        piloto.require(row['sha'] == sha and row['particao'] == partition and method not in by_id
                       and method in original['methods'], f'Método inválido: {position}/{method}')
        by_id[method] = row
    piloto.require(by_id.keys() == original['methods'].keys(), f'Inventário divergente: {position}')
    counts = {method: Counter() for method in by_id}
    seen = set()
    for row in observations:
        key = row['mutation_id'], row['test_id']
        piloto.require(row['sha'] == sha and key not in seen and key[0] in mutations and
                       key[1] in counts and row['label'] in LABELS,
                       f'Observação inválida: {position}/{key}')
        seen.add(key)
        counts[key[1]][row['label']] += 1
    totals = Counter()
    for method, row in by_id.items():
        observed = counts[method]
        target = piloto.target(observed)
        piloto.require(sum(observed.values()) == len(mutations) and
                       all(int(row[key]) == observed[key] for key in LABELS) and
                       tuple(int(row[key]) for key in FEATURES) == vector(method) and
                       (float(row['alvo']) if row['alvo'] else None) == target,
                       f'Alvo divergente: {position}/{method}')
        totals.update(observed)
    piloto.require(all(totals[key] == source['contagens_locais'][key] for key in piloto.LABELS),
                   f'Contagens do pacote divergentes: {position}')
    return original, counts, summary, len(mutations)


def describe(counts):
    totals = sum(counts.values(), Counter())
    targets = [piloto.target(value) for value in counts.values()]
    return {'metodos': len(counts), 'alvos_conhecidos': sum(t is not None for t in targets),
            'alvos_positivos': sum(t is not None and t > 0 for t in targets),
            'alvos_zero': targets.count(0), **{label: totals[label] for label in LABELS}}


def load_lots(selection_commit):
    chain = (PUBLICATION, LOT_02, LOT_03)
    piloto.require(selection_commit in chain, 'Publicação T1 desconhecida')
    revisions, tables, hashes = {}, {}, {}
    for index, commit in enumerate(chain[:chain.index(selection_commit) + 1], 1):
        folder = BUNDLE if index == 1 else f'evidencias/KAN-18/congelado-expansao-lote-{index:02}'
        raw = blob(commit, f'{folder}/manifesto.json')
        manifest = json.loads(raw)
        piloto.require(manifest['seletor'] == 'dirts-expansao-direta-reuso/1.0.0' and
                       manifest['contrato'] == '0.1.0' and not manifest['holdout']['rotulos_lidos'],
                       'Variante T1 incompatível')
        if index > 1:
            piloto.require(manifest['publicacao_base'] == PUBLICATION and
                           manifest['manifesto_base_sha256'] == hashes[PUBLICATION] and
                           not revisions.keys() & manifest['revisoes'].keys(),
                           'Lote T1 incompatível com a base')
        if index == 3:
            piloto.require(manifest['manifestos_lotes_anteriores_sha256'] == {LOT_02: hashes[LOT_02]},
                           'Linhagem do lote 02 divergente')
        hashes[commit] = piloto.digest(raw)
        files = {}
        for name, expected in manifest['saidas_sha256'].items():
            data = blob(commit, f'{folder}/{name}')
            piloto.require(piloto.digest(data) == expected, f'Hash divergente: {folder}/{name}')
            if name in ('selection.csv', 'rankings.csv', 'cobertura.csv'):
                files[name] = list(piloto.records(data))
        for key, revision in manifest['revisoes'].items():
            revisions[key] = revision
            tables[key] = files
    return revisions, tables, hashes


def prepare(selection_commit):
    provenance, methods, observations, index_hash = package_rows()
    revisions, tables, hashes = load_lots(selection_commit)
    report = {'publicacao_pacote': PACKAGE_COMMIT, 'checksums_sha256': index_hash,
              'publicacao_t1': selection_commit, 'manifestos_t1_sha256': hashes, 'revisoes': {}}
    training = []
    for position in POSITIONS:
        source = provenance['revisoes'][str(position)]
        original, counts, summary, mutations = replay_methods(
            position, source, [r for r in methods if r['posicao'] == str(position)],
            [r for r in observations if r['posicao'] == str(position)])
        entry = {
            'sha': original['sha'], 'mutantes': mutations, 'pacote': describe(counts),
            'replay_historico': {
                'hash_rotulos_git': summary['rotulos_sha256'],
                'hash_rotulos_exportados': source['rotulos_locais_sha256'],
                'hash_rotulos_resumo_local': source['rotulos_sha256_no_resumo_local'],
                'contagens_git': summary['contagens'],
            },
        }
        report['revisoes'][str(position)] = entry
        key = f'posicao-{position:03}'
        revision = revisions.get(key)
        if revision is None:
            entry['estado_t1'] = 'indisponivel'
            continue
        files = tables[key]
        coverage, = [r for r in files['cobertura.csv'] if r['posicao'] == str(position)]
        rows = [r for r in files['selection.csv'] if r['commit_sha'] == original['sha']]
        ids = {r['test_id'] for r in rows if r['selected'] == 'true'}
        ranks = [r for r in files['rankings.csv'] if r['commit_sha'] == original['sha']]
        piloto.require((revision['posicao'], revision['sha'], revision['pai']) ==
                       (position, original['sha'], original['pai']) and
                       (coverage['sha'], coverage['pai'], coverage['particao'], coverage['holdout'],
                        coverage['estado_selecao'], coverage['selecionados']) ==
                       (original['sha'], original['pai'], 'treino', 'false', 'congelado', str(len(ids))) and
                       len(rows) == len(counts) and {r['test_id'] for r in rows} == counts.keys() and
                       all(r['scenario'] == 'T1' and r['selected'] in ('true', 'false') for r in rows)
                       and len(ids) == revision['selecionados'] and
                       set_hash(ids) == revision['sha256_conjuntos']['t1'] and
                       set_hash(counts) == revision['sha256_conjuntos']['t0'] and
                       len(ranks) == len(ids) and
                       all((r['test_id'], r['scenario'], r['rank'], r['score']) ==
                           (method, 'T1', str(index), '')
                           for index, (r, method) in enumerate(zip(ranks, sorted(ids, key=piloto.ordinal)), 1)),
                       f'Seleção de treino incompatível: {position}')
        matched = {method: counts[method] for method in ids}
        entry.update(estado_t1='congelado', intersecao=describe(matched))
        for method in sorted(ids, key=piloto.ordinal):
            value = piloto.target(counts[method])
            if value is not None:
                training.append((position, original['sha'], method, *vector(method), value))
    positive = sum(row[-1] > 0 for row in training)
    report['treino'] = {
        'linhas': len(training), 'alvos_positivos': positive,
        'fracao_positivos': str(Fraction(positive, len(training))) if training else None,
        'suficiente': len(training) >= piloto.KNN['n_neighbors'] and 0 < positive < len(training)
        and all(r.get('intersecao', {}).get('alvos_conhecidos', 0) > 0
                for r in report['revisoes'].values()),
    }
    return report, training


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--t1', default=PUBLICATION, help='Commit da publicação congelada T1')
    parser.add_argument('--rodada', help='Congela ranking experimental quando a auditoria passa')
    parser.add_argument('--versionar', action='store_true', help='Grava a rodada fora de local/')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-f0-9]{40}', args.t1):
        parser.error('Informe o SHA completo do commit')
    report, training = prepare(args.t1)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.rodada:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.rodada):
            parser.error('Identificador de rodada inválido')
        parent = BASE if args.versionar else BASE / 'local'
        output = parent / f'expansao50-experimental-{args.rodada}'
        if output.exists():
            parser.error(f'Destino já existe: {output}')
        if not report['treino']['suficiente']:
            parser.error('Treino experimental insuficiente')
        run(output, training=training, training_audit=report)
