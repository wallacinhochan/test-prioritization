# Análise provisória de RQ1 e RQ2

A unidade é o método de teste do Apache Commons Lang. Cada comparação usa a mesma revisão. T0 executa a suíte completa. T1 seleciona e usa a ordem de referência congelada. T2 (KNN) e T3 (Random Forest) reordenam a população comum de T1. A expansão direta é a variante experimental do DIRTS, sujeita à decisão do protocolo principal. [Critérios KAN-30](https://cin-team-test-prioritization.atlassian.net/browse/KAN-30) · [Inventário das fontes](../KAN-32/relatorio-provisorio.md)

## RQ1 — Custo, redução e detecção

O piloto 49–50 registrou 667,540 s para T0 e 467,370 s para DIRTS expandido, diferença de 200,170 s (30,0%) no intervalo daquele piloto. O custo expandido inclui inicialização de 118,754 s. Na posição 50, selecionaram-se 72 de 4.657 métodos com DIRTS puro e 416 com expansão. Falta uma medição física completa do DIRTS puro no trecho. No replay de mutantes de 26 e 50, T0 e expansão observaram os sete detectáveis, e DIRTS puro observou seis. O oitavo mutante, na posição 50, ficou indeterminado. A decisão local de levar a expansão ao congelamento baseou-se nesses dados. 670381c, veredito (`670381c:evidencias/KAN-18/veredito-operacional.md`)

Para responder à RQ1, gerar por SHA e cenário a população elegível de T0, o tamanho bruto e elegível da seleção, a redução relativa, o tempo total e sua modalidade (parede ou estimativa serial), os custos por fase, as falhas T0, as falhas retidas e as detectadas. Comparar T0→T1 para descrever o efeito operacional da seleção e T1→T2/T3 para examinar o ranking sobre as mesmas chaves e seu custo adicional. Usar pares comparáveis por métrica, declarar denominadores, exclusões, lacunas e quantos pares sustentam cada resumo. Treinamento fica por evento de atualização, com amortização somente se houver horizonte documentado. Com T0 completo e zero falhas, a proporção de detecção é indefinida. A resposta final permanece pendente.

## RQ2 — Feedback sob orçamento

Na revisão de validação 50, o pacote sintético auditou 416 chaves comuns. Os postos abaixo são os primeiros detectores observados, sujeitos a observações desconhecidas anteriores. Cada mutante tem quatro observações desconhecidas nos 416 métodos e onze nos 4.657 do T0. T0 oferece referência de detecção observada e carece de ordem global comparável. A detecção observada foi de três mutantes em cada cenário. Os dois ganhos de posto compartilham a mesma assinatura de primeiros postos. d2c0e7a, JSON por mutante (`d2c0e7a:evidencias/KAN-19/avaliacao-expansao50.json`)

| Mutante | T1 | T2 | T3 |
|---|---:|---:|---:|
| JavaVersion.get · 290 | 50 | 60 | 223 |
| SystemUtils.isOsMatch · 22 | 306 | 135 | 93 |
| SystemUtils.isOsNameMatch · 4 | indeterminado | indeterminado | indeterminado |
| SystemUtils.isOsVersionMatch · 47 | 306 | 135 | 93 |

Para responder à RQ2, usar 25%, 50% e 75% do último T0 histórico completo e comparável comprovadamente publicado antes do corte, com piso em ms e a mesma referência para os quatro cenários. Debitar preparo, seleção, features e inferência conforme aplicável. Comparar, na interseção de SHAs calculáveis para cada limite, a contagem e proporção de métodos falhos do T0 atual concluídos até o corte, o tempo até a primeira falha observada e a curva cumulativa. Preservar zero, ausência de falhas no oráculo, falha ainda não observada e corte indisponível como estados distintos. Expor a retenção de falhas ao lado do APFDc complementar, condicionado à população compartilhada. A resposta final permanece pendente. Regra KAN-24 (`8e91fa5:evidencias/KAN-24/README.md`)

## Tabelas e figuras a produzir

| Saída | Dados e verificação |
|---|---|
| Disponibilidade por SHA, cenário e budget | Conciliar o manifesto KAN-29 com o recorte aprovado. Mostrar elegíveis, avaliáveis, interseções e motivos. |
| Tabela pareada e distribuição de diferenças para RQ1 | Derivar redução, tempo e retenção dos CSVs e das métricas. Identificar modalidade de tempo e mostrar overhead por fase. |
| Tabela por budget e curvas em degraus para RQ2 | Recalcular limites e prefixos a partir da tentativa histórica e dos eventos. Mostrar denominador, cobertura e tempos de conclusão. |
| APFDc e falhas excluídas | Conferir população e vetor de custos idênticos para T1–T3. Exibir falhas retidas e excluídas com a pontuação. |

Gerar saídas principais para os commits consecutivos elegíveis. Publicar em painel próprio a análise complementar de falhas, com a origem dos rótulos e o critério de inclusão. A revisão 50 e as fixtures servem para demonstrar componentes e não fornecem cobertura de execução, tempo oficial, disponibilidade histórica ou regressões naturais para o recorte principal.
