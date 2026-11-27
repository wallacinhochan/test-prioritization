# Balanceamento do dataset de treino

Este documento descreve a comparação de estratégias de balanceamento aplicada ao dataset de mutação sintética, a decisão tomada, o resultado na etapa 3 (ranking de testes) e como reproduzir tudo.

## 1. Problema

O alvo de cada método é `induced_failure / (induced_failure + pass)`. No treino (posições 15, 26 e 42), os exemplos são muito desbalanceados:

| Conjunto | Alvo = 0 | Alvo > 0 |
|---|---:|---:|
| Treino (15, 26, 42), dados entregues | 13.705 | 210 |
| Validação (50) | 4.639 | 3 |

Modelos sem tratamento tendem a prever zero para quase tudo. O objetivo foi comparar estratégias de balanceamento do **treino** e escolher uma, sem alterar a validação.

## 2. O que foi feito

| Arquivo (em `evidencias/MUTACAO/modelos/entrega-replay/`) | Função |
|---|---|
| `comparar_balanceamento.py` | Implementa as estratégias, o ranking e a avaliação por orçamento de tempo. |
| `escolher_balanceamento.py` | Roda a comparação (Random Forest e KNN, 4 folds, várias sementes) e grava o registro. |
| `balancear_dataset.py` | Exporta o dataset de treino balanceado. |
| `test_balanceamento.py` | 11 testes de invariantes (opcional). |
| `../criar_piloto_balanceado.py` | Gera `piloto_balanceado.py` a partir de `piloto.py`, para a etapa 3. |
| `registro-balanceamento/` | `por_fold.csv`, `resumo.csv`, `decisao.json`, `execucoes.csv` (saída da comparação). |
| `dados-balanceados/` | `treino_balanceado.csv` e `balanceamento.json` (saída do exportador). |

O `piloto.py` original **não foi alterado**. Os dados de `dados/` também não.

### Estratégias comparadas

| Estratégia | Como balanceia | Treino resultante (zeros / positivos) |
|---|---|---|
| Baseline | Nada. | 13.705 / 210 |
| Ponderação | Peso = zeros/positivos (65,26) nos exemplos com alvo > 0. **Só Random Forest**: o `KNeighborsRegressor` não aceita `sample_weight`. | 13.705 / 210 (com pesos) |
| Oversampling | Positivos reamostrados com reposição até a razão 1:1. | 13.705 / 13.705 |
| Undersampling | Zeros reamostrados sem reposição até 1:1, preservando os positivos. | 210 / 210 |
| SMOTE (regressão) | Positivos sintéticos até 1:1. Cada um interpola features e alvo entre um positivo e um de seus 5 vizinhos positivos. Features inteiras são arredondadas; as categóricas (`rota_ausente`, `classe_semente`, `classe_aninhada`) herdam o valor de um dos pais. Implementação própria (SMOTER), sem `imbalanced-learn`. | 13.705 / 13.705 (13.495 sintéticos) |

Em todas: balanceamento só no treino, alvo contínuo preservado, mesma semente base (20261122) e as 7 características pré-execução.

## 3. Como foi avaliado

- **Modelos:** Random Forest regressora (200 árvores, `min_samples_leaf=5`) e KNN regressor (StandardScaler, 15 vizinhos, distância euclidiana).
- **Folds:** o oficial (treino 15/26/42, teste 50) e três de desenvolvimento (treina em duas das revisões de treino e testa na terceira). Total de 16 mutantes.
- **Sementes:** 5 por estratégia. O KNN baseline é determinístico e rodou uma vez.
- **Métrica:** mutantes detectados dentro de 25%, 50% e 75% da média, por fold, das somas de duração intacta dos métodos selecionados por T1 nas revisões de treino. O relógio inclui balanceamento, ajuste e predição. A ordenação fica fora da medição. O máximo observável é 15 de 16.
- **Regra de decisão** (fixada antes da execução): orçamento principal de 50%; a estratégia precisa superar a baseline; desempate pelo menor posto médio da primeira detecção e depois pelo menor overhead.

### Resultado

Mutantes detectados somados nos quatro folds, com média e desvio amostral entre sementes conforme [resumo.csv](registro-balanceamento/resumo.csv). O KNN baseline teve uma execução por fold, sem desvio estimável.

