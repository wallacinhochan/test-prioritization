# KAN-18 — Prova de conceito com STARTS 1.4

Em 24/11/2026, o plugin Maven `edu.illinois:starts-maven-plugin:1.4` compilou o Commons Lang e listou classes afetadas com Java OpenLogic 21.0.9 e Maven 3.9.9 em Windows 11. As revisões vieram do manifesto KAN-10. Esta rodada verifica integração inicial e comportamento do seletor nesse ambiente. [Documentação do STARTS](https://github.com/TestingResearchIllinois/starts)

| Revisão KAN-10 | Mudança | Classes listadas no pai sem estado prévio | Classes listadas no alvo com estado do pai |
|---|---|---:|---:|
| 26 | Produção | 236 | 236 |
| 50 | Produção e teste | 236 | 236 |
| 75 | Classe de teste | 236 | 236 |
| 100 | POM | 237 | 237 |

O controle repetiu a seleção no próprio diretório do pai da revisão 26, com os checksums do mesmo SHA e sem alteração de fonte. O STARTS voltou a listar 236 classes e saiu com código zero. Assim, a integração no Windows não demonstrou seleção incremental confiável. A origem do comportamento permanece por verificar. A contagem é de classes listadas, sem conversão para os IDs de método do inventário JUnit.

## Procedimento

1. Exportar o SHA e o primeiro pai do manifesto com `git archive`, em diretórios separados por par.
2. Usar um cache Maven isolado e executar `mvn edu.illinois:starts-maven-plugin:1.4:select -DupdateSelectChecksums=true` no pai. Confirmar que `.starts/deps.zlc` foi gerado.
3. Para o controle, repetir o objetivo no próprio diretório do pai sem a opção de atualização. Para cada alvo, copiar o estado do pai e ajustar apenas o prefixo absoluto de `target/` nas URLs do arquivo para o diretório alvo. A cópia direta do estado aciona o verificador de licenças RAT. Nas rodadas alvo e no controle, usou-se `-Drat.skip=true`.
4. Contar as classes na seção `AffectedTests` dos logs bem-sucedidos. Os logs locais ficam em `local/starts-poc/<posição>/`, em `pai.log`, `corrigido.log` e, na posição 26, `controle-sem-mudanca.log`.

Os tempos Maven incluem compilação, com caches diferentes entre rodadas. O ambiente difere da imagem experimental KAN-13 e a comparação de custo com o T1 permanece indisponível. O próximo critério do piloto é selecionar zero classes no controle sem mudanças, com o estado no mesmo diretório de execução e no ambiente Linux do projeto. Depois disso, cabe validar o mapeamento para métodos e o caso da revisão 75 antes de comparar redução e custo.


## Controle sem mudanças em Linux — 24/11/2026

A imagem original da KAN-13 (`sha256:6e15bf7fd834e6998883afacb56e4b6de6b180fff899bf3fb0474840f5ac93d6`) estava ausente no Docker Desktop. A reconstrução abaixo produziu `sha256:1a9f509b7ddc690a46bed17a8ba381d699eae04821ea325ce29f28175f3fde24`. O Dockerfile preserva a base Temurin por digest e valida o SHA-512 do Maven. A execução confirmou Linux/amd64, Temurin 21.0.11+10, Maven 3.9.11 e UTC. A imagem reconstruída tem identidade distinta da imagem aprovada. [Configuração KAN-13](../../infra/commons-lang/README.md)

```powershell
docker build --platform linux/amd64 --tag test-prioritization/commons-lang:kan18-reconstruida infra/commons-lang
```

No primeiro pai da posição 26 (`a5585689a31f47b3f95808f8666d062e18097707`), as duas chamadas ocorreram em `/pilot` no mesmo contêiner, com o mesmo diretório `target/` e o mesmo estado `.starts/`. O cache Maven privado começou frio e ficou quente na segunda chamada.

```sh
mvn -B -ntp -Dstyle.color=never -Duser.timezone=UTC -Dmaven.repo.local=/maven-cache -Drat.skip=true edu.illinois:starts-maven-plugin:1.4:select -DupdateSelectChecksums=true
mvn -B -ntp -Dstyle.color=never -Duser.timezone=UTC -Dmaven.repo.local=/maven-cache -Drat.skip=true edu.illinois:starts-maven-plugin:1.4:select
```

| Fase | Classes | Saída Maven | Parede (ms) |
|---|---:|---:|---:|
| Preparação do pai e gravação dos checksums | 236 | 0 | 83.770 |
| Controle sem mudanças | 0 | 0 | 7.621 |

Os dois inventários de hashes do bytecode de produção e de teste foram idênticos (SHA-256 do manifesto `378e8a9acea8cc92f81e460ffcb0dd759265437272d7854491f2b5314f56d112`). O controle confirmou seleção incremental nesse ambiente. A diferença em relação ao Windows permanece observacional. Artefatos, script e comandos efetivos em `local/starts-poc/linux-26-20261124-130852/`.


## Controle positivo e pares do recorte

Na ordem 75, 26, 50 e 100, cada par teve um diretório Linux próprio. Os arquivos vieram do clone bare local `KAN-10-upstream.git` e foram selecionados com `git diff --name-only --diff-filter=M <pai> <alvo>`. A exportação inicial usou `git archive --format=tar <pai>`. Após gravar o estado e repetir o controle no pai, sobrepusemos apenas os caminhos modificados com `git archive --format=tar <alvo> -- <caminhos>`, extração e `touch` desses arquivos. Assim, os caminhos absolutos de `.starts/deps.zlc` continuaram válidos. O cache Maven começou frio no primeiro par e foi compartilhado entre os pares no mesmo contêiner. As três chamadas de cada par usaram a configuração acima com `-DstartsLogging=FINE`. Todos os doze comandos Maven de seleção terminaram com código zero.

| Posição | Primeiro pai | Alvo |
|---:|---|---|
| 75 | `9167659d8eec4323d569cebd39381235c098c901` | `bfcaa941b0849956972517c8559c0827c8fe5386` |
| 26 | `a5585689a31f47b3f95808f8666d062e18097707` | `04cc0339d6510ffdcb47db4676c34b40ecff6b28` |
| 50 | `cc5ecf5db64abf0d2a2f59be16f9dc49a520dca9` | `f24c027ff83b90beab2ec28696721200abb4f9e9` |
| 100 | `626e7e93aea200e6910be5597ac30de602649745` | `598dfc163b8b410fb3bb8794521206ec8dcec82a` |

Após selecionar cada alvo, a sonda KAN-16 descobriu os métodos pelo JUnit Launcher sem executar a suíte. As raízes seguem a enumeração do T1 e o mapeamento reutiliza seu parser de inventário. Cada raiz selecionada inclui seus IDs `classe#metodo(tipos)`, inclusive classes aninhadas. Os quatro arquivos `metodos.tsv` têm os mesmos SHA-256 registrados no T1, cuja verificação já conciliou essas chaves com o T0. Na posição 26, sete classes listadas pelo STARTS estavam na enumeração, mas tinham zero descritores JUnit próprios. Nenhuma classe listada ficou fora da enumeração usada. [Verificação do T1](verificacao.json)

| Posição | Classes no pai sem estado | Classes no controle | Classes no alvo | IDs brutos | IDs finais / inventário | IDs T1 | Fallback do piloto |
|---:|---:|---:|---:|---:|---:|---:|---|
| 75 | 236 | 0 | 1 | 7 | 7 / 4.659 | 7 | — |
| 26 | 236 | 0 | 228 | 4.640 | 4.640 / 4.652 | 4.648 | — |
| 50 | 236 | 0 | 16 | 562 | 562 / 4.657 | 4.653 | — |
| 100 | 237 | 0 | 0 | 0 | 4.663 / 4.663 | 4.663 | Integral por `pom.xml` |

- **75.** A única mudança foi em `FastDateParser_TimeZoneStrategyTest.java`. O STARTS listou apenas essa classe, que corresponde aos mesmos sete IDs do T1.
- **26.** A mudança em `LocaleUtils.java` levou à seleção de 228 classes e 4.640 IDs, oito a menos que o T1 em contagem.
- **50.** O STARTS incluiu `JavaVersionTest` e a classe alterada `SystemUtilsTest`. Reteve 562 IDs e excluiu 4.095 do inventário. O T1 reteve 4.653.
- **100.** Somente o `pom.xml` mudou. O STARTS reportou zero classes. A regra externa do piloto aplicou fallback integral para os 4.663 IDs, em linha com o T1.

## Custo da seleção

| Posição | Parede Maven no pai (ms) | Parede Maven no controle (ms) | Parede Maven no alvo (ms) | STARTS no alvo (ms) | Conversão e fallback (ms) | T1 registrado (ms) |
|---:|---:|---:|---:|---:|---:|---:|
| 75 | 77.252 | 8.337 | 23.044 | 518 | 79 | 522 |
| 26 | 26.297 | 8.194 | 23.773 | 518 | 91 | 433 |
| 50 | 25.800 | 7.722 | 21.642 | 434 | 76 | 503 |
| 100 | 28.976 | 8.455 | 7.578 | 561 | 30 | 382 |

A parede Maven inclui inicialização, fases até `test-compile` e execução do objetivo. Para aproximar o escopo da seleção do T1, a coluna STARTS usa o perfil interno `RUN-MOJO-TOTAL`, que começa antes de calcular os testes afetados e termina depois de listar as classes. A conversão foi medida em um processo Node novo no host Windows, da leitura das entradas prontas até a montagem dos IDs finais, com gravação fora da janela. O T1 inclui consulta Git, leitura das entradas preparadas, grafo e construção das linhas de seleção e ranking. As três janelas de seleção excluem compilação, descoberta JUnit e execução de testes. Plataforma, estado preparado e saídas ainda diferem. A amostra tem uma medição por posição e não estabelece vantagem de tempo ou custo total. [Escopo do T1](README.md#cobertura-e-overhead)

Scripts, arquivos Git exportados, logs das fases, listas de classes, inventários e IDs estão em `local/starts-poc/linux-pares-20261124-131107/`. O conversor é `local/starts-poc/mapear.mjs`. A reprodução usa `docker run --rm --platform linux/amd64 --mount "type=bind,source=<diretório-da-rodada>,target=/logs" sha256:1a9f509b7ddc690a46bed17a8ba381d699eae04821ea325ce29f28175f3fde24 bash /logs/rodar.sh`. Após a rodada, use `node evidencias/KAN-18/local/starts-poc/mapear.mjs <diretório-da-rodada> <posição>` para cada par.

O STARTS demonstrou seleção incremental nos controles e no recorte Linux avaliado. A execução JUnit ficou restrita à descoberta, de modo que a retenção de falhas ainda precisa de evidência. Os pares avaliados cobrem arquivos Java modificados e um POM, com lacunas para remoções, renomeações, recursos e mudanças entre contêineres. O piloto WALA era condicionado à falha da seleção incremental neste ambiente. Qualquer mudança no método do estudo principal fica para decisão de Wallace.
