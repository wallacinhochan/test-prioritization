# KAN-29 — Consolidação T0–T3 na janela consecutiva 57–60 (e validação técnica 49–50)

Consolidação reproduzível dos dados brutos e métricas de `T0`, `T1`, `T2` (KNN) e `T3` (Random Forest) no contrato [KAN-15 versão 0.1.0](../KAN-15/README.md), aplicando a regra de orçamento [KAN-24](../KAN-24/README.md), o simulador [KAN-23](../KAN-23/README.md) com **Modelo B de `startup`** (`plan_origin_mid_ms = prepare_ms + runner_init`, definido na [KAN-28](https://cin-team-test-prioritization.atlassian.net/browse/KAN-28)) e o pacote oficial de métricas [`scripts/metricas.py`](../../scripts/metricas.py). [Cartão KAN-29](https://cin-team-test-prioritization.atlassian.net/browse/KAN-29) · [Consolidado versionado](consolidado-58-60.json)

## 1. Cobertura nos 100 commits do recorte KAN-10

- **T1 congelado (DIRTS + expansão direta, 4 lotes):** `18/100` posições (`4, 11, 15, 26, 39, 42, 46, 47, 48, 49, 50, 58, 59, 60, 64, 75, 96, 100`); **82 lacunas**.
- **T0 instrumentado no mesmo host e mesma imagem `kan13` (`sha256:7a7650e375c4...`):** `6/100` posições (`49, 50, 57, 58, 59, 60`); **94 lacunas**. Todas as seis suítes tiveram reconciliação integral de 100% dos casos Maven/XML/rastro (`59.953` em `49, 50, 57` e `59.954` em `58, 59, 60`), **0 falhas naturais**, **13 invocações ignoradas** e `gaps = {}`.
- **Revisões completas T0–T3 avaliadas sob orçamento (25%, 50%, 75%):** `4/100` posições — **conjunto principal consecutivo (`58, 59, 60`, referências `57→58`, `58→59`, `59→60`)** e **validação técnica (`50`, referência `49→50`)**, mantidos em blocos separados.
- **Holdout 96:** preservado fechado (`labels_read = false`, `excluded_from_pack = true`).
- **Disponibilidade histórica dos rótulos:** o replay histórico da KAN-22 com disponibilidade vazia permanece com **0 rankings históricos** (`kan22_historical_ranking_rows = 0`); os rankings `T2`/`T3` de `58–60` usam o marco técnico experimental da `janela-50` (decisão em 51, treino sem balanceamento de 524 alvos conhecidos em `15, 26, 42`).

## 2. Resultados consolidados — Conjunto principal consecutivo (posições 58, 59 e 60)

### RQ1 — Tempo, redução e overhead por fase

| Posição | Cenário | Métodos selecionados / T0 elegíveis | Redução | Execução métodos (ms) | Preparo Modelo B (ms) | Seleção (ms) | Features + Inferência (ms) | Treino separado (ms) | Tempo total (ms) | Falhas T0 / detectadas |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **58** | T0 | 4.647 / 4.647 | 0,00% | 198.160 | 80.773 | — | — | — | **288.780** (parede) | 0 / 0 |
| **58** | T1 | 75 / 4.647 | **98,39%** | 30.968 | 80.773 | 520.303* | — | — | 632.044 (serial) | 0 / 0 |
| **58** | T2 (KNN) | 75 / 4.647 | **98,39%** | 30.968 | 80.773 | 520.303* | 0 + 1 | 3 | 632.045 (serial) | 0 / 0 |
| **58** | T3 (RF) | 75 / 4.647 | **98,39%** | 30.968 | 80.773 | 520.303* | 0 + 6 | 183 | 632.050 (serial) | 0 / 0 |
| **59** | T0 | 4.647 / 4.647 | 0,00% | 200.263 | 84.617 | — | — | — | **294.900** (parede) | 0 / 0 |
| **59** | T1 | 75 / 4.647 | **98,39%** | 31.427 | 84.617 | 148.021 | — | — | **264.065** (serial, −10,5%) | 0 / 0 |
| **59** | T2 (KNN) | 75 / 4.647 | **98,39%** | 31.427 | 84.617 | 148.021 | 0 + 1 | — | **264.066** (serial, −10,5%) | 0 / 0 |
| **59** | T3 (RF) | 75 / 4.647 | **98,39%** | 31.427 | 84.617 | 148.021 | 0 + 7 | — | **264.072** (serial, −10,5%) | 0 / 0 |
| **60** | T0 | 4.647 / 4.647 | 0,00% | 207.179 | 81.890 | — | — | — | **300.950** (parede) | 0 / 0 |
| **60** | T1 | 241 / 4.647 | **94,81%** | 40.080 | 81.890 | 151.683 | — | — | **273.653** (serial, −9,1%) | 0 / 0 |
| **60** | T2 (KNN) | 241 / 4.647 | **94,81%** | 40.080 | 81.890 | 151.683 | 0 + 2 | — | **273.655** (serial, −9,1%) | 0 / 0 |
| **60** | T3 (RF) | 241 / 4.647 | **94,81%** | 40.080 | 81.890 | 151.683 | 0 + 7 | — | **273.660** (serial, −9,1%) | 0 / 0 |

*\*Na posição 58, o custo de seleção (`520.303 ms`) inclui a inicialização fria do estado `.dirts` na âncora 57 (`370.404 ms`). Nas posições 59 e 60, em regime incremental, o custo de seleção foi `148–152 s`, gerando economia líquida estimada de `9,1%` a `10,5%` sobre T0.*

### RQ2 — Métodos concluídos sob orçamentos de 25%, 50% e 75% (cobertura comum 4/4 cenários)

| Posição (Ref. T0) | 25% (ms) — T0 / T1 / T2 / T3 | 50% (ms) — T0 / T1 / T2 / T3 | 75% (ms) — T0 / T1 / T2 / T3 | APFDc natural |
| --- | --- | --- | --- | --- |
| **58** (Ref. 57: 293.180 ms) | 73.295 ms → 0 / 0 / 0 / 0 | 146.590 ms → **1.424** / 0 / 0 / 0 | 219.885 ms → **4.266** / 0 / 0 / 0 | Indefinido (`sem_falhas_na_populacao`) |
| **59** (Ref. 58: 288.780 ms) | 72.195 ms → 0 / 0 / 0 / 0 | 144.390 ms → **1.424** / 0 / 0 / 0 | 216.585 ms → **4.224** / 0 / 0 / 0 | Indefinido (`sem_falhas_na_populacao`) |
| **60** (Ref. 59: 294.900 ms) | 73.725 ms → 0 / 0 / 0 / 0 | 147.450 ms → **1.424** / 0 / 0 / 0 | 221.175 ms → **4.239** / 0 / 0 / 0 | Indefinido (`sem_falhas_na_populacao`) |

- **Bloco separado de validação técnica (posição 50, ref. 49: `293.900 ms`):** redução de `91,13%` (`412 / 4.646` métodos elegíveis), `selection = 78.575 ms`, tempo total estimado `257,0 s` vs. `292,5 s` em T0 (`−12,1%`); em 75% (`220.425 ms`), `T0 = 4.265`, `T1 = 410`, `T2 = 320`, `T3 = 332` métodos concluídos.
- **Evidência auxiliar sintética (separada):** 4 mutantes na revisão 50 (`d2c0e7a:evidencias/KAN-19/avaliacao-expansao50.json`, `3/4` detectados por `T0–T3` e `1/4` indeterminado), mantida fora do oráculo natural T0.

## 3. Reprodução e verificação

Com a imagem `test-prioritization/commons-lang:kan13`, clone bare `../KAN-10-upstream.git`, JARs JUnit Platform 1.13.4 e dependências Python em `evidencias/MUTACAO/modelos/local/deps`:

```powershell
$python = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
$env:PYTHONPATH = "$PWD/evidencias/MUTACAO/modelos/local/deps"
& $python -B evidencias/KAN-29/coletar_t0_janela.py t0-nova --posicoes 57 58 59 60
& $python -B evidencias/KAN-29/consolidar.py evidencias/KAN-29/local/t0-nova --work-dir evidencias/KAN-29/local/consolidado-nova --saida evidencias/KAN-29/local/consolidado-nova/consolidado.json
& $python -B -m unittest discover -s evidencias/KAN-29 -v
```
