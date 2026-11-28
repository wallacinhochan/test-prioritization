# Análise provisória de RQ1 e RQ2

A unidade é o método de teste do Apache Commons Lang. Cada comparação usa a mesma revisão. T0 executa a suíte completa. T1 seleciona e usa a ordem de referência congelada. T2 (KNN) e T3 (Random Forest) reordenam a população comum de T1. A expansão direta é a variante experimental do DIRTS, sujeita à decisão do protocolo principal. [Critérios KAN-30](https://cin-team-test-prioritization.atlassian.net/browse/KAN-30) · [Inventário das fontes](../KAN-32/relatorio-provisorio.md)

## RQ1 — Custo, redução e detecção

O piloto 49–50 registrou 667,540 s para T0 e 467,370 s para DIRTS expandido, diferença de 200,170 s (30,0%) no intervalo daquele piloto. O custo expandido inclui inicialização de 118,754 s. Na posição 50, selecionaram-se 72 de 4.657 métodos com DIRTS puro e 416 com expansão. Falta uma medição física completa do DIRTS puro no trecho. No replay de mutantes de 26 e 50, T0 e expansão observaram os sete detectáveis, e DIRTS puro observou seis. O oitavo mutante, na posição 50, ficou indeterminado. A decisão local de levar a expansão ao congelamento baseou-se nesses dados. 670381c, veredito (`670381c:evidencias/KAN-18/veredito-operacional.md`)

### Consolidação da janela consecutiva 58–60 e validação física na posição 50 (KAN-28 / KAN-29)

Na primeira janela consecutiva consolidada com T0 instrumentado, seleção congelada (lote 04), rankings `T2`/`T3` (janela expansiva `janela-50`, sem balanceamento) e `startup` Modelo B ([`KAN-29/consolidado-58-60.json`](../KAN-29/consolidado-58-60.json)):

| Posição | T0 parede (ms) | T1/T2/T3 serial (ms) | Redução de métodos | Tempo testes T0 → T1–T3 (ms) | Seleção (ms) | Features + Inferência T2 / T3 (ms) | Falhas naturais T0 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **58** *(init frio)* | 288.780 | 632.044 / 632.045 / 632.050 | 98,39% (75/4.647) | 198.160 → 30.968 (−84,4%) | 520.303 | 1 / 6 | 0 |
| **59** *(incremental)* | 294.900 | 264.065 / 264.066 / 264.072 | 98,39% (75/4.647) | 200.263 → 31.427 (−84,3%) | 148.021 | 1 / 7 | 0 |
| **60** *(incremental)* | 300.950 | 273.653 / 273.655 / 273.660 | 94,81% (241/4.647) | 207.179 → 40.080 (−80,7%) | 151.683 | 2 / 7 | 0 |
| **50** *(técnica, ref. 49)* | 292.540 | 257.035 / 257.042 / 257.056 | 91,13% (412/4.646) | 200.786 → 96.701 (−51,8%) | 78.575 | 7 / 21 | 0 |

- **T0 → T1 (seleção):** a redução de métodos (`91–98%`) reduz drasticamente o tempo dos testes (`−52%` a `−84%`), mas o ganho líquido no tempo total depende criticamente do overhead de seleção DIRTS + expansão: quando paga inicialização fria (posição 58, `520,3 s`), `T1` é **+118,9% mais lento** que `T0`; em regime incremental (`59, 60, 50`), resulta em economia líquida estimada de **`9,1%` a `12,1%`** (e na execução física `T1 Surefire` da posição 50 na KAN-28, **`17,60%`** de economia líquida em parede com seleção incluída).
- **T1 → T2/T3 (ordenação):** o custo adicional de extração de features e inferência é de `1–2 ms` (`T2`) e `6–21 ms` (`T3`), representando `< 0,01%` do tempo total; o treinamento da `janela-50` (`3 ms` T2, `183 ms` T3, registrado separadamente na posição 58) também é desprezível.
- **Detecção natural e cobertura:** com **0 falhas naturais** nos 6 T0 instrumentados (`49, 50, 57, 58, 59, 60`) e **82 lacunas em T1 / 94 em T0**, a proporção de detecção natural segue indefinida e a resposta final à RQ1 permanece condicionada à ampliação do recorte.

Para responder à RQ1 no recorte completo, manter por SHA e cenário a população elegível de T0, o tamanho bruto e elegível da seleção, a redução relativa, o tempo total e sua modalidade (parede ou estimativa serial), os custos por fase, as falhas T0, as falhas retidas e as detectadas.

## RQ2 — Feedback sob orçamento

### Cortes 25%, 50% e 75% na janela consolidada (58–60 e validação técnica 50)

Aplicando os cortes de `25%`, `50%` e `75%` sobre o T0 imediatamente anterior no mesmo ambiente (`57→58`, `58→59`, `59→60`, `49→50`, com `startup` Modelo B):
- **25% (`72,2–73,7 s`):** todos os quatro cenários concluem **0 métodos** nas quatro revisões, porque o preparo em cache Maven frio (`80,8–84,6 s`) excede 25% de `T0`.
- **50% (`144,4–147,5 s`):** `T0` conclui **1.424 métodos** em todas as revisões; `T1`, `T2` e `T3` concluem **0 métodos** porque `preparo (~81–85 s) + seleção (78,6–520,3 s) > 147,5 s`.
- **75% (`216,6–221,2 s`):** `T0` conclui **4.224 a 4.266 métodos**. Nas posições **58, 59 e 60**, `T1–T3` ainda concluem **0 métodos** (`preparo + seleção ≥ 232,6 s > 221,2 s`). Na posição **50** (`selection = 78,6 s`), `T1` conclui **410**, `T2` **320** e `T3` **332** de 412 métodos (confrontado fisicamente na KAN-28 com `Δ = 0` em T1/T3 e `−24` conservador em T2).
- **APFDc natural:** indefinido (`sem_falhas_na_populacao`) nas quatro revisões por ausência de falhas naturais.

### Evidência auxiliar sintética (separada do oráculo natural T0)

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
