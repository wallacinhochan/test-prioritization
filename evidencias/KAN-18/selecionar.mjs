import { grafo, inventario, selecionar } from '../MUTACAO/t1/selecionar.mjs';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdirSync, mkdtempSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const raiz = fileURLToPath(new URL('.', import.meta.url));
const versao = '1.0.0';
const revisoes = readFileSync(new URL('../KAN-10/commits.csv', import.meta.url), 'utf8');
const java = /^src\/(main|test)\/java\/(.+)\.java$/u;
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const csv = linhas => linhas.map(linha => linha.map(campo =>
    `"${String(campo).replaceAll('"', '""')}"`).join(',')).join('\n') + '\n';

function git(fonte, args, input) {
    const cmd = spawnSync('git', ['-c', `safe.directory=${fonte}`, '-C', fonte, ...args], {
        input, maxBuffer: 64 * 1024 * 1024,
    });
    if (cmd.error || cmd.status !== 0) {
        throw new Error(`git ${args[0]}: ${cmd.error ?? cmd.stderr.toString()}`);
    }
    return cmd.stdout;
}

function fontesJava(fonte, sha) {
    const entradas = git(fonte, ['ls-tree', '-rz', sha, '--', 'src/main/java', 'src/test/java'])
        .toString().split('\0').filter(Boolean).map(registro => {
            const [meta, caminho] = registro.split('\t');
            return { hash: meta.split(' ')[2], caminho, tipo: caminho.match(java) };
        }).filter(item => item.tipo);
    const pedido = entradas.map(item => item.hash).join('\n') + '\n';
    const blobs = git(fonte, ['cat-file', '--batch'], pedido);
    let offset = 0;
    return entradas.map(({ hash, caminho, tipo }) => {
        const fim = blobs.indexOf(10, offset);
        const [objeto, formato, tamanho] = blobs.toString('ascii', offset, fim).split(' ');
        offset = fim + 1 + Number(tamanho);
        if (objeto !== hash || formato !== 'blob' || blobs[offset] !== 10) {
            throw new Error(`Blob inesperado para ${caminho}`);
        }
        const codigo = blobs.toString('utf8', fim + 1, offset++);
        const nome = tipo[2].replaceAll('/', '.');
        return { caminho, nome, producao: tipo[1] === 'main', codigo };
    });
}

