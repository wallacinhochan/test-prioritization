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
python -B evidencias/KAN-22/validar_dirts.py dirts-consumo
python -B -m unittest discover -s evidencias/KAN-22 -v
```

O comando materializa commits.csv, selection.csv, rankings.csv e overhead.csv em local/dirts-consumo/. O [relatório versionado](validacao-dirts.json) registra a cobertura dos 100 commits e os hashes da rodada validada. Use os rankings de replay técnico nas posições 64, 75 e 100, com 26, 7 e 4.663 métodos por cenário. O treino aparece uma vez por cenário na posição 64, primeiro SHA atendido, e fica fora do orçamento de execução. Os tempos locais de extração das features e inferência foram medidos. As três posições têm custo de seleção desconhecido no lote T1. Cortes de orçamento que dependam desse custo permanecem indisponíveis. A junção para simular o orçamento ainda exige os dados T0 e as referências de tempo que a KAN-23 valida.
