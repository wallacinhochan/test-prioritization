# Resultados do piloto de mutação no Apache Commons Lang

O piloto mede a detecção de alterações sintéticas em cinco revisões do Apache Commons Lang. O lote histórico da Entrega 3 (posições 1, 26, 50, 75 e 100) somou 298.770 invocações e 23.280 pares de revisão e método, com zero falhas observadas. As posições 26 e 50 também fazem parte do recorte de mutação (15, 26, 42, 50 e 96). Os resultados de mutação têm validade para as variantes escolhidas e as suítes executadas. A auditoria histórica continua na KAN-12 e a KAN-18 segue formalmente bloqueada. [Entrega 3](../ENTREGA-3/README.md) · [Protocolo do piloto](README.md)

**Piloto em andamento.** Esta versão consolida os resultados verificados da posição 26. As posições 15, 42 e 50 aguardam publicação dos replays, e a posição 96 está reservada para o teste final.

## Geração e validação

O protocolo foi fixado em `af6bdfc`. A unidade de observação dos replays é o par mutante e método dentro de cada SHA. Um positivo requer aprovação no controle e falha na variante. Um negativo requer aprovação observada no controle e na variante. O pipeline mantém skips, ausências, ambiguidades e problemas de infraestrutura como desconhecidos. [Geração e rótulos](mutantes/README.md)

Na posição 26, a geração exportou 77 variantes de `LocaleUtils`. O manifesto de `b0652c9` fixou quatro variantes por hash antes dos replays. O controle limpo registrou 59.439 aprovações e 13 skips em 59.452 invocações, sem falhas ou erros. A execução intacta com os binários reutilizados reproduziu os desfechos do controle limpo. [Manifesto da posição 26](mutantes/pos-26/manifesto.json)

Os quatro replays da posição 26 concluíram e a verificação foi versionada em `41318d9`. Entre os 18.608 rótulos por mutante e método, houve 12 positivos, 18.552 negativos e 44 desconhecidos. A repetição da primeira variante coincidiu por método, e a restauração reproduziu o controle. A conferência independente verificou os SHA-256 do manifesto e do CSV de rótulos e confirmou que o CSV bruto é ignorado pelo Git. [Verificação da posição 26](mutantes/pos-26/resumo.json)

## Seleção de testes

As listas e a ordem T1 foram congeladas em `0d3cd01` antes do acesso aos rótulos. T1 selecionou 23.260 dos 23.280 pares revisão e método, reduzindo a população em 20 pares (0,086%). Em cada revisão, a regra excluiu quatro métodos de `IDKeyTest`. O seletor levou de 399 a 463 ms por revisão sobre inventário e saída do jdeps preparados. A medida abrange apenas a seleção. A verificação independente do comparador em `5c3d222` passou nos três testes existentes. [Seleção T1 e comparador](t1/README.md)

Na posição 26, T0 detectou 4/4 mutantes e a projeção sobre T1 preservou as quatro detecções e os 12 rótulos positivos. A preservação ficou em 4/4 (100%), com intervalo de [100%, 100%] diante das lacunas de observação. Os 44 rótulos desconhecidos permaneceram desconhecidos no nível de método. Esse intervalo expressa a incerteza por desfechos desconhecidos no conjunto observado. O tempo físico de execução de T1 permanece indisponível. [Comparação por mutante, commit `2570ea0`](t1/comparacao/pos-26.json)

## Dataset e ranking

As posições 15, 26 e 42 compõem o treino, 50 a validação e 96 o teste final. KNN, Random Forest e a ordem de referência usam a mesma lista T1 de métodos candidatos. As entradas são limitadas a informações disponíveis antes da execução. A posição 96 fica reservada até o congelamento das características, modelos e regra de ranking. [Protocolo de ranking](README.md)

Na posição 26, a população T1 teve 12 rótulos positivos e 18.536 negativos, com 44 desconhecidos excluídos do denominador. Houve alvo para 4.637 dos 4.648 métodos selecionados. O commit `44c661a` registra o diagnóstico inicial e a implementação. A verificação independente executou os seis testes de modelos e os três testes do comparador. [Diagnóstico da posição 26](modelos/diagnostico-gate-26.json) · [Método de avaliação de ranking](modelos/README.md)
