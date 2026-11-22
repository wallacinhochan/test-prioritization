import assert from 'node:assert/strict';
import test from 'node:test';
import { avaliar, resumirEscopo } from './avaliar.mjs';
import { grafo, inventario, selecionar } from './selecionar.mjs';

test('segue bytecode transitivo por auxiliar e herança sem incluir classes irmãs de teste', () => {
    const fontes = [
        { nome: 'p.Alvo', producao: true, codigo: 'class Alvo {}' },
        { nome: 'p.Base', producao: false, codigo: 'class Base {}' },
        { nome: 'p.PrimeiroTest', producao: false, codigo: 'class PrimeiroTest extends Base {}' },
        { nome: 'p.SegundoTest', producao: false, codigo: 'class SegundoTest extends Base {}' },
    ];
    const jdeps = 'test-classes -> classes\n'
        + ' p.PrimeiroTest$Interna -> p.Auxiliar test-classes\n'
        + ' p.Auxiliar -> p.Alvo classes\n';
    const rotas = selecionar(['p.Alvo'], grafo(fontes, jdeps).reverso);
    assert.deepEqual([...rotas.keys()], ['p.Alvo', 'p.Auxiliar', 'p.PrimeiroTest']);
    assert.deepEqual(rotas.get('p.PrimeiroTest'), { destino: 'p.Auxiliar', evidencia: 'bytecode' });
});

test('usa classe aninhada, assinatura e capitalização do JUnit', () => {
    const cabecalho = 'raiz\tclasse\trotulo_classe\tmetodo\ttipos\ttipos_curtos\trotulo_metodo\ttipo_descritor\tdescritor';
    const linha = metodo => ['p.T', 'p.T$N', 'N', metodo, 'int,java.lang.String[]', 'int,String[]',
        'rótulo "interno"', 'test-template', '[engine:junit-jupiter]/[class:p.T]/[nested-class:N]']
        .map(campo => `"${campo.replaceAll('"', '""')}"`).join('\t');
    const metodos = inventario([cabecalho, linha('A'), linha('a'), ''].join('\n'));
    assert.deepEqual([...metodos.keys()], ['p.T$N#A(int,java.lang.String[])', 'p.T$N#a(int,java.lang.String[])']);
});

test('compara o mesmo mutante e mantém lacunas fora dos negativos', () => {
    const conjuntos = new Map([['sha', {
        posicao: 26, t0: new Set(['dentro', 'fora']), t1: new Set(['dentro']), custo: { ms: 4 },
    }]]);
    const row = (mutation_id, test_id, label) => ({ commit_sha: 'sha', mutation_id, test_id, label, source_ref: 'ref' });
    const positive = 'induced_failure';
    const negative = 'no_induced_failure';
    const matriz = {
        schema_version: '1.0.0',
        mutants: ['a', 'b', 'c', 'd'].map(mutation_id => ({ commit_sha: 'sha', mutation_id, source_ref: 'ref' })),
        observations: [
            row('a', 'dentro', positive),
            row('b', 'fora', positive), row('b', 'dentro', negative),
            row('c', 'fora', positive),
            row('d', 'fora', negative),
        ],
    };
    const { total, revisoes } = avaliar(conjuntos, matriz);
    assert.equal(total.comparaveis, 2);
    assert.equal(total.detectados_t0, 3);
    assert.equal(total.preservacao_entre_comparaveis, 0.5);
    assert.deepEqual(total.intervalo_entre_detectados_t0, [1 / 3, 2 / 3]);
    assert.equal(revisoes[0].reducao_metodos, 0.5);
    assert.deepEqual(resumirEscopo(new Set(['dentro']), new Map()), {
        status: 'unknown', induced_failure: 0, no_induced_failure: 0, unknown: 0, ausente: 1,
    });
    assert.equal(avaliar(conjuntos, { ...matriz, observations: [] }).total.preservacao_entre_comparaveis, null);
    assert.throws(() => avaliar(conjuntos, { ...matriz, observations: [matriz.observations[0], matriz.observations[0]] }));
});
