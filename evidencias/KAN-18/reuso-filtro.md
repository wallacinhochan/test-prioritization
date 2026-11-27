# KAN-18 — Reuso de estado DIRTS e filtro da expansão

A base do estudo é `f4a25e96e7f2a6d74171ecbb80e8fd29863196e8`. A branch local `investigacao/KAN-18-reuso-filtro` parte de `52b0102`, que registra o diagnóstico anterior. Os [critérios](criterios-reuso-filtro.md) foram fixados no commit `0f74e5f`, antes da leitura dos rótulos da rodada complementar.

## Reuso cronológico do estado DIRTS

O trecho termina na posição 50, que já tem medição física da própria expansão. As posições 48, 49 e 50 são uma cadeia de primeiro pai verificada no Git bare.

| Papel | Posição | SHA |
|---|---:|---|
| Inicialização | 48 | `913225106ac80fdf01e5b0bbfe42991d424f2642` |
| Primeiro alvo | 49 | `cc5ecf5db64abf0d2a2f59be16f9dc49a520dca9` |
| Segundo alvo | 50 | `f24c027ff83b90beab2ec28696721200abb4f9e9` |

O Docker executa Linux/amd64 com Maven 3.9.11 e Temurin 21.0.11+10, imagem `sha256:fad87a144128c905f9ba915f61c03abe436372c2c6e26a02a18984369c42a4ea`, DIRTS `62efcec2f909f93fffdd4ae1da24b0aee1071749`. Ambos os braços usam o mesmo cache Maven semeado como origem, com cópias próprias e fuso UTC. O braço incremental transfere somente `.dirts` entre árvores Git novas, checa o SHA do pai e o manifesto de hashes antes da seleção e sela o estado resultante. O DIRTS calcula exclusões por classe. A saída de inclusões é validada no universo das classes-raiz do inventário JUnit, inclusive quando o plugin também lista classes aninhadas. O primeiro arranque foi interrompido para corrigir essa projeção. Os resultados usam a repetição completa após a correção.

A medição contabiliza extração de fonte, etapas DIRTS, validação leve sempre executada, compilação, inventário, jdeps, expansão, Maven `test` e coleta de XML quando aplicáveis. A inicialização é registrada à parte. A preparação comum do ambiente e a criação dos tarballs antecedem os relógios. Controles sem alteração, reconstruções isoladas e injeções de falha são verificações do experimento e ficam fora dos totais de produção e de T0.

| Posição | Métodos T0 | Métodos DIRTS | Métodos na expansão | Invocações T0 | Invocações na expansão | Reuso em regime | T0 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 49 | 4.657 | 295 | 295 | 59.953 | 304 | 112,133 s | 356,991 s |
| 50 | 4.657 | 72 | 416 | 59.953 | 51.172 | 236,484 s | 310,550 s |
| **Total** | **9.314** | **367** | **711** | **119.906** | **51.476** | **348,617 s** | **667,540 s** |

As quatro execuções Maven terminaram sem falhas ou erros. O Surefire reportou 13 invocações ignoradas em cada T0, nenhuma na expansão da posição 49 e seis na expansão da posição 50. Métodos são IDs únicos do inventário por revisão. Invocações incluem parametrizações e as ocorrências ignoradas reportadas pelo Surefire. A posição 50 teve 416 métodos em nove classes-raiz e repetiu o hash da expansão anterior.

A inicialização tomou **118,754 s**. Com ela, o reuso somou **467,370 s**, uma economia de **200,170 s (30,0%)** frente ao T0 medido nos mesmos SHAs. Em regime, a economia foi de **318,924 s (47,8%)**. A inicialização representa **59,377 s por alvo** quando rateada pelos dois. A economia de 244,858 s no primeiro alvo cobriu a inicialização. Na posição 50, o ganho incremental foi de **74,066 s**, abaixo do custo de uma inicialização do tamanho observado. Uma mudança no perfil da sequência pode alterar a amortização.

| Etapa | Posição 49 | Posição 50 |
|---|---:|---:|
| DIRTS incremental | 40,212 s | 35,549 s |
| Compilação, inventário e jdeps | 54,608 s | 42,067 s |
| Maven test da expansão e coleta de XML | 16,640 s | 157,909 s |
| Maven test do T0 e coleta de XML | 356,812 s | 310,287 s |

A etapa Maven da expansão reaproveita a compilação feita para o inventário no mesmo alvo. Os totais incluem essa compilação, a extração Git e as demais etapas cobradas. Houve uma observação física por braço e alvo. O recorte de dez revisões do filtro permanece o do estudo publicado.

Nos dois alvos, os IDs do DIRTS incremental coincidiram com os IDs do DIRTS reconstruído a partir do primeiro pai, com 295 métodos na posição 49 e 72 na 50. Os controles sem alteração retornaram zero. Na posição 50, os 72 IDs também coincidiram com o ranking da integração, e os 416 IDs da união coincidiram com o hash anterior. Os selos incluem grafo, checksums e mapeamento de unidades de compilação. A injeção de pai divergente, estado ausente e estado adulterado foi rejeitada. A reconstrução real do estado para o SHA 50 passou na checagem, em 93,736 s medidos fora do custo do fluxo normal.

Em uma execução com Maven instrumentado, a reconstrução indisponível e o diff marcado como incompatível encaminharam a `mvn test` sem filtro de classe. O controle verificou os argumentos dessa chamada. A suíte completa foi executada no braço físico T0.

