# KAN-22 — Replay com janela expansiva

O replay percorre todos os commits do recorte em ordem de primeiro pai. Por padrão, decide sobre o primeiro ajuste imediatamente antes da posição 11 e volta a decidir nas posições 21, 31 e seguintes. Commits sem T1 contam na cadência. Na decisão de posição p, o prefixo termina em p−1 e um rótulo só pode entrar se tanto o SHA de origem quanto a posição de disponibilidade forem menores que p. Rótulos liberados entre decisões aguardam a próxima atualização. As janelas acumulam todos os exemplos elegíveis anteriores.

Cada decisão registra corte, SHA, contagem de exemplos, fontes de rótulos e janela ativa. A janela exige ao menos os 15 exemplos que o KNN precisa para inferência. Até atingir esse mínimo, ambas as estratégias ficam sem modelo. Depois do primeiro ajuste, uma decisão sem rótulos elegíveis adicionais conserva os dois modelos. O KNN preserva a ordem física do treino congelado e ajusta o StandardScaler dentro de cada janela. A Random Forest usa os mesmos exemplos em ordem de posição e test_id ordinal UTF-16, com os valores brutos. Ambos usam as configurações do piloto. [KAN-20](../KAN-20/README.md) · [KAN-21](../KAN-21/README.md)

## Entradas congeladas

- **commits** usa position e commit_sha da KAN-10. Forneça a sequência completa do recorte, com posições consecutivas a partir de 1.
- **train** usa o formato treino_sintetico.csv da KAN-19, com as sete features na ordem publicada, partition igual a treino e target_synthetic entre 0 e 1 ou vazio. A partição precisa vir da publicação de treino. Mantenha holdouts fora dessa entrada.
- **availability** tem o cabeçalho commit_sha,available_position,source_ref. Registre uma linha por lote de rótulos de um SHA, com a posição em que o lote ficou disponível e uma referência à evidência da liberação. Se houver liberação parcial, use para o lote consolidado a posição em que todos os seus rótulos já estavam disponíveis. SHAs sem evidência de disponibilidade e alvos vazios ficam fora do ajuste. Para o replay hipotético, forneça uma política explícita de liberação na referência.
- **features** usa o formato features_inferencia.csv da KAN-19, com o cabeçalho exato de chaves e features estáticas, na ordem T1 dentro de cada SHA. A execução depende da proveniência pré-execução desses vetores. Nenhum arquivo de T0 entra no replay.
- **selection**, **t1** e **overhead** recebem os CSVs KAN-15 de uma mesma publicação T1. Para saídas por SHA, concatene os arquivos de cada tipo com um único cabeçalho. O overhead contém somente a fase selection de T1 e identifica os SHAs com seleção disponível, inclusive um conjunto vazio. O replay confere a igualdade entre métodos selecionados, população ranqueada e população de inferência, com identidade exata, postos contíguos e ordem de entrada verificada. [KAN-15](../KAN-15/README.md) · [KAN-19](../KAN-19/README.md)

## Saídas e execução

Cada rodada cria um diretório novo em local/ com rankings.csv, overhead.csv, manifesto.json e os modelos ajustados em cada janela. T2 e T3 cobrem o conjunto completo de T1 nos SHAs com modelo ativo e seleção não vazia. O ranking usa escore decrescente e desempate ordinal UTF-16 por test_id. O manifesto registra SHAs sem T1, conjuntos vazios, SHAs sem modelo e SHAs ranqueados, além de hashes das entradas, do código e das saídas.

O cronômetro monotônico mede fit separadamente da inferência. O ajuste inclui o escalonamento do pipeline KNN e começa com matriz e alvos preparados. A inferência inclui conversão dos vetores, predict, ordenação e montagem das linhas. O overhead herda a fase selection e registra features como unknown, pois os vetores já chegam materializados. Para cada cenário, o overhead registra training uma vez, no primeiro SHA efetivamente ranqueado pela janela. Ajustes que não chegam a servir um SHA continuam registrados com seu custo no manifesto. Use apenas selection, features e inference no orçamento de execução.

Use as dependências fixadas no piloto. O comando abaixo usa caminhos de exemplo para entradas preparadas.

```powershell
python -B evidencias/KAN-22/replay.py rodada-a --commits evidencias/KAN-10/commits.csv --train entradas/treino_sintetico.csv --availability entradas/disponibilidade.csv --features entradas/features_inferencia.csv --selection entradas/selection.csv --t1 entradas/rankings.csv --overhead entradas/overhead.csv
python -B -m unittest discover -s evidencias/KAN-22 -v
```

