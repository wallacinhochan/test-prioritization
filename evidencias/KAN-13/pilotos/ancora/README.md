# Piloto da âncora

O clone de referência resolveu `598dfc163b8b410fb3bb8794521206ec8dcec82a^{commit}` para `598dfc163b8b410fb3bb8794521206ec8dcec82a`. A revisão usa `commons-parent` 92.

## Resultado de 20 de novembro de 2026

O [comando da âncora](../../README.md#reprodução-e-integração) rodou a suíte completa em UTC com cache frio. O Surefire registrou 59.960 casos, 59.946 aprovados, 14 ignorados, 0 falhas e 0 erros. Os totais coincidem com a [suíte completa em UTC da KAN-9](../../../KAN-9/resultados/utc/suite.log). Maven e executor retornaram 0. A rodada levou 306,912 s de ponta a ponta.

O `maven.log` preservou as linhas abaixo.

```text
KAN-13 cache Maven inicial: frio
[INFO] Compiling 259 source files with javac [debug release 8] to target/classes
[INFO] Compiling 268 source files with javac [debug release 8] to target/test-classes
[WARNING] Tests run: 59960, Failures: 0, Errors: 0, Skipped: 14
[INFO] BUILD SUCCESS
KAN-13 código Maven: 0
```

A rodada foi `20261120T150800719Z-a24ed681244a469e80a93be9467c11b1`. As saídas locais ficam sob `resultados/KAN-13/598dfc163b8b410fb3bb8794521206ec8dcec82a/<id-da-execucao>/`. O SHA-256 da árvore exportada é `d9d3736b176743f464afe2787a607d41b547c6ef49df5c7d92d2b0ef78a064eb`.

## Conferência dos XML

Os 228 arquivos `surefire/TEST-*.xml` registram `user.timezone=UTC`. O caso `DurationFormatUtilsTest#testFourYears`, que falhou no fuso local da KAN-9, passou no contêiner. O XML registrou 4,196 s para esse caso.

| Contagem nos XML | Total |
| --- | ---: |
| Elementos `/testsuite/testcase` | 59.960 |
| Elementos `/testsuite/testcase/skipped` | 14 |
| Elementos `/testsuite/testcase/failure` ou `/testsuite/testcase/error` | 0 |
| Soma dos atributos `/testsuite/@tests` | 59.676 |

`TEST-org.apache.commons.lang3.compare.ComparableUtilsTest.xml` e `TEST-org.apache.commons.lang3.ValidateTest.xml` declaram `tests="0"` e contêm, respectivamente, 70 e 214 elementos `testcase`. A diferença de 284 explica o desvio entre a soma dos atributos e o resumo do Maven. Esse detalhe afeta a conferência de cobertura da KAN-17.
