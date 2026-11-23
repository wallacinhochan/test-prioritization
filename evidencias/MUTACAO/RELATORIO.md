# Resultados do piloto de mutação no Apache Commons Lang

Em cinco revisões, T0 detectou 18 das 20 variantes sintéticas. A projeção sobre T1 preservou as 18 detecções, com 20 métodos excluídos de 23.280 pares de revisão e método (0,086%). Duas variantes ficaram indeterminadas nos dois cenários. No teste final, KNN e Random Forest anteciparam as três detecções observadas em relação à ordem T1.

O lote histórico da Entrega 3 (posições 1, 26, 50, 75 e 100) registrou 298.770 invocações e 23.280 pares de revisão e método em UTC, com zero falhas observadas. O piloto de mutação usou as posições 15, 26, 42, 50 e 96. Os dois recortes compartilham as posições 26 e 50. [Entrega 3](../ENTREGA-3/README.md) · [Protocolo do piloto](README.md)

## Execuções e rótulos

Cada variante alterou o bytecode de produção, com os testes intactos. O manifesto de cada revisão congelou quatro variantes por hash antes dos replays. O rótulo por SHA, mutante e método é positivo quando o método passa no controle e falha na variante. A aprovação observada nas duas execuções dá o rótulo negativo. Skip, ausência, ambiguidade e infraestrutura permanecem desconhecidos. Os números da tabela agregam rótulos, com denominador distinto da contagem de mutantes.

| Posição | Partição | Variantes | Positivos | Negativos | Desconhecidos | Detecções T0 / T1 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| [15](mutantes/pos-15/resumo.json) | Treino | 4 | 280 | 18.280 | 44 | 4 / 4 |
| [26](mutantes/pos-26/resumo.json) | Treino | 4 | 12 | 18.552 | 44 | 4 / 4 |
| [42](mutantes/pos-42/resumo.json) | Treino | 4 | 17 | 18.567 | 44 | 4 / 4 |
| [50](mutantes/pos-50/resumo.json) | Validação | 4 | 4 | 18.580 | 44 | 3 / 3 |
| [96](mutantes/pos-96/resumo.json) | Teste final | 4 | 6 | 18.598 | 48 | 3 / 3 |
| **Total** | | **20** | **319** | **92.577** | **224** | **18 / 18** |

As cinco revisões confirmaram equivalência entre o controle limpo e a cópia intacta, coincidência dos rótulos na repetição e restauração do resultado original. Na posição 26, o PIT exportou 77 variantes de `LocaleUtils` e o manifesto de `b0652c9` fixou quatro. O resumo `41318d9` verificou a viabilidade para ampliar o piloto. Na posição 15, a evidência de controle foi recuperada do contêiner após perda da sessão. Na posição 42, uma interrupção do Docker exigiu repetir somente a restauração a partir da mesma árvore compilada. A conferência da coordenação validou os hashes dos manifestos e CSVs de rótulos e as etapas completas de cada revisão. [Geração, comandos e ocorrências](mutantes/README.md)

## Preservação pelo T1

A seleção estática por dependências e a ordem T1 foram congeladas em `0d3cd01`. O seletor excluiu quatro métodos de `IDKeyTest` por revisão. T1 reteve os 319 rótulos positivos e os 224 desconhecidos no nível de método. A preservação foi de 18/18 (100%) entre os mutantes detectados pelo T0. O intervalo relativo a desfechos T1 desconhecidos entre esses 18 foi [100%, 100%]. As duas variantes sem detecção observada, uma na posição 50 e outra na 96, ficaram indeterminadas por lacunas e estão fora do denominador da preservação.

O seletor levou de 399 a 463 ms por revisão sobre inventário e saída do jdeps preparados. A avaliação reaplicou o conjunto T1 à matriz do replay T0. O tempo físico de execução do T1 permanece indisponível. [Método e reprodução](t1/README.md) · [Comparação por revisão e mutante, commit `085709c`](t1/comparacao/consolidado.json)

