import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const raiz = fileURLToPath(new URL('.', import.meta.url));
const versao = '1.0.0';
const revisoes = JSON.parse(readFileSync(join(raiz, 'revisoes.json'), 'utf8'));
const java = /^src\/(main|test)\/java\/(.+)\.java$/u;
const identificador = /[\p{L}_$][\p{L}\p{N}_$]*/gu;
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const csv = linhas => linhas.map(linha => linha.map(campo =>
    `"${String(campo).replaceAll('"', '""')}"`).join(',')).join('\n') + '\n';
const classeRaiz = nome => nome.split('$', 1)[0];
const nomeSimples = nome => nome.split('.').at(-1);

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

function inventario(tsv) {
    // A sonda usa aspas inclusive para rótulos com tabulação ou quebra de linha.
    const registros = tsv.match(/^"(?:[^"]|"")*"(?:\t"(?:[^"]|"")*"){8}\r?$/gm) ?? [];
    const linhas = registros.map(linha => linha.match(/"(?:[^"]|"")*"/g)
        .map(campo => campo.slice(1, -1).replaceAll('""', '"')));
    const cabecalho = 'raiz\tclasse\trotulo_classe\tmetodo\ttipos\ttipos_curtos\trotulo_metodo\ttipo_descritor\tdescritor';
    if (!linhas.length || tsv.replace(/\r\n/g, '\n').trimEnd() !==
        [cabecalho, ...registros.map(linha => linha.replace(/\r$/, ''))].join('\n')) {
        throw new Error('TSV da descoberta ausente ou malformado');
    }
    const testes = new Map();
    for (const [raizClasse, classe, , metodo, tipos, , , tipo, descritor] of linhas) {
        if (!['method', 'test-template', 'test-factory'].includes(tipo) ||
            !descritor.startsWith('[engine:junit-jupiter]/') || raizClasse !== classeRaiz(classe)) {
            throw new Error(`Descritor não tratado: ${descritor}`);
        }
        const id = `${classe}#${metodo}(${tipos})`;
        if (testes.has(id)) throw new Error(`Identidade duplicada: ${id}`);
        testes.set(id, { classe: raizClasse, descritor });
    }
    return testes;
}

function grafo(fontes, jdeps) {
    const reverso = new Map();
    function ligar(origem, destino, tipo) {
        if (origem === destino) return;
        if (!reverso.has(destino)) reverso.set(destino, new Map());
        const anteriores = reverso.get(destino);
        if (!anteriores.has(origem)) anteriores.set(origem, tipo);
    }

    let grupo;
    const compiladas = new Set();
    for (const linha of jdeps.split(/\r?\n/u)) {
        const bloco = /^(classes|test-classes)\s+->\s+/u.exec(linha);
        if (bloco) grupo = bloco[1];
        const aresta = /^\s+(\S+)\s+->\s+(\S+)\s+(.+?)\s*$/u.exec(linha);
        if (!aresta) continue;
        const [, origem, destino, artefato] = aresta;
        if (!grupo) throw new Error('Saída jdeps sem bloco de classes do projeto');
        compiladas.add(classeRaiz(origem));
        if (['classes', 'test-classes'].includes(artefato)) {
            ligar(classeRaiz(origem), classeRaiz(destino), 'bytecode');
        }
    }
    if (!compiladas.size) throw new Error('Grafo jdeps vazio');

    const porNome = new Map();
    for (const { nome } of fontes) {
        const simples = nomeSimples(nome);
        if (!porNome.has(simples)) porNome.set(simples, []);
        porNome.get(simples).push(nome);
    }
    const producao = new Set(fontes.filter(arquivo => arquivo.producao).map(arquivo => arquivo.nome));
    for (const { nome, codigo } of fontes) {
        // Comentários são descartados. Strings permanecem para captar nomes refletidos literais.
        const semComentarios = codigo.replace(/"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\/\/[^\r\n]*|\/\*[\s\S]*?\*\//gu,
            trecho => trecho.startsWith('/') ? ' ' : trecho);
        const tokens = new Set(semComentarios.match(identificador) ?? []);
        for (const token of tokens) {
            for (const alvo of porNome.get(token) ?? []) ligar(nome, alvo, 'fonte');
        }
        // Um chamador pelo supertipo também pode alcançar a implementação modificada.
        if (!producao.has(nome)) continue;
        for (const clausula of semComentarios.matchAll(/\b(?:extends|implements)\s+([^{};\r\n]+)/gu)) {
            for (const token of clausula[1].match(identificador) ?? []) {
                for (const alvo of porNome.get(token) ?? []) {
                    if (producao.has(alvo)) ligar(alvo, nome, 'supertipo');
                }
            }
        }
    }
    return { reverso, compiladas };
}

function selecionar(sementes, reverso) {
    const fila = [...sementes].sort();
    const rotas = new Map(fila.map(classe => [classe, null]));
    for (const destino of fila) {
        const chegadas = reverso.get(destino) ?? new Map();
        for (const origem of [...chegadas.keys()].sort()) {
            if (rotas.has(origem)) continue;
            rotas.set(origem, { destino, evidencia: chegadas.get(origem) });
            fila.push(origem);
        }
    }
    return rotas;
}

