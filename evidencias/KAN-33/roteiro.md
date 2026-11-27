# Roteiro provisório da apresentação

O roteiro prepara a revisão com o grupo. As conclusões públicas dependem da análise principal reproduzível e da revisão dos participantes. [Critérios KAN-33](https://cin-team-test-prioritization.atlassian.net/browse/KAN-33)

| Slide | Fala e visual | Fonte ou condição |
|---|---|---|
| 1 · Problema e perguntas | Em CI, reduzir a suíte pode economizar tempo e excluir testes que detectam falhas. Apresentar RQ1 sobre custo, redução e retenção e RQ2 sobre feedback sob orçamento. | [Desenho](../KAN-32/relatorio-provisorio.md) |
| 2 · Quatro cenários | Mostrar T0 e o fluxo seleção T1 → ordem de referência, KNN T2 ou RF T3. Indicar população comum e custos de cada fase. | Contrato e fontes KAN-18–22 no [relatório](../KAN-32/relatorio-provisorio.md). |
| 3 · Cronologia e comparabilidade | Mostrar a decisão congelada, a tentativa T0 histórica publicada antes do corte e a tentativa oráculo do SHA atual. Indicar 25%, 50% e 75% e o papel da validação física. | Regra KAN-24 e KAN-23 no [relatório](../KAN-32/relatorio-provisorio.md). |
| 4 · Evidência auxiliar | Usar a tabela de postos da revisão 50 com legenda de mutantes sintéticos, postos observados e lacunas. Explicar que dois postos anteciparam e um atrasou em relação ao T1 e que o quarto mutante é indeterminado. | [Tabela auditada](../KAN-30/analise-provisoria.md). |
| 5 · RQ1 | Reservar quadro para diferenças pareadas de tempo e redução, overhead por fase e falhas retidas. Apresentar intervalo medido, tipo de tempo e cobertura. | Preencher após KAN-28/29 e resposta da KAN-30. |
| 6 · RQ2 | Reservar tabela de falhas detectadas por budget e curvas cumulativas. Mostrar primeira detecção, denominadores e interseção calculável. Usar APFDc apenas junto da retenção. | Preencher após KAN-28/29 e resposta da KAN-30. |
| 7 · Limitações e conclusão | Explicar projeto único, dependência entre commits, escassez de positivos, origem dos rótulos e limites da simulação. Encerrar com uma frase por RQ quando revisada. | [Ameaças à validade](../KAN-31/ameacas-validade.md). |

## Revisão pelo grupo

Compartilhar a revisão Git do roteiro e, quando integrados, o manifesto KAN-29, as tabelas, os gráficos e as respostas. Pedir aos participantes que confiram a distinção entre seleção e ordenação, origem dos rótulos, critérios de comparação, denominadores e correspondência de cada conclusão com sua figura. Registrar participantes, data, versão revisada, comentários, ajustes e aceite explícito no registro da revisão. A revisão permanece pendente.
