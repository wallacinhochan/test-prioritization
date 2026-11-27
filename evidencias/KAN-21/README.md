# KAN-21 — Ranking T3 com Random Forest

Na revisão 50 da expansão direta congelada, a Random Forest reproduziu os escores e postos técnicos dos 416 IDs de T1 em duas execuções, com treino de fixture sem balanceamento. [Regra de features, reprodução e lacuna de treino experimental](../KAN-19/README.md#expansão-direta-congelada-na-revisão-50)

O teste provisório DIRTS roda a Random Forest com a configuração do piloto e treino de fixture. Nas posições 50, 75 e 100, o teste verificou 4.742 chaves T3, postos contíguos e desempates ordinais contra T1. Os resultados abaixo pertencem ao replay histórico. [Reprodução, escopo e custos DIRTS](../KAN-19/README.md#dirts-provisório)

Teste técnico inicial de ordenação no Apache Commons Lang, seguindo a sequência de replay por primeiro pai da KAN-10. O corte em 42 corresponde ao último SHA com exemplos sintéticos deste ajuste. As partições do estudo e o reajuste em janela expansiva ficam com a KAN-22. A disponibilidade descrita aqui é a do replay com artefatos preparados. A execução não mede detecção de regressões, qualidade preditiva ou desempenho histórico.

## Entradas e corte

A publicação `92aff717b2521317966e8e4076afb79a77aa0287` fixa os resumos da KAN-19 e a referência do T1 formal. As duas frentes usam os arquivos e a ordem de colunas da KAN-19. O script rejeita divergências de SHA-256 e confere as chaves e a ordem das features por SHA contra os rankings formais da KAN-18. [Dataset KAN-19](../KAN-19/README.md) · [Seleção KAN-18](../KAN-18/README.md)

| CSV | SHA-256 |
| --- | --- |
| `treino_sintetico.csv` | `bdb13c98bbb2bc4ec92d44ddfb2e1ce6146d89b680e1eb048e1a43d6f8a8a20d` |
| `features_inferencia.csv` | `98c77fff5f268ae6717de057ef59d016b28ff4bc5ad7d06bacedf5e502c41661` |

Ajuste com as posições 15, 26 e 42, em posição crescente e `test_id` ordinal crescente dentro de cada revisão. Usamos 13.915 dos 13.948 exemplos de treino, todos com alvo sintético conhecido. O alvo é `induced_failure / (induced_failure + pass)`. O ajuste e o ranking usam apenas os dois CSVs acima como dados de modelo. O processo não abre o oráculo T0 nem os rótulos de mutantes de 50 e 96.

As sete features são, em ordem, `distancia_rota`, `rota_ausente`, `arestas_lexicais`, `classe_semente`, `comprimento_nome`, `quantidade_parametros` e `classe_aninhada`. São vetores estáticos calculados a partir da descoberta e da seleção T1 e já materializados pela KAN-19 antes da inferência. A Random Forest usa os valores sem escalonamento. A configuração do piloto fixa 200 árvores, mínimo de cinco exemplos por folha, todas as features elegíveis por divisão, semente 20261122 e um trabalhador. Os demais parâmetros seguem os padrões do scikit-learn 1.7.2. [Piloto de mutação](../MUTACAO/modelos/README.md)

| Posição formal | Métodos T1 | T3 |
| ---: | ---: | --- |
| 1 | 4.649 | Sem ranking por anterioridade |
| 2 | 4.649 | Sem ranking por anterioridade |
| 26 | 4.648 | Sem ranking por anterioridade |
| 50 | 4.653 | 4.653 |
| 75 | 7 | 7 |
| 100 | 4.663 | 4.663 |

As posições 15 e 42 só entram no treino. A posição 26 também tem seleção formal e aparece na auditoria de cobertura, sem inferência. As outras 94 posições do recorte ainda estão sem seleção formal. A inferência percorre as revisões elegíveis em ordem cronológica, com vetores na ordem de T1. A exportação usa score decrescente, empate por `test_id` ordinal UTF-16 sensível à capitalização e postos de 1 a N por SHA. A identidade do método é preservada no par `(commit_sha, test_id)`.

## Medição e resultados

| Fase ou revisão | Replay A (ms) | Replay B (ms) |
| --- | ---: | ---: |
| Ajuste | 528,039 | 502,188 |
| Inferência 50 | 27,702 | 28,725 |
| Inferência 75 | 5,987 | 6,514 |
| Inferência 100 | 49,614 | 49,360 |

Cada execução usa um processo Windows x64 com CPython 3.12.14, dependências fixadas no piloto, um trabalhador e cache não controlado. O relógio monotônico `perf_counter_ns` mede o ajuste em torno de `fit`, com matriz e alvos já preparados. A inferência inclui a conversão dos vetores disponíveis, `predict`, ordenação e construção das linhas. Ambas as medições excluem leitura e escrita de arquivos, hashes e verificações de contrato. Os CSVs registram milissegundos e o manifesto mantém nanossegundos. São duas medições técnicas no host, sem estimativa de variabilidade nem tempo de ponta a ponta.

O `overhead.csv` herda a fase `selection` com duração, estado e referência de T1. Registra `features` como `unknown`, pois a extração estática dos vetores não tem medição publicada. A conversão dos vetores já disponíveis conta em `inference`. A fase `training` fica separada e é vinculada ao SHA da posição 50, primeiro elegível para o modelo ajustado. O overhead total de execução isolada de T3 permanece sem medida completa. [Contrato KAN-15](../KAN-15/README.md)

## Reprodução e verificação

Na raiz do repositório, prepare os CSVs da KAN-19 e os rankings e custos locais publicados da KAN-18. Use as dependências fixadas no diretório do piloto conforme o seu README. Os nomes de execução devem ser novos.

```powershell
$python = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
$env:PYTHONPATH = "$PWD/evidencias/MUTACAO/modelos/local/deps"
$treino = 'evidencias/KAN-19/local/confirmacao/treino_sintetico.csv'
$inferencia = 'evidencias/KAN-19/local/principal-a/features_inferencia.csv'
foreach ($execucao in 'replay-a', 'replay-b') {
    & $python -B evidencias/KAN-21/ranking.py $execucao --treino $treino --inferencia $inferencia
    if ($LASTEXITCODE -ne 0) { throw "Falha em $execucao" }
}
& $python -B evidencias/KAN-21/verificar.py replay-a replay-b --resumo verificacao.json
```

As duas execuções verificadas tiveram os mesmos 9.323 escores e postos. A verificação confere cabeçalhos, cobertura, chaves comparadas diretamente com T1, desempate, postos contíguos, custos herdados e fases do overhead. O hash comum ignora apenas `source_ref`, que aponta para o manifesto da respectiva execução. Os dois CSVs completos e seus tempos têm hashes próprios. [Verificação das execuções](verificacao.json)

## Interface para a KAN-22

Cada execução publica `local/<execução>/rankings.csv` e `overhead.csv` no contrato KAN-15, com `scenario=T3`. Use `(commit_sha, scenario, test_id)` para rankings e `(commit_sha, scenario, phase)` para overhead. O `manifesto.json` descreve o corte, a primeira posição atendida, as lacunas, o vetor ordenado, hashes, versão, parâmetros e tempos. O modelo `RandomForest.joblib` registra a instância ajustada para o replay.

`rank_revision(model, sha, rows, source_ref)` recebe o estimador já ajustado e linhas da KAN-19 de um único SHA, na ordem T1 e com identidade verificada. Retorna linhas KAN-15 e tempo em nanossegundos. Para cada atualização, a KAN-22 define o próprio prefixo de treino e evento de disponibilidade e pode reutilizar essa função, o vetor `vector(row)` e a configuração `FOREST`. O carregador desta tarefa valida a publicação congelada para o corte 42. Modelos, CSVs e manifestos por execução ficam em `local/`, ignorado pelo Git.

## Verificação conjunta de T1, T2 e T3

A coordenação executou novamente os dois modelos em processos separados, com os CSVs verificados da KAN-19 e a mesma janela de treino. Cada nova execução reproduziu os 9.323 escores e postos da sua execução de referência. Nos SHAs das posições 50, 75 e 100, o conjunto de chaves `(commit_sha, test_id)` de T2 e T3 coincidiu com o ranking T1 formal. Os postos de cada modelo foram contíguos de 1 a N em cada SHA. A verificação se aplica aos rankings do replay técnico. A extração de features ainda carece de aferição para compor o custo completo. [Seleção T1](../KAN-18/README.md) · [Dataset de entrada](../KAN-19/README.md) · [Reprodução T2](../KAN-20/README.md)
