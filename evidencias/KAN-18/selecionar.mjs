import { inventario } from '../MUTACAO/t1/selecionar.mjs';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const raiz = fileURLToPath(new URL('.', import.meta.url));
const versao = '2.0.0';
const revisoes = readFileSync(new URL('../KAN-10/commits.csv', import.meta.url), 'utf8');
const java = /^src\/(main|test)\/java\/(.+)\.java$/u;
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const csv = linhas => linhas.map(linha => linha.map(campo =>
    `"${String(campo).replaceAll('"', '""')}"`).join(',')).join('\n') + '\n';

function git(fonte, args) {
    const cmd = spawnSync('git', ['-c', `safe.directory=${fonte}`, '-C', fonte, ...args], {
        maxBuffer: 64 * 1024 * 1024,
    });
    if (cmd.error || cmd.status !== 0) {
        throw new Error(`git ${args[0]}: ${cmd.error ?? cmd.stderr.toString()}`);
    }
    return cmd.stdout;
}

function exclusoes(ler, fase) {
    const linhas = ler(fase + '.excludes').toString().trimEnd().split(/\r?\n/u);
    if (linhas.shift() !== '# DIRTS excluded' || linhas.shift() !== '**/*$*' ||
        linhas.some(linha => !/^[\w$]+(?:\/[\w$]+)+\.java$/u.test(linha))) {
        throw new Error('Lista de exclusões inválida: ' + fase);
    }
    return new Set(linhas.map(linha => linha.slice(0, -5).replaceAll('/', '.')));
}

function aplicarDirts(ler, classesTeste, testesAlterados, adicionados) {
    if (ler('dirts.status').toString().trim() !== 'ok') throw new Error('Execução DIRTS indisponível');
    const controle = exclusoes(ler, 'controle');
    if ([...classesTeste].some(classe => !adicionados.has(classe) && !controle.has(classe))) {
        throw new Error('O controle DIRTS não excluiu todos os testes do pai');
    }
    const excluidas = exclusoes(ler, 'alvo');
    const selecionadas = new Set([...classesTeste].filter(classe => !excluidas.has(classe)));
    const log = ler('alvo.log').toString().replaceAll('\r\n', '\n');
    const incluidas = log.match(/^DIRTS included: \[([\s\S]*?)\]\n\[INFO\] -/mu);
    const recalculo = log.match(/^\[INFO\] Recalculating primary dependencies of:\n([\s\S]*?)^\[TIME\] Cropping dependency graph/mu);
    if (!incluidas || !recalculo) throw new Error('Diagnóstico DIRTS incompleto');
    const registradas = new Set([...incluidas[1].matchAll(/^([\w$.]+) <-- /gmu)].map(item => item[1]));
    if ([...classesTeste].some(classe => selecionadas.has(classe) !== registradas.has(classe))) {
        throw new Error('Exclusões e inclusões DIRTS divergentes');
    }
    if (!selecionadas.size && recalculo[1].trim()) throw new Error('DIRTS detectou alterações sem selecionar testes');
    if (recalculo[1].trim() &&
        [...testesAlterados].some(classe => !selecionadas.has(classe))) {
        throw new Error('Classe de teste alterada sem seleção DIRTS');
    }
    return selecionadas;
}

