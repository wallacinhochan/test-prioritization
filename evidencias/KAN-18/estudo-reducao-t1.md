# KAN-18 — Redução da seleção T1 no Commons Lang

A métrica é o número de métodos JUnit selecionados por revisão, em relação ao T1 atual. Cada método conta uma vez por revisão, inclusive quando tem várias invocações parametrizadas. O recorte, o T1 usado pelo estudo principal e seus artefatos foram preservados. As rodadas abaixo não executam a suíte.

## Levantamento de ferramentas

| Ferramenta | Como seleciona | Uso neste estudo |
|---|---|---|
| STARTS 1.4 | Dependências estáticas e mudanças no bytecode. Seleciona classes de teste. | Candidato medido no Commons Lang. |
| DIRTS 1.0 | Analisa dependências no fonte por método e consolida a exclusão por classe de teste no plugin Maven. | Candidato medido com `method_level_select` em modo standalone. |
| WALA | Biblioteca de análise de bytecode e grafos de chamadas. | Requer um seletor próprio para unir diff, grafo e inventário JUnit. |
| Ekstazi, HyRTS, OpenClover e SAP Smart Test Picker | Dependem de informações coletadas durante execuções anteriores. O Smart Test Picker usa cobertura por método de teste. | Alternativas para uma rodada que admita coleta dinâmica. |