| Modelo | Estratégia | 25% | 50% | 75% | Posto médio 1ª detecção | Overhead (ms) |
|---|---|---|---|---|---:|---:|
| RF | Baseline | 13,0 ± 0,71 | 15,0 | 15,0 | 66,12 | 599,13 |
| RF | Ponderação | 15,0 ± 0,00 | 15,0 | 15,0 | 54,12 | 637,41 |
| RF | Oversampling | 14,2 ± 0,45 | 15,0 | 15,0 | 50,25 | 1.106,55 |
| RF | Undersampling | 11,4 ± 1,52 | 15,0 | 15,0 | 70,61 | 210,50 |
| RF | SMOTE | 14,6 ± 0,55 | 15,0 | 15,0 | 55,73 | 1.158,27 |
| KNN | Baseline | 15,0 | 15,0 | 15,0 | 49,94 | 112,39 |
| KNN | Oversampling | 12,8 ± 1,10 | 14,4 ± 0,55 | 15,0 | 61,96 | 116,01 |
| KNN | Undersampling | 15,0 ± 0,00 | 15,0 | 15,0 | 66,65 | 20,99 |
| KNN | SMOTE | 12,0 ± 0,00 | 14,0 | 15,0 | 68,86 | 128,01 |

### Decisão

[decisao.json](registro-balanceamento/decisao.json) registra **baseline para Random Forest e KNN**. A 50%, RF baseline e RF ponderada detectaram 15 de 15 mutantes observáveis em todas as cinco sementes. O KNN baseline também detectou 15. A regra exige superar o baseline antes de aplicar os desempates.

A 25%, a RF ponderada passou de **13,0 ± 0,71 para 15,0 ± 0,00**. Todo o ganho veio do fold de desenvolvimento da posição 26. Nas sementes 20261122 a 20261126, o baseline detectou 2, 2, 3, 1 e 2 mutantes, e a ponderação detectou 4 em cada execução. Na posição 50, ambas detectaram 3 em cada semente. O posto médio caiu de 66,12 para 54,12, e o overhead subiu de 599,13 para 637,41 ms. O corte secundário foi usado após observar a saturação no corte principal. [Por fold](registro-balanceamento/por_fold.csv) · [Por semente](registro-balanceamento/execucoes.csv)

