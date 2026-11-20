# KAN-16 — Resultados e durações do T0

A coleta segue o [contrato KAN-15 versão 0.1.0](../KAN-15/README.md), a [regra de identidade da KAN-17](../KAN-17/README.md) e as referências selecionadas pela [KAN-14](../KAN-14/README.md), nas posições 1, 26, 50, 75 e 100 da [auditoria](../KAN-10/commits.csv). O extrator verifica o vínculo com a auditoria por SHA completo e preserva essa ordem no CSV de execuções. [Cartão KAN-16](https://cin-team-test-prioritization.atlassian.net/browse/KAN-16)

## Verificação inicial

A exportação de diagnóstico conferiu os XML já verificados da KAN-14 (posição 1) e da âncora KAN-13 (posição 100), ainda sem inventários de descoberta das respectivas tentativas. O diagnóstico preservou 119.409 registros brutos. [Resumo e hashes](resumo-extremos.json)

| Posição | SHA | XML | Casos | Aprovados | Falhas | Erros | Skips | Parede (ms) | Associadas | Sem associação |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `921c1b4e09ed7b6900ad7243cffb33b373980cc5` | 227 | 59.449 | 59.436 | 0 | 0 | 13 | 291.482 | 0 | 59.449 |
| 100 | `598dfc163b8b410fb3bb8794521206ec8dcec82a` | 228 | 59.960 | 59.946 | 0 | 0 | 14 | 306.912 | 0 | 59.960 |

Os elementos `testcase` reconciliam com o resumo do Maven. Em ambas as revisões, dois XML de fábricas em `StreamsTest` têm `tests="0"` e juntos registram 284 elementos `testcase`. Na âncora, `FastDateParserTest` registra `time="-0.001"` no elemento `/testsuite/testcase[5875]`; a evidência preserva o valor bruto e classifica sua duração como indisponível.

## Reprodução

Use PowerShell 7.5 ou superior na raiz do repositório. A opção de diagnóstico lê apenas as duas tentativas fixadas no CSV do lote.

```powershell
./evidencias/KAN-16/exportar.ps1 -Extremos
```

Depois que a KAN-14 publicar `resultados/KAN-14/execucoes.json` com as cinco referências, a descoberta pode ser executada com o clone do Commons Lang e a imagem da KAN-13. Ela adquire o mesmo bloqueio do lote e verifica a existência das cinco referências antes de iniciar qualquer compilação. A imagem, a árvore exportada e o classpath do Surefire são conferidos. O comando auxiliar só compila e descobre descritores. [Bootstrap da KAN-13](../../infra/commons-lang/README.md#bootstrap)

```powershell
./evidencias/KAN-16/descobrir.ps1 -Fonte $fonte
./evidencias/KAN-16/exportar.ps1
```

A exportação também funciona quando a descoberta só está disponível para parte do lote. Os resultados ficam em `local/lote/`, ignorado pelo Git. O diretório contém `t0_runs.csv`, `t0_results.csv`, `invocacoes.csv`, `xml.sha256` e `resumo.json`, que declara o contrato e registra hashes por artefato. A saída de diagnóstico usa `local/extremos/`. Os logs auxiliares ficam em `local/inventarios/`. Mantenha a linha de `t0_runs.csv` vinculada à linha da KAN-10 pelo SHA. Cada `source_ref` de método aponta para `invocacoes.csv`, com o SHA e o `test_id` codificado para URL. Localize cada invocação pelo arquivo e XPath indicados nessa tabela.

## Critérios de coleta

- A descoberta retrospectiva usa as classes identificadas nos XML da tentativa, os binários recompilados da mesma árvore, a imagem original e o classpath registrado pelo Surefire. Ela sustenta a associação dos resultados observados. A cobertura do inventário para seleção pré-execução fica fora deste fluxo.
- A associação compara a classe binária ou o rótulo de classe descoberto dentro do relatório correspondente, além do método e da assinatura compatível. A chave usa tipos obtidos por reflexão, preserva maiúsculas, classe aninhada e contexto de execução de métodos herdados. Invocações sem origem inequívoca conservam no CSV o nome bruto, o relatório, o XPath e o motivo da lacuna. A cobertura do resumo é por invocação observada.
- O desfecho agrega as invocações associadas com precedência de falha ou erro de teste, seguida de aprovação e skip. O código exige confirmação de falha pelo Surefire e reconciliação com o Maven para aceitar uma referência de T0 com falhas. O manifesto da KAN-14 preserva o histórico de tentativas rejeitadas com seus diagnósticos. Erros de ambiente da tentativa ficam fora da contagem de falhas de teste.
- A duração do método soma segundos decimais das invocações executadas e só então arredonda para milissegundos. Skip integral ou uma medida executada indisponível deixa a célula vazia. Zero medido permanece zero. O tempo de parede é calculado entre início e fim do executor e inclui preparo, Maven e cópia de relatórios. Use o resumo para conferir quantos componentes entraram nos somatórios.
- Os XML não registram sequência global de inícios. O campo `execution_order` fica vazio. A ordenação dos arquivos só estabiliza a exportação e o XPath localiza um elemento dentro do XML.

## Lote completo da Entrega 3

A exportação das cinco referências reconciliou 298.770 invocações com os XML e o Maven. Todas foram associadas ao inventário da revisão e da tentativa. A tabela por método contém 23.280 pares de revisão e método, com 23.224 aprovações, 56 métodos ignorados e zero falhas. [Manifesto da KAN-14](../KAN-14/execucoes.json) · [Resumo completo e hashes](resumo-lote.json)

| Posição | Invocações associadas | Registros por método | Métodos com duração | Métodos sem duração | Soma das durações conhecidas (ms) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 59.449 | 4.649 | 4.638 | 11 | 197.472 |
| 26 | 59.452 | 4.652 | 4.640 | 12 | 177.233 |
| 50 | 59.953 | 4.657 | 4.646 | 11 | 198.620 |
| 75 | 59.956 | 4.659 | 4.648 | 11 | 199.010 |
| 100 | 59.960 | 4.663 | 4.650 | 13 | 192.229 |

Os 58 valores ausentes de duração incluem 56 métodos ignorados e dois métodos afetados por registros negativos nos XML das posições 26 e 100. Os valores brutos ficam no CSV de invocações. A ordem global de início permanece indisponível nos cinco SHAs. A associação cobre todas as invocações observadas no piloto, e a descoberta retrospectiva verifica a identidade para a coleta.

Conferi os SHA-256 dos quatro artefatos exportados, a unicidade das cinco execuções e dos 23.280 pares de SHA e método, as referências por SHA e as contagens por revisão. Os CSVs completos permanecem em `evidencias/KAN-16/local/lote/`. O resumo versionado preserva os totais, os caminhos para os dados brutos e os hashes necessários para verificá-los.
