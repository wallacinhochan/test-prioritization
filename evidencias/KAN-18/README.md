# KAN-18 — Seleção estática T1 no estudo principal

O fluxo usa o primeiro pai e as posições do [recorte KAN-10](../KAN-10/commits.csv), o contrato [KAN-15 v0.1.0](../KAN-15/README.md) e a identidade de método da [KAN-17](../KAN-17/README.md). Reutiliza a descoberta e as funções de inventário, grafo e busca do [piloto de mutação](../MUTACAO/t1/README.md). A decisão da [KAN-12](../KAN-12/README.md) mantém Commons Lang como objeto do estudo e o piloto de mutação como evidência auxiliar.

## Regra de seleção

1. Arquive o SHA alvo e prepare as classes de produção e de teste com Maven `clean test-compile`, o classpath de teste, o POM efetivo, o inventário de métodos do JUnit Launcher e a saída de `jdeps`. A sonda usa descoberta sem executar a suíte. A árvore alvo e o diff desde o primeiro pai são lidos do Git. O seletor recebe somente essas entradas pré-execução.
2. Use como sementes as classes mapeadas no bytecode dos arquivos Java adicionados ou modificados em produção e testes. Use arestas de bytecode, referências lexicais no fonte e a aproximação de supertipo para subtipo de produção do piloto. Busque transitivamente no sentido inverso. A cada raiz de execução corresponde uma rota mais curta e determinística até uma semente quando existe caminho. A seleção inclui todos os métodos da raiz alcançada, com identidades distintas para classes aninhadas, métodos herdados e assinaturas.
3. Se houver alteração sem mapeamento seguro, inclua todo o inventário. Isso cobre recursos, POM e outras configurações, remoções de Java, renomeações vistas como remoção e adição, classes ou referências internas sem resolução e sementes sem caminho até um teste. A exceção explícita é `src/changes/changes.xml`, changelog ignorado na formação de sementes. Se nenhuma semente for mapeada, inclusive em um diff apenas de changelog, vale o fallback integral. Grafo ilegível também leva ao fallback quando houver inventário válido e os arquivos de entrada estiverem presentes. Descoberta incompleta ou inventário inválido impede publicar o conjunto.

O grafo usa granularidade de classe. Homônimos podem ampliar a seleção. Reflexão calculada, despacho por bibliotecas externas e efeitos de estado global podem escapar à análise. Na posição 26, a rota de bytecode verificada foi `BooleanUtilsTest → BooleanUtils → ObjectUtils → StringUtils → LocaleUtils`. Na posição 75, a semente é a própria classe de teste alterada, `FastDateParser_TimeZoneStrategyTest`. Os fallbacks observados no lote cobrem POM e ausência de sementes. Alterações de recursos seguem a mesma regra de caminho sem mapeamento aplicada ao POM e ficaram sem caso real na amostra executada.

## Reprodução

Na raiz do repositório de pesquisa, use PowerShell 7.5+, Node 24, Git, Docker e o clone da KAN-10. Use a imagem fixada pela KAN-13, `sha256:6e15bf7fd834e6998883afacb56e4b6de6b180fff899bf3fb0474840f5ac93d6`, com Linux/amd64, Temurin 21.0.11, Maven 3.9.11, UTC e cache Maven inicialmente vazio por contêiner. A descoberta exige acesso ao Docker e resolução Maven. O script reutilizado enumera raízes `*Test.class` e o JUnit inclui descritores de classes aninhadas. Nos seis SHAs, a inspeção dos fontes encontrou apenas o auxiliar ASM `TestClassBuilder.java` entre os outros padrões usuais do Surefire. Para ampliar a cobertura, confira o POM efetivo e os padrões do Surefire antes de usar o inventário. [Ambiente KAN-13](../KAN-13/README.md) · [Sonda KAN-16](../KAN-16/README.md)

```powershell
$kan18 = './evidencias/KAN-18'
$fonte = Join-Path $env:TEMP 'kan10-commons-lang-598dfc163b8b.git'
$posicoes = 1,2,26,50,75,100
foreach ($posicao in $posicoes) {
    & "$kan18/descobrir.ps1" -Fonte $fonte -Posicao $posicao
    node "$kan18/selecionar.mjs" $posicao $fonte
    if ($LASTEXITCODE -ne 0) { throw "Seleção falhou na posição $posicao" }
}
& "$kan18/verificar.ps1" -Posicoes $posicoes
node --test evidencias/MUTACAO/t1/t1.test.mjs
```

