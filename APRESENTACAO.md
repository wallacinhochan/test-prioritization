# Seleção e priorização de testes no Apache Commons Lang

Resultados preliminares para apresentação · 23/11/2026

## Pergunta e desenho do estudo

Em integração contínua, executar a suíte inteira dá uma referência de execução e custo. A pesquisa investiga quanto se pode reduzir a execução e em que medida uma ordem diferente ajuda a encontrar falhas mais cedo, especialmente quando há pouco tempo.

- **RQ1** avalia custo, tempo e capacidade de detectar falhas.
- **RQ2** avalia detecção com orçamentos de 25%, 50% e 75% de um tempo de referência T0 anterior e comparável.

| Cenário | Como os testes são escolhidos e ordenados |
| --- | --- |
| **T0** | Suíte completa. Fornece os resultados de referência por método. |
| **T1** | Seleção por dependências estáticas, com retorno à suíte completa quando o impacto é incerto. |
| **T2** | KNN reordena os métodos selecionados pelo T1. |
| **T3** | Random Forest reordena o mesmo conjunto do T1. |

A unidade de coleta é o método de teste por revisão. Os rankings usam características disponíveis antes da execução. As mutações geram rótulos de treino para os modelos. A avaliação de regressões naturais usa o T0 como referência. [Objeto do estudo](evidencias/KAN-12/README.md) · [Contrato dos dados](evidencias/KAN-15/README.md) · [Regra de orçamento](evidencias/KAN-24/README.md)

## Resultados do estudo principal até aqui

**T0 · Suíte completa.** Cinco das 100 revisões candidatas tiveram execução completa. As **298.770 invocações** foram associadas a **23.280 registros de método por revisão**. Foram observadas **zero falhas ou erros**. O tempo de parede variou de **283,184 a 306,912 s** no ambiente de referência. [Coleta T0](evidencias/ENTREGA-3/README.md)

**T1 · Seleção por dependências.** Nos cinco pares com T0 completo, T1 selecionou **18.620 dos 23.280 métodos**, uma redução agregada de **20,02% na quantidade de métodos**.

| Posição | Métodos em T0 | Métodos selecionados em T1 | Métodos excluídos |
| ---: | ---: | ---: | ---: |
| 1 | 4.649 | 4.649 | 0 |
| 26 | 4.652 | 4.648 | 4 |
| 50 | 4.657 | 4.653 | 4 |
| 75 | 4.659 | 7 | 4.652 |
| 100 | 4.663 | 4.663 | 0 |
| **Total** | **23.280** | **18.620** | **4.660** |

A posição 75, cujo diff altera apenas uma classe de teste, respondeu por **4.652 das 4.660 exclusões**. O seletor levou **382 a 539 ms** nas seis revisões com seleção materializada, com inventário e dependências já preparados. O tempo físico da suíte selecionada e o custo total de T1 ainda estão sem medição comparável. [Seleção e verificação por revisão](evidencias/KAN-18/README.md)

**T2 e T3 · Ranking.** Os modelos foram ajustados com os mesmos **13.915 exemplos de treino com alvo sintético conhecido**, das posições 15, 26 e 42. Cada modelo reproduziu **9.323 escores e postos** nas posições 50, 75 e 100 e ordenou exatamente os mesmos métodos do T1 em cada fluxo. A inferência foi cronometrada separadamente. A extração de características ainda precisa de aferição para compor o custo total. [Dataset](evidencias/KAN-19/README.md) · [KNN](evidencias/KAN-20/README.md) · [Random Forest e conferência conjunta](evidencias/KAN-21/README.md)

## Evidência auxiliar do piloto de mutação

O piloto criou **20 variantes artificiais** com alterações no código de produção. A suíte completa detectou 18, e a projeção sobre a lista T1 exploratória preservou as 18 detecções. Duas variantes ficaram indeterminadas. Esse resultado se refere às variantes e às cinco revisões do piloto sintético. [Relatório de mutação](evidencias/MUTACAO/RELATORIO.md)

Na revisão sintética reservada, houve três detecções observadas. A tabela mostra o posto do primeiro teste que detectou cada variante.

| Variante | Ordem T1 | KNN | Random Forest |
| --- | ---: | ---: | ---: |
| 1 | 3.685 | 2 | 14 |
| 2 | 3.685 | 2 | 14 |
| 3 | Indeterminado | Indeterminado | Indeterminado |
| 4 | 3.705 | 28 | 25 |

Esses postos verificam o funcionamento do ranking com falhas induzidas. A amostra principal ainda tem zero falhas naturais observadas, então a antecipação de regressões reais permanece sem estimativa. [Evidência por variante](evidencias/MUTACAO/modelos/teste-final.json)

## Roteiro de fala em cinco slides

| Slide | O que mostrar | Sugestão de fala |
| --- | --- | --- |
| **1. Problema** | Pergunta sobre custo e detecção em CI | “Queremos saber quando vale a pena executar toda a suíte, quando podemos reduzir a lista e quando a ordem dos testes faz diferença.” |
| **2. Método** | Fluxo T0, T1 e ramificação T2/T3 | “Usamos o Commons Lang e medimos por método. T0 dá a referência. T1 escolhe uma lista por dependências. KNN e Random Forest recebem a mesma lista e mudam sua ordem.” |
| **3. Resultado da seleção** | Tabela por revisão, com a posição 75 destacada | “Nos cinco pares observados, a lista passou de 23.280 para 18.620 métodos. Quase toda a redução veio de uma revisão que modificou uma classe de teste. A economia de tempo físico ainda precisa ser medida.” |
| **4. Dataset e ranking** | 13.915 exemplos de treino e 9.323 postos reproduzidos por modelo | “Usamos alterações artificiais para gerar exemplos rotulados de treino. Verificamos que os dois modelos conseguem gerar rankings reproduzíveis para a mesma lista do T1.” |
| **5. Conclusão e próximos passos** | Cobertura atual, limite de falhas naturais e sequência KAN-22 → KAN-23 | “O fluxo de coleta, seleção e ranking funciona no recorte verificado. Como as cinco suítes completas não apresentaram falhas, ainda não podemos estimar quanto os rankings antecipam regressões reais. O próximo passo é atualizar os modelos em janela expansiva, integrar a simulação e aferir os custos que faltam.” |

Se houver tempo, use a tabela sintética como slide de apoio. Explique que os valores são **postos na fila** e que duas das três detecções observadas ocorreram em variantes do mesmo método de produção. [Atualização dos modelos](https://cin-team-test-prioritization.atlassian.net/browse/KAN-22) · [Simulação T0–T3](https://cin-team-test-prioritization.atlassian.net/browse/KAN-23)
