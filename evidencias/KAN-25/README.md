# KAN-25 — Trade-offs da RQ1

A unidade é o método de teste do Apache Commons Lang. O avaliador trabalha por SHA elegível incluído no manifesto da KAN-23. O JSON lista os elegíveis fora do manifesto e mantém os motivos de indisponibilidade por métrica. A seleção e os rankings devem estar completos e congelados antes de consultar o T0 do SHA avaliado. [KAN-25](https://cin-team-test-prioritization.atlassian.net/browse/KAN-25) · [Protocolo aprovado, seções 3–6](https://docs.google.com/document/d/13vJhblJTfYqXugi6Vey-nF3gxNk_Um_n/edit) · [Contrato KAN-15](../KAN-15/README.md)

| Métrica por SHA e cenário | Fórmula e unidade |
| --- | --- |
| Tempo total T0 | Tempo de parede da tentativa completa, em ms, no intervalo do executor |
| Tempo total serial T1–T3 | Preparo e custos iniciais do runner + seleção + features + inferência + soma dos tempos dos métodos executados, em ms |
| Redução | `1 − métodos elegíveis selecionados / métodos elegíveis no T0`, proporção |
| Detecção relativa | Métodos falhos de referência detectados / métodos falhos no T0 completo, proporção |
| Overhead | Seleção, features e inferência, cada uma em ms. Treinamento aparece em campo próprio |

Na avaliação retrospectiva, os métodos com desfecho `pass` ou `fail` formam o conjunto elegível do T0. O avaliador também reporta o tamanho bruto da seleção, que pode incluir métodos comprovadamente ignorados. Um selecionado sem associação ao T0 impede a comparação da população. Com T0 completo sem falhas, a contagem é zero e a proporção é indefinida. Um conjunto elegível vazio torna a redução indefinida. Os resultados completos de replay são projeções sobre o oráculo, inclusive quando falta a ordem mas a população está comprovada. Validação física pode revelar efeitos de ordem, cache ou dependências.

Fase inaplicável vale zero. Custo medido igual a zero permanece válido. Preparo ou fase aplicável sem medição, ou falta de duração em método executado, tornam o tempo estimado indisponível. Seleção compartilhada é debitada uma vez por cenário. Treinamento pertence ao evento de atualização e fica fora do total operacional. A amostra tem 100 ms de treino T2 e carece de horizonte para amortização. Se houver um horizonte documentado em execuções servidas, a amortização em ms por execução será o custo total das atualizações atribuídas dividido por esse número de execuções.

O tempo T0 de parede inclui fechamento do executor. As estimativas T1–T3 cobrem preparo e execução dos métodos, conforme a especificação de tempo total da Entrega 2. A KAN-23 entrega os custos iniciais. Uma comparação de parede ponta a ponta requer medição dos quatro cenários com o mesmo intervalo e configuração na KAN-28.

## CLI e validação

Na raiz do worktree das métricas, aponte para a pasta dos seis CSVs e do manifesto usados pelo simulador e para o JSON produzido naquela execução. Para usar o worktree irmão com PowerShell, adapte os caminhos aos artefatos congelados:

```powershell
$kan23 = '../KAN-23-24-checkout/evidencias/KAN-23'
$dados = Join-Path $kan23 'fixtures'
$replay = Join-Path ([System.IO.Path]::GetTempPath()) 'kan23-replay.json'
python -B (Join-Path $kan23 'simular.py') $dados | Set-Content -Encoding utf8 $replay
python -B evidencias/KAN-25/metricas.py $dados $replay
python -B -m unittest discover -s evidencias/KAN-25 -v
```

O código reutilizável está em `src/test_prioritization/metrics` e o ponto de
entrada estável é `scripts/metricas.py`. `metricas.py` permanece neste diretório
como wrapper compatível com as reproduções publicadas.

O teste de integração extrai o commit KAN-23 `c6e1ca1` para uma pasta temporária e executa os dois CLIs. Na revisão sintética `5555555…`, T0 tem quatro métodos elegíveis e dois falhos. T1–T3 selecionam três métodos e detectam as duas falhas na execução integral. As reduções T0/T1/T2/T3 são 0/25/25/25% e os tempos são 99/55/60/71 ms. O teste unitário também verifica perda de uma falha, denominador zero, duração zero e custo ausente. [Testes](test_metricas.py)

O campo `data_kind` vem do manifesto combinado ao replay e `modo` identifica a avaliação serial. Os números acima são de uma fixture controlada. A revisão 50 em `d2c0e7a` é replay sintético auxiliar, sem orçamento oficial. Seus rótulos ficam fora desta validação. Para reportar resultados da avaliação principal, são necessários artefatos aprovados e comparáveis da KAN-28. [RQ2](../KAN-26/README.md) · [APFDc](../KAN-27/README.md)

## Passagem para KAN-28–30

- **KAN-28** — Validar o replay em amostra física com ordem observada, configuração e intervalo comparáveis, overhead e tempos de conclusão auditáveis. Quantificar divergências e decidir quando a simulação é adequada.
- **KAN-29** — Fixar o recorte cronológico, o manifesto, as versões e as referências históricas antes do processamento. Consolidar dados brutos e métricas por SHA e cenário, com exclusões e lacunas. Manter a avaliação principal e os dados auxiliares de falhas em conjuntos distintos.
- **KAN-30** — Comparar cenários por SHA e no conjunto comum de cada orçamento. Reportar denominadores, cobertura, retenção de falhas, curvas e custo operacional. Associar T0→T1 à seleção e T1→T2/T3 à ordenação sobre a mesma seleção, considerando o overhead adicional. Interpretar o APFDc junto da perda de falhas na seleção.