Fontes primárias. [STARTS](https://github.com/TestingResearchIllinois/starts) · [DIRTS](https://github.com/tum-i4/dirts) · [Consolidação por classe no DIRTS](https://github.com/tum-i4/dirts/blob/62efcec2f909f93fffdd4ae1da24b0aee1071749/dirts-maven-plugin/src/main/java/edu/tum/sse/dirts/mojos/AbstractSelectMojo.java) · [WALA](https://github.com/wala/WALA) · [Ekstazi](https://github.com/gliga/ekstazi) · [HyRTS](https://personal.utdallas.edu/~lxz144130/publications/icse2018.pdf) · [OpenClover](https://openclover.org/doc/manual/latest/maven--using-test-optimization.html) · [SAP Smart Test Picker](https://github.com/SAP/smart-test-picker)

## Amostra e critérios

A amostra dirigida acrescentou as posições 4, 11, 39, 46, 64 e 96 aos quatro pares anteriores. Ela cobre mudanças em `StringUtils`, `EnumUtils`, `MutablePair`, `TimedSemaphore`, `StopWatch`, `TypeUtils`, documentação e formatação Java, mudança isolada em teste e alteração do POM. O resultado é válido para os pares medidos. As posições de documentação e formatação são apresentadas também fora do corte de mudanças funcionais para que não inflem a interpretação deste último.

Cada par usa o primeiro pai do manifesto KAN-10 e o inventário JUnit do alvo. STARTS e DIRTS selecionam classes e a contagem inclui os IDs de método atribuídos a essas raízes pelo mesmo parser do T1. Aplicamos o fallback integral do T1 aos candidatos quando o próprio T1 o registrou para o par. A comparação exige sucesso do comando, zero no controle sem alteração e seleção da classe esperada no controle positivo da posição 75. No controle de um pai anterior à adição de uma classe de teste, essa classe ainda não existe e fica fora da contagem de controle.

Os pilotos usam Linux/amd64, Temurin 21.0.11+10, Maven 3.9.11 e UTC na imagem reconstruída da KAN-13 `sha256:1a9f509b7ddc690a46bed17a8ba381d699eae04821ea325ce29f28175f3fde24`. A primeira tentativa da extensão do STARTS falhou ao resolver dependências do Maven. A repetição semeou o cache de dependências local e fixou o Central como espelho. A cópia isolada do T1 usa o mesmo código e lê o `jdeps` e o inventário preparados na rodada. A identidade da imagem reconstruída difere da original aprovada.

O DIRTS foi compilado do SHA `62efcec2f909f93fffdd4ae1da24b0aee1071749` via `mvn -DskipTests install`. O objetivo foi `edu.tum.sse.dirts:dirts-maven-plugin:1.0:method_level_select -Dstandalone=true`. Na execução sem configuração explícita de `excludesFile`, o DIRTS acrescentou blocos de exclusões ao arquivo `Excludes` do projeto. A comparação lê o último bloco de cada chamada, que descreve a revisão corrente. A rodada com estado contínuo limpa esse arquivo antes de cada chamada e preserva apenas o grafo e os metadados em `.dirts` ao trocar de árvore. O controle positivo da posição 75 foi também confirmado na lista `DIRTS included` emitida pelo plugin.

Scripts e saídas brutas estão em `local/starts-poc/`. Os diretórios `linux-pares-20261124-131107`, `estudo-20261124-134619` e `dirts-20261124-151151` guardam os logs e seleções. `baseline-estudo.ps1` reproduz o T1 na cópia isolada e `comparar.mjs` consolida as contagens e SHAs. [Piloto anterior STARTS](poc-starts.md) · [Identidade de métodos KAN-17](../KAN-17/README.md) · [Manifesto KAN-10](../KAN-10/commits.csv)

## Resultados

| Posição | Alteração | Inventário | T1 atual | STARTS | DIRTS | Rodada DIRTS |
|---:|---|---:|---:|---:|---:|---|
| 4 | Javadoc de StringUtils | 4.651 | 4.647 | 0 | 0 | Independente |
| 11 | Correção em EnumUtils | 4.651 | 48 | 48 | 48 | Estado contínuo |
| 26 | Refatoração de LocaleUtils | 4.652 | 4.648 | 4.640 | 50 | Independente |
| 39 | Novo método em MutablePair | 4.657 | 4.653 | 31 | 13 | Estado contínuo |
| 46 | Javadoc e formatação de TimedSemaphore | 4.657 | 17 | 0 | 0 | Estado contínuo |
| 50 | Suporte a Java 26 | 4.657 | 4.653 | 562 | 72 | Independente |
| 64 | Javadoc de StopWatch | 4.658 | 4.654 | 0 | 0 | Estado contínuo |
| 75 | Alteração isolada em teste | 4.659 | 7 | 7 | 7 | Independente |
| 96 | Correção em TypeUtils e teste novo | 4.663 | 4.659 | 4.651 | 51 | Estado contínuo |
| 100 | POM com fallback integral | 4.663 | 4.663 | 4.663 | 4.663 | Independente |

| Amostra | T1 atual | STARTS | Redução STARTS | DIRTS | Redução DIRTS |
|---|---:|---:|---:|---:|---:|
| Dez revisões | 32.649 | 14.602 | 55,28% | 4.904 | **84,98%** |
| Cinco revisões com alterações no código de produção além de comentários e formatação | 18.661 | 9.932 | 46,78% | 234 | **98,75%** |

O DIRTS selecionou menos métodos que o STARTS nas posições 26, 39, 50 e 96 e empatou nas outras seis. Nas posições 50 e 96, a lista do DIRTS incluiu respectivamente `SystemUtilsTest` e `Lang1792Test`, classes de teste alterada e adicionada. Na posição 75, o hash da lista de sete IDs do DIRTS coincidiu com o do STARTS. A repetição da posição 26 com estado contínuo produziu o mesmo conjunto de exclusões da rodada independente. Todos os controles sem mudanças selecionaram zero classes no STARTS e zero métodos mapeados no DIRTS. O fallback da posição 100 incluiu 4.663 métodos para as duas ferramentas.

**Para reduzir a seleção T1, o DIRTS 1.0 foi a melhor ferramenta medida nesta amostra.** O total conta pares revisão–método e os percentuais usam o T1 como denominador. A amostra dirigida cobre dez dos 100 SHAs e mede tamanho da seleção. A eventual adoção do DIRTS exigiria uma integração que use apenas a decisão da rodada corrente e preserve o fallback por configuração. A integração posterior adota o DIRTS no T1 2.0.0. [Fluxo atual](README.md)

O arquivo `local/starts-poc/estudo-20261124-134619/comparacao.json` contém os SHAs completos, o tipo de rodada, os controles e as contagens antes e depois do fallback. As listas de IDs finais estão ao lado dos logs de cada ferramenta.

[Contagens e SHAs da comparação](comparacao-dirts.json)