function congelar(posicao, fonte) {
    const registro = revisoes.split(/\r?\n/).find(linha => linha.startsWith(`"${posicao}",`));
    const revisao = /^"\d+","([0-9a-f]{40})","([0-9a-f]{40})",/.exec(registro ?? '');
    if (!revisao) throw new Error(`Posição ausente ou inválida na KAN-10: ${posicao}`);
    const [, sha, pai] = revisao;
    const pasta = join(raiz, 'local', 'entradas', sha);
    const saida = join(raiz, 'local', 'selecao', sha);
    const ler = nome => readFileSync(join(pasta, nome));

    if (ler('compilacao-ok').toString().trim() !== sha) throw new Error('SHA da descoberta divergente');
    const inicio = process.hrtime.bigint();
    if (git(fonte, ['rev-parse', `${sha}^1`]).toString().trim() !== pai) {
        throw new Error('Primeiro pai divergente do protocolo');
    }
    const alteracoes = git(fonte, ['diff', '--no-renames', '--no-ext-diff', '--name-status', '-z', pai, sha])
        .toString().split('\0').filter(Boolean);
    const diff = git(fonte, ['diff', '--no-renames', '--full-index', '--no-ext-diff', '--no-color', '--no-textconv', pai, sha]);
    const arquivos = fontesJava(fonte, sha);
    const arquivoPorCaminho = new Map(arquivos.map(item => [item.caminho, item]));
    const tsv = ler('metodos.tsv');
    const testes = inventario(tsv.toString());
    const jdeps = ler('jdeps.txt');
    const fallback = [];
    let reverso = new Map();
    let compiladas = new Set();
    try {
        ({ reverso, compiladas } = grafo(arquivos, jdeps.toString()));
    } catch (erro) {
        fallback.push(`Grafo indisponível: ${erro.message}`);
    }

    const sementes = new Map();
    if (/^\s+\S+\s+->\s+org\.apache\.commons\.lang3\.[^\s]+\s+not found\s*$/m.test(jdeps.toString())) {
        fallback.push('Referência interna não resolvida pelo jdeps');
    }
    for (let i = 0; i < alteracoes.length; i += 2) {
        const [status, caminho] = alteracoes.slice(i, i + 2);
        if (caminho === 'src/changes/changes.xml') continue;
        const arquivo = arquivoPorCaminho.get(caminho);
        if (!arquivo || !['A', 'M'].includes(status) || !compiladas.has(arquivo.nome)) {
            fallback.push(`Alteração sem mapeamento Java compilado: ${status} ${caminho}`);
        } else {
            sementes.set(arquivo.nome, caminho);
        }
    }
    if (!sementes.size) fallback.push('Diff sem classe-alvo Java mapeada');
    const rotas = selecionar(sementes.keys(), reverso);
    const classesTeste = new Set([...testes.values()].map(teste => teste.classe));
    if ([...classesTeste].some(classe => !compiladas.has(classe))) {
        fallback.push('Classe de execução sem mapeamento no grafo compilado');
    }
    for (const [classe, caminho] of sementes) {
        if (![...selecionar([classe], reverso).keys()].some(alvo => classesTeste.has(alvo))) {
            fallback.push(`Nenhum teste alcança a semente: ${caminho}`);
        }
    }
    const motivoClasse = classe => fallback.length ? 'fallback' : rotas.has(classe) ? 'dependency' : 'no_dependency';
    const base = `evidencias/KAN-18/local/selecao/${sha}`;
    const selecao = [['commit_sha', 'scenario', 'test_id', 'selected', 'selection_reason', 'source_ref']];
    const ranking = [['commit_sha', 'scenario', 'test_id', 'rank', 'score', 'source_ref']];
    const ids = [...testes.keys()].sort();
    for (const id of ids) {
        const { classe } = testes.get(id);
        const motivo = motivoClasse(classe);
        const incluir = motivo !== 'no_dependency';
        selecao.push([sha, 'T1', id, incluir, motivo, `${base}/decisoes.json#${classe}`]);
        if (incluir) ranking.push([sha, 'T1', id, ranking.length, '', `${base}/manifesto.json#ordem`]);
    }
    const custoNs = Number(process.hrtime.bigint() - inicio);
    mkdirSync(join(raiz, 'local', 'selecao'), { recursive: true });
    const temporaria = mkdtempSync(`${saida}-`);
    try {
        const escrever = (nome, conteudo) => writeFileSync(join(temporaria, nome), conteudo, { flag: 'wx' });
        const json = valor => JSON.stringify(valor, null, 2) + '\n';
        escrever('diff.patch', diff);
        escrever('selection.csv', csv(selecao));
        escrever('rankings.csv', csv(ranking));
        escrever('overhead.csv', csv([
            ['commit_sha', 'scenario', 'phase', 'measurement_status', 'duration_ms', 'source_ref'],
            [sha, 'T1', 'selection', 'measured', Math.round(custoNs / 1e6), `${base}/manifesto.json#custo`],
        ]));
        escrever('decisoes.json', json({
            sementes: Object.fromEntries(sementes),
            fallback,
            rotas: Object.fromEntries([...rotas].sort(([a], [b]) => a < b ? -1 : a === b ? 0 : 1)),
            classes_de_execucao: Object.fromEntries([...classesTeste].sort().map(classe =>
                [classe, motivoClasse(classe)])),
        }));
        const entradas = ['fonte.tar', 'pom-efetivo.xml', 'classpath.txt', 'classes.txt',
            'metodos.tsv', 'jdeps.txt', 'DescobertaT0.java', 'descobrir.sh', 'descoberta.log'];
        const saidas = ['diff.patch', 'selection.csv', 'rankings.csv', 'overhead.csv', 'decisoes.json'];
        escrever('manifesto.json', json({
            protocolo: 'KAN-18', contrato: '0.1.0', seletor: versao, posicao: Number(posicao), sha, pai,
            ordem: 'test_id crescente (ordem ordinal, sensível a maiúsculas), todas as prioridades empatadas',
            inventario: 'JUnit Launcher.discover sobre classes raiz *Test do classpath da mesma revisão',
            imagem: 'sha256:6e15bf7fd834e6998883afacb56e4b6de6b180fff899bf3fb0474840f5ac93d6',
            candidatos: ids.length, selecionados: ranking.length - 1, fallback,
            custo: {
                ns: custoNs, ms: Math.round(custoNs / 1e6), node: process.version,
                plataforma: process.platform, arquitetura: process.arch,
                intervalo: 'do primeiro pai e diff à construção das linhas, com leitura do inventário e do jdeps locais',
                cache: 'um processo, sem cache do seletor, cache do sistema operacional não controlado',
            },
            codigo_sha256: {
                seletor: sha256(readFileSync(fileURLToPath(import.meta.url))),
                seletor_piloto: sha256(readFileSync(new URL('../MUTACAO/t1/selecionar.mjs', import.meta.url))),
                recorte_kan10: sha256(readFileSync(new URL('../KAN-10/commits.csv', import.meta.url))),
            },
            entradas_sha256: Object.fromEntries(entradas.map(nome => [nome, sha256(ler(nome))])),
            saidas_sha256: Object.fromEntries(saidas.map(nome => [nome, sha256(readFileSync(join(temporaria, nome)))])),
        }));
        renameSync(temporaria, saida);
    } finally {
        rmSync(temporaria, { recursive: true, force: true });
    }
    console.log(`${posicao}: ${ranking.length - 1}/${ids.length}, ${Math.round(custoNs / 1e6)} ms`);
}

const [posicao, fonte] = process.argv.slice(2);
if (!/^[1-9]\d?$|^100$/.test(posicao ?? '') || !fonte) {
    throw new Error('Uso: node selecionar.mjs <posição KAN-10> <clone Commons Lang>');
}
congelar(posicao, resolve(fonte).replaceAll('\\', '/'));
