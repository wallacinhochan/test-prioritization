"""Avalia os rankings já congelados usando apenas o replay sintético da revisão 50."""
import json
import math
from collections import Counter

from auditar_treino_expansao import LABELS, PACKAGE_COMMIT, blob, package_rows, replay_methods
from expansao50 import POSITION, PUBLICATION, SHA, frozen_input, piloto, set_hash

FREEZE = 'a06d381c7a9e0fc896e7c5ae84d94a452eedc56a'
FOLDER = 'evidencias/KAN-19/expansao50-experimental-v1'


def verified_rankings():
    raw = blob(FREEZE, f'{FOLDER}/manifesto.json')
    manifest = json.loads(raw)
    ids, _, _, revision, _, t1_hash = frozen_input()
    piloto.require(
        (manifest['estado'], manifest['sha'], manifest['posicao'], manifest['publicacao_t1'],
         manifest['manifesto_t1_sha256'], manifest['conjunto_t1_sha256'], manifest['selecionados']) ==
        ('ranking_experimental_congelado_sem_avaliacao', SHA, POSITION, PUBLICATION,
         t1_hash, set_hash(ids), len(ids)), 'Manifesto de ranking incompatível')
    files = {}
    for name, expected in manifest['sha256_saida'].items():
        data = blob(FREEZE, f'{FOLDER}/{name}')
        piloto.require(piloto.digest(data) == expected, f'Hash do congelamento divergente: {name}')
        files[name] = data
    rows = list(piloto.records(files['rankings.csv']))
    piloto.require(len(rows) == 2 * len(ids), 'Quantidade de rankings incompatível')
    orders = {'T1': ids}
    for scenario in ('T2', 'T3'):
        subset = [r for r in rows if r['scenario'] == scenario]
        order = [r['test_id'] for r in subset]
        piloto.require(len(order) == len(ids) and set(order) == set(ids) and
                       all(r['commit_sha'] == SHA and r['rank'] == str(rank)
                           and r['source_ref'] == f'{FOLDER}/manifesto.json'
                           and math.isfinite(float(r['score']))
                           for rank, r in enumerate(subset, 1)) and
                       subset == sorted(subset, key=lambda r: (
                           -float(r['score']), piloto.ordinal(r['test_id']))),
                       f'Chaves, postos ou escores divergentes: {scenario}')
        orders[scenario] = order
    return orders, revision, piloto.digest(raw)


def evaluate():
    orders, revision, freeze_hash = verified_rankings()
    provenance, methods, observations, index_hash = package_rows()
    source = provenance['revisoes'][str(POSITION)]
    methods = [r for r in methods if r['posicao'] == str(POSITION)]
    observations = [r for r in observations if r['posicao'] == str(POSITION)]
    original, counts, summary, num_mutations = replay_methods(
        POSITION, source, methods, observations, partition='validacao')
    piloto.require(set_hash(counts) == revision['sha256_conjuntos']['t0'] and
                   revision['pai'] == original['pai'] and
                   source['rotulos_locais_sha256'] == source['rotulos_sha256_no_resumo_local'],
                   'Replay T0 incompatível')
    labels = {(r['mutation_id'], r['test_id']): r['label'] for r in observations}
    mutations = sorted({key[0] for key in labels})
    piloto.require(len(mutations) == num_mutations, 'Mutantes incompatíveis')
    results = {}
    totals = Counter()
    for mutation in mutations:
        t0 = Counter(labels.get((mutation, test_id), 'ausente') for test_id in counts)
        scenarios = {'T0': {
            'estado': ('detectado' if t0['induced_failure'] else
                       'indeterminado' if t0['unknown'] or t0['ausente'] else 'sem_deteccao'),
            'primeira_posicao_observada': None, 'primeira_posicao_possivel': None,
            'lacunas_antes': None, **{label: t0[label] for label in LABELS},
            'metodos': len(counts), 'denominador_conhecido': t0['pass'] + t0['induced_failure'],
        }}
        for scenario, order in orders.items():
            result = piloto.detection(order, mutation, labels)
            scenarios[scenario] = {**result, 'metodos': len(order),
                                   'denominador_conhecido': result['pass'] + result['induced_failure']}
        for scenario, result in scenarios.items():
            totals[scenario] += result['estado'] == 'detectado'
        results[mutation] = scenarios
    return {'sha': SHA, 'posicao': POSITION, 'congelamento': FREEZE,
            'manifesto_congelamento_sha256': freeze_hash, 't1': PUBLICATION,
            'pacote_replay': PACKAGE_COMMIT, 'sha256_indice_replay': index_hash,
            'rotulos_fonte_sha256': source['rotulos_locais_sha256'],
            'rotulos_resumo_historico_sha256': summary['rotulos_sha256'],
            'denominador_mutantes': num_mutations,
            'detectados': {scenario: totals[scenario] for scenario in ('T0', *orders)},
            'mutantes': results,
            'ordem_t0': 'indisponivel', 'orcamento_oficial': 'indisponivel'}


if __name__ == '__main__':
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2))
