# Entrega 3 — Resultados preliminares

Em 20/11/2026, o piloto do Apache Commons Lang executou cinco suítes completas e associou **298.770 de 298.770 invocações** a métodos. A coleta gerou **23.280 registros de método por revisão**, com 23.224 aprovações, 56 métodos integralmente ignorados e zero falhas. Os totais da suíte incluem 66 invocações ignoradas e zero falhas ou erros. [Execuções da KAN-14](../KAN-14/README.md) · [Coleta da KAN-16](../KAN-16/README.md)

## Método e resultados por revisão

O lote usa as posições 1, 26, 50, 75 e 100 do recorte auditado de 100 SHAs, com Linux/amd64, Eclipse Temurin 21.0.11, Maven 3.9.11, UTC e cache Maven frio. A KAN-16 conciliou os XMLs do Surefire com os resumos do Maven e aplicou a identidade `classe#metodo(tipos)` e a agregação por método da KAN-17. Um método presente em dois SHAs contribui um registro em cada revisão. [Recorte auditado](../KAN-10/commits.csv) · [Ambiente](../KAN-13/README.md) · [Identidade e agregação](../KAN-17/README.md)

| Posição | SHA | Invocações | Métodos | Métodos aprovados | Métodos ignorados | Métodos com falha | Métodos com duração | Soma das durações conhecidas (s) | Tempo de parede (s) | Evidência local |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `921c1b4e09ed7b6900ad7243cffb33b373980cc5` | 59.449 | 4.649 | 4.638 | 11 | 0 | 4.638 | 197,472 | 291,482 | [Execução](../../resultados/KAN-14/921c1b4e09ed7b6900ad7243cffb33b373980cc5/20261120T160458376Z-baac2d8746094e99ae971f9c73160837/ambiente.json) |
| 26 | `04cc0339d6510ffdcb47db4676c34b40ecff6b28` | 59.452 | 4.652 | 4.641 | 11 | 0 | 4.640 | 177,233 | 283,184 | [Execução](../../resultados/KAN-14/04cc0339d6510ffdcb47db4676c34b40ecff6b28/20261120T163308947Z-2051ac8c262c4c21a821d8799a35203a/ambiente.json) |
| 50 | `f24c027ff83b90beab2ec28696721200abb4f9e9` | 59.953 | 4.657 | 4.646 | 11 | 0 | 4.646 | 198,620 | 292,398 | [Execução](../../resultados/KAN-14/f24c027ff83b90beab2ec28696721200abb4f9e9/20261120T163754499Z-9e08e75c329741b3bbef31999c8fc6bf/ambiente.json) |
| 75 | `bfcaa941b0849956972517c8559c0827c8fe5386` | 59.956 | 4.659 | 4.648 | 11 | 0 | 4.648 | 199,010 | 291,649 | [Execução](../../resultados/KAN-14/bfcaa941b0849956972517c8559c0827c8fe5386/20261120T164249149Z-13ac8225456e408db9c52eeee35cabba/ambiente.json) |
| 100 | `598dfc163b8b410fb3bb8794521206ec8dcec82a` | 59.960 | 4.663 | 4.651 | 12 | 0 | 4.650 | 192,229 | 306,912 | [Execução](../../resultados/KAN-13/598dfc163b8b410fb3bb8794521206ec8dcec82a/20261120T150800719Z-a24ed681244a469e80a93be9467c11b1/ambiente.json) |

A duração por método está disponível em 23.222 registros. Os 58 valores ausentes correspondem a 56 métodos ignorados e dois métodos com invocações de duração negativa nos XMLs. A soma das durações conhecidas usa os tempos de invocação agregados por método. O tempo de parede inclui inicialização, dependências, suíte e coleta de relatórios, e variou de 283,184 a 306,912 segundos. A ordem global de início permaneceu indisponível nas cinco execuções. [Resumo, caminhos e hashes da coleta](../KAN-16/resumo-lote.json)

## O que a evidência permite concluir

- O fluxo de T0 foi reproduzido nas cinco revisões do lote, com todos os resultados observados associados a métodos. A verificação abrange cinco das 100 revisões candidatas. A frequência de falhas nas 95 restantes continua desconhecida.
- As cinco suítes em UTC não registraram episódios naturais de falha. A KAN-11 mantém separado o episódio ambiental de fuso observado anteriormente. Esses resultados sustentam a descrição do T0, com disponibilidade insuficiente de positivos para avaliar detecção de regressões, KNN ou Random Forest. [Reavaliação de falhas](../KAN-11/README.md#atualização-após-o-t0-preliminar)
- A comparação T0 × T1 ficou pendente porque a KAN-18 depende da conclusão da KAN-12. Commons Lang permanece como objeto do piloto, e a escolha definitiva do projeto permanece em análise. [Parecer da KAN-12](../KAN-12/README.md) · [KAN-18](https://cin-team-test-prioritization.atlassian.net/browse/KAN-18)

## Verificação e reprodução

- [Manifesto por SHA e tentativa](../KAN-14/execucoes.json) e [comandos do lote](../KAN-14/README.md#reprodução-e-retomada).
- [Exportação e inventários da KAN-16](../KAN-16/README.md#reprodução) e [resumo versionado](../KAN-16/resumo-lote.json).
- CSVs completos preservados no repositório local em `evidencias/KAN-16/local/lote/`. O `t0_results.csv` contém o desfecho, a duração, quando disponível, e a referência das invocações para cada par de SHA e método. O `t0_runs.csv` identifica as cinco tentativas completas. Os hashes no resumo permitem conferir os arquivos.
