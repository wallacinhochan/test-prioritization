# KAN-11 — Disponibilidade de resultados históricos do Commons Lang

**Parecer de 20/11/2026.** As fontes auditadas ainda não sustentam uma avaliação temporal supervisionada de KNN ou Random Forest para falhas naturais no recorte candidato. Há resultados por método em **2 de 100 revisões**, com suíte completa em **1** e um único método na outra. Nos resultados elegíveis como observação de teste por SHA, encontramos **0 episódios naturais confirmados e 1 ambiental confirmado**. O zero descreve a evidência disponível. A frequência de regressões nas revisões sem resultados continua desconhecida.

## Cobertura

A [tabela por revisão](cobertura.csv) preserva a ordem e os SHAs da [KAN-10](../KAN-10/commits.csv). A primeira revisão é de 24/09/2025 às 13:51:27 UTC e a última de 12/11/2025 às 19:55:59 UTC. O intervalo é de 49 dias, 6 horas, 4 minutos e 32 segundos. Os resultados locais foram produzidos em 20/11/2026 e se referem às árvores exatas dessas revisões. A sequência das revisões e as datas das execuções têm papéis distintos. Os 98 SHAs entre as duas posições observadas ficam identificados como sem resultado por método nas fontes consultadas.

| Posição | Fonte | Alcance e resultado |
| --- | --- | --- |
| 1 | KAN-13, rodada `20261120T150615596Z-2d06695aa11d40d7b8ba85f640fbfb1b` | Um caso aprovado, `org.apache.commons.lang3.StringUtilsTest#testReverse_String()`, em 43 ms. [Piloto](../KAN-13/pilotos/mais-antigo/README.md) · [Conferência da identidade](../KAN-17/README.md) |
| 100 | KAN-9, Windows, UTC | Suíte com 59.960 casos, 59.946 aprovados, 14 ignorados e nenhuma falha ou erro. A evidência versionada contém o log, testes dirigidos e extratos de XML. [Ambiente](../KAN-9/resultados/utc/ambiente.txt) · [Log](../KAN-9/resultados/utc/suite.log) |
| 100 | KAN-13, Linux, UTC, rodada `20261120T150800719Z-a24ed681244a469e80a93be9467c11b1` | 228 XML do Surefire, 59.960 elementos `testcase`, 14 com `skipped`, nenhum com `failure`, `error` ou marcadores de rerun/flaky. A soma do atributo `tests` em `testsuite` dá 59.676. Contamos os elementos individuais, que incluem casos de classes aninhadas e reconciliam com o total do Maven. Os 59.960 são casos, com possíveis várias invocações de um mesmo método. [Piloto](../KAN-13/pilotos/ancora/README.md) |
| 100 | KAN-9, Windows, America/Sao_Paulo | Uma falha na suíte, reproduzida isoladamente no mesmo SHA. O diagnóstico em UTC passa. [Suíte](../KAN-9/resultados/fuso-local/suite.log) · [Isolado no fuso local](../KAN-9/resultados/diagnostico-local/duration-format.log) · [Isolado em UTC](../KAN-9/resultados/diagnostico-utc/duration-format.log) |

Os resultados brutos da KAN-13 estavam em `resultados/KAN-13/<sha>/<id>/` no repositório local. Na âncora, o SHA-256 de `ambiente.json` é `1b5d9ac1d9f75eed07f5d7511aaf92759cef5296dcb6dd93b74aab17aeba99b0` e o de `maven.log` é `8555fd56e408e3b02d1195ffdd4c9e8a1f71faa4bdbe2c78fe83d4c23c80b6e4`. No piloto mais antigo, o SHA-256 de `ambiente.json` é `309f2ccb17eb17a9abf1d79521014f070ff1f1a99a18481bd68e478db36520ad`.

## Fontes e rótulos

