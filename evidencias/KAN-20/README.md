# KAN-20 — Ranking T2 com KNN

Na revisão 50 da expansão direta congelada, o KNN reproduziu os escores e postos técnicos dos 416 IDs de T1 em duas execuções, com treino de fixture sem balanceamento. [Regra de features, reprodução e lacuna de treino experimental](../KAN-19/README.md#expansão-direta-congelada-na-revisão-50)

O teste provisório DIRTS roda o KNN com a configuração do piloto e `StandardScaler` ajustado no treino de fixture. Nas posições 50, 75 e 100, o teste verificou 4.742 chaves T2, postos contíguos e desempates ordinais contra T1. Os resultados abaixo pertencem ao replay histórico. [Reprodução, escopo e custos DIRTS](../KAN-19/README.md#dirts-provisório)

Ajuste único de referência para o Apache Commons Lang no [replay técnico inicial](../KAN-19/README.md). O corte de disponibilidade segue a posição KAN-10, ordenada pelo primeiro pai. Este replay demonstra a produção do ranking com as entradas congeladas e antecedência por posição. Sua cobertura é a da publicação atual e os resultados medem ordenação e tempo local, sem avaliação histórica de desempenho ou alteração das partições da pesquisa.

## Entradas e disponibilidade

Os CSVs da KAN-19 são conferidos contra os SHA-256 publicados em `92aff717b2521317966e8e4076afb79a77aa0287`, a mesma referência prevista para T3.

| Entrada | SHA-256 |
| --- | --- |
| `treino_sintetico.csv` | `bdb13c98bbb2bc4ec92d44ddfb2e1ce6146d89b680e1eb048e1a43d6f8a8a20d` |
| `features_inferencia.csv` | `98c77fff5f268ae6717de057ef59d016b28ff4bc5ad7d06bacedf5e502c41661` |

A ordem das colunas é `distancia_rota`, `rota_ausente`, `arestas_lexicais`, `classe_semente`, `comprimento_nome`, `quantidade_parametros`, `classe_aninhada`. O ajuste preserva a ordem física do CSV de treino e usa 13.915 pares SHA e método com alvo conhecido, dos quais 290 têm alvo positivo. Os rótulos sintéticos das posições 15, 26 e 42 estão congelados antes da inferência no replay. O pipeline ajusta `StandardScaler` somente nesse treino e usa o KNN do piloto, com 15 vizinhos, distância euclidiana, pesos uniformes, `kd_tree` e um trabalhador. O fluxo abre somente os CSVs preditivos indicados, a evidência formal de T1 e os metadados versionados. O oráculo T0 e os rótulos dos mutantes de 50 e 96 ficam fora do ajuste e do ranking. [Piloto](../MUTACAO/modelos/README.md)

Os vetores de inferência são estáticos e estão disponíveis após a descoberta e seleção pré-execução no replay. A comparação com o ranking formal confirma a identidade exata `commit_sha × test_id` e a ordem de entrada de cada SHA. A inferência percorre as posições em ordem crescente. Dentro de cada SHA, ordena por escore decrescente e por `test_id` ordinal em unidades UTF-16 nos empates.

| Posição | Métodos T1 | Resultado |
| ---: | ---: | --- |
| 1 | 4.649 | Sem ranking por anterioridade |
| 2 | 4.649 | Sem ranking por anterioridade |
| 26 | 4.648 | Sem ranking por anterioridade. Contribui ao treino sintético |
| 50 | 4.653 | Ranking T2 |
| 75 | 7 | Ranking T2 |
| 100 | 4.663 | Ranking T2 |

O corte inclusivo do treino é 42. As demais 94 posições carecem de T1 formal e de vetores de inferência nessa publicação. As posições 15 e 42 contribuem somente ao treino. SHAs, hashes de T1, cobertura e condições das rodadas constam em [verificacao.json](verificacao.json).

## Overhead e interface para a KAN-22

Cada rodada grava em `local/<rodada>/` o `rankings.csv`, o `overhead.csv` e o `manifesto.json`, com o modelo em `knn.joblib`. O cenário é `T2`. Para integrar à KAN-22, use os nomes de colunas e as chaves da [KAN-15](../KAN-15/README.md). Compare o conjunto do ranking com T1 por SHA antes de qualquer junção ao oráculo. Leia o manifesto para verificar a linhagem dos vetores, a disponibilidade do modelo, os hashes e a cobertura. A KAN-22 poderá usar o mesmo contrato com um evento de ajuste por atualização e associá-lo ao primeiro SHA servido pelo novo modelo.

| Fase | Regra nesta implementação |
| --- | --- |
| `selection` | Reaproveita a duração e a referência originais de T1 uma vez por SHA ranqueado |
| `features` | `unknown`, com duração vazia, pois os vetores foram materializados pela KAN-19 sem aferição dessa fase |
| `inference` | Cronômetro monotônico da conversão dos vetores em memória até a construção das linhas, incluindo escalonamento, `predict` e ordenação |
| `training` | Cronômetro separado para o `fit` do pipeline, associado uma vez ao SHA da posição 50 |

As durações brutas são registradas em ns e exportadas em ms. As janelas medidas excluem leitura, escrita, checagens de hashes e serialização. As rodadas foram executadas em processos novos no mesmo host Windows x64, com um trabalhador e cache do sistema operacional sem controle. As durações são amostras locais por rodada e cobrem apenas as janelas descritas. Como a geração de features ficou sem aferição, essas saídas dão apenas um custo parcial para o orçamento. A janela expansiva cabe à KAN-22.

## Reprodução e testes

Na raiz do repositório, use CPython 3.12.14 e as dependências fixadas no [piloto](../MUTACAO/modelos/README.md). Prepare os CSVs conforme a [KAN-19](../KAN-19/README.md) e mantenha os rankings e overhead de T1 da publicação indicados pela [KAN-18](../KAN-18/README.md). Use nomes de rodada novos.

```powershell
$kanPython = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
$env:PYTHONPATH = "$PWD/evidencias/MUTACAO/modelos/local/deps"
$kan20 = 'evidencias/KAN-20'
$treino = 'evidencias/KAN-19/local/confirmacao/treino_sintetico.csv'
$features = 'evidencias/KAN-19/local/principal-a/features_inferencia.csv'
foreach ($rodada in 'repeticao-a', 'repeticao-b') {
    & $kanPython -B "$kan20/ordenar.py" $rodada --train $treino --features $features
    if ($LASTEXITCODE -ne 0) { throw "Falha na rodada $rodada" }
}
& $kanPython -B "$kan20/verificar.py" repeticao-a repeticao-b --train $treino --features $features --report "$kan20/local/repeticao.json"
& $kanPython -B -m unittest discover -s evidencias/MUTACAO/modelos -v
```

As duas rodadas registradas reproduziram as 9.323 chaves, os postos e os escores, com o mesmo conjunto de T1, ordem contígua e desempate ordinal. As referências dos rankings incluem o diretório da rodada, por isso a comparação de reprodução ignora somente esse campo depois de verificá-lo em cada arquivo. O verificador também conferiu os hashes, a cobertura e as fases de overhead. Os oito testes do piloto passaram.
