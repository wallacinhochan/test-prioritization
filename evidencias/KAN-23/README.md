# KAN-23 — Replay serial sob orçamento

O avaliador consome os seis CSVs da KAN-15 0.1.0 e um manifesto de proveniência. A população e as ordens T1–T3 vêm de artefatos congelados. A referência usa ordem auditada, completude, tempo de parede, configuração comparável e publicação anterior ao corte. O avaliador associa o oráculo atual pelo par SHA e identidade do método e usa a ordem global observada no T0.

## Entradas e saída

- O manifesto declara `contract_version` e `data_kind`. Em `references`, indexe por SHA o identificador da tentativa T0 (`attempt`), sua publicação (`available_at`, ISO 8601 UTC) e a identidade da configuração comparável (`configuration`). Inclua nessa identidade o ambiente, o intervalo de parede, o escopo de suíte e a política de cache.
- Em `targets`, indexe por SHA elegível o instante ISO 8601 UTC `cutoff`, a mesma identidade de configuração e `startup` por cenário, com `duration_ms` e `source_ref`. Inclua preparo e custos de runner que possam ser debitados no início do replay serial. Use medições sem sobreposição. Custos distribuídos entre métodos exigem uma linha do tempo de eventos.
- Registre `selection_ref` para seleção completa e `ranking_refs` para cada ranking fechado, inclusive para conjuntos vazios. As referências devem demonstrar completude, versão e congelamento prévio. T0 requer uma execução completa e posições globais observadas.
- A saída para a KAN-26 tem um registro por SHA, cenário e percentual com a proveniência do limite, a tentativa atual, custos e treinamento em campo próprio. Cada evento do prefixo registra o horário acumulado de conclusão e o desfecho. Um prefixo vazio tem valor `[]`. Um corte indisponível tem valor `null` e um motivo em `gap`. Uma lacuna afeta também um corte exatamente no instante em que ela começa, pois um método desconhecido poderia ter duração zero.

## Fixture controlada

Os SHAs, métodos, tempos e falhas em [fixtures](fixtures/) são sintéticos. A fixture reproduz a tabela KAN-24 com T0 histórico de 103 ms e cortes de 25, 51 e 77 ms. Para o primeiro alvo falta referência. Para o segundo, os três antecedentes mais próximos são descartados por incompletude, publicação posterior ou configuração incompatível. As linhas de resultados e rankings estão fora da ordem de execução. O treinamento de 100 ms aparece à parte.

Na raiz do repositório, execute `python -B evidencias/KAN-23/simular.py evidencias/KAN-23/fixtures` para gerar o JSON e `python -B -m unittest discover -s evidencias/KAN-23 -v` para conferir os cortes.

## Validação física na KAN-28

1. Fixe a configuração e o corte de disponibilidade por SHA. Arquive a tentativa T0 histórica escolhida e congele a seleção e os rankings vindos da KAN-19–22 antes de consultar o oráculo atual.
2. Em cada cenário serial, confira a ordem aplicada pelo runner. Use relógio monotônico a partir do início do executor e registre preparo, seleção, features, inferência, início e fim de cada invocação e o fechamento dos relatórios. Meça treinamento à parte. Preserve custos entre métodos nos tempos dos eventos.
3. Agregue invocações por método segundo a KAN-17 e confronte métodos concluídos, falhas e instantes de conclusão em cada corte. Registre divergências e lacunas. Se a execução física for paralela, derive o prefixo pelos instantes observados no relógio comum.
4. Antes de calcular as métricas principais, confirme a cobertura comum dos quatro cenários por limite, a ordem global observada no T0 e a completude das medições comparáveis. O lote KAN-16 citado pela KAN-24 carece de ordem global, tem durações ausentes e contém zero falhas naturais. A fixture demonstra a regra de corte e usa apenas valores sintéticos.
