import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const raiz = fileURLToPath(new URL('.', import.meta.url));
const repo = resolve(raiz, '../../..');
const revisoes = JSON.parse(readFileSync(resolve(raiz, 'revisoes.json'), 'utf8'));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const estados = new Set(['induced_failure', 'no_induced_failure', 'unknown']);

function congeladas(repo, versao) {
    const artefato = caminho => execFileSync('git', [
        '-C', repo, 'show', `${versao}:evidencias/MUTACAO/t1/${caminho}`,
    ], { maxBuffer: 16 * 1024 * 1024 });
    const conjuntos = new Map();
    for (const [posicao, { sha, pai }] of Object.entries(revisoes)) {
        const dir = `congelado/${posicao}`;
        const manifesto = JSON.parse(artefato(`${dir}/manifesto.json`));
        if (manifesto.sha !== sha || manifesto.pai !== pai || manifesto.seletor !== '1.0.0') {
            throw new Error(`Manifesto incompatível na posição ${posicao}`);
        }
        const arquivos = new Map();
        for (const nome of ['selection.csv', 'rankings.csv', 'overhead.csv', 'decisoes.json', 'diff.patch']) {
            const bytes = artefato(`${dir}/${nome}`);
            if (hash(bytes) !== manifesto.saidas_sha256[nome]) throw new Error(`Hash divergente: ${dir}/${nome}`);
            arquivos.set(nome, bytes.toString());
        }
        const t0 = new Set();
        const t1 = new Set();
        for (const linha of arquivos.get('selection.csv').trimEnd().split('\n').slice(1)) {
            const campos = linha.match(/"(?:[^"]|"")*"/g)?.map(campo => campo.slice(1, -1).replaceAll('""', '"'));
            if (!campos || campos.length !== 6 || campos[0] !== sha || campos[1] !== 'T1' ||
                !['true', 'false'].includes(campos[3]) || t0.has(campos[2])) {
                throw new Error(`CSV congelado inválido na posição ${posicao}`);
            }
            t0.add(campos[2]);
            if (campos[3] === 'true') t1.add(campos[2]);
        }
        if (!t0.size || t0.size !== manifesto.candidatos || t1.size !== manifesto.selecionados) {
            throw new Error(`Contagens do manifesto divergentes na posição ${posicao}`);
        }
        conjuntos.set(sha, { posicao: Number(posicao), t0, t1, custo: manifesto.custo });
    }
    return conjuntos;
}

function detectar(escopo, observacoes) {
    let desconhecido = false;
    for (const id of escopo) {
        const estado = observacoes.get(id);
        if (estado === 'induced_failure') return 'detected';
        if (estado !== 'no_induced_failure') desconhecido = true;
    }
    return desconhecido ? 'unknown' : 'not_detected';
}

function avaliar(conjuntos, matriz) {
    if (matriz.schema_version !== '1.0.0' || !Array.isArray(matriz.mutants) ||
        !Array.isArray(matriz.observations)) throw new Error('Esquema de matriz incompatível');
    const porSha = new Map([...conjuntos.keys()].map(sha => [sha, new Map()]));
    for (const { commit_sha, mutation_id, source_ref } of matriz.mutants) {
        const variantes = porSha.get(commit_sha);
        if (!variantes || typeof mutation_id !== 'string' || !mutation_id || !source_ref ||
            variantes.has(mutation_id)) throw new Error('Mutante inválido ou duplicado');
        variantes.set(mutation_id, { observacoes: new Map(), source_ref });
    }
    for (const { commit_sha, mutation_id, test_id, label, source_ref } of matriz.observations) {
        const variante = porSha.get(commit_sha)?.get(mutation_id);
        if (!variante || !conjuntos.get(commit_sha).t0.has(test_id) ||
            !estados.has(label) || !source_ref || variante.observacoes.has(test_id)) {
            throw new Error(`Observação inválida, fora do inventário ou duplicada: ${commit_sha} ${mutation_id} ${test_id}`);
        }
        variante.observacoes.set(test_id, label);
    }

    const revisoes = [];
    const totais = { mutantes: 0, comparaveis: 0, detectados_t0: 0, preservados: 0, perdidos: 0, t1_desconhecido_entre_detectados_t0: 0 };
    for (const [sha, { posicao, t0, t1, custo }] of conjuntos) {
        const comparacao = [];
        for (const [mutation_id, { observacoes, source_ref }] of porSha.get(sha)) {
            const status_t0 = detectar(t0, observacoes);
            const status_t1 = detectar(t1, observacoes);
            comparacao.push({
                mutation_id, source_ref, status_t0, status_t1,
                comparavel: status_t0 !== 'unknown' && status_t1 !== 'unknown',
            });
        }
        comparacao.sort((a, b) => a.mutation_id < b.mutation_id ? -1 : a.mutation_id === b.mutation_id ? 0 : 1);
        const detectados = comparacao.filter(row => row.status_t0 === 'detected');
        const resumo = {
            mutantes: comparacao.length,
            comparaveis: comparacao.filter(row => row.comparavel).length,
            detectados_t0: detectados.length,
            preservados: detectados.filter(row => row.status_t1 === 'detected').length,
            perdidos: detectados.filter(row => row.status_t1 === 'not_detected').length,
            t1_desconhecido_entre_detectados_t0: detectados.filter(row => row.status_t1 === 'unknown').length,
        };
        for (const chave of Object.keys(totais)) totais[chave] += resumo[chave];
        revisoes.push({
            posicao, commit_sha: sha, metodos_t0: t0.size, metodos_t1: t1.size,
            reducao_metodos: (t0.size - t1.size) / t0.size, custo_selecao_ms: custo.ms,
            ...resumo, ...taxas(resumo), comparacao,
        });
    }
    return { total: { ...totais, ...taxas(totais) }, revisoes };
}

function taxas({ preservados, perdidos, detectados_t0, t1_desconhecido_entre_detectados_t0 }) {
    const conhecidos = preservados + perdidos;
    return {
        preservacao_entre_comparaveis: conhecidos ? preservados / conhecidos : null,
        intervalo_entre_detectados_t0: detectados_t0 ? [
            preservados / detectados_t0,
            (preservados + t1_desconhecido_entre_detectados_t0) / detectados_t0,
        ] : null,
    };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
    const [versao, caminho] = process.argv.slice(2);
    if (!versao || !caminho) throw new Error('Uso: node avaliar.mjs <commit do congelamento completo> <matriz.json>');
    const commit = execFileSync('git', ['-C', repo, 'rev-parse', '--verify', `${versao}^{commit}`]).toString().trim();
    const conjuntos = congeladas(repo, commit);
    const bytes = readFileSync(caminho);
    const dados = avaliar(conjuntos, JSON.parse(bytes));
    console.log(JSON.stringify({
        tipo: 'projeção sobre observações T0',
        esquema: '1.0.0', congelamento: commit, matriz_sha256: hash(bytes), ...dados,
    }, null, 2));
}

export { avaliar, detectar, congeladas };
