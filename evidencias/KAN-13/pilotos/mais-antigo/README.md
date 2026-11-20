# Piloto da revisão mais antiga

O clone de referência resolveu `921c1b4e09ed7b6900ad7243cffb33b373980cc5^{commit}` para `921c1b4e09ed7b6900ad7243cffb33b373980cc5`. É a posição 1 do [recorte da KAN-10](../../../KAN-10/commits.csv), com `commons-parent` 88 e versão `3.19.1-SNAPSHOT`.

A inspeção com `git show <sha>:src/test/java/org/apache/commons/lang3/StringUtilsTest.java` confirmou a presença de `StringUtilsTest#testReverse_String`, o mesmo método [executado isoladamente na KAN-9](../../../KAN-9/resultados/utc/string-utils.log).

## Resultado de 20 de novembro de 2026

O [comando do piloto](../../README.md#reprodução-e-integração) verificou o SHA exato e exportou a árvore para o contêiner. O Maven resolveu as dependências necessárias a partir de cache frio, compilou o código e os testes e executou 1 caso, com 0 falhas, 0 erros e 0 ignorados. Maven e executor retornaram 0. A rodada levou 84,562 s de ponta a ponta.

O `maven.log` preservou as linhas abaixo.

```text
KAN-13 cache Maven inicial: frio
[INFO] Compiling 259 source files with javac [debug release 8] to target/classes
[INFO] Compiling 267 source files with javac [debug release 8] to target/test-classes
[INFO] Running org.apache.commons.lang3.StringUtilsTest
[INFO] Tests run: 1, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
KAN-13 código Maven: 0
```

O relatório `TEST-org.apache.commons.lang3.StringUtilsTest.xml` contém a propriedade `user.timezone=UTC` e o caso `org.apache.commons.lang3.StringUtilsTest#testReverse_String`, com duração de 0,043 s. A rodada foi `20261120T150615596Z-2d06695aa11d40d7b8ba85f640fbfb1b`. As saídas locais ficam sob `resultados/KAN-13/921c1b4e09ed7b6900ad7243cffb33b373980cc5/<id-da-execucao>/`. O SHA-256 da árvore exportada é `4e89aae29613b869701b42fb784822100da6b82c24d2339fc1631e643b9bcdfe`.

Esse piloto cobre o início da suíte e um método. O resultado da suíte completa nessa revisão será medido pela KAN-14.