Na verificação registrada, os inventários 26 e 50 vieram das compilações pré-execução já disponíveis em `evidencias/MUTACAO/t1/local/{26,50}`. Foram copiados para `local/entradas/<sha>` com os manifestos de entrada reconstruídos pelo seletor. Os outros quatro foram preparados pelo comando acima. Execute a descoberta e a seleção com os destinos livres. Para repetir a seleção com as mesmas entradas, mova a pasta de saída anterior para outro nome local antes de executar o seletor.

## Conjuntos para T2 e T3

Cada pasta `local/selecao/<sha>` contém `selection.csv` com uma decisão por candidato e `rankings.csv` com os selecionados em ordem ordinal crescente de `test_id`, sensível à capitalização. As prioridades T1 são empatadas, o escore fica vazio e os postos começam em 1. T2 e T3 devem usar exatamente as chaves `(commit_sha, test_id)` de `rankings.csv` e atribuir seus próprios postos. A fase `selection` de `overhead.csv` é compartilhada, com a mesma referência de medição para os cenários que a usariam isoladamente.

`decisoes.json` lista sementes, fallback, rotas e decisões por classe. `manifesto.json` identifica SHA, pai, imagem, fontes e hashes das entradas e saídas. A pasta de saída é publicada após a gravação completa. Arquivos brutos e CSVs completos ficam em `local/`, ignorado pelo Git. [A verificação versionada](verificacao.json) contém as contagens e os hashes para conferir os artefatos locais e as reproduções. Hashes de logs e do overhead identificam a tentativa e podem variar entre execuções.

## Cobertura e overhead

| Posição | Inventário | Selecionados | Motivo principal | Overhead (ms) | Junção T0 |
| ---: | ---: | ---: | --- | ---: | --- |
| 1 | 4.649 | 4.649 | Fallback por diff apenas de changelog | 496 | Chaves iguais |
| 2 | 4.649 | 4.649 | Fallback por `pom.xml` | 539 | Sem T0 completo |
| 26 | 4.652 | 4.648 | Dependências de `LocaleUtils` | 433 | Chaves iguais |
| 50 | 4.657 | 4.653 | Dependências estáticas | 503 | Chaves iguais |
| 75 | 4.659 | 7 | Classe de teste modificada | 522 | Chaves iguais |
| 100 | 4.663 | 4.663 | Fallback por `pom.xml` | 382 | Chaves iguais |

Foram materializados **6/100 SHAs** e conciliados **5/5 T0 completos disponíveis**, equivalentes a **5/100 SHAs** do recorte. A posição 2 foi escolhida para verificar o fallback com uma alteração real de configuração. Para as demais 94 posições, a seleção ainda não foi materializada. Nos cinco pares com T0, o conjunto reteve **18.620 de 23.280 métodos**, redução agregada de **20,02%**. A posição 75 responde por 4.652 das 4.660 exclusões e altera apenas testes. As posições 26 e 50 excluem quatro métodos cada, e o fallback preserva todos nas posições 1 e 100.

O verificador abriu o oráculo da KAN-16 depois de materializar os conjuntos e verificou hashes, unicidade, coerência das decisões, igualdade entre conjunto selecionado e ranking, postos contíguos em ordem ordinal e junção por SHA e método. As cinco primeiras posições da tabela tiveram os mesmos hashes de seleção, ranking, diff e decisões em duas execuções. Os testes existentes passaram, incluindo transitividade por auxiliar e herança e identidade do JUnit. A saída por SHA registra os dois métodos executados e selecionados com duração ausente nas posições 26 e 100. T0 teve zero falhas nos cinco pares. Detecção relativa e antecipação de falhas ficam inaplicáveis nessa amostra.

O overhead mede a duração de parede do seletor, da consulta do primeiro pai até a construção das linhas de seleção e ranking. Inclui diff, leitura dos fontes e das entradas preparadas, grafo, buscas e ordenação. Exclui checkout e arquivamento para a descoberta, compilação, downloads Maven, descoberta JUnit, geração de `jdeps`, gravação e hash de artefatos, junção com T0 e execução dos testes. A janela foi medida em processo Node novo no host Windows/x64, com cache do sistema operacional não controlado. Os números se aplicam ao seletor com entradas prontas. O custo total de T1, o tempo físico da suíte selecionada e os efeitos de ordem e cache seguem sem medição comparável. O tempo de parede do T0 e a duração por método têm escopos próprios.