## Dataset e ranking

Para cada SHA e método, o alvo é a fração de falhas induzidas entre os rótulos conhecidos. As sete características usam a assinatura do teste e as rotas estáticas do T1, disponíveis antes da execução. O treino teve 55.660 observações conhecidas em T1 (309 positivas e 55.351 negativas), com 132 desconhecidas. A validação teve 18.568 conhecidas (4 positivas e 18.564 negativas), com 44 desconhecidas. Os dois modelos foram ajustados no treino e ordenaram a mesma população do T1.

Na validação, os primeiros postos observados do T1 foram 1.693, 1.693 e 999. O KNN os antecipou para 15, 15 e 221 e a Random Forest para 25, 25 e 268, respectivamente. A quarta variante ficou indeterminada nas três ordens. [Diagnóstico](modelos/diagnostico-validacao-50.json) · [Postos na validação](modelos/deteccao-validacao-50.json)

### Teste final na posição 96

O commit `cbb462b` fixou as características, os modelos e as três ordens antes do replay final. A coordenação conferiu os hashes dos 21 artefatos nas duas execuções e o conjunto idêntico de 4.659 métodos por ordem, incluindo a ordem T1 original. Os manifestos das duas execuções diferem apenas no registro de HEAD, pois houve um commit da comparação T1 entre elas. A liberação foi registrada em `6e97157`, com SHA-256 do manifesto `121b9e14784fdd8a706977b6fee4f9fb2d8997e3ce3f3bff8961ab5f3306baea`. O resumo de replay em `f4a9da2` referencia esse congelamento e essa liberação. [Manifesto](modelos/congelamento.json) · [Resumo do replay](mutantes/pos-96/resumo.json)

| Variante de `TypeUtils` | Primeiro posto T1 | Primeiro posto KNN | Primeiro posto Random Forest |
| --- | ---: | ---: | ---: |
| `containsTypeVariables`, igualdade | 3.685 | 2 | 14 |
| `containsTypeVariables`, ordem | 3.685 | 2 | 14 |
| `isAssignable`, `GenericArrayType` | Indeterminado | Indeterminado | Indeterminado |
| `isAssignable`, `WildcardType` | 3.705 | 28 | 25 |

O teste final cumpriu o critério de suficiência do piloto, com 18.588 observações conhecidas em T1 (6 positivas e 18.582 negativas), além de 48 desconhecidas. Os postos da tabela são as primeiras detecções observadas. O diagnóstico registra também a primeira posição em que uma detecção seria possível diante de lacunas. Na variante indeterminada, cada ordem tem 12 desconhecidos. [Diagnóstico e postos do teste final, commit `2da6096`](modelos/teste-final.json)

## Limites e reprodução

A seleção reduziu pouco a quantidade de métodos, e os ganhos de ranking foram medidos em postos. As estimativas cobrem as 20 alterações artificiais escolhidas. As quatro variantes finais pertencem a uma única classe, com duas no mesmo método. Essa concentração e as cinco revisões limitam a generalização para regressões naturais e ambientes de CI. O piloto confirma viabilidade para estudar detecção sintética. A decisão sobre o objeto do estudo principal segue na KAN-12, e a KAN-18 permanece formalmente bloqueada. [KAN-12](https://cin-team-test-prioritization.atlassian.net/browse/KAN-12) · [KAN-18](https://cin-team-test-prioritization.atlassian.net/browse/KAN-18)

Os resultados versionados registram caminhos e SHA-256 para reprodução. Os CSVs brutos, XML, logs e modelos serializados ficam em diretórios locais ignorados pelo Git. Passaram os três testes automatizados do comparador e os oito testes dos modelos. A execução independente da comparação das cinco revisões reproduziu integralmente o JSON versionado. [Reprodução dos mutantes](mutantes/README.md#reprodução) · [Reprodução da seleção](t1/README.md#reprodução) · [Reprodução dos rankings](modelos/README.md#reprodução)