| Fonte | Ligação à revisão e ao teste | O que sustenta | Limitação |
| --- | --- | --- | --- |
| KAN-9 | SHA completo em `ambiente.txt`, método na saída dos diagnósticos e no extrato do Surefire | Ambiente e falha de fuso na posição 100, com resultados dirigidos rastreáveis. | A suíte fora de UTC tem uma falha ambiental. O log agregado e os extratos versionados cobrem somente parte da identificação por método. [Evidência](../KAN-9/README.md) |
| KAN-13 | `sha_verificado` em `ambiente.json`, XML da rodada e identidade aprovada na KAN-17 | Execução local da suíte na posição 100 e de um método na posição 1. | Diferença de escopo entre as duas revisões. XML completos disponíveis como saídas locais. [Ambiente](../KAN-13/README.md) · [Identidade](../KAN-17/README.md) |
| GitHub Actions | Consultas de workflows, check runs e status agregado por SHA exato, nos 100 registros. | As 300 consultas responderam com contagem zero para workflows, check runs e status individuais. A API de status pode indicar `pending` com lista vazia. | Conclusões de workflow ou job indicam estado agregado. A consulta abrange registros ainda visíveis no repositório oficial. Execuções removidas, com SHA de merge de PR diferente ou em forks ficam fora da junção. A ausência de registros consultáveis deixa o resultado histórico desconhecido. [CI oficial](https://commons.apache.org/proper/commons-lang/ci-management.html) · [Workflow da âncora](https://github.com/apache/commons-lang/blob/598dfc163b8b410fb3bb8794521206ec8dcec82a/.github/workflows/maven.yml) · [Consulta registrada](consulta-publica.json) |
| Git e Jira da Apache | Diff do primeiro pai, SHA da alteração, chamado e eventual teste de regressão adicionado. | Contexto de defeito e alteração do código. | Um relato ou teste novo, mesmo se passa depois da correção, deixa em aberto o resultado da suíte original antes da correção. [Relatório da Apache](https://commons.apache.org/proper/commons-lang/jira-changes.html) · [LANG-1792](https://issues.apache.org/jira/browse/LANG-1792) |
| Defects4J v3.0.1 | Junção de `revision.id.buggy` e `revision.id.fixed` por SHA completo no catálogo de Lang. | 61 casos ativos e 4 descontinuados. Nenhum SHA buggy ou fixed coincide com a KAN-10. | Casos do benchmark usam versões e testes de reprodução curados. [Ativos](https://github.com/rjust/defects4j/blob/v3.0.1/framework/projects/Lang/active-bugs.csv) · [Descontinuados](https://github.com/rjust/defects4j/blob/v3.0.1/framework/projects/Lang/deprecated-bugs.csv) |

### Episódios por causa confirmada

Wallace aprovou em 20/11/2026 a contagem por causa confirmada. Ocorrências atribuídas à mesma causa contam uma vez, ainda que apareçam em múltiplos métodos, revisões ou reruns. Causas distintas exigem evidência que permita distingui-las. Ocorrências com causa ou separação incerta ficam indeterminadas. Lacunas sem resultados deixam o início e o fim de um episódio desconhecidos quando não há outra evidência. Usamos os identificadores aprovados na [KAN-17](../KAN-17/README.md) quando o método pode ser resolvido.

- **Ambiental.** Um episódio confirmado na posição 100 para `org.apache.commons.lang3.time.DurationFormatUtilsTest#testFourYears()`. A mesma asserção falha na suíte e no método isolado em America/Sao_Paulo. A duração de 23 h no intervalo local cruza uma transição de horário de verão, e o teste passa em UTC. O episódio é ambiental sob o protocolo do piloto. [Diagnóstico](../KAN-9/README.md#diagnóstico-do-fuso)
- **Natural, com relato de produto.** [LANG-1792](https://issues.apache.org/jira/browse/LANG-1792) documenta uma regressão de formatação de tipos genéricos. Na posição 96, o [diff da correção](https://github.com/apache/commons-lang/commit/5454931eb735deb59e9b671fd8a14cd4c14d8272) corrige o código e introduz `org.apache.commons.lang3.reflect.Lang1792Test#testStackOverflowError()`. O XML da KAN-13 na posição 100 registra aprovação em UTC, em 1 ms. Seu SHA-256 é `f948d31041b3ed976e679284b3809481628af13130e9af2f50f743fd98872415`. O relato compara releases, o método novo estava ausente do primeiro pai e falta uma observação de falha da suíte original em um SHA do recorte. Por isso há um defeito de produto rastreável, com zero positivo observável para esse episódio no histórico auditado.
- **Relato sem rótulo confirmado.** [LANG-1791](https://issues.apache.org/jira/browse/LANG-1791) relata comportamento em releases anteriores, com fuso de Toronto. A [posição 61](https://github.com/apache/commons-lang/commit/a22cfcd0539b5fb208415ae118783fc9dc1f902d) altera testes, e o Jira foi encerrado como *Information Provided*. A inclusão de um cenário de teste e a dependência de fuso deixam em aberto a causa e o resultado da suíte nos SHAs centrais.
- **Defects4J, fora do recorte.** Lang-1, ligado ao caso [LANG-747](https://issues.apache.org/jira/browse/LANG-747), tem `org.apache.commons.lang3.math.NumberUtilsTest::TestLang747` como [teste gatilho catalogado](https://github.com/rjust/defects4j/blob/v3.0.1/framework/projects/Lang/trigger_tests/1), com `NumberFormatException`. Os SHAs buggy e fixed do catálogo estão fora dos 100. Há zero casos mapeados ao recorte.
- **Sem dados.** Qualquer SHA sem resultado por método confirmado segue sem rótulo de execução. Pass, fail, erro e ignorado se aplicam às observações da suíte. Ausência de resultado é uma condição da evidência.

## Reprodução da auditoria

1. Em PowerShell, na raiz do repositório, execute `./evidencias/KAN-11/consultar-fontes.ps1` para repetir a consulta pública. A auditoria usou o conector GitHub depois que a consulta REST anônima atingiu o limite de requisições. Para consultar os 100 SHAs diretamente por REST em uma rodada, use autenticação com `-GitHubToken`. A [resposta preservada](consulta-publica.json) registra as rotas, totais por SHA e junções disponíveis na data da auditoria. Metadados públicos podem mudar conforme retenção. [Documentação do GitHub](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)
2. Reproduza o [recorte da KAN-10](../KAN-10/README.md#reprodução-do-recorte) e inspecione `git show 5454931 -- src/main src/test` e `git show a22cfcd -- src/test` no clone do Commons Lang. O SHA-256 do CSV usado nesta auditoria é `ed7545c232b5df2271d48f59ef4c733c798de1ab54399e5f61e6e3f07b3a60ed`.
3. Para recontar os XML da âncora, abra o diretório `surefire` da rodada da KAN-13 indicada acima. Para cada `TEST-*.xml` use `[xml]$xml = Get-Content $arquivo.FullName -Raw`, `$xml.SelectNodes('/testsuite/testcase').Count` e, para cada resultado, `$xml.SelectNodes('/testsuite/testcase/failure').Count` ou os elementos correspondentes. Compare os totais com `Select-String -Path maven.log -Pattern 'Tests run: 59960','BUILD SUCCESS'`. [Comandos dos pilotos](../KAN-13/README.md#reprodução-e-integração) · [Comandos da KAN-9](../KAN-9/README.md#como-reproduzir-no-windows)

## Suficiência e encaminhamento

Com apenas dois pontos observados no tempo e zero episódios naturais confirmados por teste e revisão, faltam positivos independentes em períodos de treino e avaliação. Tratar lacunas como aprovação reduziria artificialmente a taxa de falha. Usar informações de uma execução posterior, ou o teste introduzido pela própria correção em uma revisão anterior, alteraria o cenário temporal. A coleta do T0 pela [KAN-14](https://cin-team-test-prioritization.atlassian.net/browse/KAN-14) é a próxima fonte para checar cobertura e falhas nos SHAs intermediários sob um mesmo protocolo.

| Opção submetida a Wallace | Impacto |
| --- | --- |
| Manter o piloto exploratório no recorte e reavaliar após o T0 | Preserva a Entrega 3 e permite descrever execução e cobertura enquanto a disponibilidade de positivos é medida. É a recomendação da KAN-11. |
| Ampliar o recorte no Commons Lang | Aumenta as revisões e o custo de execução e validação. O ganho de episódios independentes é incerto. |
| Reavaliar o Commons Lang na KAN-12 | Permite comparar projetos com resultados históricos por método. Pode exigir refazer parte do ambiente e da coleta. |

### Decisão aprovada e fechamento técnico

Em 20/11/2026, Wallace aprovou manter o piloto exploratório do Apache Commons Lang na Entrega 3 com os 100 SHAs da KAN-10. A disponibilidade de falhas naturais será reavaliada após a coleta do T0 pela [KAN-14](https://cin-team-test-prioritization.atlassian.net/browse/KAN-14), com a regra aprovada de contagem por causa confirmada.

A auditoria está tecnicamente encerrada com a evidência disponível em 20/11/2026. A conclusão de insuficiência para avaliação temporal supervisionada vale para essa evidência. A decisão sobre o objeto definitivo pertence à [KAN-12](https://cin-team-test-prioritization.atlassian.net/browse/KAN-12).

## Atualização após o T0 preliminar

Em 20/11/2026, a KAN-14 revalidou as suítes completas das posições 1 e 100 e executou as posições 26, 50 e 75. As cinco rodadas usaram a mesma imagem com Eclipse Temurin 21.0.11, Maven 3.9.11, UTC e cache Maven frio. Os 1.136 XML conferidos registraram 298.770 casos, com 298.704 aprovados, 66 ignorados, zero falhas e zero erros. [Relatório da KAN-14](../KAN-14/README.md) · [Manifesto por SHA](../KAN-14/execucoes.json)

O resultado amplia de uma para cinco as suítes completas observadas no recorte de 100 revisões. As 95 posições restantes não foram executadas nesse piloto, e suas falhas continuam desconhecidas. A contagem de episódios naturais confirmados por resultados de teste e revisão permanece em zero na evidência observada. O episódio ambiental de fuso documentado pela KAN-9 permanece separado. O relato de produto LANG-1792 continua sendo evidência de correção, sem falha observada da suíte original em um dos SHAs auditados.

As cinco revisões sustentam resultados descritivos do T0. Ainda faltam episódios naturais independentes distribuídos entre períodos de treino e avaliação para testar KNN e Random Forest. A conclusão mantém Commons Lang como piloto exploratório da Entrega 3. A [KAN-12](../KAN-12/README.md) concentra a escolha definitiva do objeto.
