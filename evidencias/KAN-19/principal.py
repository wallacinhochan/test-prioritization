"""Exporta as features de inferência da KAN-18 e sua cobertura T0."""
import argparse
import csv
import io
import json

from dataset import BASE, checked, load_natural, piloto

KAN18 = 'evidencias/KAN-18'
PUBLICATION = '260c1af381b3137b1591af9f33e47e987ac7b2b2'
POSITIONS = (1, 2, 26, 50, 75, 100)
KEYS = ('position', 'commit_sha', 'test_id')
OUTPUTS = ('diff.patch', 'selection.csv', 'rankings.csv', 'overhead.csv', 'decisoes.json')


def load_selection(reference, commit, recorte_hash, *,
                   local=BASE.parent / 'KAN-18' / 'local',
                   reference_root=f'{KAN18}/local', extract=piloto.features):
    pos, sha, parent = (commit[key] for key in ('position', 'commit_sha', 'first_parent_sha'))
    piloto.require((reference['posicao'], reference['sha'], reference['pai']) ==
                   (int(pos), sha, parent), f'Verificação fora do recorte: {pos}')
    directory = local / 'selecao' / sha
    manifest_bytes = (directory / 'manifesto.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    piloto.require(manifest['protocolo'] == 'KAN-18' and manifest['contrato'] == '0.1.0' and
                   all(manifest[name] == value for name, value in reference.items() if name != 't0')
                   and manifest['codigo_sha256']['recorte_kan10'] == recorte_hash,
                   f'Manifesto divergente da verificação publicada: {sha}')
    assets = {name: checked(directory / name, manifest['saidas_sha256'][name]) for name in OUTPUTS}
    inventory = checked(local / 'entradas' / sha / 'metodos.tsv',
                        manifest['entradas_sha256']['metodos.tsv'])
    candidates = {}
    for row in csv.DictReader(io.StringIO(inventory.decode('utf-8-sig'), newline=''), delimiter='\t'):
        method = f"{row['classe']}#{row['metodo']}({row['tipos']})"
        piloto.require(method not in candidates and row['raiz'] == row['classe'].split('$', 1)[0],
                       f'Identidade de inventário inválida: {sha}/{method}')
        candidates[method] = row['raiz']

    decisions = json.loads(assets['decisoes.json'])
    prefix = f'{reference_root}/selecao/{sha}'
    selected = {}
    seen = set()
    for row in piloto.records(assets['selection.csv']):
        method = row['test_id']
        root = candidates.get(method)
        reason = decisions['classes_de_execucao'].get(root)
        piloto.require(row['commit_sha'] == sha and row['scenario'] == 'T1' and
                       root is not None and method not in seen and
                       reason in ('dependency', 'fallback', 'no_dependency') and
                       row['selection_reason'] == reason and
                       row['selected'] == ('false' if reason == 'no_dependency' else 'true') and
                       row['source_ref'] == f'{prefix}/decisoes.json#{root}',
                       f'Seleção divergente: {sha}/{method}')
        seen.add(method)
        if row['selected'] == 'true':
            selected[method] = root

    order = sorted(selected, key=piloto.ordinal)
    ranks = list(piloto.records(assets['rankings.csv']))
    piloto.require(seen == candidates.keys() and len(seen) == manifest['candidatos'] and
                   len(ranks) == len(order) == manifest['selecionados'] and
                   all((row['commit_sha'], row['scenario'], row['test_id'], row['rank'],
                        row['score'], row['source_ref']) ==
                       (sha, 'T1', method, str(rank), '', f'{prefix}/manifesto.json#ordem')
                       for rank, (method, row) in enumerate(zip(order, ranks), 1)),
                   f'Inventário ou ranking divergente: {sha}')
    return [(int(pos), sha, method, *extract(method, selected[method], decisions))
            for method in order], candidates, {
        'sha': sha,
        'manifesto_ref': f'{prefix}/manifesto.json',
        'manifesto_sha256': piloto.digest(manifest_bytes),
        'ranking_sha256': manifest['saidas_sha256']['rankings.csv'],
        'selection_sha256': manifest['saidas_sha256']['selection.csv'],
        'decisoes_sha256': manifest['saidas_sha256']['decisoes.json'],
        'inventario_sha256': manifest['entradas_sha256']['metodos.tsv'],
    }


