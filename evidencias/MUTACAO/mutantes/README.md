# Mutantes e rótulos do piloto

Primeiro gate na posição 26, SHA `04cc0339d6510ffdcb47db4676c34b40ecff6b28`. O diff do primeiro pai altera apenas `org.apache.commons.lang3.LocaleUtils`. As revisões e partições seguem o [protocolo aprovado](../README.md).

## Plano e configuração

1. Exportar a árvore Git limpa e executar `mvn clean test` na imagem KAN-13 `sha256:6e15bf7fd834e6998883afacb56e4b6de6b180fff899bf3fb0474840f5ac93d6`, Linux/amd64, Temurin 21.0.11, Maven 3.9.11 e UTC. Usar um cache Maven inicialmente frio por revisão. [KAN-13](../../KAN-13/README.md)
2. Usar PIT 1.19.4 e o plugin JUnit 5 1.2.3. Executar `pit.dryRun=true` com `+EXPORT`, operadores `DEFAULTS` e nomes exatos de classes de produção do diff. O dry run gera variantes e mede cobertura sem executar testes contra variantes. O exportador integrado grava a classe modificada e `details.txt` por variante no diretório do relatório. O número do diretório serve de localizador. [Dry run e classes alvo](https://pitest.org/quickstart/maven/) · [Exportação](https://pitest.org/faq/) · [Formato do exportador](https://github.com/pitest/export-plugin) · [Compatibilidade JUnit 5](https://github.com/pitest/pitest-junit5-plugin#versions)
3. Ordenar os candidatos por SHA-256 de `tp-mutation-v1` concatenado com a identidade canônica em UTF-8. Deduplicar por classe e SHA-256 do bytecode. Congelar até quatro identidades com hashes e localizadores antes de executar qualquer replay.
4. Recriar uma cópia da árvore compilada para cada execução. Reproduzir as metas JaCoCo e Surefire com as configurações das execuções originais. Comparar o controle completo com a execução intacta reutilizando os binários. Preservar a classe original, os XML, logs, códigos de saída e hashes. Verificar os rótulos da primeira variante repetida e repetir o controle após restaurar o bytecode.
5. Associar invocações pelas regras da [KAN-17](../../KAN-17/README.md). Publicar o gate quando controle, positivo, negativo, repetição e restauração forem verificados. A posição 96 fica com publicação pendente até o congelamento do modelo.

## Estado

Gate da posição 26 em preparação.
