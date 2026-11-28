# KAN-28 — Validação física da simulação híbrida (revisão 50)

Validação empírica do simulador serial da [KAN-23](../KAN-23/README.md) contra execuções físicas controladas dos quatro cenários (`T0`, `T1`, `T2` KNN e `T3` Random Forest) no Apache Commons Lang. [Cartão KAN-28](https://cin-team-test-prioritization.atlassian.net/browse/KAN-28) · [Orçamentos KAN-24](../KAN-24/README.md) · [Métricas KAN-25](../KAN-25/README.md) · [Dados estruturados](validacao-fisica-50.json)

## 1. Regra de seleção da amostra e ambiente controlado

- **Amostra selecionada:** revisão **50** (`f24c027ff83b90beab2ec28696721200abb4f9e9`), única revisão pré-holdout fora da partição de treino (`15, 26, 42`) que dispõe simultaneamente de seleção congelada DIRTS + expansão direta sem fallback (**416 métodos** em 9 classes raiz, [KAN-18](../KAN-18/congelado-expansao-v1/manifesto.json) @ `ef57715`) e rankings congelados `T1`/`T2`/`T3` com custos de `selection` (`78.575 ms`), `features` (`1,86 ms`) e `inference` (`5,35 ms` T2; `19,41 ms` T3) registrados ([KAN-19](../KAN-19/expansao50-experimental-v1/manifesto.json) @ `a06d381`).
- **Referência técnica de calibração:** revisão **49** (`cc5ecf5db64abf0d2a2f59be16f9dc49a520dca9`), coletada fisicamente no **mesmo host e na mesma imagem** imediatamente antes da revisão 50 para calibrar cortes técnicos de 25%, 50% e 75% sem misturar ambientes. Esta rodada **não** constitui avaliação oficial de orçamento histórico (`official_budget_evaluation = false`).
- **Holdout preservado:** a revisão **96** não foi executada nem consultada.
- **Ambiente fixado (6 contêineres executados em série, sem concorrência):**
  - Imagem `test-prioritization/commons-lang:kan13` (`sha256:7a7650e375c4c3534f0302953449f953e075f656f46d7a2dd2156892384fcc4a`)
  - Base `eclipse-temurin:21.0.11_10-jdk-noble@sha256:d435e5eb685fa668f894f20710bfc12608ec65f8509fec480da3f278f2382081`, Maven `3.9.11`, `linux/amd64`, `TZ=UTC`, cache Maven inicialmente frio (`/maven-cache`), 1 fork, paralelismo JUnit desabilitado.
  - Instrumentação contínua por `System.nanoTime()` ancorado em `/proc/uptime` (resolução 10 ms): `RastroJUnit` para Surefire (`t0-49`, `t0-50`, `t1-surefire-50`) e [`ExecutarOrdenado.java`](ExecutarOrdenado.java) para execução exata método-a-método de `T1`, `T2` e `T3`.

## 2. Resultados das seis execuções físicas em série

| Execução | Modo | Métodos (exec.) | Invocações (conciliadas) | Falhas | Preparo (ms) | Plano JUnit (ms) | Soma métodos (ms) | Overhead framework/inter-método | Parede executor (ms) | Largura âncora (ms) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `t0-49` | Surefire | 4.657 (4.646) | 59.953 (59.953) | 0 | 74.700 | 209.635,1 | 201.860,7 | 7.774,4 ms (3,85%) | 293.900 | 16,00 |
| `t0-50` | Surefire | 4.657 (4.646) | 59.953 (59.953) | 0 | 73.970 | 208.800,2 | 201.228,2 | 7.572,0 ms (3,76%) | 292.540 | 20,39 |
| `t1-surefire-50` | Surefire (9 classes) | 416 (412) | 51.172 (51.172) | 0 | 72.240 | 83.849,0 | 77.891,9 | 5.957,1 ms (7,65%) | 162.480 | 19,41 |
| `t1-ordenado-50` | Launcher ordenado (8 trocas) | 416 (412) | 51.172 (51.172) | 0 | 88.180 | 61.664,9 | 53.658,2 | 8.006,8 ms (14,92%) | 150.010 | 15,33 |
| `t2-ordenado-50` | Launcher ordenado (75 trocas) | 416 (412) | 51.172 (51.172) | 0 | 86.320 | 72.413,6 | 64.495,3 | 7.918,4 ms (12,28%) | 158.900 | 14,02 |
| `t3-ordenado-50` | Launcher ordenado (178 trocas) | 416 (412) | 51.172 (51.172) | 0 | 80.040 | 74.940,6 | 66.526,1 | 8.414,5 ms (12,65%) | 155.160 | 19,74 |

- **População, invocações e desfechos:** **100% de concordância** (`416/416` métodos, `51.172/51.172` invocações, `412 pass` e `4 skip`, `0` divergências de desfecho e `0` lacunas de reconciliação).
- **Redução física medida (T1 Surefire vs. T0 na revisão 50):** apesar da redução de **91,07% em quantidade de métodos** (`416 / 4.657`), as 9 classes selecionadas concentram **85,35% das invocações** (`51.172 / 59.953`). A redução física no plano JUnit foi de **59,84%** (`208,8 s → 83,8 s`); no tempo de parede sem seleção foi de **44,46%** (`292,5 s → 162,5 s`); e no tempo total **com o overhead de seleção DIRTS + expansão (`78.575 ms`)** foi de **17,60%** (`292,5 s → 241,1 s`).
- **Fidelidade de ordem:** `t1/t2/t3-ordenado-50` executaram **100% (416/416)** na ordem congelada. Em contraste, `t1-surefire-50` coincidiu em apenas **3 de 412 posições** com a ordem T1 congelada (**Spearman ρ = 0,3914**), pois o Surefire/JUnit 5 agrupa por classe e aplica ordenação própria, sem suporte à intercalação entre classes necessária em `T2` (75 trocas) e `T3` (178 trocas).

## 3. Quantificação de discrepâncias: execução física vs. simulação serial

### Durações por método (412 métodos executados comuns contra T0-50 = `96.754,2 ms`)

| Comparação | Soma física (ms) | Diferença soma (ms / %) | Mediana abs. por método (ms) | P90 abs. (ms) | P95 abs. (ms) | Máx. abs. (ms) | Pearson r | Spearman ρ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `T1 Surefire` vs. `T0-50` | 77.891,9 | −18.862,3 (−19,50%) | 0,472 | 2,715 | 5,487 | 15.674,1 | 0,9763 | 0,6378 |
| `T1 ordenado` vs. `T0-50` | 53.658,2 | −43.096,1 (−44,54%) | 0,285 | 1,943 | 8,516 | 21.291,6 | 0,9225 | 0,4734 |
| `T2 ordenado` vs. `T0-50` | 64.495,3 | −32.258,9 (−33,34%) | 0,306 | 2,545 | 7,802 | 16.899,9 | 0,9457 | 0,3902 |
| `T3 ordenado` vs. `T0-50` | 66.526,1 | −30.228,1 (−31,24%) | 0,326 | 2,651 | 6,924 | 18.930,9 | 0,9608 | 0,4241 |

**Diagnóstico das diferenças de duração:**
1. A mediana da diferença por método é submilissegundo (`0,285–0,472 ms`) e a correlação linear é alta (`r = 0,92–0,98`); quase toda a diferença acumulada se concentra em poucos métodos parametrizados pesados (em especial `FastDateParserTest`, com até `15,7–21,3 s` de variação).
2. **Fator de confusão identificado (JaCoCo):** o `mvn surefire:test` do Commons Lang ativa `jacoco:0.8.14:prepare-agent`, enquanto o runner ordenado direto executou sem o agente JaCoCo — o que explica a parcela adicional de aceleração entre `T1 Surefire` (`−19,5%`) e `T1 ordenado` (`−44,5%`).
3. **Efeito real de ordem / trocas de classe:** comparando apenas execuções do mesmo runner ordenado sem JaCoCo, intercalar classes elevou a soma das durações dos mesmos 412 métodos de `53,66 s` (`T1`, 8 trocas) para `64,50 s` (`T2`, 75 trocas, `+20,2%`) e `66,53 s` (`T3`, 178 trocas, `+24,0%`).

### Cortes de orçamento calibrados por `T0-49` (`293.900 ms` → `25% = 73.475 ms`, `50% = 146.950 ms`, `75% = 220.425 ms`)

Comparação da quantidade de métodos concluídos entre o **físico** (com incerteza `/proc/uptime` verificada — `0` métodos incertos na fronteira em todos os 12 cortes) e o simulador [`KAN-23/simular.py`](../KAN-23/simular.py) sob dois modelos de `startup`: **Modelo A** (`prepare_ms` apenas) e **Modelo B** (`plan_origin_mid_ms` = preparo + inicialização do runner até o início do plano):

| Corte (ms) | Cenário | Físico concluídos | Simulado Modelo A (`Δ`) | Simulado Modelo B (`Δ`) |
| --- | --- | ---: | ---: | ---: |
| **25%** (73.475) | T0 / T1 / T2 / T3 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 (`0`) | 0 / 0 / 0 / 0 (`0`) |
| **50%** (146.950) | **T0** | **1.424** | 1.430 (`+6`) | **1.424 (`0`)** |
| **50%** (146.950) | T1 / T2 / T3 | 0 / 0 / 0 | 0 / 0 / 0 (`0`) | 0 / 0 / 0 (`0`) |
| **75%** (220.425) | **T0** | **4.224** | 4.265 (`+41`) | 4.265 (`+41`, `+0,97%`) |
| **75%** (220.425) | **T1** | **410** | 410 (`0`) | **410 (`0`)** |
| **75%** (220.425) | **T2** | **344** | 320 (`−24`) | 320 (`−24`, `−6,98%`) |
| **75%** (220.425) | **T3** | **332** | 332 (`0`) | **332 (`0`)** |

### Tempo total (RQ1: Modelo B vs. conclusão física do plano + overhead externo)
- `T0`: simulado `292.540 ms` vs. conclusão física do plano `290.560 ms` (`+0,68%`, diferença corresponde à cópia de relatórios `1.690 ms`).
- `T1`: simulado `263.568 ms` vs. físico ordenado `228.532 ms` (`+15,33%`, conservador).
- `T2`: simulado `261.716 ms` vs. físico ordenado `237.429 ms` (`+10,23%`, conservador).
- `T3`: simulado `255.457 ms` vs. físico ordenado `233.696 ms` (`+9,31%`, conservador).

## 4. Decisão sobre adequação da simulação híbrida

**Veredito:** **`adequada_com_restricoes_explicitas`** para o estudo no recorte de Commons Lang, condicionada às seguintes regras operacionais na **KAN-29** e na análise **KAN-30/KAN-31**:

1. **Incluir inicialização do runner no `startup` (Modelo B obrigatório):** o `startup` da KAN-23 deve somar o preparo (`prepare_ms`) e a inicialização do runner até o início do plano (`runner_init`), eliminando o viés sistemático visto no Modelo A (`+6` métodos em T0 a 50%).
2. **Reportar margem de erro de framework e variação por ordem:** a simulação serial ignora `~3,8%` de overhead de framework em T0 Surefire (gerando `+0,97%` de erro em métodos concluídos a 75%) e não modela o acréscimo de `20–24%` na duração dos métodos causado por trocas frequentes de classe em `T2`/`T3` nem diferenças de instrumentação (como JaCoCo). Diferenças pequenas entre cenários ou próximas da fronteira de um corte não devem ser interpretadas como ganhos conclusivos sem verificação de sensibilidade.
3. **Alinhar instrumentação ao comparar fisicamente:** em eventuais novas medições físicas com runner ordenado direto, incluir a mesma política de agente JaCoCo do T0 (ou desabilitá-lo uniformemente em todos os cenários) para eliminar o viés de `−19,5%` vs. `−31%..−44%`.
4. **Explicitar o efeito do cache Maven frio nos cortes de 25% e 50%:** com cache frio (`~74 s`) e seleção de `78,6 s`, cortes de 25% (todos os cenários) e 50% (`T1–T3`) resultam em prefixos vazios válidos (`0` métodos) tanto na execução física quanto na simulação.
5. **Limite quanto a falhas naturais:** como a revisão 50 apresentou **0 falhas naturais** em T0, a adequação comprovada cobre população, ordem, desfechos `pass`/`skip` e modelagem de tempo/prefixos; efeitos dependentes de ordem sobre falhas reais (flakiness ou poluição de estado) permanecem como ameaça documentada na [KAN-31](../KAN-31/ameacas-validade.md).

## 5. Reprodução e testes

Na raiz do repositório, com Docker Linux ativo (`test-prioritization/commons-lang:kan13`), clone bare `../KAN-10-upstream.git` e JARs JUnit Platform 1.13.4 no `.m2`:

```powershell
$python = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
& $python -B evidencias/KAN-28/executar_validacao.py rodada-nova
& $python -B evidencias/KAN-28/comparar.py evidencias/KAN-28/local/rodada-nova --saida evidencias/KAN-28/local/rodada-nova/comparacao.json
& $python -B -m unittest discover -s evidencias/KAN-28 -v
```

Os arquivos brutos de `rodada-v1` permanecem em `evidencias/KAN-28/local/rodada-v1/` (ignorado pelo Git); o manifesto consolidado versionado está em [`validacao-fisica-50.json`](validacao-fisica-50.json).
