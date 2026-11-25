# Dados para comparar o balanceamento

A coleta reproduziu mutações do Apache Commons Lang. As falhas são induzidas.
Treine nas posições 15, 26 e 42 e compare as estratégias na posição 50.

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
