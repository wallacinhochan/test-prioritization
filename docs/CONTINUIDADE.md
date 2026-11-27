# Guia de continuidade

Este documento permite retomar o trabalho com acesso apenas ao repositório.

## Estado validado

- Base integrada antes da reorganização: `13792f4c3e1f5e3ed6976ddef86b0cd4a0cc66b8`.
- Objeto do estudo: Apache Commons Lang, tag `rel/commons-lang-3.20.0`.
- Âncora: `598dfc163b8b410fb3bb8794521206ec8dcec82a`.
- Recorte auditado: `evidencias/KAN-10/commits.csv`.
- Contrato tabular: `evidencias/KAN-15/README.md`, versão `0.1.0`.
- T1 formal e DIRTS: `evidencias/KAN-18/README.md`.
- T2/T3: KAN-19–22; simulação de orçamento: KAN-23–24; métricas: KAN-25–27.
- Relatórios provisórios: KAN-30–33; reconciliação do replay: KAN-34.

O Jira usa o projeto `KAN` em
`https://cin-team-test-prioritization.atlassian.net`. Não deduza o estado de um
ticket apenas pelo diretório: confira o README, o commit e o cartão antes de
coordenar novo trabalho. Não atualize Jira como efeito colateral de uma execução.

## Protocolo mínimo

1. Comece de checkout limpo e registre o commit deste repositório.
2. Resolva a revisão Commons Lang pelo SHA completo do recorte KAN-10.
3. Verifique ambiente, imagem e digests conforme `infra/commons-lang/README.md`.
4. Leia o manifesto da entrada e confira todos os hashes antes do processamento.
5. Preserve o corte temporal: treino e features devem existir antes do alvo.
6. Grave saídas numa pasta nova; nunca sobrescreva um congelamento.
7. Registre comando, versões, hashes, tempos, lacunas e razão de indisponibilidade.
8. Rode os testes locais e compare chaves, contagens e checksums.
9. Só então publique resumo no ticket correspondente.

## Entradas operacionais

- Ambiente Commons Lang: `infra/commons-lang/executar.ps1`.
- Métricas: `scripts/metricas.py`.
- Testes estruturais: `python -B -m unittest discover -s tests -v`.
- Testes de cada estágio: comandos listados no README da raiz.

## Bloqueios e limites

- Diretórios `local/` e `resultados/KAN-13|14` são ignorados; um clone pode não
  conter as entradas brutas citadas por manifests.
- O holdout e os congelamentos são somente leitura nesta continuidade.
- Não execute campanha experimental durante manutenção estrutural.
- Não mova worktrees, não troque remotes e não renomeie o repositório como parte
  de uma alteração de layout.
- Para qualquer dado ausente, registre indisponibilidade; não sintetize uma
  substituição silenciosa.

## Próxima extração possível

Os módulos KAN-19–24 são candidatos a `src/`, mas apenas após criar testes de
equivalência que executem os caminhos novo e histórico sobre fixtures pequenas e
compare bytes ou JSON normalizado. Até lá, são mantidos por compatibilidade e
proveniência.