Os testes geram fixtures temporárias e exercitam o CLI e os dois estimadores. As fixtures cobrem anterioridade, liberação tardia, rótulos indisponíveis, decisão sem rótulos novos, ausência de modelo e validação de T1. A rodada com o recorte real depende dos vetores, da publicação T1 correspondente e da evidência de liberação dos rótulos.

## Validação com o DIRTS expandido

A [KAN-22](https://cin-team-test-prioritization.atlassian.net/browse/KAN-22) exige atualização periódica, evidência do corte e medição à parte do ajuste. O validador lê os três lotes DIRTS diretamente dos commits Git identificados no relatório. Confere os hashes dos manifestos e dos CSVs, deriva as três features de assinatura pela política aprovada na KAN-19 e reproduz os 416 vetores da revisão 50. O treino congelado tem 524 alvos conhecidos, dos quais 181 positivos, nas posições 15, 26 e 42. Sua proveniência registra o pacote do PR #2 e os hashes auditados pela KAN-19.

O manifesto da revisão 50 em a06d381 demonstra que os três lotes estavam disponíveis para aquele ajuste experimental. O replay técnico usa esse marco em conjunto para os três lotes. Isso torna a posição 51 a primeira decisão periódica elegível. As decisões em 11, 21, 31 e 41 ficam sem ajuste e as de 61, 71, 81 e 91 reutilizam os modelos de 51. Como a cronologia histórica de liberação permanece sem evidência, o validador também executa o protocolo histórico com a disponibilidade vazia e registra zero rankings históricos. Os rótulos de avaliação da revisão 50 e os rótulos do holdout 96 ficam fora da execução. A posição 96 é mantida somente na cronologia e marcada como excluída. O congelamento fixo da revisão 50 continua disponível em a06d381.

### Consumo na KAN-23

```powershell
python -B evidencias/KAN-22/validar_dirts.py dirts-consumo --ate-lote 03
python -B evidencias/KAN-22/validar_dirts.py dirts-lote04 --ate-lote 04
python -B -m unittest discover -s evidencias/KAN-22 -v
```

O comando `--ate-lote 03` reproduz a validação histórica de três lotes ([`validacao-dirts.json`](validacao-dirts.json)), preservada intacta para compatibilidade com a base `edf1259`: 15 de 100 revisões (11 sem modelo, 3 ranqueadas em 64, 75 e 100 com 26, 7 e 4.663 métodos por cenário, todas com custo de seleção desconhecido, 1 holdout excluído na posição 96 e 85 lacunas).

#### Reconciliação com o lote 04 (18/100 revisões)

O padrão `--ate-lote 04` incorpora o quarto lote congelado da KAN-18 ([`congelado-expansao-lote-04`](../KAN-18/congelado-expansao-lote-04/manifesto.json) no commit `767f08b`), conferindo o hash do manifesto, a linhagem criptográfica em relação à publicação base e aos lotes 02–03, os hashes de saída, a ausência de sobreposição entre lotes e a reconciliação com `disponibilidade.csv`. O [relatório versionado do lote 04](validacao-dirts-lote-04.json) registra:

- **Cobertura nos 100 commits:** 18 revisões congeladas (11 `no_model`, **6 `ranked`**, 1 `excluded_holdout` na posição 96 sem leitura de rótulos) e 82 lacunas (`missing_t1`).
- **Replay técnico pós-decisão 51 (`janela-50`, 524 alvos conhecidos sem balanceamento em 15, 26 e 42):** 5.087 métodos por cenário (`T2` e `T3`) nas posições **58 (75), 59 (75), 60 (241)**, 64 (26), 75 (7) e 100 (4.663). Duas rodadas independentes em CPython 3.12.14 com scikit-learn 1.7.2 reproduziram os mesmos hashes SHA-256 de `commits.csv`, `selection.csv` e `rankings.csv`.
- **Custos medidos para consumo na KAN-23/KAN-29:** as três posições consecutivas **58, 59 e 60** possuem todas as fases de overhead T1–T3 medidas (`selection`: 520.303 ms, 148.021 ms e 151.683 ms; `features` e `inference` medidas localmente). O evento `training` aparece uma vez por cenário na posição **58**, primeiro SHA atendido pela `janela-50`, e permanece fora do orçamento de execução. As posições 64, 75 e 100 mantêm `selection` como `unknown`.
- **Limites preservados:** o exercício histórico com disponibilidade vazia continua produzindo **zero rankings históricos**. A aplicação oficial dos orçamentos na KAN-23/KAN-29 continua condicionada à coleta de T0 instrumentado comparável (com ordem global e referência histórica publicada antes do corte) e à ampliação da seleção T1 nas 82 revisões restantes.
