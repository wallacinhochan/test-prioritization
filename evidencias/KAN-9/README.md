# KAN-9 — Validação inicial do Apache Commons Lang

A [KAN-9](https://cin-team-test-prioritization.atlassian.net/browse/KAN-9) verifica se o Commons Lang pode ser compilado e testado em uma revisão fixa antes da seleção do objeto experimental.

## Revisão e ambiente

Usei o release oficial `3.20.0` como ponto de partida, com o commit [`598dfc163b8b410fb3bb8794521206ec8dcec82a`](https://github.com/apache/commons-lang/commit/598dfc163b8b410fb3bb8794521206ec8dcec82a) da tag `rel/commons-lang-3.20.0`. A revisão serve para validar o ambiente. O recorte cronológico dos commits para o experimento pertence à KAN-10.

- Windows 11 x64, idioma `pt_BR`.
- Microsoft Build of OpenJDK 21.0.11 e Apache Maven 3.9.11.
- A suíte roda com `mvn clean test`, que inclui a compilação do código e dos testes. Em seguida, o script roda dois métodos de classes diferentes, um por invocação do Maven.
- Por padrão, o script usa um cache Maven novo. A primeira suíte inclui o tempo de obtenção das dependências. Os testes individuais reaproveitam o cache e os arquivos compilados. Os tempos de ponta a ponta incluem a inicialização do Maven.

## Como reproduzir no Windows

Use Windows 11 x64 com locale `pt_BR`, PowerShell, Git, Microsoft Build of OpenJDK 21.0.11 e Apache Maven 3.9.11. O script executa `clean test` e dois métodos individuais do Commons Lang 3.20.0. A primeira rodada com cache vazio precisa de acesso ao GitHub e ao Maven Central.

Na raiz do repositório de pesquisa, prepare uma cópia limpa e execute a validação em **UTC**, a condição reproduzida em que a suíte passou. Se `mvn.cmd` estiver fora do `PATH`, use seu caminho absoluto em `$maven`.

```powershell
$fonte = Join-Path ([IO.Path]::GetTempPath()) ('commons-lang-3.20.0-' + [guid]::NewGuid())
$saida = Join-Path ([IO.Path]::GetTempPath()) ('kan9-' + [guid]::NewGuid())
$jdk = '<caminho do JDK 21.0.11>'
$maven = 'mvn.cmd'
git clone --depth 1 --branch rel/commons-lang-3.20.0 https://github.com/apache/commons-lang.git $fonte
if ($LASTEXITCODE -ne 0) { throw 'Falha ao clonar o Commons Lang.' }
$comum = @{ Fonte = $fonte; Jdk = $jdk; Maven = $maven }
./evidencias/KAN-9/validar.ps1 @comum -Saida "$saida-utc" -Fuso UTC
```

O script verifica o commit e a cópia de trabalho, confere as versões do compilador, do Java usado pelo Maven e do Maven, e grava `ambiente.txt`, um log por execução e `execucoes.json`. Em UTC, repassa `-Duser.timezone=UTC` ao Maven e aos testes do Surefire.

Para repetir a comparação histórica, rode os comandos abaixo no fuso `America/Sao_Paulo`, depois da preparação do código acima. As duas chamadas sem `-Fuso` herdam o fuso do ambiente e retornam código 1 quando a falha registrada se repete. A rodada em UTC reutiliza o cache local, como no registro original.

```powershell
./evidencias/KAN-9/validar.ps1 @comum -Saida "$saida-local"
$comum.CacheMaven = Join-Path "$saida-local" 'cache-maven'
./evidencias/KAN-9/validar.ps1 @comum -Saida "$saida-diag-local" -SomenteDiagnostico
./evidencias/KAN-9/validar.ps1 @comum -Saida "$saida-diag-utc" -SomenteDiagnostico -Fuso UTC
./evidencias/KAN-9/validar.ps1 @comum -Saida "$saida-utc-cache-reutilizado" -Fuso UTC
```

## Diagnóstico do fuso

Em `America/Sao_Paulo`, `DurationFormatUtilsTest#testFourYears` esperava `1` dia e obteve `0` no intervalo de 2 a 3 de novembro de 2004. O valor `10` para o mês na mensagem original representa novembro em `Calendar`. No JDK usado, o início de 2 de novembro foi ajustado para `01:00` pela transição do horário de verão. Até a meia-noite seguinte, passaram-se 23 horas. Em UTC, o mesmo intervalo de datas locais teve 24 horas.

O relatório XML do Surefire confirmou `America/Sao_Paulo` na suíte inicial e no primeiro diagnóstico, e `UTC` no segundo diagnóstico e na segunda suíte. O [extrato do XML da segunda suíte](resultados/utc/surefire-duration-format.txt) registra o fuso efetivo e o resultado de `testFourYears`. Cada pasta de `resultados/` contém o ambiente, a saída do Maven e o `execucoes.json` com os argumentos específicos, códigos de saída e tempos de ponta a ponta. Os caminhos do perfil local foram substituídos por `<perfil-local>`.

## Resultados de 20 de novembro de 2026

| Execução | Casos registrados | Falhas | Erros | Ignorados | Tempo de ponta a ponta |
| --- | ---: | ---: | ---: | ---: | ---: |
| [Suíte completa no fuso local](resultados/fuso-local/suite.log) | 59.960 | 1 | 0 | 14 | 344,094 s |
| [`StringUtilsTest#testReverse_String` no fuso local](resultados/fuso-local/string-utils.log) | 1 | 0 | 0 | 0 | 21,529 s |
| [`ArrayUtilsTest#testIsEmptyObject` no fuso local](resultados/fuso-local/array-utils.log) | 1 | 0 | 0 | 0 | 18,572 s |
| [`DurationFormatUtilsTest#testFourYears` no fuso local](resultados/diagnostico-local/duration-format.log) | 1 | 1 | 0 | 0 | 16,933 s |
| [`DurationFormatUtilsTest#testFourYears` em UTC](resultados/diagnostico-utc/duration-format.log) | 1 | 0 | 0 | 0 | 19,963 s |
| [Suíte completa em UTC](resultados/utc/suite.log) | 59.960 | 0 | 0 | 14 | 245,546 s |
| [`StringUtilsTest#testReverse_String` em UTC](resultados/utc/string-utils.log) | 1 | 0 | 0 | 0 | 16,227 s |
| [`ArrayUtilsTest#testIsEmptyObject` em UTC](resultados/utc/array-utils.log) | 1 | 0 | 0 | 0 | 18,517 s |

O total do Surefire inclui os casos ignorados. A segunda suíte reutilizou o cache Maven da primeira, portanto os tempos registram as rodadas reais e servem como evidência de execução.

## Parecer de executabilidade

O **Apache Commons Lang 3.20.0** compilou e executou a suíte padrão no Windows 11 x64 na revisão `598dfc163b8b410fb3bb8794521206ec8dcec82a`, com **Microsoft Build of OpenJDK 21.0.11 e Apache Maven 3.9.11**. **UTC é a condição reproduzida**. O Surefire registrou 59.960 casos, com 59.946 aprovações, 14 ignorados, zero falhas e zero erros. Em `America/Sao_Paulo`, o único caso com falha foi `DurationFormatUtilsTest#testFourYears`. O método falhou também isoladamente nesse fuso e passou no diagnóstico em UTC.

A KAN-9 cobre essa revisão e esse ambiente. A validação operacional dos commits históricos fica para a etapa própria.

## Aceite da KAN-9

- **Logs e comandos reproduzíveis.** O [script](validar.ps1), os [comandos acima](#como-reproduzir-no-windows) e os registros por rodada cobrem a suíte completa, testes individuais, ambiente, tempos e a diferença entre fusos.
- **Parecer de executabilidade.** Os totais vêm dos resumos do Surefire. A contagem de aprovações em UTC é o total menos os ignorados, as falhas e os erros.
- **Entregável.** A evidência está no repositório de pesquisa. A revisão e o aceite formal no Jira cabem à coordenação.

## Ocorrências de ambiente

- O `java` padrão apontava para o Oracle JRE 8 sem `javac`. O script selecionou o JDK 21 já instalado por meio de `JAVA_HOME`, limitado à execução.
- A primeira passagem de propriedades do PowerShell ao `mvn.cmd` separou o caminho do cache e fez o Maven interpretar `C:` como prefixo de plugin. O script passou as propriedades entre aspas por `MAVEN_ARGS` e a rodada oficial usou uma cópia limpa com cache separado.
- O compilador emitiu avisos sobre o alvo Java 8 e sobre código existente. O log da suíte preserva esses avisos.
