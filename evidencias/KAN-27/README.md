# KAN-27 — APFDc complementar

Cada método com `fail` no T0 do SHA avaliado representa um evento de falha distinto, com peso unitário, detectado apenas por esse método. Trata-se de uma aproximação observável quando falta o mapeamento de testes para defeitos independentes. O custo é a duração do método em ms no T0. Métodos comprovadamente ignorados ficam fora do cálculo. O APFDc compara a ordem sobre a seleção compartilhada de T1–T3, com o mesmo vetor de custos. [KAN-27](https://cin-team-test-prioritization.atlassian.net/browse/KAN-27) · [Protocolo, seção 5](https://docs.google.com/document/d/13vJhblJTfYqXugi6Vey-nF3gxNk_Um_n/edit)

Para cada método falho selecionado, calcule o tempo restante desde a metade de sua execução, `C − início − custo/2`, em que `C` é o custo total da população. Some esses valores e divida por `C × número de métodos falhos selecionados`. O resultado está entre 0 e 1. O cálculo mede o efeito do ranking com custos por método. Preparo, overhead operacional e orçamento pertencem às métricas de tempo e detecção.

O APFDc fica indisponível para os três cenários quando falta oráculo, cobertura da seleção pelo T0, uma ordem completa, duração aplicável, custo total positivo ou falhas na população compartilhada. Falhas excluídas são contadas à parte contra o T0 completo, mesmo quando o APFDc é indefinido e a seleção está comprovada. O resultado complementar pode ser alto em uma seleção que exclui muitas falhas de referência.

## Exemplo conhecido

No alvo sintético `5555555…` da KAN-23 `c6e1ca1`, A/B/C duram 20/15/10 ms e B/C falham. O denominador é `45 × 2 = 90`.

| Ordem | Soma das caudas | APFDc |
| --- | ---: | ---: |
| T1 · A B C | 17,5 + 5 | 0,25 |
| T2 · C B A | 40 + 27,5 | 0,75 |
| T3 · B C A | 37,5 + 25 | 0,694444… |

Os testes cobrem ordens idênticas, os extremos 0 e 1 com uma falha de custo zero, tempo total zero, falta de duração e de ordem, população incompatível e ausência de falhas. Um caso acrescenta uma falha em D fora da seleção para verificar a contagem de perdas. [Testes](../KAN-25/test_metricas.py)
