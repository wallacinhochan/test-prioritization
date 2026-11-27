# Dados para comparar o balanceamento

A coleta reproduziu mutações do Apache Commons Lang. As falhas são induzidas.
Treine nas posições 15, 26 e 42 e compare as estratégias na posição 50.

## Resultado versionado

A regra prévia de 50% selecionou baseline para RF e KNN. A RF ponderada foi levada à etapa 3 como variante exploratória após a análise do corte de 25%. O arquivo `dados-balanceados/treino_balanceado.csv` contém a exportação SMOTE da comparação. Os resultados por fold e semente, a proveniência dos artefatos e a regra de tempo do replay sintético estão em [BALANCEAMENTO.md](BALANCEAMENTO.md).

## Arquivos

- `dados/metodos.csv` contém uma linha por revisão e método, a seleção T1,
  as sete características pré-execução e a taxa observada de detecção.
  Para treinar, use `particao == "treino"`, `selecionado_t1 == 1` e alvo conhecido.
  O alvo é `induced_failure / (induced_failure + pass)`. Alvo vazio indica falta
  de observações conhecidas. O indicador `alvo > 0` identifica os exemplos
  positivos para ponderação ou reamostragem, preservando a taxa contínua
  como alvo da regressão.
- `dados/observacoes.csv` contém uma linha por revisão, mutante e método.
  Use `label` para identificar quais métodos detectaram cada mutante.
  `unknown` e `ausente` indicam resultados indeterminados.
- `dados/proveniencia.json` identifica imagem, revisão, hashes, partições e
  contagens. Na posição 15, a coleta local registra 203 falhas induzidas.
  O piloto publicado registra 280. A comparação deve usar os rótulos locais
  neste pacote de forma consistente entre as estratégias.

As chaves para juntar as tabelas são `sha` e `test_id`. As durações em
milissegundos somam as invocações associadas a cada método pelos XMLs
Surefire. `duracao_intacto_ms` vem da execução intacta. `duracao_ms` vem
da execução contra o mutante. Contabilize a preparação do ranking no
orçamento de tempo e fixe a regra do tempo-base antes da comparação.
Trate as durações por teste como medidas para avaliação retrospectiva.
Os tempos de overhead do novo pipeline precisam ser medidos na comparação.

Use somente as sete colunas de características do piloto como entrada do
modelo. Rótulos, indicadores derivados do alvo e durações da revisão
avaliada são entradas da avaliação. Aplique o balanceamento apenas ao treino
e preserve os mesmos métodos selecionados em todos os rankings da validação.

```text
distancia_rota, rota_ausente, arestas_lexicais, classe_semente,
comprimento_nome, quantidade_parametros, classe_aninhada
```

## Protocolo proposto para a comparação

A pergunta desta etapa é qual estratégia de balanceamento ajuda a Random
Forest a detectar mais mutantes dentro do orçamento de tempo, em comparação
com o treino original. A Random Forest sem balanceamento é a baseline desta
comparação. A suíte completa (T0) fornece a referência de tempo e de detecção
do experimento de seleção e priorização.

### Prepare os dados

1. Na raiz do repositório, execute
   `(cd evidencias/MUTACAO/modelos/entrega-replay && sha256sum -c SHA256SUMS)`.
2. Em `metodos.csv`, separe as posições 15, 26 e 42 para treino e a 50 para
   validação. Em ambos os conjuntos, use os métodos com `selecionado_t1 == 1`.
   No ajuste, use apenas linhas de treino com alvo conhecido.
3. Use somente as sete características listadas acima para prever a taxa de
   detecção. O modelo produz um escore para cada método. Ordene os métodos
   por escore decrescente e use a mesma regra de desempate por `test_id`
   em todas as configurações. A posição 96 fica fora desta comparação.

### Compare quatro estratégias

| Estratégia | Como ajustar a Random Forest |
| --- | --- |
| Baseline | Use os exemplos de treino com peso uniforme. |
| Ponderação | Aumente o peso de exemplos com `alvo > 0`. |
| Oversampling | Reamostre exemplos com `alvo > 0` com reposição. |
| Undersampling | Reamostre exemplos com `alvo == 0` sem reposição e conserve os positivos. |

Use o mesmo modelo, as mesmas características e os mesmos hiperparâmetros.
Fixe e registre a semente, os pesos e as razões de amostragem. Preserve os
valores contínuos do alvo e aplique as alterações apenas no treino.
Qualquer ajuste feito olhando os resultados da posição 50 deve ser reportado
como validação de desenvolvimento.

### Avalie os rankings sob orçamento de tempo

- Antes da comparação, defina a regra para calcular o tempo-base de T0 a
  partir de informação disponível antes da predição, como medições
  históricas. Use essa mesma referência para os quatro rankings e calcule
  os limites de 25%, 50% e 75%. Fixe qual dos três será o orçamento principal.
- Para cada mutante, cruze o ranking da posição 50 com `observacoes.csv`
  pelas chaves `sha` e `test_id`, filtrando pelo `mutation_id`. Comece o
  relógio pelo overhead de preparação aplicável e acumule `duracao_ms`
  na ordem prevista. Conte o mutante uma vez, quando terminar o primeiro
  teste rotulado como `induced_failure` dentro do limite.
- Registre separadamente os casos em que rótulos desconhecidos impedem
  confirmar a ausência de detecção. Identifique as contagens como resultados
  da simulação retrospectiva sobre falhas induzidas.

### Resultados esperados

Entregue uma tabela com uma linha por estratégia e, para cada orçamento,
o número de mutantes detectados e a diferença em relação à baseline.
Inclua a regra de orçamento, o overhead medido, as configurações e as
contagens de alvos zero e positivos antes e depois do balanceamento.
Use o orçamento principal para indicar qual estratégia teve o melhor
resultado observado. Registre como empate se duas ou mais obtiverem a
mesma contagem.

## Validação e reprodução

Dentro desta pasta, confira os arquivos com `sha256sum -c SHA256SUMS`.
Os CSVs estão prontos para leitura em Python, sem Docker, PIT ou PowerShell.
A geração é opcional e exige os artefatos brutos da nova coleta na máquina
que executou os replays. Da raiz do repositório, depois de instalar esta pasta:

```sh
python3 evidencias/MUTACAO/modelos/entrega-replay/preparar_dados.py . /tmp/dados-replay-novos
```

O exportador verifica os manifestos, as contagens e os hashes locais de
rótulos e XMLs. A posição 96 fica fora da coleta e da validação.
