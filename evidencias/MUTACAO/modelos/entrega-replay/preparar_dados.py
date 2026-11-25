"""Exporta a coleta local de mutações para comparação de balanceamento."""
import argparse
import csv
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

METHOD = re.compile(r'(?P<nome>[a-zA-Z_$][\w$]*)(?:\((?P<tipos>[^()]*)\))?(?:\[(?P<indice>[0-9]+)\])?')


def tempos(pasta, rodada, resumo, piloto):
    by_name = defaultdict(list)
    by_root = defaultdict(set)
    inventory = pasta / 'inventario/metodos.tsv'
    with inventory.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream, delimiter='\t'):
            test_id = f"{row['classe']}#{row['metodo']}({row['tipos']})"
            by_name[row['raiz'], row['metodo']].append((test_id, row))
            by_root[row['raiz']].add(test_id)

    source = pasta / rodada
    index = (source / 'xml.sha256').read_bytes()
    piloto.require(piloto.digest(index) == resumo['xml_manifesto_sha256'],
                   f'Índice dos XMLs divergente: {source}')
    results, ambiguous = defaultdict(Decimal), set()
    for line in index.decode('utf-8-sig').splitlines():
        expected, name = line.split('  ', 1)
        data = (source / 'surefire' / name).read_bytes()
        piloto.require(piloto.digest(data) == expected, f'XML divergente: {name}')
        root = name.removeprefix('TEST-').removesuffix('.xml')
        for item in ET.fromstring(data).findall('testcase'):
            label = item.get('name', '')
            match = METHOD.fullmatch(label)
            candidates = by_name.get((root, match['nome']), []) if match else []
            matches = []
            for test_id, row in candidates:
                if item.get('classname') not in (row['classe'], row['rotulo_classe']):
                    continue
                types = match['tipos']
                if types is not None:
                    if re.sub(r'\s+', '', types) not in (row['tipos'], row['tipos_curtos']):
                        continue
                elif row['tipos'] and row['rotulo_metodo'] != label:
                    continue
                if match['indice'] and row['tipo_descritor'] not in ('test-template', 'test-factory'):
                    continue
                matches.append(test_id)
            if len(matches) != 1:
                ambiguous.update(matches or [test_id for test_id, _ in candidates] or by_root[root])
                continue
            if any(item.find(tag) is not None for tag in
                   ('flakyFailure', 'flakyError', 'rerunFailure', 'rerunError')):
                ambiguous.add(matches[0])
                continue
            durations = item.get('time')
            if durations is None:
                ambiguous.add(matches[0])
                continue
            results[matches[0]] += Decimal(durations) * 1000
    return {test_id: duration for test_id, duration in results.items() if test_id not in ambiguous}


def exportar(repo, output):
    sys.path.insert(0, str(repo / 'evidencias/MUTACAO/modelos'))
    import piloto

    base = piloto.BASE.parent / 'mutantes'
    output.mkdir(parents=True, exist_ok=False)
    samples, observations, provenance = [], [], {}
    for pos in piloto.DEVELOPMENT:
        directory = base / f'pos-{pos}'
        local = base / 'local' / str(pos)
        selection = piloto.frozen_selection(pos)
        summary = json.loads((directory / 'resumo.json').read_bytes())
        historical = json.loads(subprocess.check_output(
            ['git', 'show', f'HEAD:{(directory / "resumo.json").relative_to(repo)}'], cwd=repo))
        manifest_data = (directory / 'manifesto.json').read_bytes()
        manifest = json.loads(manifest_data)
        data = (local / 'rotulos.csv').read_bytes()
        label_hash = piloto.digest(data)
        alternatives = [data, data.replace(b'\r\n', b'\n')]
        piloto.require(
            all(summary[k] for k in ('gate_aprovado', 'equivalencia_controle',
                                     'repeticao_coincidente', 'restauracao'))
            and summary['sha'] == selection['sha']
            and summary['inventario_sha256'] == selection['inventario_sha256']
            and summary['manifesto_sha256'] == piloto.digest(manifest_data)
            and summary['rotulos_sha256'] in map(piloto.digest, alternatives),
            f'Coleta local divergente na posição {pos}.',
        )
        mutations = [row['mutation_id'] for row in manifest['selecionados']]
        labels = {}
        for row in piloto.records(data):
            key = row['mutation_id'], row['test_id']
            piloto.require(row['sha'] == selection['sha'] and key not in labels
                           and key[0] in mutations and key[1] in selection['methods']
                           and row['label'] in piloto.LABELS, f'Rótulo inválido em {pos}: {key}')
            labels[key] = row['label']
        piloto.require(Counter(labels.values()) == summary['contagens'],
                       f'Contagens divergentes em {pos}.')
        totals = piloto.aggregate(labels, mutations, selection['methods'])
        run_reports = {row['rodada']: row for row in summary['rodadas']}
        intact = tempos(local, 'intacto', run_reports['intacto'], piloto)
        for idx, mutation in enumerate(mutations, 1):
            run = f'variante-{idx}'
            durations = tempos(local, run, run_reports[run], piloto)
            for test_id in selection['methods']:
                observations.append((pos, selection['sha'], mutation, test_id,
                                     labels.get((mutation, test_id), 'ausente'),
                                     durations.get(test_id)))
        split = 'treino' if pos in piloto.TRAIN else 'validacao'
        selected = set(selection['selected'])
        for test_id, features in selection['methods'].items():
            counts = totals[test_id]
            samples.append((pos, split, selection['sha'], test_id, int(test_id in selected),
                            *features, *(counts[label] for label in (*piloto.LABELS, 'ausente')),
                            piloto.target(counts), intact.get(test_id)))
        provenance[pos] = {
            'particao': split, 'sha': selection['sha'],
            'imagem': json.loads((local / 'entrada/fonte.json').read_bytes())['imagem'],
            'manifesto_sha256': summary['manifesto_sha256'],
            'rotulos_locais_sha256': label_hash,
            'rotulos_sha256_no_resumo_local': summary['rotulos_sha256'],
            'contagens_locais': summary['contagens'],
            'contagens_no_git': historical['contagens'],
            'metodos_com_duracao_intacto': len(intact),
            'metodos_t1_sem_duracao_intacto': len(selected.difference(intact)),
            'xml_manifestos': {name: row['xml_manifesto_sha256']
                              for name, row in run_reports.items()},
        }

    piloto.write_csv(output / 'metodos.csv',
                     ('posicao', 'particao', 'sha', 'test_id', 'selecionado_t1',
                      *piloto.FEATURES, *piloto.LABELS, 'ausente', 'alvo',
                      'duracao_intacto_ms'), samples)
    piloto.write_csv(output / 'observacoes.csv',
                     ('posicao', 'sha', 'mutation_id', 'test_id', 'label', 'duracao_ms'),
                     observations)
    piloto.write_json(output / 'proveniencia.json', {
        'natureza': 'mutacao_sintetica',
        't1_commit': piloto.T1,
        'revisoes': provenance,
        'arquivos_sha256': {name: piloto.digest((output / name).read_bytes())
                            for name in ('metodos.csv', 'observacoes.csv')},
    })
    print(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    parser.add_argument('saida', type=Path)
    options = parser.parse_args()
    exportar(options.repo.resolve(), options.saida.resolve())
