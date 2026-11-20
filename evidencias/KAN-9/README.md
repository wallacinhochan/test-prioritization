# KAN-9 — Validação inicial do Apache Commons Lang

A [KAN-9](https://cin-team-test-prioritization.atlassian.net/browse/KAN-9) verifica se o Commons Lang pode ser compilado e testado em uma revisão fixa antes da seleção do objeto experimental.

## Revisão e ambiente

Usei o release oficial `3.20.0` como ponto de partida, com o commit [`598dfc163b8b410fb3bb8794521206ec8dcec82a`](https://github.com/apache/commons-lang/commit/598dfc163b8b410fb3bb8794521206ec8dcec82a) da tag `rel/commons-lang-3.20.0`. A revisão serve para validar o ambiente. O recorte cronológico dos commits para o experimento pertence à KAN-10.

- Windows 11 x64, idioma `pt_BR`.
- Microsoft Build of OpenJDK 21.0.11 e Apache Maven 3.9.11.
- A suíte roda com `mvn clean test`, que inclui a compilação do código e dos testes. Em seguida, o script roda dois métodos de classes diferentes, um por invocação do Maven.
- Por padrão, o script usa um cache Maven novo. A primeira suíte inclui o tempo de obtenção das dependências. Os testes individuais reaproveitam o cache e os arquivos compilados. Os tempos de ponta a ponta incluem a inicialização do Maven.

## Como reproduzir no Windows

Execute a partir da raiz do repositório de pesquisa, em PowerShell, com Git, JDK 21.0.11 e Maven 3.9.11 disponíveis. Use pastas temporárias novas para a cópia da fonte e para a saída. A primeira execução precisa de acesso ao GitHub e ao Maven Central.

```powershell
$fonte = Join-Path ([IO.Path]::GetTempPath()) ('commons-lang-3.20.0-' + [guid]::NewGuid())
$saida = Join-Path ([IO.Path]::GetTempPath()) ('kan9-' + [guid]::NewGuid())
git clone --depth 1 --branch rel/commons-lang-3.20.0 https://github.com/apache/commons-lang.git $fonte
$jdk = '<caminho do JDK 21.0.11>'
./evidencias/KAN-9/validar.ps1 -Fonte $fonte -Jdk $jdk -Saida $saida
```

O script verifica o commit e a cópia de trabalho, registra o ambiente e salva um log por execução e um resumo em `execucoes.json`. Se o Maven estiver fora do `PATH`, passe o caminho de `mvn.cmd` em `-Maven`.

Para repetir o diagnóstico e comparar a suíte em UTC, reaproveite o cache da primeira rodada. O primeiro comando de diagnóstico usa o fuso da máquina. Rode-o em `America/Sao_Paulo` para repetir o cenário observado.

```powershell
$comum = @{ Fonte = $fonte; Jdk = $jdk; CacheMaven = (Join-Path $saida 'cache-maven') }
./evidencias/KAN-9/validar.ps1 @comum -Saida "$saida-diag-local" -SomenteDiagnostico
./evidencias/KAN-9/validar.ps1 @comum -Saida "$saida-diag-utc" -SomenteDiagnostico -Fuso UTC
./evidencias/KAN-9/validar.ps1 @comum -Saida "$saida-utc" -Fuso UTC
```

## Diagnóstico do fuso

Em `America/Sao_Paulo`, `DurationFormatUtilsTest#testFourYears` esperava `1` dia e obteve `0` no intervalo de 2 a 3 de novembro de 2004. O valor `10` para o mês na mensagem original representa novembro em `Calendar`. No JDK usado, o início de 2 de novembro foi ajustado para `01:00` pela transição do horário de verão. Até a meia-noite seguinte, passaram-se 23 horas. Em UTC, o mesmo intervalo de datas locais teve 24 horas.

O relatório XML do Surefire confirmou `America/Sao_Paulo` na suíte inicial e no primeiro diagnóstico, e `UTC` no segundo diagnóstico e na segunda suíte. Os logs arquivados em `resultados/` preservam a saída e os tempos. Os caminhos do perfil local foram substituídos por `<perfil-local>`.

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

O Commons Lang 3.20.0 compilou e executou a suíte padrão neste Windows com JDK 21.0.11 e Maven 3.9.11. Em UTC, 59.946 casos passaram e 14 foram ignorados pelo Surefire. Fixar UTC na execução experimental reproduz a condição em que a suíte passou. O diagnóstico cobre este commit e este ambiente. A KAN-10 deve verificar as demais revisões elegíveis.

## Ocorrências de ambiente

- O `java` padrão apontava para o Oracle JRE 8 sem `javac`. O script selecionou o JDK 21 já instalado por meio de `JAVA_HOME`, limitado à execução.
- A primeira passagem de propriedades do PowerShell ao `mvn.cmd` separou o caminho do cache e fez o Maven interpretar `C:` como prefixo de plugin. O script passou as propriedades entre aspas por `MAVEN_ARGS` e a rodada oficial usou uma cópia limpa com cache separado.
- O compilador emitiu avisos sobre o alvo Java 8 e sobre código existente. O log da suíte preserva esses avisos.