def verify_join(reference, candidates, observed, matched, status):
    published = reference['t0']
    if status != 'complete':
        piloto.require(published['estado'] == 'sem_t0_completo',
                       f'Estado de T0 divergente: {reference["sha"]}')
        return
    only_t0 = observed.keys() - candidates.keys()
    only_inventory = candidates.keys() - observed.keys()
    piloto.require(published['estado'] == 'chaves_iguais' and not only_t0 and not only_inventory
                   and published['metodos'] == len(observed)
                   and published['falhas'] == sum(row['outcome'] == 'fail' for row in observed.values())
                   and published['retidas'] == sum(row['outcome'] == 'fail' for row in matched)
                   and published['duracoes_ausentes_t1_executados'] == sum(
                       row['outcome'] != 'skip' and not row['duration_ms'] for row in matched),
                   f'Junção T0 divergente: {reference["sha"]}')


def export(output):
    commits, runs, oracle, t0_manifest = load_natural()
    source = f'{KAN18}/verificacao.json'
    published = piloto.git('show', f'{PUBLICATION}:{source}')
    references = json.loads(published)
    piloto.require(tuple(item['posicao'] for item in references) == POSITIONS,
                   'As seis posições publicadas da KAN-18 são obrigatórias')
    features, inventory, provenance = {}, {}, {}
    for item in references:
        pos = item['posicao']
        features[pos], inventory[pos], provenance[pos] = load_selection(
            item, commits[pos - 1], t0_manifest['auditoria_sha256'])
    piloto.write_csv(output / 'features_inferencia.csv', (*KEYS, *piloto.FEATURES),
                     (row for rows in features.values() for row in rows))

    references = {item['posicao']: item for item in references}
    coverage, joined = [], []
    for pos, commit in enumerate(commits, 1):
        observed = oracle.get(pos, {})
        status = runs.get(pos, 'sem_t0')
        selected = features.get(pos, [])
        matched = [observed[row[2]] for row in selected if row[2] in observed]
        if pos in references:
            verify_join(references[pos], inventory[pos], observed, matched, status)
        if status == 'complete':
            for row in matched:
                joined.append((pos, row['commit_sha'], row['test_id'], row['outcome'],
                               row['duration_ms'], row['execution_order'], row['source_ref']))
        coverage.append({
            'position': pos, 'commit_sha': commit['commit_sha'],
            'eligibility_kan10': commit['eligibility_status'], 't0_status': status,
            't0_methods': len(observed) if pos in runs else None,
            't0_failures': sum(row['outcome'] == 'fail' for row in observed.values()) if pos in runs else None,
            't1_candidates': len(inventory[pos]) if pos in inventory else None,
            't1_selected': len(selected) if pos in inventory else None,
            't1_with_t0': len(matched) if status == 'complete' and pos in inventory else None,
        })
    fields = tuple(coverage[0])
    piloto.write_csv(output / 'cobertura_principal.csv', fields,
                     ([row[key] for key in fields] for row in coverage))
    piloto.write_csv(output / 'juncao_t1_t0.csv',
                     (*KEYS, 'outcome', 'duration_ms', 'execution_order', 'source_ref'), joined)
    return {
        'protocolo': 'kan19-kan18-v1',
        'kan18_commit': PUBLICATION,
        'verificacao_ref': source,
        'verificacao_sha256': piloto.digest(published),
        'sha256_entrada': {'commits.csv': t0_manifest['auditoria_sha256'],
                           **{name: t0_manifest['sha256'][name] for name in
                              ('t0_runs.csv', 't0_results.csv')}},
        'features_modelo': piloto.FEATURES,
        'selecao': provenance,
        'linhas_inferencia': sum(map(len, features.values())),
        'linhas_juncao': len(joined),
        'falhas_t0': sum(row['t0_failures'] or 0 for row in coverage),
        'falhas_retidas_t1': sum(row[3] == 'fail' for row in joined),
        'revisoes_formais': [row for row in coverage if row['position'] in references],
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
    piloto.write_json(output / 'resumo_principal.json', export(output))


if __name__ == '__main__':
    main()
