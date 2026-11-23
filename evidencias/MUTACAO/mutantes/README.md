# Mutantes e rótulos do piloto

Primeiro gate na posição 26, SHA `04cc0339d6510ffdcb47db4676c34b40ecff6b28`. O diff do primeiro pai altera apenas `org.apache.commons.lang3.LocaleUtils`. As revisões e partições seguem o [protocolo aprovado](../README.md).

## Plano e configuração

1. Exportar a árvore Git limpa e executar `mvn clean test` na imagem KAN-13 `sha256:6e15bf7fd834e6998883afacb56e4b6de6b180fff899bf3fb0474840f5ac93d6`, Linux/amd64, Temurin 21.0.11, Maven 3.9.11 e UTC. Usar um cache Maven inicialmente frio por revisão. [KAN-13](../../KAN-13/README.md)
2. Usar PIT 1.19.4 e o plugin JUnit 5 1.2.3. Executar `pit.dryRun=true` com `+EXPORT`, operadores `DEFAULTS` e nomes exatos de classes de produção do diff. O dry run gera variantes e mede cobertura sem executar testes contra variantes. O exportador integrado grava a classe modificada e `details.txt` por variante no diretório do relatório. O número do diretório serve de localizador. [Dry run e classes alvo](https://pitest.org/quickstart/maven/) · [Exportação](https://pitest.org/faq/) · [Formato do exportador](https://github.com/pitest/export-plugin) · [Compatibilidade JUnit 5](https://github.com/pitest/pitest-junit5-plugin#versions)
3. Ordenar os candidatos por SHA-256 de `tp-mutation-v1` concatenado com a identidade canônica em UTF-8. Deduplicar por classe e SHA-256 do bytecode. Congelar até quatro identidades com hashes e localizadores antes de executar qualquer replay.
4. Recriar uma cópia da árvore compilada para cada execução. Reproduzir as metas JaCoCo e Surefire com as configurações das execuções originais. Comparar o controle completo com a execução intacta reutilizando os binários. Preservar a classe original, os XML, logs, códigos de saída e hashes. Verificar os rótulos da primeira variante repetida e repetir o controle após restaurar o bytecode.
5. Associar invocações pelas regras da [KAN-17](../../KAN-17/README.md). Publicar o gate quando controle, positivo, negativo, repetição e restauração forem verificados. A posição 96 fica com publicação pendente até o congelamento do modelo.

## Reprodução

Na raiz do repositório, use PowerShell 7.5, o clone da auditoria e acesso autorizado ao Docker. Passe `-Fonte` se o clone estiver em outro caminho.

```powershell
$mutantes = './evidencias/MUTACAO/mutantes'
& "$mutantes/executar.ps1" -Posicao 26 -Fase controle
& "$mutantes/executar.ps1" -Posicao 26 -Fase pit
& "$mutantes/manifestar.ps1" -Posicao 26
# Versione os candidatos e o manifesto antes de iniciar os replays.
& "$mutantes/executar.ps1" -Posicao 26 -Fase replay
& "$mutantes/rotular.ps1" -Posicao 26
& "$mutantes/executar.ps1" -Posicao 26 -Fase encerrar
```

O contêiner próprio de cada revisão preserva a árvore compilada de referência. Cada replay recria `/trabalho` a partir dessa árvore, remove relatórios e cobertura anteriores, verifica os hashes da classe original e da variante e executa em novo processo Maven com o fork padrão do Surefire. As metas usam as execuções `prepare-agent` do JaCoCo na versão registrada pelo controle daquela revisão e `default-test` do Surefire 3.5.4. O JaCoCo foi 0.8.13 na posição 26. A execução intacta verifica Java, fuso, classpath, argumentos JVM registrados pelo JaCoCo e o conjunto de invocações com os respectivos desfechos. Os hashes da árvore de testes e dos binários são comparados antes e depois de cada substituição e restauração.

O identificador do mutante concatena classe binária, método, descritor JVM, mutador e índices do PIT, usando `|` entre os campos. A seleção usa o primeiro representante por classe e hash seguindo a ordem do hash com a semente. Também exclui candidatos cujo bytecode tem o hash do original e mutações com mais de um índice. `pos-<posição>/candidatos.csv` e `manifesto.json` preservam a seleção e apontam para os dados em `local/<posição>/pit/`.

## Posição 26

O controle limpo produziu 59.452 invocações em 227 XML, com 59.439 aprovações, 13 skips e zero falhas ou erros. O SHA-256 do arquivo fonte coincide com o registrado pela KAN-14. O controle levou 324,288 s. A primeira tentativa de preparação do PIT terminou antes de lançar o Maven porque o POM histórico usa CRLF. A busca pela seção de plugins passou a aceitar ambos os finais de linha. A tentativa anterior está em `local/26/pit-tentativa-01/`.

A segunda tentativa está em `local/26/pit-tentativa-02/`. A JVM de cobertura do PIT rejeitou `SystemPropertiesTest#testGetJavaAwtHeadless()`, que passou no Surefire. A geração configura `skipFailingTests=true` e `parseSurefireConfig=false` para que o PIT ignore a falha durante o cálculo de cobertura. O descritor `META-INF/maven/plugin.xml` do PIT 1.19.4 documenta que a importação da configuração do Surefire pode sobrescrever a opção. O dry run usa os argumentos JVM fixados em `pit.xml`. Controle e replays continuam com todo o conjunto de testes e a configuração do Surefire, incluindo o teste em questão.

Na variante 3, o Surefire registrou um erro de teste e omitiu a mensagem textual `There are test failures` no encerramento. O classificador passou a aceitar esse formato quando o resumo Maven e os XML reconciliam, a meta Surefire confirma a falha e não há dump ou sinal de falha de infraestrutura. Os XML e os replays originais foram reaproveitados. A primeira classificação ficou preservada em `local/26/resumo-checker-v1.json`.

**Gate aprovado.** O PIT exportou 77 variantes elegíveis em 180,400 s. O [manifesto](pos-26/manifesto.json) foi congelado em `b0652c9` antes do replay. Os quatro replays levaram 749,300 s no total e produziram 18.608 rótulos para 4.652 métodos. A repetição da primeira variante produziu os mesmos rótulos. Com o bytecode original restaurado, os hashes e os desfechos das 59.452 invocações coincidiram com o controle. O [resumo](pos-26/resumo.json) contém hashes, tempos e contagens dos XML por rodada.

| Variante | Falhas induzidas | Aprovações observadas | Desconhecidos |
| ---: | ---: | ---: | ---: |
| 1 | 2 | 4.639 | 11 |
| 2 | 8 | 4.633 | 11 |
| 3 | 1 | 4.640 | 11 |
| 4 | 1 | 4.640 | 11 |
| **Total** | **12** | **18.552** | **44** |

O CSV do gate está em `local/26/rotulos.csv`. Os XML de cada replay estão em `local/26/variante-N/surefire/`. A classe original, os logs Maven e os manifestos de hash ficam nas respectivas pastas em `local/26/`.

## Ocorrências na ampliação

Na posição 15, a sessão de acompanhamento terminou depois da execução do controle. A rodada completa foi recuperada do contêiner, com código 0, 59.451 invocações e os XML originais.

Na posição 42, a primeira rodada restaurada foi interrompida com o daemon Linux do Docker indisponível. O contêiner preservou um log parcial sem resumo final Maven ou XML completos. A tentativa está em `local/42/restaurado-interrompido/`. Após reativar o Docker, a restauração foi executada em uma nova cópia da árvore compilada original. Os quatro replays, a repetição e os demais controles completos foram preservados.

## Revisões publicadas

Cada revisão abaixo tem quatro variantes, controle equivalente ao original, repetição coincidente e restauração do bytecode confirmada. Os resumos versionados registram as referências e os hashes dos CSVs locais.

| Posição | Uso | Falhas induzidas | Aprovações observadas | Desconhecidos | Evidência |
| ---: | --- | ---: | ---: | ---: | --- |
| 15 | Treino | 280 | 18.280 | 44 | [Resumo](pos-15/resumo.json) |
| 26 | Viabilidade e treino | 12 | 18.552 | 44 | [Resumo](pos-26/resumo.json) |
| 42 | Treino | 17 | 18.567 | 44 | [Resumo](pos-42/resumo.json) |
| 50 | Validação | 4 | 18.580 | 44 | [Resumo](pos-50/resumo.json) |
| 96 | Teste final | 6 | 18.598 | 48 | [Resumo](pos-96/resumo.json) |

O [manifesto de variantes da posição 96](pos-96/manifesto.json) foi congelado em `d3cb78b`. A publicação dos rótulos em `f4a9da2` sucedeu o congelamento do modelo em `cbb462b` e a liberação da coordenação em `RELATORIO.md@6e97157d56bdfacb9533944974463ee83306f39c`. O CSV do teste final está em `local/96/rotulos.csv`.

## Consumo pelos modelos

Use as posições aprovadas no [protocolo](../README.md). Para cada revisão, confira `pos-<posição>/resumo.json` e os hashes do manifesto e do CSV local. Junte `rotulos.csv` ao inventário pelo SHA completo e pelo `test_id` da KAN-17. Cada linha é única por `sha`, `mutation_id` e `test_id`. Os campos `controle` e `replay` dão o resultado associado por método.

Conte `induced_failure` como positivo e `pass` como negativo observado. Exclua `unknown` do denominador. O alvo do método por revisão é a fração de positivos entre as observações conhecidas, com alvo ausente se todas forem desconhecidas. Use apenas atributos pré-execução e histórico estritamente anterior. As posições 15, 26 e 42 são de treino, a 50 é de validação e a 96 fica reservada para avaliação final após o congelamento do modelo.

Na posição 96, prepare o controle limpo e congele o manifesto pelo fluxo acima. O replay aguarda o congelamento versionado e a liberação da coordenação. Para o replay, passe `-Fase replay -Congelamento ./evidencias/MUTACAO/modelos/congelamento.json -Liberacao $referenciaDaCoordenacao`. O executor confere a suficiência do treino e da validação e registra o commit, o SHA-256 do congelamento e a referência da liberação no resumo final.
