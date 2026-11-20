# KAN-17 — Unidade experimental e identidade dos testes

**Decisões aprovadas por Wallace em 20/11/2026.** O método de teste é a unidade de coleta T0, seleção T1, rankings T1–T3 e avaliação. A regra abaixo foi aprovada para o piloto do Apache Commons Lang. O aceite do dicionário da KAN-15 continua com o grupo. [Cartão KAN-17](https://cin-team-test-prioritization.atlassian.net/browse/KAN-17) · [Dicionário KAN-15](../KAN-15/README.md)

## Identidade e histórico

- Forme `test_id` como `classe#metodo(tipos)`. Use o nome binário qualificado da classe em cujo contexto o teste é descoberto, com `$` para classes aninhadas. Use o nome Java do método e a lista ordenada de tipos dos parâmetros após apagamento dos genéricos. Use o nome qualificado dos tipos de referência, nomes Java para tipos primitivos e `[]` por dimensão de array, inclusive em varargs. Separe os tipos com vírgula sem espaços e inclua `()` quando a lista estiver vazia. Preserve a capitalização. Para um método herdado, a identidade usa a classe de execução descoberta; a declaração pode ser registrada como proveniência.
- Parametrizações, repetições e testes dinâmicos gerados pelo mesmo método compartilham a chave do método ou da fábrica no mesmo contexto de classe. Índice, argumentos, nome de exibição e identificador de invocação ficam na evidência bruta. Para testes dinâmicos, a origem é o método da fábrica identificado no plano ou na árvore de execução.
- Compare o histórico pela chave exata, respeitando o corte temporal da KAN-15. Renomear classe ou método, mover para outro contexto de classe ou alterar os tipos dos parâmetros gera uma chave nova e inicia histórico novo. Métodos removidos saem do inventário da revisão em que não existem, com seus registros históricos preservados. Uma chave que volta a aparecer continua sujeita à igualdade exata e ao corte temporal. Renomeações e movimentos podem reduzir a quantidade de histórico disponível, mas evitam transferir observações com base em correspondência aproximada.

A granularidade por classe reduziria o número de candidatos e agruparia métodos com resultados e custos diferentes. Por método, o seletor e os rankings podem distinguir esses métodos, inclusive sobrecargas. Usar o nome literal do XML como chave faria variantes do mesmo método ocuparem posições independentes e mudaria o denominador de testes em função da quantidade de invocações. Usar assinatura somente para nomes sobrecarregados faria a chave de um método já existente mudar quando uma sobrecarga fosse introduzida ou retirada.

## Inventário e associação com resultados

Na revisão avaliada, use a descoberta do provedor sobre as classes de teste compiladas, com classpath e filtros da suíte pretendida, antes de executar os testes. A inspeção com `Launcher.discover()` retornou `MethodSource` com classe, nome e tipos para os exemplos abaixo, inclusive templates parametrizados e repetidos, fábricas e classes aninhadas. Os descendentes criados em execução podem acrescentar invocações a um candidato que já existe. A checagem executou apenas a descoberta de dez classes com JUnit Jupiter, com 368 descritores com `MethodSource`. A equivalência entre um inventário completo e a descoberta do Surefire no recorte histórico permanece a verificar. [Sonda de descoberta](fontes/Kan17Discovery.java) · [Saída preservada](fontes/descoberta-junit.tsv)

Na coleta, prefira a origem do método fornecida pela execução e pelos ancestrais dos eventos quando necessário. Se a origem disponível for apenas o Surefire XML, faça a associação pelo inventário da mesma revisão e configuração e aceite somente correspondência inequívoca entre o contexto de classe e o método. `classname` pode ser um rótulo de exibição. Uma assinatura abreviada do XML pode corroborar o inventário, inclusive quando a origem do método usa nomes qualificados. Preserve o XML original e o localizador de cada invocação. Quando não houver associação inequívoca, preserve também o motivo e conte o registro como lacuna de cobertura. Para o método sem resultado associável, a linha de T0 fica ausente conforme o contrato.

## Agregação para T0

Para cada método da tentativa de referência, agregue as invocações associadas.

| Campo | Regra aprovada | Efeito nas métricas |
| --- | --- | --- |
| `outcome` | `fail` se alguma invocação tiver falha ou erro atribuível ao teste. Senão, `pass` se alguma passar. Use `skip` quando todas forem ignoradas. Preserve os desfechos originais e trate infraestrutura pelo estado da execução da KAN-15. | Um método que falha contribui uma vez na contagem de falhas, independentemente do número de invocações com falha. Para execuções incompletas, o estado da tentativa acompanha a interpretação dos resultados observados. |
| `duration_ms` | Some os tempos brutos das invocações executadas e converta o total decimal em segundos para milissegundos, com arredondamento uma vez para o inteiro mais próximo e empate para cima. Deixe vazio se faltar o tempo de qualquer invocação executada ou se todas forem ignoradas. Um zero medido é válido. | A soma representa o custo observado das invocações do método. O tempo de parede da suíte pertence a `t0_runs`. Média ou máximo ocultariam parte do custo de executar todas as variantes. |
| `execution_order` | Registre a posição do primeiro início de invocação do método quando houver sequência global observada. Métodos sem início observado ficam com o campo vazio. A ordem de arquivos, a ordem interna do XML e o índice de invocação não comprovam uma cronologia global. | A posição descreve o início do método. O instante em que uma invocação falha pode ser posterior. A comparação de ordem e as métricas que dependem dela precisam declarar a cobertura observada. |

## Exemplos conferidos

Os localizadores estão nos [extratos XML](fontes/surefire-kan9-utc.txt), com arquivo, linha e SHA-256 do original, e na [saída da descoberta JUnit](fontes/descoberta-junit.tsv). Os totais abaixo são exemplos de método calculados sobre esses registros, sem exportação de uma suíte T0.

| Registro observado | Identidade ou agregação pela regra aprovada |
| --- | --- |
| `AppendableJoinerTest`, `testDelimiterAppendable(Class)[1]` a `[5]` | `org.apache.commons.lang3.AppendableJoinerTest#testDelimiterAppendable(java.lang.Class)`. Cinco aprovações resultam em `pass` e 31 ms. O XML usa `Class`; a descoberta informa `java.lang.Class`. |
| `RandomUtilsTest`, `testNextDouble` e `testNextDouble(RandomUtils)[1]` a `[3]` | Duas chaves: `org.apache.commons.lang3.RandomUtilsTest#testNextDouble()` e `org.apache.commons.lang3.RandomUtilsTest#testNextDouble(org.apache.commons.lang3.RandomUtils)`. As duas passam e cada uma tem duração medida de 0 ms. |
| `ComparableUtilsTest`, `lessThan_returns_true` com `classname="B is 10 (B &gt; A)"` | `org.apache.commons.lang3.compare.ComparableUtilsTest$A_is_1$B_is_10#lessThan_returns_true()`, com a classe confirmada na descoberta. A linha registra `pass` e 1 ms. |
| `StopWatchTest`, `testGetTime()[1]` a `[10]` | `org.apache.commons.lang3.time.StopWatchTest#testGetTime()`, um método repetido, com `pass` e 305 ms. |
| `StreamsTest`, `simpleStreamFilterFailing()[1]` a `[3]` em cada um de dois arquivos | `org.apache.commons.lang3.StreamsTest#simpleStreamFilterFailing()` e `org.apache.commons.lang3.stream.StreamsTest#simpleStreamFilterFailing()`. São duas fábricas distintas, com três descendentes aprovados e 1 ms e 6 ms, respectivamente. |
| `RandomStringUtilsTest`, `testHugeStrings(int)` com `<skipped>` e `time="0.0"` | `org.apache.commons.lang3.RandomStringUtilsTest#testHugeStrings(int)`, com `skip` e duração vazia. A invocação não executou. |
| `DurationFormatUtilsTest`, `testFourYears` | A chave `org.apache.commons.lang3.time.DurationFormatUtilsTest#testFourYears()` é a mesma no fuso local, onde o log registra uma falha, e na execução em UTC, cujo XML registra `pass` e 4.893 ms. [Log local](../KAN-9/resultados/fuso-local/suite.log) · [Diagnóstico da KAN-9](../KAN-9/README.md#diagnóstico-do-fuso) |
| `BooleanUtilsTest`, `test_toStringOnOff_Boolean` e `test_toStringOnOff_boolean` | Dois métodos diferentes. Uma estrutura de dados com comparação sem distinção de caixa fundiria essas chaves. |

O campo `execution_order` fica vazio para todos esses exemplos. A KAN-9 não preservou uma sequência global de inícios de invocação. Os XML inspecionados não trazem exemplos de erro de teste, rerun ou duração ausente. A falha no fuso local está preservada no log. Também não há exemplo verificado de renomeação entre duas revisões com inventários completos, nem de método com invocações simultaneamente aprovadas e ignoradas.

## Proveniência e reprodução

A inspeção usa o checkout local `kan9-commons-lang-3.20.0-clean-598dfc1`, sob a pasta temporária da máquina da KAN-9. O Git confirmou a revisão `598dfc163b8b410fb3bb8794521206ec8dcec82a` e a árvore sem alterações rastreadas. A suíte usou Microsoft Build of OpenJDK 21.0.11, Maven 3.9.11, Surefire 3.5.4 e UTC. [README da KAN-9](../KAN-9/README.md) · [Log da suíte](../KAN-9/resultados/utc/suite.log)

```powershell
$checkout = Join-Path ([IO.Path]::GetTempPath()) 'kan9-commons-lang-3.20.0-clean-598dfc1'
$relatorios = Join-Path $checkout 'target/surefire-reports'
./evidencias/KAN-17/fontes/inspecionar-surefire.ps1 -Relatorios $relatorios
```

Os 228 arquivos contêm 59.443 elementos `testcase`, com 13 `skipped`, zero `failure` e zero `error`. O log da suíte registra 59.960 casos e 14 ignorados. Os XML atuais de `ArrayUtilsTest` e `StringUtilsTest` são das execuções isoladas posteriores, com um caso cada. No log da suíte essas classes tiveram 355 e 164 casos, respectivamente, com um ignorado em `StringUtilsTest`. A diferença de 517 casos e um ignorado é reconciliada exatamente por essas substituições. Os cabeçalhos `testsuite/@tests` somam 59.159. Dois relatórios com cabeçalho `tests="0"` ainda contêm elementos `testcase`. A contagem de cobertura dos registros usa os elementos, junto com o log e a proveniência da tentativa. [Execução isolada de ArrayUtilsTest](../KAN-9/resultados/utc/array-utils.log) · [Execução isolada de StringUtilsTest](../KAN-9/resultados/utc/string-utils.log)

Dos 59.443 registros, 55.419 têm sufixo numérico e assinatura aparente, dois têm assinatura sem sufixo, e 63 têm `classname` fora do prefixo esperado, todos em `ComparableUtilsTest`. Um agrupamento diagnóstico por `classname` bruto e nome sem assinatura ou índice encontra 40 grupos com grafias de assinatura diferentes. O total sinaliza possíveis colisões e inclui classes de exibição, portanto não é uma contagem de métodos físicos. Os relatórios originais foram lidos sem alteração. O extrato versionado preserva as linhas usadas nos exemplos, sem carregar o bloco de propriedades locais.

Para repetir a sonda, indique o Java 21.0.11 em `$java` e o JAR `junit-platform-launcher-1.13.4.jar` em `$launcher`. No ensaio retrospectivo, o XML serviu apenas para recuperar o classpath já utilizado pela KAN-9. Na seleção, o classpath deve vir da configuração de build e das dependências resolvidas antes da suíte da revisão.

```powershell
$xml = [xml](Get-Content (Join-Path $relatorios 'TEST-org.apache.commons.lang3.AppendableJoinerTest.xml') -Raw)
$cp = $xml.testsuite.SelectSingleNode("properties/property[@name='surefire.test.class.path']").GetAttribute('value')
$classes = @(
    'org.apache.commons.lang3.AppendableJoinerTest'
    'org.apache.commons.lang3.RandomUtilsTest'
    'org.apache.commons.lang3.RandomStringUtilsTest'
    'org.apache.commons.lang3.compare.ComparableUtilsTest'
    'org.apache.commons.lang3.stream.StreamsTest'
    'org.apache.commons.lang3.StreamsTest'
    'org.apache.commons.lang3.time.StopWatchTest'
    'org.apache.commons.lang3.concurrent.LazyInitializerSimpleTest'
    'org.apache.commons.lang3.BooleanUtilsTest'
    'org.apache.commons.lang3.time.DurationFormatUtilsTest'
)
& $java --class-path "$cp;$launcher" evidencias/KAN-17/fontes/Kan17Discovery.java @classes
```

## Integração e pendências

- **KAN-15.** Referenciar o formato e a política histórica da KAN-17 para a chave opaca compartilhada. Usar exemplos com proveniência da tentativa de referência. A revisão e o aceite do dicionário permanecem com o grupo. [Contrato](../KAN-15/README.md)
- **KAN-16.** Capturar XML por tentativa antes que execuções posteriores o sobrescrevam. Reter a origem do método e a relação com cada invocação, o desfecho original e o tempo bruto. Aplicar a regra de agregação por `(commit_sha, test_id)`, distinguir duração vazia de zero e registrar a cobertura de associação e ordem. Usar o estado da tentativa para indicar incompletude. [Cartão KAN-16](https://cin-team-test-prioritization.atlassian.net/browse/KAN-16)
- **KAN-18.** Gerar o inventário de métodos no SHA alvo antes da suíte e usar a chave aprovada em todos os candidatos T1, inclusive fallback e excluídos. Incluir classe de execução e localizar a declaração quando houver herança. Usar o T0 da mesma revisão somente após fixar seleção e ranking, para medir cobertura e explicar divergências na junção. [Cartão KAN-18](https://cin-team-test-prioritization.atlassian.net/browse/KAN-18)

## Checagem complementar da KAN-13

### Posição 1 do recorte

A execução `20261120T150615596Z-2d06695aa11d40d7b8ba85f640fbfb1b` verificou o SHA `921c1b4e09ed7b6900ad7243cffb33b373980cc5` e executou `StringUtilsTest#testReverse_String` isoladamente em UTC. `ambiente.json` registra saída Maven 0 e um XML. `maven.log` confirma um caso, sem falhas, erros ou ignorados. A inspeção do fonte no mesmo SHA confirmou a declaração `@Test void testReverse_String()`. A chave é `org.apache.commons.lang3.StringUtilsTest#testReverse_String()`, com `pass`, 43 ms e ordem global do T0 indisponível. O piloto cobre esse método na revisão mais antiga do recorte. [Piloto da KAN-13](../KAN-13/pilotos/mais-antigo/README.md)

No diretório `resultados/KAN-13/921c1b4e09ed7b6900ad7243cffb33b373980cc5/20261120T150615596Z-2d06695aa11d40d7b8ba85f640fbfb1b/`, o arquivo `surefire/TEST-org.apache.commons.lang3.StringUtilsTest.xml` tem SHA-256 `ee81faba723ff6d08116e28a6e654ae9214856a770c069c996e8bdb88ea69e2c`. A linha 10 registra `<property name="user.timezone" value="UTC"/>`. A linha 61 registra:

```xml
<testcase name="testReverse_String" classname="org.apache.commons.lang3.StringUtilsTest" time="0.043"/>
```

A inspeção usou `inspecionar-surefire.ps1 -Relatorios <diretório surefire>` sobre a pasta `surefire` da execução e `git show <sha>:src/test/java/org/apache/commons/lang3/StringUtilsTest.java` sobre o clone da KAN-10.

### Âncora

A execução `20261120T150800719Z-a24ed681244a469e80a93be9467c11b1` verificou o SHA `598dfc163b8b410fb3bb8794521206ec8dcec82a` e executou `mvn clean test` em UTC com Eclipse Adoptium 21.0.11, Maven 3.9.11, Surefire 3.5.4 e Linux/amd64. O manifesto registra saída Maven 0 e 228 relatórios. Os arquivos `ambiente.json`, `maven.log` e a pasta `surefire/` estão em `resultados/KAN-13/598dfc163b8b410fb3bb8794521206ec8dcec82a/20261120T150800719Z-a24ed681244a469e80a93be9467c11b1/`. [Piloto da âncora](../KAN-13/pilotos/ancora/README.md)

```powershell
$ancora = 'resultados/KAN-13/598dfc163b8b410fb3bb8794521206ec8dcec82a/20261120T150800719Z-a24ed681244a469e80a93be9467c11b1'
./evidencias/KAN-17/fontes/inspecionar-surefire.ps1 -Relatorios (Join-Path $ancora 'surefire')
```

- Foram conferidos **59.960 elementos `testcase`**, com 14 ignorados, zero falhas e zero erros, em acordo com o resumo do Maven. A soma de `testsuite/@tests` foi 59.676. Dois relatórios tinham casos apesar do cabeçalho com zero. Todos os XML indicaram UTC.
- A comparação por nome de arquivo e pelo multiconjunto de pares brutos `(classname, name)`, com distinção de maiúsculas, coincidiu em 226 dos 228 arquivos da KAN-9. As únicas diferenças foram `ArrayUtilsTest` (355 casos na âncora e um nos XML locais da KAN-9) e `StringUtilsTest` (164 e um). Os relatórios da suíte completa recuperam os 517 elementos ausentes nos arquivos sobrescritos.
- A âncora repete as sobrecargas de `RandomUtilsTest#testNextDouble`, o rótulo de classe aninhada em `ComparableUtilsTest` e o skip de `testHugeStrings(int)`. `testDelimiterAppendable(java.lang.Class)` passou com cinco invocações e total de 6 ms. `testFourYears()` passou com 4.196 ms. Os tempos pertencem ao ambiente e à tentativa documentados. [Extratos XML e hashes](fontes/surefire-kan13-ancora.txt)
- A checagem confirmou a compatibilidade dos exemplos com os relatórios da KAN-13. O mapeamento de todas as invocações para um inventário pré-execução completo e a cobertura de ordem global continuam pendentes para o recorte histórico.
