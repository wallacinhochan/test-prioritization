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
- **Métrica:** mutantes detectados dentro de 25%, 50% e 75% do tempo-base T0 (média histórica das revisões de treino), com o overhead de treino e ranking somado ao relógio. O máximo observável é 15 de 16.
- **Regra de decisão** (fixada antes da execução): orçamento principal de 50%; a estratégia precisa superar a baseline; desempate pelo menor posto médio da primeira detecção e depois pelo menor overhead.

### Resultado

Mutantes detectados somados nos 4 folds (média ± desvio entre sementes):

| Modelo | Estratégia | 25% | 50% | 75% | Posto médio 1ª detecção | Overhead (ms) |
|---|---|---|---|---|---:|---:|
| RF | Baseline | 13,0 ± 1,22 | 15,0 | 15,0 | 67,7 | 542 |
| RF | **Ponderação** | **15,0 ± 0,00** | 15,0 | 15,0 | 60,4 | 475 |
| RF | Oversampling | 14,2 ± 0,45 | 15,0 | 15,0 | 50,2 | 1.009 |
| RF | Undersampling | 11,2 ± 1,79 | 14,8 | 15,0 | 71,8 | 131 |
| RF | SMOTE | 14,0 ± 0,00 | 15,0 | 15,0 | 56,1 | 1.057 |
| KNN | **Baseline** | **15,0** | 15,0 | 15,0 | 58,4 | 67 |
| KNN | Oversampling | 12,4 ± 0,89 | 14,2 | 15,0 | 60,4 | 68 |
| KNN | Undersampling | 15,0 ± 0,00 | 15,0 | 15,0 | 65,9 | 14 |
| KNN | SMOTE | 12,8 ± 1,10 | 14,4 | 15,0 | 61,0 | 81 |

### Decisão

- **Random Forest: ponderação.** Detectou 15,0 de 15 em 25% em todas as sementes (baseline: 13,0), sem criar linhas nem aumentar o overhead. Oversampling e SMOTE ficaram abaixo e dobram o overhead; undersampling foi o pior.
- **KNN: sem balanceamento.** Oversampling e SMOTE pioraram o resultado (12,4 e 12,8 contra 15,0).
- **Ressalva.** Pela regra literal (orçamento de 50%), nenhuma estratégia supera a baseline, porque todas saturam em 15 de 15. A escolha da ponderação se apoia no orçamento de 25%, examinado **depois** de ver essa saturação. É uma decisão posterior aos resultados.

## 4. Resultado na etapa 3 (`piloto.py`)

Foram executados o `piloto.py` (RF sem balanceamento, `base-3`) e o `piloto_balanceado.py` (RF ponderada; KNN sem balanceamento, `bal-3`), na mesma coleta. Posição em que cada mutante é detectado na validação (posição 50, 4.653 métodos; menor é melhor):

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
python escolher_balanceamento.py --dados dados --saida registro-balanceamento --sementes 5
```

Leva alguns minutos. Gera `por_fold.csv`, `resumo.csv`, `execucoes.csv` e `decisao.json` em `registro-balanceamento/`. O `decisao.json` registra a regra literal; a recomendação por modelo está na seção 3.

### Gerar o dataset balanceado

```powershell
# um dataset por estratégia
python balancear_dataset.py --dados dados --saida dados-balanceados
# só a estratégia escolhida (treino_balanceado.csv)
python balancear_dataset.py --dados dados --saida dados-balanceados --estrategia ponderacao
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
- A comparação usa uma única regra de tempo-base e um orçamento principal de 50%, fixados antes da execução; a escolha final da ponderação usou o orçamento de 25% e é, como dito, posterior aos resultados.