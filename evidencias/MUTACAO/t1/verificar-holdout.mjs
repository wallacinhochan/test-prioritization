import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const repo = fileURLToPath(new URL('../../../', import.meta.url));
const raiz = 'evidencias/MUTACAO';
const modeloCommit = 'cbb462b79df5de284678ce0ac7c06f20e26d12c1';
const liberacaoCommit = '6e97157d56bdfacb9533944974463ee83306f39c';
const replayCommit = 'f4a9da2';
const modeloRef = `${raiz}/modelos/congelamento.json`;
const resumoRef = `${raiz}/mutantes/pos-96/resumo.json`;
const [t1Ref, resumoLocal] = process.argv.slice(2);

const git = (...args) => execFileSync('git', ['-C', repo, ...args], { maxBuffer: 16 * 1024 * 1024 });
const blob = (commit, caminho) => git('show', `${commit}:${caminho}`);
const digest = bytes => createHash('sha256').update(bytes).digest('hex');

git('merge-base', '--is-ancestor', modeloCommit, liberacaoCommit);
git('merge-base', '--is-ancestor', liberacaoCommit, replayCommit);
const resumoBytes = blob(replayCommit, resumoRef);
if (!readFileSync(resumoLocal).equals(resumoBytes)) {
    throw new Error('O resumo local da posição 96 diverge do replay publicado.');
}
const resumo = JSON.parse(resumoBytes);
const vinculo = resumo.congelamento_modelo;
const registro = JSON.parse(readFileSync(resolve(repo, raiz, 'mutantes/local/96/congelamento.json')));
const modeloBytes = blob(modeloCommit, modeloRef);
const sha256 = digest(modeloBytes);
const liberacao = blob(liberacaoCommit, `${raiz}/RELATORIO.md`).toString();
const esperado = {
    commit: modeloCommit, referencia: modeloRef, sha256, liberacao: `RELATORIO.md@${liberacaoCommit}`,
};
if (Object.entries(esperado).some(([chave, valor]) => vinculo?.[chave] !== valor || registro[chave] !== valor) ||
    !liberacao.includes('## Liberação do teste final') || !liberacao.includes(modeloCommit) || !liberacao.includes(sha256)) {
    throw new Error('Vínculo entre publicação, congelamento dos modelos e liberação oficial divergente.');
}

const modelo = JSON.parse(modeloBytes);
const commitT1 = git('rev-parse', '--verify', `${t1Ref}^{commit}`).toString().trim();
const entrada = modelo.entradas_t1['96'];
if (modelo.t1_commit !== commitT1 || entrada.sha !== resumo.sha) {
    throw new Error('O modelo congelado usa outra revisão ou seleção T1.');
}
for (const [nome, hash] of Object.entries({ 'manifesto.json': entrada.manifesto_sha256, ...entrada.arquivos })) {
    if (digest(blob(commitT1, `${raiz}/t1/congelado/96/${nome}`)) !== hash) {
        throw new Error(`Arquivo T1 divergente do congelamento dos modelos: ${nome}`);
    }
}
