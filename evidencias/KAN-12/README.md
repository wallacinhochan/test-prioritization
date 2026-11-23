# KAN-12 — Definição do objeto de estudo

## Decisão de 22/11/2026

Wallace confirmou o **Apache Commons Lang** como objeto do estudo principal. A pesquisa mantém o desenho de comparação T0–T3 para seleção e priorização de testes de regressão. A decisão se apoia no ambiente reproduzível, na coleta por método e nas cinco suítes T0 verificadas na Entrega 3. [Entrega 3](../ENTREGA-3/README.md)

As mutações têm a função de gerar exemplos rotulados para treinar KNN e Random Forest. A validação e o teste em dados sintéticos documentados no piloto verificaram o procedimento de treinamento e ranking. As contagens sintéticas permanecem separadas das falhas naturais na avaliação do estudo principal. A escassez de falhas naturais observadas limita as análises que dependem de detecção de regressões. [Piloto de mutação](../MUTACAO/RELATORIO.md)

## Histórico do parecer exploratório

**Parecer parcial de 20/11/2026.** Wallace aprovou o Apache Commons Lang para o **piloto exploratório**, com os mesmos 100 SHAs candidatos da KAN-10 e lote preliminar nas posições **1, 26, 50, 75 e 100**. A recomendação é executar esse piloto e reavaliar o objeto do estudo principal depois da coleta histórica. Duas suítes completas em UTC comprovam a execução de T0 nos extremos do recorte. Os dados disponíveis ainda são insuficientes para avaliar KNN ou Random Forest com falhas naturais. A escolha definitiva depende das evidências abaixo e da aprovação de Wallace. [KAN-12](https://cin-team-test-prioritization.atlassian.net/browse/KAN-12) · [Decisão do piloto na KAN-11](https://cin-team-test-prioritization.atlassian.net/browse/KAN-11?focusedCommentId=10005)

## Recorte e evidência observada

Os 100 SHAs seguem o primeiro pai, do mais antigo à âncora `rel/commons-lang-3.20.0`. Todos passaram na triagem estática. O CSV registra a posição 100 como elegível e as outras 99 como pendentes na data da auditoria. A execução posterior da posição 1 pela KAN-14 acrescenta evidência operacional para esse SHA. O CSV original é a referência de posições e tem SHA-256 `ed7545c232b5df2271d48f59ef4c733c798de1ab54399e5f61e6e3f07b3a60ed`. Preservar SHA, posição e motivo para revisões inviáveis ou pendentes evita recompor a amostra com base em resultados favoráveis. [KAN-10, critérios e reprodução](../KAN-10/README.md) · [CSV dos 100 SHAs](../KAN-10/commits.csv)

| Posição | SHA | Resultado no ambiente da KAN-13 |
| ---: | --- | --- |
| 1 | `921c1b4e09ed7b6900ad7243cffb33b373980cc5` | KAN-14: 227 XML, 59.449 casos, 59.436 aprovações, 13 ignorados, 0 falhas, 0 erros, 291,482 s de ponta a ponta. [Execução](../KAN-14/README.md) |
| 26 | `04cc0339d6510ffdcb47db4676c34b40ecff6b28` | Tentativa iniciada pela KAN-14, com resultado final pendente no corte da análise. Rodada `20261120T163308947Z-2051ac8c262c4c21a821d8799a35203a`. |
| 50 | `f24c027ff83b90beab2ec28696721200abb4f9e9` | Suíte completa pendente. |
| 75 | `bfcaa941b0849956972517c8559c0827c8fe5386` | Suíte completa pendente. |
| 100 | `598dfc163b8b410fb3bb8794521206ec8dcec82a` | KAN-13: 228 XML, 59.960 casos, 59.946 aprovações, 14 ignorados, 0 falhas, 0 erros, 306,912 s de ponta a ponta. [Execução](../KAN-13/pilotos/ancora/README.md) |

As duas rodadas usaram Linux/amd64, Temurin 21.0.11, Maven 3.9.11, UTC e cache Maven frio. Os `ambiente.json` registram os SHAs exatos e o mesmo ID local de imagem `sha256:6e15bf7fd834e6998883afacb56e4b6de6b180fff899bf3fb0474840f5ac93d6`. A KAN-9 validou a âncora no Windows com OpenJDK da Microsoft e reproduziu a contagem em UTC. Suas durações pertencem a outro ambiente e política de cache. [Ambiente da KAN-13](../KAN-13/README.md) · [Validação da KAN-9](../KAN-9/README.md)

Foram recontados os elementos `/testsuite/testcase` e os marcadores `skipped`, `failure`, `error`, `rerunFailure`, `rerunError`, `flakyFailure` e `flakyError` nos XML originais das duas rodadas. Nenhum marcador de rerun ou flakiness apareceu nessas saídas. Os totais representam invocações do Surefire. Para reproduzir, use o executor indicado nos relatórios, leia `ambiente.json` e `maven.log` da tentativa e conte os elementos em `surefire/TEST-*.xml`. Os XML brutos estão em `resultados/`, ignorado pelo Git. Os hashes abaixo identificam os arquivos locais conferidos.

| Origem e ID da rodada sob `resultados/<KAN>/<sha>/` | SHA-256 de `ambiente.json` | SHA-256 de `maven.log` |
| --- | --- | --- |
| KAN-14 · `20261120T160458376Z-baac2d8746094e99ae971f9c73160837` | `db07233062687f913c613ebf1f8f42968558c8db383755052b2536d30b707914` | `b973ff7642fbbed38712e08446cfc8fdd9f7f143e892bdd4a3697fa0279b154` |
| KAN-13 · `20261120T150800719Z-a24ed681244a469e80a93be9467c11b1` | `1b5d9ac1d9f75eed07f5d7511aaf92759cef5296dcb6dd93b74aab17aeba99b0` | `8555fd56e408e3b02d1195ffdd4c9e8a1f71faa4bdbe2c78fe83d4c23c80b6e4` |

A KAN-11 tinha evidência por método em dois SHAs, com suíte completa só na âncora. A KAN-14 elevou a cobertura de suítes completas para **2/100 no recorte e 2/5 no lote**, contando a âncora da KAN-13 como evidência de execução. A cobertura continua concentrada nos mesmos dois SHAs e o aceite da tentativa de referência, a agregação e a cobertura de associação por método ficam a verificar na KAN-16. As posições 2 a 99 seguem sem suíte completa documentada. [Auditoria KAN-11](../KAN-11/README.md) · [Coleta KAN-16](https://cin-team-test-prioritization.atlassian.net/browse/KAN-16)

## Suficiência por cenário

| Cenário | Avaliação para a Entrega 3 | Evidência necessária para avançar |
| --- | --- | --- |
| **T0 · suíte completa** | O executor por SHA, o ambiente e a coleta de XML foram demonstrados nos extremos. Há resultado agregado e tempo de parede das rodadas, além de exemplos de associação a métodos. | Completar o lote e publicar `t0_runs` e `t0_results` por tentativa de referência e método conforme o contrato. Informar impedimentos, cobertura de identidade, duração e ordem. |
| **T1 · seleção por dependências** | Há recorte, primeiro pai para o diff, ambiente e regra aprovada de identidade por método. Isso sustenta preparar o inventário pré-execução e desenhar uma seleção exploratória. Ainda falta um conjunto T1 rastreável nos SHAs do lote. | Fixar inventário, seleção e ranking antes de consultar o T0 do SHA alvo. Considerar dependências transitivas, alterações de build, recursos e configuração, com fallback conservador e motivo registrado. Medir overhead e confrontar seleção e T0 por `(commit_sha, test_id)` sob o protocolo aplicável. |
| **T2 / T3 · KNN / Random Forest** | A evidência disponível carece de positivos naturais confirmados e de cobertura intermediária para avaliação temporal supervisionada. | Usar o mesmo conjunto T1 e as mesmas features para os dois modelos. Demonstrar cobertura temporal, origem dos rótulos e episódios independentes no treino e na avaliação, com o T0 da própria revisão reservado ao oráculo. |

[Identidade e agregação KAN-17](../KAN-17/README.md) · [Contrato KAN-15](../KAN-15/README.md), commit `1faf725` · [T1](https://cin-team-test-prioritization.atlassian.net/browse/KAN-18) · [T2](https://cin-team-test-prioritization.atlassian.net/browse/KAN-20) · [T3](https://cin-team-test-prioritization.atlassian.net/browse/KAN-21)

Quando houver T0 e T1 comparáveis, relatar redução da seleção, custos e overhead nos SHAs com junção verificável, declarando a cobertura em relação ao lote. Calcular medidas dependentes de falhas apenas onde o oráculo tiver falhas elegíveis. Para uma revisão sem falhas observadas, detecção e antecipação de falhas ficam sem valor aplicável. Comparações dependentes da ordem de T0 exigem evidência da sequência global. O tempo de parede do build e da suíte, que inclui downloads em cache frio, tem escopo diferente da duração agregada das invocações de um método. [Regras KAN-17](../KAN-17/README.md#agregação-para-t0)

## Falhas naturais e alternativa jsoup

A evidência confirma **zero episódios naturais observados por teste e SHA** e **um episódio ambiental** no fuso `America/Sao_Paulo`. As duas suítes em UTC tiveram zero falhas ou erros e as lacunas deixam a frequência histórica desconhecida. A KAN-11 encontrou uma regressão de produto em LANG-1792, mas o teste de regressão foi introduzido na correção e falta a observação da falha na suíte original anterior. LANG-1791 segue indeterminado. As consultas públicas da KAN-11 aos 100 SHAs retornaram zero workflows, check runs e status individuais visíveis, com as limitações de retenção e correspondência por SHA. O catálogo Defects4J v3.0.1 não tem pares buggy/fixed com SHA no recorte de Commons Lang. [KAN-11, cobertura e classificação](../KAN-11/README.md) · [Diagnóstico de fuso](../KAN-9/README.md#diagnóstico-do-fuso)

| Critério | Commons Lang | jsoup |
| --- | --- | --- |
| Build e T0 | Execução local comprovada em dois SHAs no ambiente aprovado. [KAN-13](../KAN-13/README.md) · [KAN-14](../KAN-14/README.md) | O POM da release `jsoup-1.21.2` declara Maven, JUnit Jupiter e Surefire. É evidência documental de compatibilidade potencial. Executabilidade, saída por método e comparabilidade no ambiente do piloto permanecem sem validação nesta análise. [Release oficial](https://github.com/jhy/jsoup/releases/tag/jsoup-1.21.2) · [POM da release](https://raw.githubusercontent.com/jhy/jsoup/jsoup-1.21.2/pom.xml) |
| Sequência histórica e T1 | 100 SHAs auditados, primeiro pai definido e exemplos de identidade por método. [KAN-10](../KAN-10/README.md) · [KAN-17](../KAN-17/README.md) | A release consultada fixa uma referência documental para o POM no commit `b02837b6c77b94799c055f8fa446fb770bfb49f1`. Ainda faltam um recorte auditado, inventário, verificação do seletor e cobertura histórica por método. [Referência da release](https://github.com/jhy/jsoup/releases/tag/jsoup-1.21.2) |
| Positivos para KNN e RF | Zero episódios naturais confirmados nas fontes auditadas. O Defects4J lista 61 casos ativos de Lang e a KAN-11 verificou zero revisões do catálogo no recorte. | O Defects4J v3.0.1 lista 93 casos ativos de jsoup. São casos curados com testes gatilho. Sem recorte consecutivo, junção por SHA e resultados da suíte original, a contagem de falhas naturais observáveis e sua distribuição temporal permanecem desconhecidas. [Catálogo Defects4J v3.0.1](https://github.com/rjust/defects4j/tree/v3.0.1#the-projects) |

O Commons Lang tem evidência operacional mais diretamente aplicável à Entrega 3. Para comparar candidatos ao estudo principal sob o mesmo desenho, aplicar a jsoup os mesmos critérios de amostragem, execução, identidade e episódios naturais. Uma eventual troca exigiria nova auditoria de recorte, validação do ambiente e do seletor, coleta T0 e verificação da comparabilidade. A maior contagem de casos curados, por si só, deixa em aberto a suficiência para uma série temporal natural.

## Reavaliação após KAN-14 e KAN-16

1. **KAN-14 — cobertura operacional.** Conciliar os 100 SHAs por posição e o lote de cinco por SHA exato. Para cada revisão, registrar tentativa, ambiente e versões, escopo da suíte, código de saída, completude e localização do log/XML. Distinguir teste executado com falha, execução parcial, impedimento de infraestrutura e revisão ainda sem tentativa. Confirmar se a rodada da âncora satisfaz as condições da referência ou se é necessária uma rodada nas mesmas condições das demais.
2. **KAN-16 — oráculo por método.** Conferir `t0_runs` e `t0_results`, integridade e unicidade de `(commit_sha, test_id)`, associação das invocações e concordância com os totais brutos. Reportar métodos descobertos, associados e sem associação inequívoca, desfechos, disponibilidade de duração e de ordem global por SHA. Distinguir duração desconhecida de zero. Lacunas e tentativas incompletas preservam seu estado e ficam fora dos denominadores que exigem T0 completo. [Regra aprovada](../KAN-17/README.md#agregação-para-t0)
3. **Falhas — atribuição e independência.** Para cada falha ou erro, rastrear SHA, `test_id`, execução, assinatura da falha e evidência de causa. Quando necessário, conferir reexecução no mesmo ambiente e evidência nos vizinhos ou diffs. Contar uma vez por causa confirmada, mesmo que haja múltiplos métodos, SHAs ou tentativas. Manter falhas ambientais, infraestrutura, causas indeterminadas e casos do Defects4J fora dos positivos naturais do estudo. Reexaminar LANG-1792 e LANG-1791 apenas com resultados da suíte original vinculados ao SHA e ao teste. Declarar o que as lacunas deixam em aberto sobre começo e fim de episódios. [Regra de episódios](../KAN-11/README.md#episódios-por-causa-confirmada)
4. **T1 — cobertura da comparação.** Conferir inventário pré-execução e a junção com T0 nos SHAs em que ambos existirem. Registrar os candidatos sem par, a justificativa para seleção, exclusão ou fallback e o overhead. Reportar quantas revisões têm dados comparáveis e em quais o T0 permite medir detecção ou antecipação de falhas. [KAN-18](https://cin-team-test-prioritization.atlassian.net/browse/KAN-18)
5. **T2/T3 — suficiência temporal.** Para as janelas cronológicas do desenho, tabular por janela os SHAs com T0 utilizável, métodos observados, positivos naturais, episódios independentes e falhas naturais que permanecem no conjunto T1. Verificar se há exemplos das classes necessárias no treino e episódios independentes na avaliação, se cada feature histórica usa apenas SHAs anteriores e se recorrências da mesma causa comprometem a independência entre janelas. Explicitar a concentração dos positivos, janelas sem suporte e limites da avaliação. A presença de algum positivo é condição necessária. A suficiência para uma comparação depende também da distribuição e da independência, sem limiar numérico adotado nesta análise. [Dataset temporal KAN-19](https://cin-team-test-prioritization.atlassian.net/browse/KAN-19)
6. **Decisão definitiva.** Se o Commons Lang sustentar o desenho principal, apresentar a Wallace a recomendação fundamentada de permanência. Se os positivos ou sua cobertura temporal forem insuficientes, apresentar os resultados e os impactos de manter a pesquisa exploratória, ampliar o recorte ou auditar jsoup em condições comparáveis. Submeter a Wallace qualquer mudança de projeto, recorte, métricas ou ambiente comparável e versionar a decisão autorizada com as fontes e os efeitos no protocolo.

## Aceite e dependência no Jira

| Critério da KAN-12 | Estado |
| --- | --- |
| Decisão justificada e rastreável | Commons Lang confirmado por Wallace em 22/11/2026, com justificativa e limites registrados nesta nota. |
| Riscos remanescentes explicitados | Os cinco T0 cobrem 5 dos 100 SHAs, sem falhas naturais observadas, com duas durações ausentes entre métodos executados e sem ordem global de início. O piloto sintético fornece evidência auxiliar em uma amostra pequena de mutações e tem alcance limitado para regressões naturais. |

Em 22/11/2026, com autorização de Wallace, a **KAN-12 foi concluída no Jira**. O comentário de aceite vincula esta nota à decisão publicada em `4107125a07659763f56a457ce84540fa3e008f16`. A verificação usou `git show --check 4107125`, `git branch -r --contains 4107125` e a leitura do resumo da KAN-16 e do relatório de mutação. Após a transição, a consulta aos dois cartões confirmou a **KAN-18 em BackLog**, com as duas dependências diretas concluídas (KAN-12 e KAN-17). O vínculo original `Blocks` de ID `10009` foi preservado. A coordenação pode abrir a KAN-18. [Comentário de aceite](https://cin-team-test-prioritization.atlassian.net/browse/KAN-12?focusedCommentId=10014) · [KAN-18](https://cin-team-test-prioritization.atlassian.net/browse/KAN-18)

## Reavaliação com os cinco T0

O lote da KAN-14 terminou com cinco suítes completas, 298.770 invocações e zero falhas ou erros. A KAN-16 associou todas as invocações observadas a 23.280 registros por método e revisão. Há duração válida em 23.222 registros e a ordem global de início permanece indisponível. [Resultados preliminares](../ENTREGA-3/README.md) · [Resumo da coleta](../KAN-16/resumo-lote.json)

O resultado confirma a viabilidade operacional do Commons Lang para o piloto da Entrega 3. As cinco suítes não acrescentaram episódios naturais observados, e as 95 posições fora do piloto não forneceram novas execuções. A evidência disponível na reavaliação limitava a medição temporal de detecção de falhas naturais. A confirmação posterior do Commons Lang está registrada no início desta nota.
