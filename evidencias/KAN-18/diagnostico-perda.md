# KAN-18 — Perda de detecção no replay da posição 50

O DIRTS 1.0 selecionou 72 dos 4.657 métodos e preservou dois dos três mutantes detectados pelo T0. O T1 congelado do piloto selecionou 4.653 e preservou os três. O único detector observado de `JavaVersion#get` com `NullReturnValsMutator` foi `org.apache.commons.lang3.JavaVersionTest#testGetJavaVersion()`. Ele está no posto 999 do T1 congelado e ausente no ranking DIRTS. O bytecode do mutante tem SHA-256 `7030e3ed13f6b0ddb6cca4999f628f4b43f0b3021ede848986b743e864f390f6`. O quarto mutante não teve falha induzida observada no T0. Cada mutante tem 11 resultados desconhecidos. O denominador da preservação é três.

O [resultado reproduzível](diagnostico-perda-50.json) registra todos os IDs canônicos, detectores, postos e hashes. O CSV da [entrega do PR #2](https://github.com/wallacinhochan/test-prioritization/blob/f4a25e96e7f2a6d74171ecbb80e8fd29863196e8/evidencias/MUTACAO/modelos/entrega-replay/dados/observacoes.csv) foi verificado pelo objeto Git local do merge e pelo `SHA256SUMS` do PR. A cópia de trabalho Windows coincide após normalização CRLF → LF. A consulta web direta ao PR não retornou seu conteúdo.

## Onde a perda ocorre

- No diff real de `cc5ecf5db64abf0d2a2f59be16f9dc49a520dca9` para `f24c027ff83b90beab2ec28696721200abb4f9e9`, a classe `JavaVersion` ganha a constante `JAVA_26`. O corpo de `get(String)` fica fora dos hunks. O teste detector chama diretamente `JavaVersion.get` e já verificava resultados para versões anteriores e o tratamento de `"26"`. O replay gera mutantes por classe alterada, enquanto o DIRTS usa alterações e impacto no nível de método. A diferença de granularidade permite que o replay altere um método fora dos hunks.
- O controle no pai registra `DIRTS included: []`, a execução alvo termina com sucesso e o `Excludes` bruto já contém `org/apache/commons/lang3/JavaVersionTest.java`. O agregado exclui a mesma classe. O `jdeps` do alvo registra a aresta direta `JavaVersionTest → JavaVersion`. Há dependência observável no nível de classe, e a evidência localiza a exclusão antes da conversão para CSV. A saída disponível não distingue se o DIRTS conhece a aresta de chamada para `get` ou se a aresta simplesmente não é alcançada a partir das sementes de mudança.
- O DIRTS também selecionou `EnumUtilsTest` alegando `testStream() D`, embora o arquivo esteja fora do diff. A saída é evidência de uma divergência adicional no cálculo de mudanças. Atribuir a divergência ao estado do grafo, ao parser Java ou à preparação de insumos requer verificar o grafo e repetir pai/controle/alvo. A perda em `JavaVersionTest` é compatível com o escopo do replay e a granularidade da seleção. O diagnóstico não confirma um defeito no adaptador nem uma falha específica do grafo interno.

## Ajustes diagnósticos

As variantes foram definidas por entradas anteriores aos desfechos do alvo. As sementes são todas as classes de produção Java no diff real. A expansão direta agrega ao DIRTS os métodos de classes de teste no inventário com dependência direta para uma semente em `jdeps`. A transitiva segue o fecho reverso através das classes internas ao projeto, colapsando classes binárias aninhadas na classe externa. O fallback integral usa o inventário. O script fixa os conjuntos e os postos por `test_id` ordinal antes de abrir o CSV de rótulos. Os desfechos entram apenas na interseção final.

| Variante | Métodos | Adicionais sobre DIRTS | Inventário | Preservação no replay |
| --- | ---: | ---: | ---: | ---: |
| DIRTS | 72 | 0 | 1,55% | 2/3 |
| DIRTS + dependência direta | 416 | 344 | 8,93% | 3/3 |
| DIRTS + dependência transitiva | 610 | 538 | 13,10% | 3/3 |
| T1 congelado do piloto | 4.653 | 4.581 | 99,91% | 3/3 |
| Fallback integral | 4.657 | 4.585 | 100% | 3/3 |

A expansão direta põe o detector recuperado no posto 50. Os primeiros detectores dos dois mutantes de `SystemUtils` passam do posto 67 para o 306 na ordem ordinal. Preservação do conjunto e antecipação devem ser avaliadas separadamente. O manifesto original mede 302,704 s para o fluxo de seleção DIRTS, dos quais 302,110 s correspondem ao preparo do estado e às chamadas da ferramenta. Os contadores acima medem carga em métodos. As variantes reutilizaram o `jdeps` salvo e não têm tempo físico de compilação, seleção ou testes medido. O Docker Linux não respondeu a `docker info --format '{{.OSType}}'` porque o pipe `dockerDesktopLinuxEngine` estava ausente.

**Recomendação para Wallace.** Levar a expansão direta a uma rodada diagnóstica predefinida, com verificação de integridade do grafo e do inventário, e avaliar retenção e detecção por orçamento em outros SHAs. Nesta posição ela recuperou o mesmo que a transitiva com 194 métodos a menos. Quando a validação pré-execução indicar insumos indisponíveis ou inconsistentes, testar fallback integral e registrar o gatilho. A evidência de uma posição e três mutantes não estima segurança em regressões naturais. Qualquer promoção de variante ou mudança de protocolo depende da decisão de Wallace.

## Contrato proposto para KAN-19–21

- **KAN-18 → KAN-19.** Uma pasta de rodada por política e SHA com `selection.csv`, `rankings.csv`, `overhead.csv`, `decisoes.json` e `manifesto.json` no contrato KAN-15. Usar `scenario=T1` dentro da rodada. Identificar política diagnóstica, versão, SHA, primeiro pai, hash do recorte e do inventário, fontes e hashes, classes semente, regra de grafo, fallback e motivo, contagens e hash ordenado dos IDs. Registrar motivo e evidência por classe raiz. Preservar uma decisão por método descoberto e a equivalência entre os selecionados e o conjunto do ranking. Associar testes aninhados à classe raiz pelo inventário KAN-17, com validação de mapeamentos ambíguos antes da promoção.
- **KAN-19 → KAN-20/21.** Materializar as sete features em um vetor por `(commit_sha, test_id)` selecionado, com a mesma ordem do ranking T1. Vincular o manifesto à versão e ao hash exatos desse ranking. Para expansão por `jdeps`, registrar distância de rota e arestas lexicais segundo a mesma definição das features KAN-19. Se a rota exigida não estiver disponível, usar a codificação de rota ausente com evidência explícita. Validar a paridade das chaves e a anterioridade dos dados de treino antes de inferir.
- **KAN-20/21.** Produzir T2 e T3 com exatamente o mesmo conjunto de IDs do T1 da própria rodada, postos contíguos e desempate ordinal do contrato. Registrar hashes do T1, features, treino e modelo, último SHA elegível no treino e overhead por fase. Usar `unknown` e duração vazia para fase sem aferição. Juntar os rótulos do SHA somente após congelar os rankings, mantendo métricas diagnósticas em artefato separado dos vetores de inferência.

## Reprodução

Na raiz do worktree de investigação, com o checkout de referência e o Git do Commons Lang acessíveis em diretórios irmãos:

```powershell
python -B evidencias/KAN-18/diagnosticar-perda.py ../KAN-18-checkout/evidencias/KAN-18/local/dirts ../KAN-10-upstream.git
```

O script confere os hashes dos rankings e insumos, a paridade entre seleção e ranking DIRTS, os postos contíguos e a unicidade das observações. O mapeamento das variantes é específico dos artefatos da posição 50. O teste físico, a aferição incremental e a inspeção do grafo interno permanecem pendentes.
