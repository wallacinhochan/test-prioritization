# KAN-14 — Primeira execução histórica do T0

Em 20/11/2026, a suíte completa da posição 1 do [recorte da KAN-10](../KAN-10/commits.csv) passou em UTC. A KAN-13 já tinha validado um método nessa posição. Esta rodada registrou a suíte completa no mesmo SHA, com o executor e a imagem aprovados para a Entrega 3. [KAN-14](https://cin-team-test-prioritization.atlassian.net/browse/KAN-14) · [Ambiente da KAN-13](../KAN-13/README.md)

## Resultado

| Posição e SHA | Casos no Surefire | Aprovados | Ignorados | Falhas | Erros | Tempo de ponta a ponta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 · `921c1b4e09ed7b6900ad7243cffb33b373980cc5` | 59.449 | 59.436 | 13 | 0 | 0 | 291,482 s |

O Maven e o executor retornaram 0. Conferi 227 relatórios XML em UTC, com 59.449 elementos `testcase` e 13 elementos `skipped`, de acordo com o resumo do Maven. Os atributos `testsuite/@tests` somaram 59.165. A cobertura registrada usa os elementos `testcase`. Esses totais são casos de execução do Surefire. A associação e a agregação por método ficam para a KAN-16, seguindo a [regra da KAN-17](../KAN-17/README.md).

```text
[WARNING] Tests run: 59449, Failures: 0, Errors: 0, Skipped: 13
[INFO] BUILD SUCCESS
KAN-13 código Maven: 0
```

## Reprodução e saídas

Com a imagem e o clone preparados pelo [bootstrap da KAN-13](../../infra/commons-lang/README.md#bootstrap), execute na raiz em PowerShell.

```powershell
./infra/commons-lang/executar.ps1 -Fonte $fonte -Sha 921c1b4e09ed7b6900ad7243cffb33b373980cc5 -Saida ./resultados/KAN-14
```

- Ambiente observado com Temurin 21.0.11, Maven 3.9.11, UTC e cache Maven frio. O tempo de ponta a ponta inclui a resolução de dependências.
- ID da imagem local `sha256:6e15bf7fd834e6998883afacb56e4b6de6b180fff899bf3fb0474840f5ac93d6`.
- SHA-256 da fonte exportada `4e89aae29613b869701b42fb784822100da6b82c24d2339fc1631e643b9bcdfe`.
- As saídas brutas estão em `resultados/KAN-14/921c1b4e09ed7b6900ad7243cffb33b373980cc5/20261120T160458376Z-baac2d8746094e99ae971f9c73160837/`, com `ambiente.json`, `maven.log` e os XML em `surefire/`.

Há suíte completa nos dois extremos do recorte sob o mesmo ambiente, incluindo a [âncora da KAN-13](../KAN-13/pilotos/ancora/README.md). Os resultados das revisões intermediárias e a disponibilidade de falhas naturais ainda precisam ser medidos. [Parecer da KAN-11](../KAN-11/README.md)
