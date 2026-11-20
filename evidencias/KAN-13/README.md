# KAN-13 — Ambiente experimental do Apache Commons Lang

A referência aprovada para os pilotos é JDK 21.0.11, Maven 3.9.11 e UTC. A [KAN-9](../KAN-9/README.md) obteve 59.960 casos, sem falhas nem erros e com 14 ignorados, usando Microsoft Build of OpenJDK em Windows 11. Esse resultado é a referência histórica para comparar a suíte no contêiner. [Cartão KAN-13](https://cin-team-test-prioritization.atlassian.net/browse/KAN-13)

## Pilotos

| Revisão | Verificação aprovada | Evidência |
| --- | --- | --- |
| `598dfc163b8b410fb3bb8794521206ec8dcec82a` | Suíte completa passou. 59.960 casos, 14 ignorados, 0 falhas e 0 erros. | [Âncora da KAN-9](pilotos/ancora/README.md) |
| `921c1b4e09ed7b6900ad7243cffb33b373980cc5` | SHA exato conferido, dependências resolvidas, código e testes compilados e um método aprovado. | [Posição 1 da KAN-10](pilotos/mais-antigo/README.md) |

A seleção foi conferida no [CSV da KAN-10](../KAN-10/commits.csv) e os dois SHAs foram resolvidos no clone local com `git rev-parse '<sha>^{commit}'`.

## Reprodução e integração

Faça o [bootstrap da imagem e da fonte](../../infra/commons-lang/README.md#bootstrap). Os comandos abaixo são para PowerShell na raiz do repositório de pesquisa, com `$fonte` apontando para o clone do Commons Lang.

```powershell
# Suíte completa da âncora
./infra/commons-lang/executar.ps1 -Fonte $fonte -Sha 598dfc163b8b410fb3bb8794521206ec8dcec82a -Saida ./resultados/KAN-13

# Piloto de um método na revisão mais antiga
./infra/commons-lang/executar.ps1 -Fonte $fonte -Sha 921c1b4e09ed7b6900ad7243cffb33b373980cc5 -Saida ./resultados/KAN-13 -Teste 'StringUtilsTest#testReverse_String'
```

- **KAN-14.** Para o T0, use a chamada sem `-Teste` com o SHA da revisão, na ordem da KAN-10. A segunda chamada acima cobre a verificação inicial da posição 1. A execução da suíte completa nessa posição pertence à coleta histórica.
- **KAN-17.** Os XML estão em `resultados/KAN-13/<sha>/<id-da-execucao>/surefire/TEST-*.xml`. Use os IDs registrados nos relatórios dos pilotos. Na mesma pasta da rodada, `ambiente.json` contém o SHA verificado, o ID da imagem e o código de saída. A conferência da âncora encontrou 59.960 elementos `testcase` em 228 XML. Dois relatórios com `tests="0"` contêm 284 casos ao todo. [Detalhes dos XML da âncora](pilotos/ancora/README.md#conferência-dos-xml)

## Decisões aprovadas

- Usar Eclipse Temurin 21.0.11 em Linux/amd64 com Maven 3.9.11 e UTC. A KAN-9 usou o fornecedor Microsoft e o Windows. O piloto da âncora mede se o resultado da suíte é preservado nessa mudança de ambiente.
- Preparar a fonte com `git archive` do SHA confirmado. O contêiner descartável recebe a árvore versionada e mantém isolados o build, as configurações do Maven e os arquivos de trabalho.
- Começar com cache Maven vazio em cada piloto e nas rodadas medidas da KAN-14. A duração de ponta a ponta inclui a resolução de dependências. As versões do JDK e do Maven são fixadas na imagem, e o acesso ao Maven Central continua necessário.
- Executar `StringUtilsTest#testReverse_String` na posição 1. O teste já passou isoladamente na KAN-9 e a inspeção da árvore confirmou sua presença na revisão mais antiga.

## Inspeção do ambiente

- `docker version` confirmou Docker Desktop 4.70.0 com cliente 29.4.0, contexto `desktop-linux` e servidor Linux/amd64. A sessão padrão do sandbox recebeu acesso negado ao pipe do Docker. Fora do sandbox, a consulta funcionou. `docker image ls --digests` mostrou que o daemon ainda não tinha imagens locais.
- `docker info` registrou 16 CPUs e 8.212.643.840 bytes de memória disponíveis no daemon. Os pilotos usaram os recursos disponíveis do Docker Desktop, sem cotas específicas por contêiner.
- `docker buildx imagetools inspect eclipse-temurin:21.0.11_10-jdk-noble` retornou o manifesto Linux/amd64 `sha256:d435e5eb685fa668f894f20710bfc12608ec65f8509fec480da3f278f2382081`, fixado no [Dockerfile](../../infra/commons-lang/Dockerfile). O build confirmou `/tmp/maven.tar.gz: OK`, `javac 21.0.11` e Maven 3.9.11. [Checksum do Apache](https://archive.apache.org/dist/maven/maven-3/3.9.11/binaries/apache-maven-3.9.11-bin.tar.gz.sha512)
- Os pilotos usaram o ID local `sha256:6e15bf7fd834e6998883afacb56e4b6de6b180fff899bf3fb0474840f5ac93d6`. A saída do Maven registrou Eclipse Adoptium 21.0.11, Maven 3.9.11, locale `en_US`, UTF-8 e Linux/amd64 com kernel `6.6.87.2-microsoft-standard-wsl2`.
- Na inspeção das alternativas, as tags `mcr.microsoft.com/openjdk/jdk:21.0.11-ubuntu` e `mcr.microsoft.com/openjdk/jdk:21.0.11-mariner` retornaram `not found`. A Microsoft publica um pacote Linux x64 para esse patch. [Versões anteriores do Microsoft Build of OpenJDK](https://learn.microsoft.com/en-us/java/openjdk/older-releases)

## Limites e verificações

- O tempo de ponta a ponta inclui downloads, inicialização do contêiner e coleta dos relatórios. A rodada UTC da KAN-9 reutilizou cache e rodou em Windows com locale `pt_BR`. As durações das rodadas servem para rastrear as execuções em seus respectivos ambientes.
- A fonte exportada omite o diretório `.git`. O build registrou `scmBranch: UNKNOWN_BRANCH`. O SHA analisado vem da verificação do Git antes da exportação e consta em `ambiente.json`.
- O executor rejeitou um SHA inexistente antes de iniciar o Docker, retornou 1 e preservou o diagnóstico em `ambiente.json` e `maven.log`.
- Em um repositório temporário de controle, um teste JUnit 4 chamado `ControleTest#falhaEsperada` produziu uma falha por asserção. A chamada ao executor com o SHA do controle retornou 1, preservou `BUILD FAILURE` no log e copiou `TEST-ControleTest.xml` com um caso e uma falha. O JSON registrou os códigos do Maven e do executor como 1. O controle usou a mesma imagem Docker e fica fora dos resultados experimentais do Commons Lang.