Os limites deste replay são exploratórios e medem detecção de falhas induzidas. O [KAN-24](https://cin-team-test-prioritization.atlassian.net/browse/KAN-24) trata da regra comparável entre T0–T3. A referência dessa regra usa o tempo de parede de uma tentativa T0 anterior, completa e disponível no corte, com piso inteiro e custos aplicáveis por cenário. Nos folds de desenvolvimento que avaliam 15 e 26, o treino pode incluir revisões posteriores à revisão avaliada.

O arquivo [treino_balanceado.csv](dados-balanceados/treino_balanceado.csv) é a **exportação SMOTE da comparação**. Seu [metadado](dados-balanceados/balanceamento.json) registra razão 1:1, semente 20261122, 27.410 linhas e 13.495 exemplos sintéticos. O piloto ponderado calcula os pesos diretamente sobre o próprio treino.

## 4. Variante exploratória na etapa 3

Foram executados o `piloto.py` (RF sem balanceamento, `base-3`) e o `piloto_balanceado.py` (variante exploratória com RF ponderada; KNN sem balanceamento, `bal-3`), na mesma coleta. Posição em que cada mutante é detectado na validação (posição 50, 4.653 métodos; menor é melhor):

| Mutante | T1 | KNN | RF baseline | RF ponderada |
|---|---:|---:|---:|---:|
| `SystemUtils.isOsVersionMatch` | 1693 | 196 | 66 | **50** |
| `SystemUtils.isOsMatch` | 1693 | 196 | 66 | **50** |
| `JavaVersion.get` | 999 | **69** | 205 | 150 |
| `SystemUtils.isOsNameMatch` | indeterminado | indeterminado | indeterminado | indeterminado |

T1 e KNN ficaram idênticos nas duas execuções, como esperado. A RF ponderada detectou os três mutantes mais cedo que a RF baseline. A posição "possível" (`primeira_posicao_possivel`) da RF caiu de 52 para 3; isso **não** é melhora: indica que um teste com resultado `unknown` aparece mais cedo no ranking, o que antecipa a incerteza sobre a detecção.

Na coleta usada, o peso calculado foi 80,85 (menos positivos na posição 15 que nos dados entregues).

## 5. Como rodar

### Ambiente

Python 3.12 e as dependências do projeto, mais `pandas`. Exemplo no Windows (PowerShell):

```powershell
python -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install -r evidencias/MUTACAO/modelos/requirements.txt pandas
```

(`requirements.txt`: scikit-learn 1.7.2, numpy 2.2.6, scipy 1.15.3, joblib 1.5.2, threadpoolctl 3.6.0.) Se o venv foi criado com `uv`, instale com `uv pip install --python .\.venv312\Scripts\python.exe -r evidencias/MUTACAO/modelos/requirements.txt pandas`.

### Comparar as estratégias e escolher

Não precisa de Docker, PIT nem da pasta `local/`: usa só `dados/metodos.csv` e `dados/observacoes.csv`.

```powershell
cd evidencias/MUTACAO/modelos/entrega-replay
python escolher_balanceamento.py --dados dados --saida registro-reproducao --sementes 5
```

Leva alguns minutos. Gera `por_fold.csv`, `resumo.csv`, `execucoes.csv` e `decisao.json` em `registro-reproducao/`. O `decisao.json` registra a regra literal; a análise exploratória do corte de 25% está na seção 3.

### Gerar o dataset balanceado

```powershell
# grava um CSV por estratégia em um diretório separado da evidência versionada
python balancear_dataset.py --dados dados --saida exportacao-treino
# exporta a variante ponderada em outro diretório (treino_balanceado.csv)
python balancear_dataset.py --dados dados --saida exportacao-ponderacao --estrategia ponderacao
```

Opções: `--razao 1.0` (positivos/negativos desejado em oversampling, undersampling e SMOTE) e `--seed 20261122`. Os CSVs têm as colunas de `metodos.csv` mais `peso` e `sintetico` (1 nas linhas criadas por SMOTE). Na ponderação, o treino não muda de tamanho: use a coluna `peso` como `sample_weight` da Random Forest.

### Testes

```powershell
$env:DADOS = "dados"
python -m unittest test_balanceamento -v
```

Esperado: 11 testes, `OK`.

### Etapa 3 com o balanceamento

Na raiz do repositório:

```powershell
$m = 'evidencias/MUTACAO/modelos'
python $m/criar_piloto_balanceado.py        # cria $m/piloto_balanceado.py (piloto.py não muda)
python $m/piloto.py congelar base-1         # referência
python $m/piloto_balanceado.py congelar bal-1
```

Use um nome de execução novo a cada vez; os resultados ficam em `$m/local/<execução>/` (`ranking-50.csv`, `deteccao-50.json`, `congelamento.json`). Não rode a etapa `final`, que depende de liberação da coordenação.

**Requisito de proveniência.** O `piloto.py` lê o `resumo.json` do **histórico do Git** e compara o hash de `mutantes/local/<posição>/rotulos.csv` com o do resumo commitado. Por isso a etapa 3 só roda se a pasta `local/` tiver os rótulos exatos dos resumos publicados (peça-a a quem executou a coleta). Se você regenerou a coleta, a posição 15 pode divergir (veja a seção 6); nesse caso, para um teste local, commite o `resumo.json` regenerado numa branch **local e separada**, nunca na branch do PR.

## 6. Limitações

- Há apenas 16 mutantes em 4 revisões e 4 linhas de mutante na validação (3 deles do `SystemUtils`, detectados pelos mesmos testes). Diferenças de uma ou duas posições não são conclusivas por si só.
- Os três folds de desenvolvimento usam revisões de treino: são validação de desenvolvimento, não avaliação final. A posição 96 não foi usada.
- O mutante `ToStringStyle.appendInternal` (`RemoveConditionalMutator_EQUAL_ELSE`, índice 239) da posição 15 é **instável**: numa regeneração da coleta, 118 pares de teste mudaram de rótulo (79 de `induced_failure` para `pass` e 39 no sentido contrário). A causa provável é estado estático compartilhado em `ToStringStyle`, que torna o resultado dependente da ordem de execução. Os rótulos da posição 15 têm, portanto, ruído. As posições 26, 42 e 50 reproduziram os rótulos publicados byte a byte.
- Só foi testada a razão 1:1, extrema para este desbalanceamento (65 vezes mais positivos no oversampling e no SMOTE).
- O SMOTE aqui interpola features quase todas discretas (contagens e indicadores), o que limita o valor da interpolação.
- O KNN não aceita pesos; por isso só a Random Forest usa a ponderação.
- A comparação usa uma única regra de tempo-base e um orçamento principal de 50%, fixados antes da execução; a adoção da ponderação na variante do piloto decorreu da análise posterior do corte de 25%.