A soma de registros `<testcase>` confirmou o total do log Maven nas quatro execuções. Os dois T0 apresentaram a mesma divergência de XML. `ComparableUtilsTest` e `ValidateTest` declararam zero no atributo `tests`, embora listassem 70 e 214 casos, respectivamente. Os totais acima contam os registros e foram confirmados pelo resumo Maven.

**Parecer do reuso.** Manter o reuso como variante experimental. Os dois alvos confirmaram equivalência e ganho de tempo na sequência observada. A amostra tem dois alvos consecutivos e uma medição por braço. Os controles verificam a recuperação e o encaminhamento do fallback para os casos injetados. O recorte ainda não mede a frequência de reinicializações nem a preservação de detecções em uma sequência mais longa.

[Resultados, fases e hashes](reuso-resultado.json) · [Verificação do fallback](fallback-reuso.json)

## Filtro conservador de comentários e formatação

O filtro compara objetos Git com o scanner do javac da imagem do piloto. Ele autoriza suprimir a expansão quando todos os arquivos efetivos são modificações de Java regular, os tokens têm a mesma grafia e ordem e as marcas de depreciação reconhecidas pelo javac coincidem. O changelog modificado conserva o tratamento do seletor existente. Entradas incertas e mudanças de código continuam no fluxo de expansão. Os controles léxicos do filtro cobrem comentários, espaços, literais, formação de operadores, depreciação documental, escapes Unicode e erro léxico. As sete saídas coincidiram com o esperado. As duas execuções do congelamento produziram arquivos idênticos. O manifesto foi commitado em `77312a7`, antes da leitura dos rótulos. A rodada valida os primeiros pais, as contagens e listas disponíveis e os hashes da expansão anterior, do jdeps e dos dois CSVs do replay.

| Posição | Métodos DIRTS | Métodos com expansão | Métodos com filtro | Decisão |
|---:|---:|---:|---:|---|
| 4 | 0 | 1.018 | 1.018 | Incerteza por escapes Unicode no arquivo |
| 11 | 48 | 48 | 48 | Tokens distintos |
| 26 | 50 | 56 | 56 | Tokens distintos |
| 39 | 13 | 31 | 31 | Tokens distintos |
| 46 | 0 | 17 | 0 | Equivalente |
| 50 | 72 | 416 | 416 | Tokens distintos |
| 64 | 0 | 26 | 0 | Equivalente |
| 75 | 7 | 7 | 7 | Tokens distintos no teste alterado |
| 96 | 51 | 112 | 112 | Diff inclui adição de teste |
| 100 | 4.663 | 4.663 | 4.663 | Fallback integral por configuração |
| **Total** | **4.904** | **6.394** | **6.351** | **−43 pares revisão–método** |

O filtro preservou 4/4 detecções na posição 26 e 3/3 na 50, como a expansão. O DIRTS puro preservou 4/4 e 2/3. O quarto mutante rotulado na posição 50 ficou sem detector observado no T0. Os rótulos disponíveis cobrem 26 e 50, ambas com os mesmos conjuntos antes e depois do filtro. As posições 46 e 64 demonstram redução da seleção. A disponibilidade de rótulos impede medir diretamente a preservação nesses dois pares. O piloto do filtro mede métodos e detecções observadas. Invocações Surefire e tempo de parede foram medidos apenas no piloto cronológico.

**Parecer do filtro.** Manter como variante experimental. A regra elimina a ampliação na formatação e Javadoc de 46 e 64. Seu requisito de segurança para escapes Unicode mantém integralmente a ampliação no caso que motivou a rodada, na posição 4. A classificação também se limita às propriedades léxicas verificadas e ao build deste recorte.

[Manifesto congelado](filtro-congelado.json) · [Resultados do replay](filtro-resultado.json)

## Reprodução

Na raiz do worktree local, em PowerShell, com acesso ao Docker Linux e usando pastas de saída novas:

```powershell
$d = 'evidencias/KAN-18'
python -B "$d/preparar-reuso.py" ../KAN-10-upstream.git "$d/local/reuso-49-50-v2"
python -B "$d/consolidar-reuso.py" "$d/local/reuso-49-50-v2" ../KAN-18-checkout
python -B "$d/verificar-fallback-reuso.py" "$d/local/reuso-49-50-v2" "$d/local/fallback"
python -B "$d/validar-filtro.py" congelar ../KAN-18-checkout ../KAN-10-upstream.git "$d/local/filtro"
python -B "$d/validar-filtro.py" rotular ../KAN-18-checkout "$d/local/filtro"
```

Os três arquivos de validação anterior foram preservados no worktree original e copiados para a branch com os mesmos SHA-256 no momento da cópia. Os logs brutos, os XMLs e as listas congeladas completas ficam sob `evidencias/KAN-18/local/`. A branch contém scripts, critérios e resultados consolidados.

| Arquivo original | SHA-256 verificado |
|---|---|
| `validacao-expansao.md` | `a66eebb1debcfaee5908fd6c39f3282907b13241e2d09bdf5c330c0de03046fc` |
| `validacao-expansao.json` | `c8a07c9fcc9800aaec74656f3d57900759c989a46b67e81ff8235fb6e78e0bc5` |
| `validar-expansao.py` | `5e216a21492499dd0a1163d93571c384f562c59e64f4210f8c2543155384f375` |