function congelar(posicao, fonte) {
    const registro = revisoes.split(/\r?\n/).find(linha => linha.startsWith(`"${posicao}",`));
    const revisao = /^"\d+","([0-9a-f]{40})","([0-9a-f]{40})",/.exec(registro ?? '');
    if (!revisao) throw new Error(`Posição ausente ou inválida na KAN-10: ${posicao}`);
    const [, sha, pai] = revisao;
    const pasta = join(raiz, 'local', 'dirts', 'entradas', sha);
    const saida = join(raiz, 'local', 'dirts', 'selecao', sha);
    const ler = nome => readFileSync(join(pasta, nome));

    if (existsSync(saida)) throw new Error(`Seleção já publicada em ${saida}`);
    if (ler('compilacao-ok').toString().trim() !== sha) throw new Error('SHA da descoberta divergente');
    const inicio = process.hrtime.bigint();
    if (git(fonte, ['rev-parse', `${sha}^1`]).toString().trim() !== pai) {
        throw new Error('Primeiro pai divergente do protocolo');
    }
    const alteracoes = git(fonte, ['diff', '--no-renames', '--no-ext-diff', '--name-status', '-z', pai, sha])
        .toString().split('\0').filter(Boolean);
    const diff = git(fonte, ['diff', '--no-renames', '--full-index', '--no-ext-diff', '--no-color', '--no-textconv', pai, sha]);
    const testes = inventario(ler('metodos.tsv').toString());
    const classesTeste = new Set([...testes.values()].map(teste => teste.classe));
    const compiladas = new Set(ler('jdeps.txt').toString().split(/\r?\n/u)
        .map(linha => /^\s+(\S+)\s+->/u.exec(linha)?.[1]).filter(Boolean));
    const fallback = [];
    const sementes = new Map();
    const testesAlterados = new Set();
    const adicionados = new Set();
    for (let i = 0; i < alteracoes.length; i += 2) {
        const [status, caminho] = alteracoes.slice(i, i + 2);
        if (status === 'M' && caminho === 'src/changes/changes.xml') continue;
        const tipo = java.exec(caminho);
        const classe = tipo?.[2].replaceAll('/', '.');
        if (!classe || !['A', 'M'].includes(status) || !compiladas.has(classe)) {
            fallback.push(`Alteração sem mapeamento Java compilado: ${status} ${caminho}`);
            continue;
        }
        sementes.set(classe, caminho);
        if (tipo[1] === 'test' && classesTeste.has(classe)) {
            testesAlterados.add(classe);
            if (status === 'A') adicionados.add(classe);
        }
    }
    if (!sementes.size) fallback.push('Diff sem classe-alvo Java mapeada');
    if ([...classesTeste].some(classe => !compiladas.has(classe))) {
        fallback.push('Classe de execução sem mapeamento no bytecode');
    }
    if (/^\s+\S+\s+->\s+org\.apache\.commons\.lang3\.[^\s]+\s+not found\s*$/mu.test(ler('jdeps.txt').toString())) {
        fallback.push('Referência interna não resolvida pelo jdeps');
    }
    let selecionadas = new Set();
    if (!fallback.length) {
        try {
            selecionadas = aplicarDirts(ler, classesTeste, testesAlterados, adicionados);
        } catch (erro) {
            fallback.push(erro.message);
        }
    }
    const motivoClasse = classe => fallback.length ? 'fallback' : selecionadas.has(classe) ? 'dependency' : 'no_dependency';
    const base = `evidencias/KAN-18/local/dirts/selecao/${sha}`;
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
    const textoTempo = ler('dirts.ns').toString().trim();
    const dirtsNs = Number(textoTempo);
    if (!/^\d+$/u.test(textoTempo) || !Number.isSafeInteger(dirtsNs)) throw new Error('Tempo DIRTS inválido');
    const custoNs = Number(process.hrtime.bigint() - inicio) + dirtsNs;
    mkdirSync(join(raiz, 'local', 'dirts', 'selecao'), { recursive: true });
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
            dirts_status: ler('dirts.status').toString().trim(),
            classes_de_execucao: Object.fromEntries([...classesTeste].sort().map(classe =>
                [classe, motivoClasse(classe)])),
        }));
        const entradas = ['fonte.tar', 'pom-efetivo.xml', 'classpath.txt', 'classes.txt',
            'metodos.tsv', 'jdeps.txt', 'DescobertaT0.java', 'descobrir.sh', 'descoberta.log',
            'dirts.sh', 'dirts.status', 'dirts.ns', 'imagem.txt', 'compilacao-ok'];
        for (const nome of ['pai.tar', 'alteracoes.tar', 'pai.log', 'controle.log', 'alvo.log',
            'pai.excludes', 'controle.excludes', 'alvo.excludes']) {
            if (existsSync(join(pasta, nome))) entradas.push(nome);
        }
        const saidas = ['diff.patch', 'selection.csv', 'rankings.csv', 'overhead.csv', 'decisoes.json'];
        escrever('manifesto.json', json({
            protocolo: 'KAN-18', contrato: '0.1.0', seletor: versao, posicao: Number(posicao), sha, pai,
            ordem: 'test_id crescente (ordem ordinal, sensível a maiúsculas), todas as prioridades empatadas',
            inventario: 'JUnit Launcher.discover sobre classes raiz *Test do classpath da mesma revisão',
            imagem: ler('imagem.txt').toString().trim(),
            ferramenta: { nome: 'DIRTS', versao: '1.0', commit: '62efcec2f909f93fffdd4ae1da24b0aee1071749' },
            candidatos: ids.length, selecionados: ranking.length - 1, fallback,
            custo: {
                ns: custoNs, ms: Math.round(custoNs / 1e6), node: process.version,
                plataforma: process.platform, arquitetura: process.arch,
                intervalo: 'preparo do estado DIRTS no pai, controle, seleção do alvo e construção dos CSVs no host',
                dirts_ns: dirtsNs,
                cache: 'estado DIRTS novo por par, cache Maven semeado pela imagem',
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
