# KAN-26 — Detecção sob orçamento da RQ2

Os quatro cenários usam os cortes de 25%, 50% e 75% do T0 histórico definidos na KAN-24. O CLI recebe os prefixos KAN-23, conserva a referência histórica, a tentativa atual, os eventos, os custos e as lacunas, e verifica que o orçamento inteiro em ms corresponde ao piso do percentual. O denominador vem de todos os métodos falhos no T0 completo do **SHA avaliado**. [KAN-26](https://cin-team-test-prioritization.atlassian.net/browse/KAN-26) · [Regra KAN-24](../KAN-24/README.md) · [CLI](../KAN-25/README.md#cli-e-validação)

- A contagem usa métodos falhos distintos concluídos até o orçamento, inclusive na fronteira. A proporção divide essa contagem pelas falhas de referência quando o denominador é positivo.
- A primeira falha usa o primeiro instante de conclusão, em ms desde o início do executor. A curva é uma função em degraus com pontos em zero, nas conclusões de falhas e no limite. Falhas no mesmo instante entram juntas.
- Um corte disponível sem falhas detectadas tem contagem zero e primeira falha `nao_observada`, inclusive quando o prefixo é vazio ou o T0 completo não contém falhas. Com zero falhas em T0, a proporção é indefinida.
- Um corte indisponível ou oráculo incompleto produz contagem, proporção, tempo e curva nulos, com motivo explícito. A cobertura por limite lista a interseção dos SHAs com os quatro cenários calculáveis e os motivos por cenário para os demais.

## Validação controlada

No commit KAN-23 `c6e1ca1`, a primeira revisão sintética carece de referência anterior. Para a revisão sintética `5555555…`, a referência de 103 ms produz cortes de 25/51/77 ms. Há duas falhas de referência.

| Cenário | Falhas em 25 ms | Falhas em 51 ms | Falhas em 77 ms | Primeira falha em corte que a observa |
| --- | ---: | ---: | ---: | ---: |
| T0 | 0 | 2 | 2 | 40 ms |
| T1 | 0 | 1 | 2 | 45 ms |
| T2 | 1 | 2 | 2 | 25 ms |
| T3 | 0 | 2 | 2 | 41 ms |

Cada limite cobre uma de duas revisões elegíveis declaradas no manifesto. Antes do relatório principal, a KAN-28 precisa comprovar ordem global do T0 e conferir prefixos, overhead e tempos com execuções comparáveis. A convenção de conclusão por método pode adiar a detecção de uma falha ocorrida durante suas invocações.
