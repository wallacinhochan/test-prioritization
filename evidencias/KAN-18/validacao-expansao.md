# KAN-18 — Validação da expansão por dependências diretas

Hipótese diagnóstica. À lista do DIRTS, somar todos os métodos JUnit nas classes de teste com dependência direta de bytecode para uma classe Java de produção alterada no diff contra o primeiro pai. Preservar a seleção integral já adotada para alterações de configuração. A regra é a mesma aplicada na investigação da posição 50.

A amostra é a das dez revisões da comparação publicada, escolhida antes deste diagnóstico. Os conjuntos foram congelados a partir do Git, do inventário JUnit e do `jdeps` antes de ler os rótulos. Foram conferidos os pares de SHAs, os conjuntos de IDs quando há ranking da integração e os hashes dos dois CSVs do replay. Na revisão 26, os insumos DIRTS foram regenerados em Docker Linux e os 50 IDs coincidiram com o piloto. Duas execuções reproduziram as contagens e os hashes dos conjuntos. Os três testes do piloto passaram.

| Revisão | T1 anterior | DIRTS | Expansão direta |
|---:|---:|---:|---:|
| 4 | 4.647 | 0 | 1.018 |
| 11 | 48 | 48 | 48 |
| 26 | 4.648 | 50 | 56 |
| 39 | 4.653 | 13 | 31 |
| 46 | 17 | 0 | 17 |
| 50 | 4.653 | 72 | 416 |
| 64 | 4.654 | 0 | 26 |
| 75 | 7 | 7 | 7 |
| 96 | 4.659 | 51 | 112 |
| 100 | 4.663 | 4.663 | 4.663 |
| Total | 32.649 | 4.904 | 6.394 |

Nas cinco revisões com mudanças de código de produção além de comentários e formatação, a expansão passou de 234 para 663 pares revisão–método. O T1 anterior selecionava 18.661. A revisão 4 acrescenta 1.018 métodos por uma mudança de Javadoc. Esse resultado motiva examinar um filtro pré-execução para mudanças comprovadamente não funcionais em uma rodada separada.

O CSV do replay permite avaliar a preservação nas revisões 26 e 50. Na 26, DIRTS e expansão preservaram os 4 mutantes detectados pelo T0. Na 50, a expansão recuperou um mutante e passou de 2/3 para 3/3. Um quarto mutante da revisão 50 não teve detector observado no T0. Os rótulos por método da revisão 96 não estavam disponíveis no checkout e ela contribui apenas para a contagem de seleção.

## Custo

Com o grafo já disponível em memória, a expansão mede somente a leitura das arestas por classe e a composição do conjunto de métodos. As medianas de sete repetições ficaram entre 41 e 60 ms quando houve leitura do grafo. Na revisão 26, a soma das durações intactas dos métodos sobe de 21,686 s para 75,905 s ao acrescentar seis métodos. Na 50, sobe de 0,033 s para 74,820 s e recupera uma detecção. Essas somas dos XMLs do replay são medidas retrospectivas e têm escopo diferente do tempo de parede.

A medição física da posição 50 usa o SHA intacto e a imagem Linux DIRTS `fad87a144128`. As duas rodadas usam árvores limpas e cópias separadas do mesmo cache Maven semeado, em sequência. Para a expansão, `-Dtest` recebe as nove classes raiz que contêm exatamente os 416 IDs do inventário. Os XMLs confirmam as nove classes. A suíte completa roda sem esse filtro. Cada relógio cobre apenas a chamada Maven `test`, incluindo compilação e execução. O preparo anterior do DIRTS 2.0 na mesma revisão tinha custo publicado de 302,704 s, com escopo próprio. A comparação física é uma repetição por configuração e usa a imagem reconstruída, com cache semeado.

| Execução | Invocações reportadas pelo Surefire | Ignoradas | Falhas ou erros | Tempo de parede |
|---|---:|---:|---:|---:|
| T0 | 59.953 | 13 | 0 | 369,003 s |
| Expansão | 51.172 | 6 | 0 | 286,252 s |

A chamada Maven da expansão economizou 82,751 s (22,4%). Das 51.172 invocações, 48.151 vieram de duas classes de `FastDateParser`, que somaram 193,53 s no relatório. O preparo DIRTS medido em outra rodada, sozinho, excede a economia observada. Por isso, o resultado não demonstra ganho de ponta a ponta para o fluxo atual com estado DIRTS novo por par. Um estado reaproveitado pode mudar o custo e precisa de medição própria. Logs e protocolo da medição estão em `local/tempo-expansao-50/`.

**Parecer:** manter a expansão direta como variante experimental. Ela preservou 7/7 mutantes detectados pelo T0 nos dois SHAs avaliáveis, contra 6/7 do DIRTS puro. A aprovação para o fluxo principal depende de confirmar a preservação em mais revisões e medir a economia líquida com estado reaproveitado, além de tratar o aumento de seleção em mudanças de documentação.

## Reprodução

Na raiz do worktree de investigação:

```powershell
python -B evidencias/KAN-18/validar-expansao.py ../KAN-18-checkout ../KAN-10-upstream.git
```

[Arquivo de resultados](validacao-expansao.json) · [Comparação de origem](https://github.com/wallacinhochan/test-prioritization/blob/f4a25e9/evidencias/KAN-18/estudo-reducao-t1.md)