function congelar(posicao, fonte) {
    const { sha, pai } = revisoes[posicao];
    const pasta = join(raiz, 'local', posicao);
    const saida = join(raiz, 'congelado', posicao);
    const ler = nome => readFileSync(join(pasta, nome));
    if (existsSync(saida)) throw new Error(`Seleção já registrada em ${saida}`);
    if (ler('compilacao-ok').toString().trim() !== sha) throw new Error('SHA da descoberta divergente');
    const inicio = process.hrtime.bigint();
    if (git(fonte, ['rev-parse', `${sha}^1`]).toString().trim() !== pai) {
        throw new Error('Primeiro pai divergente do protocolo');
    }
    const alteracoes = git(fonte, ['diff', '--no-renames', '--name-status', '-z', pai, sha])
        .toString().split('\0').filter(Boolean);
    const diff = git(fonte, ['diff', '--no-renames', '--full-index', '--no-ext-diff', '--no-color', '--no-textconv', pai, sha]);
    const arquivos = fontesJava(fonte, sha);
    const arquivoPorCaminho = new Map(arquivos.map(item => [item.caminho, item]));
    const tsv = ler('metodos.tsv');
    const testes = inventario(tsv.toString());
    const jdeps = ler('jdeps.txt');
    const { reverso, compiladas } = grafo(arquivos, jdeps.toString());

    const sementes = new Map();
    const fallback = [];
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
    if (![...classesTeste].some(classe => rotas.has(classe))) {
        fallback.push('Nenhum caminho encontrado entre os candidatos e as classes do diff');
    }
    const base = `evidencias/MUTACAO/t1/congelado/${posicao}`;
    const selecao = [['commit_sha', 'scenario', 'test_id', 'selected', 'selection_reason', 'source_ref']];
    const ranking = [['commit_sha', 'scenario', 'test_id', 'rank', 'score', 'source_ref']];
    const ids = [...testes.keys()].sort();
    for (const id of ids) {
        const { classe } = testes.get(id);
        const motivo = rotas.has(classe) ? 'dependency' : fallback.length ? 'fallback' : 'no_dependency';
        const incluir = motivo !== 'no_dependency';
        selecao.push([sha, 'T1', id, incluir, motivo, `${base}/decisoes.json#${classe}`]);
        if (incluir) ranking.push([sha, 'T1', id, ranking.length, '', `${base}/manifesto.json#ordem`]);
    }
    const custoNs = Number(process.hrtime.bigint() - inicio);
    mkdirSync(saida, { recursive: true });
    const escrever = (nome, conteudo) => writeFileSync(join(saida, nome), conteudo, { flag: 'wx' });
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
            [classe, rotas.has(classe) ? 'dependency' : fallback.length ? 'fallback' : 'no_dependency'])),
    }));
    const entradas = ['fonte.tar', 'pom-efetivo.xml', 'classpath.txt', 'classes.txt',
        'metodos.tsv', 'jdeps.txt', 'DescobertaT0.java', 'descobrir.sh', 'descoberta.log'];
    const saidas = ['diff.patch', 'selection.csv', 'rankings.csv', 'overhead.csv', 'decisoes.json'];
    escrever('manifesto.json', json({
        protocolo: 'af6bdfc', contrato: '0.1.0', seletor: versao, posicao: Number(posicao), sha, pai,
        ordem: 'test_id crescente (ordem ordinal, sensível a maiúsculas), todas as prioridades empatadas',
        inventario: 'JUnit Launcher.discover, filtros do pom efetivo, árvore Git e classpath da mesma revisão',
        imagem: 'sha256:6e15bf7fd834e6998883afacb56e4b6de6b180fff899bf3fb0474840f5ac93d6',
        candidatos: ids.length, selecionados: ranking.length - 1, fallback,
        custo: {
            ns: custoNs, ms: Math.round(custoNs / 1e6), node: process.version,
            plataforma: process.platform, arquitetura: process.arch,
            intervalo: 'do primeiro pai e diff à construção das linhas, com leitura do inventário e do jdeps locais',
            cache: 'um processo, sem cache do seletor, cache do sistema operacional não controlado',
        },
        entradas_sha256: Object.fromEntries(entradas.map(nome => [nome, sha256(ler(nome))])),
        saidas_sha256: Object.fromEntries(saidas.map(nome => [nome, sha256(readFileSync(join(saida, nome)))])),
    }));
    console.log(`${posicao}: ${ranking.length - 1}/${ids.length}, ${Math.round(custoNs / 1e6)} ms`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
    const [posicao, fonte] = process.argv.slice(2);
    if (!Object.hasOwn(revisoes, posicao) || !fonte) {
        throw new Error('Uso: node selecionar.mjs <posição> <clone Commons Lang>');
    }
    congelar(posicao, resolve(fonte).replaceAll('\\', '/'));
}

export { grafo, inventario, selecionar };
