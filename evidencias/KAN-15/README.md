# KAN-15 — Contrato de dados experimentais

**Versão do contrato** `0.1.0` · **Aceite** técnico concluído em 20/11/2026.

A KAN-15 define os identificadores e formatos para integrar a auditoria, a coleta da suíte completa, a seleção, os rankings e as medições de overhead. A KAN-9 validou o ambiente do Apache Commons Lang em uma revisão fixa e registrou sensibilidade ao fuso e diferenças entre tempos de suíte e de invocações isoladas. O recorte experimental vem da KAN-10. Os tempos de ponta a ponta das invocações de Maven da KAN-9 incluem inicialização e, na primeira suíte, obtenção de dependências. A coleta por teste e por commit pertence à KAN-16. [KAN-15](https://cin-team-test-prioritization.atlassian.net/browse/KAN-15) · [Evidência KAN-9](../KAN-9/README.md) · [KAN-10](https://cin-team-test-prioritization.atlassian.net/browse/KAN-10) · [KAN-16](https://cin-team-test-prioritization.atlassian.net/browse/KAN-16)

## Formato e identidade

- CSV em UTF-8 sem BOM, com vírgula, aspas duplas para escape e uma linha de cabeçalho na ordem do dicionário. Escapar uma aspa interna com outra aspa. Usar célula vazia para nulo e `true`/`false` para booleanos. Decimal usa ponto sem separador de milhares. `datetime` usa ISO 8601 com fuso UTC (`Z`).
- `sha` é o SHA-1 completo do commit do Commons Lang, 40 dígitos hexadecimais minúsculos. Fazer junções por igualdade exata de `commit_sha`. A ordem auditada serve para recorte e disponibilidade temporal.
- `test_id` é texto opaco, obrigatório e sensível a maiúsculas, compartilhado entre produtores sob a mesma regra de identidade. Preservar o valor byte a byte. A unidade experimental é o método de teste. Os produtores seguem a regra aprovada em [Evidência KAN-17](../KAN-17/README.md): `classe#metodo(tipos)` com assinatura em todas as chaves, histórico por igualdade exata e parametrizações associadas ao método de origem. Os exemplos com `test_id` ficam somente com cabeçalho até a coleta rastreável da KAN-16. [KAN-17](https://cin-team-test-prioritization.atlassian.net/browse/KAN-17)
- `ms` significa inteiro de 64 bits não negativo em milissegundos. Converter na origem, arredondando para o milissegundo mais próximo, com empate para cima, e preservar a medida bruta na evidência. `0` é medição válida que resultou em zero após conversão. Célula vazia indica duração indisponível ou inaplicável, conforme o contexto. Somatórios destinados à avaliação devem sinalizar componentes obrigatórios desconhecidos.
- `ref` é caminho relativo à raiz do repositório de pesquisa ou URL persistente para evidência rastreável, com localizador quando necessário. Para artefatos gerados, a referência deve permitir recuperar o log, relatório ou manifesto e a configuração que produziu a linha.
- Cada exportação de dados deve declarar a versão do contrato junto ao conjunto de arquivos. Mudanças incompatíveis de chaves, campos, tipos ou significado exigem nova versão e regra explícita de migração. Esta revisão usa `0.1.0` em todos os exemplos.
- `T0` é a suíte completa, `T1` é seleção por dependências, `T2` é a mesma seleção ordenada por KNN e `T3` é a mesma seleção ordenada por Random Forest. PK designa chave primária e FK designa chave estrangeira. Campos opcionais e condicionais continuam presentes no cabeçalho. [KAN-18](https://cin-team-test-prioritization.atlassian.net/browse/KAN-18) · [KAN-20](https://cin-team-test-prioritization.atlassian.net/browse/KAN-20) · [KAN-21](https://cin-team-test-prioritization.atlassian.net/browse/KAN-21)

## Dicionário

### commits

Uma linha por revisão auditada. [CSV de exemplo](exemplos/commits.csv)

| Campo | Tipo | Obrigatório | Regra |
| --- | --- | --- | --- |
| `commit_sha` | sha | Sim | PK. Identifica a revisão no repositório do objeto experimental. |
| `commit_order` | int64 ≥ 1 | Sim | Único. Posição na sequência auditada da KAN-10, incluindo revisões excluídas. Define a ordem experimental. |
| `committed_at` | datetime | Sim | Data do committer registrada pelo Git, normalizada para UTC. A ordem vem de `commit_order`. |
| `eligibility_status` | enum | Sim | `pending`, `eligible` ou `ineligible`. Somente `eligible` entra no recorte usado para avaliação. |
| `exclusion_reason` | texto | Condicional | Obrigatório se `eligibility_status=ineligible`. Vazio nos outros estados. |
| `build_changed` | bool | Opcional | Alteração de build segundo a regra da auditoria. Vazio quando indeterminado. |
| `tests_changed` | bool | Opcional | Alteração de testes segundo a regra da auditoria. Vazio quando indeterminado. |
| `source_ref` | ref | Sim | Referência à evidência da KAN-10 para este SHA e sua posição na auditoria. |

### t0_runs

Uma linha por commit com uma tentativa de referência de T0. As tentativas adicionais ficam nos artefatos brutos, e uma reexportação atualiza a execução de referência junto com seus resultados. [CSV de exemplo](exemplos/t0_runs.csv)

| Campo | Tipo | Obrigatório | Regra |
| --- | --- | --- | --- |
| `commit_sha` | sha | Sim | PK e FK → `commits.commit_sha`. |
| `scenario` | enum | Sim | Valor fixo `T0`. |
| `run_status` | enum | Sim | `complete`, `incomplete` ou `environment_error`. `complete` admite falhas de teste quando a suíte produz resultados completos. |
| `suite_duration_ms` | ms | Opcional | Tempo observado de parede da execução física da suíte, segundo o intervalo de medição declarado em `source_ref`. Pode existir mesmo em tentativa incompleta. |
| `source_ref` | ref | Sim | Identifica relatórios, logs, ambiente, configuração de execução e tentativa de referência para o commit. |

### t0_results

Uma linha por unidade com resultado observado por commit. PK composta por `(commit_sha, test_id)`. Um erro de infraestrutura é registrado em `t0_runs`. Sem resultado observado para um teste, a linha fica ausente. Uma execução incompleta pode conservar linhas observadas, com a completude identificada pela execução de referência. A coleta da KAN-16 aplica a [agregação aprovada na KAN-17](../KAN-17/README.md#agregação-para-t0): falha ou erro atribuível ao teste prevalece. Sem falhas, use `pass` se ao menos uma invocação passar e `skip` se todas forem ignoradas. Some os tempos brutos das invocações executadas e arredonde o total uma vez. Deixe a duração vazia se faltar tempo de uma invocação executada ou se todas forem ignoradas. Registre o primeiro início somente quando a sequência global foi observada. [CSV de exemplo](exemplos/t0_results.csv)

| Campo | Tipo | Obrigatório | Regra |
| --- | --- | --- | --- |
| `commit_sha` | sha | Sim | Parte da PK. FK → `t0_runs.commit_sha`. |
| `scenario` | enum | Sim | Valor fixo `T0`. |
| `test_id` | texto | Sim | Parte da PK. Identidade opaca da unidade de teste. |
| `outcome` | enum | Sim | `pass`, `fail` ou `skip`. Erro atribuível ao teste é `fail` e sua classificação original fica no relatório bruto. |
| `duration_ms` | ms | Opcional | Tempo observado para essa unidade no T0. Vazio quando indisponível, inclusive para `skip` sem medição. |
| `execution_order` | int64 ≥ 1 | Opcional | Posição de execução no T0 quando recuperável. Única por commit entre posições preenchidas. |
| `source_ref` | ref | Sim | Relatório bruto e localizador da unidade ou dos registros agregados que sustentam a linha. |

### selection

Uma linha por candidato, incluindo os excluídos da seleção. PK composta por `(commit_sha, scenario, test_id)`. A população vem do inventário disponível antes da execução e deve cobrir também os candidatos de fallback. O artefato do seletor registra a completude e permite comprovar um conjunto vazio. [CSV de exemplo](exemplos/selection.csv)

| Campo | Tipo | Obrigatório | Regra |
| --- | --- | --- | --- |
| `commit_sha` | sha | Sim | Parte da PK. FK → `commits.commit_sha`. |
| `scenario` | enum | Sim | Parte da PK. Valor fixo `T1`. |
| `test_id` | texto | Sim | Parte da PK. Identidade da unidade presente no inventário de candidatos. |
| `selected` | bool | Sim | `true` inclui o candidato no conjunto compartilhado por T1–T3. |
| `selection_reason` | enum | Sim | `dependency`, `fallback` ou `no_dependency`. Os dois primeiros exigem `selected=true` e o último, `false`. |
| `source_ref` | ref | Sim | Localiza inventário, revisão-base do diff, versão do seletor e evidência da decisão ou do fallback. |

### rankings

Uma linha por teste selecionado em cada cenário de ordenação. PK composta por `(commit_sha, scenario, test_id)`. T1 registra a ordem de referência da seleção. T2 e T3 devem cobrir exatamente o conjunto selecionado em T1, uma vez por cenário, com a regra de desempate versionada. A ordem observada de T0 fica em `t0_results`. [CSV de exemplo](exemplos/rankings.csv)

| Campo | Tipo | Obrigatório | Regra |
| --- | --- | --- | --- |
| `commit_sha` | sha | Sim | Parte da PK. FK → `commits.commit_sha`. |
| `scenario` | enum | Sim | Parte da PK. `T1`, `T2` ou `T3`. |
| `test_id` | texto | Sim | Parte da PK. FK lógica → `selection(commit_sha,T1,test_id)` com `selected=true`. |
| `rank` | int64 ≥ 1 | Sim | Posição efetiva na execução simulada. Única e contígua a partir de 1 por commit e cenário. |
| `score` | decimal finito | Condicional | Escore produzido pelo modelo. Obrigatório em `T2` e `T3`. Vazio em `T1`. |
| `source_ref` | ref | Sim | Localiza a configuração da ordenação e do desempate. Em T2/T3 inclui a versão das features, a janela de treino e o modelo usados. |

### overhead

Uma linha por commit, cenário e fase. PK composta por `(commit_sha, scenario, phase)`. Registre as fases aplicáveis mesmo quando a medição estiver indisponível. Para T0, as fases deste contrato são inaplicáveis. T1 usa seleção. T2 e T3 herdam o custo de seleção medido em T1 e acrescentam features e inferência. Atribua as fases compartilhadas a cada cenário que as usaria em execução isolada, uma vez por cenário, com a mesma referência de medição. Represente seleção compartilhada em T2 e T3 conforme a medição de T1. Registre treinamento em T2/T3 apenas no evento de atualização e reporte seu custo em separado. Seleção, features e inferência aplicáveis consomem o orçamento experimental. O tempo da suíte e as durações por teste têm campos próprios. [CSV de exemplo](exemplos/overhead.csv)

| Campo | Tipo | Obrigatório | Regra |
| --- | --- | --- | --- |
| `commit_sha` | sha | Sim | Parte da PK. FK → `commits.commit_sha`. Em treinamento, identifica o primeiro commit para o qual o modelo atualizado fica disponível. |
| `scenario` | enum | Sim | Parte da PK. `T0`, `T1`, `T2` ou `T3`. |
| `phase` | enum | Sim | Parte da PK. `selection`, `features`, `inference` ou `training`. |
| `measurement_status` | enum | Sim | `measured`, `unknown` ou `not_applicable`. |
| `duration_ms` | ms | Condicional | Preenchido somente com `measured`. Vazio em `unknown` e `not_applicable`. |
| `source_ref` | ref | Sim | Localiza log ou manifesto com início/fim da fase, ambiente, política de cache e motivo de indisponibilidade ou inaplicabilidade. Para treino, identifica a janela e a versão do modelo. |

## Entradas preditivas e avaliação retrospectiva

| Etapa | Entradas permitidas | Saída |
| --- | --- | --- |
| Seleção T1 | SHA e revisão-base declarada, diff, dependências e inventário de testes disponíveis quando a decisão é tomada. | Conjunto T1 com evidência de decisões e fallback. |
| Ranking T1–T3 | T1 fornece a população e sua ordem de referência. T2/T3 usam as mesmas features conforme KAN-19, com dados do commit disponíveis antes da execução e histórico de commits anteriores somente se já observável pela estratégia. A janela de treino termina antes do commit avaliado. | Uma posição por teste selecionado em cada cenário, com escore em T2/T3. |
| Avaliação T0–T3 | Após fixar seleção e rankings, juntar pelo par `(commit_sha, test_id)`, usando a execução T0 de referência do mesmo commit. | Resultados, durações e ordem observada do T0 dão a referência para simular tempo, identificar falhas detectadas ou perdidas e calcular métricas. |

Para cada commit, mantenha desfechos, indicadores de falha, skips, duração medida, ordem do T0 e derivados do próprio commit exclusivamente no avaliador. O mesmo vale para dados de commits posteriores. Um resultado de T0 de um commit anterior pode entrar no histórico preditivo somente se a política de observabilidade da KAN-19 o disponibilizar antes da decisão. Registre o corte temporal e a proveniência das features e do treinamento na evidência do ranking. [KAN-19](https://cin-team-test-prioritization.atlassian.net/browse/KAN-19) · [KAN-22](https://cin-team-test-prioritization.atlassian.net/browse/KAN-22) · [KAN-23](https://cin-team-test-prioritization.atlassian.net/browse/KAN-23) · [KAN-24](https://cin-team-test-prioritization.atlassian.net/browse/KAN-24)

## Verificação com a KAN-10

**Verificação em 20/11/2026.** A amostra da KAN-10 tem posições `1` e `2` com SHAs completos, distintos e presentes no Apache Commons Lang. A cópia Git da auditoria confirmou primeiro pai, datas do committer e diffs. O SHA da posição 1 é o primeiro pai da posição 2. A junção pela chave encontrou uma correspondência por linha (2 de 2), inclusive com a ordem dos exemplos invertida. Os dois commits foram importados para o exemplo com elegibilidade `pending`. [Amostra auditada preservada](fontes/kan10-amostra.csv) · [Commit na posição 1](https://github.com/apache/commons-lang/commit/921c1b4e09ed7b6900ad7243cffb33b373980cc5) · [Commit na posição 2](https://github.com/apache/commons-lang/commit/766c028c96afbc831e842684c85e90fdad08722c)

A amostra preserva o cabeçalho e as duas primeiras linhas de dados de `evidencias/KAN-10/commits.csv` no workspace compartilhado. Ela registra o estado usado na verificação de 20/11/2026.

O contrato foi ajustado para preservar `eligibility_status`, inclusive a triagem pendente. Para a KAN-10, a chave e as duas primeiras posições conferem. A importação segue o mapeamento abaixo. A associação continua válida se a saída da auditoria for reordenada.

| KAN-10 | KAN-15 |
| --- | --- |
| `commit_sha`, `build_changed`, `tests_changed` | Campos homônimos. |
| `position` | `commit_order`. |
| `committer_date_utc` | `committed_at`. |
| `eligibility_status` | `eligibility_status`. Preservar `pending`. Uma decisão operacional favorável vai para `eligible`. Um impedimento `blocked` vai para `ineligible` quando a exclusão for decidida, com o motivo registrado. |
| `blocker_reason` | `exclusion_reason` quando a decisão for pela exclusão. |
| Arquivo auditado e SHA da linha | `source_ref`. Primeiro pai, indicação de merge, caminhos alterados, evidências e checagens pendentes ficam acessíveis na origem. |

**Revisão do contrato 0.1.0 em 20/11/2026.** Os seis CSVs estão em UTF-8 sem BOM e têm os cabeçalhos na ordem do dicionário, sem colunas duplicadas. Em `commits`, as duas linhas passaram nas checagens dos tipos, da chave, da ordem, da referência de origem e do motivo de exclusão vazio para `pending`. A junção com a amostra preservada encontrou uma correspondência por SHA nas duas linhas, com a ordem invertida.

`t0_runs`, `t0_results`, `selection`, `rankings` e `overhead` mantêm apenas os cabeçalhos. Nessas cinco tabelas, a revisão de tipos, chaves e campos vazios ficou no nível do esquema. As colunas previstas nas chaves estão presentes. O esquema distingue duração medida igual a zero de célula vazia, exige escore em T2/T3 e o deixa vazio em T1, e exige duração de overhead somente para `measured`. A integridade referencial e essas regras por linha serão verificadas quando houver dados rastreáveis. `test_id` identifica um método de teste e permanece opaco para os consumidores. A especificação de seleção e ranking usa apenas entradas disponíveis antes da execução. Desfechos, skips, duração, ordem e derivados do T0 do próprio commit ficam reservados à avaliação retrospectiva.

**Recorte completo da KAN-10.** Conferi **100 de 100 registros** do `evidencias/KAN-10/commits.csv` no repositório oficial. [CSV completo da KAN-10](../KAN-10/commits.csv). SHA-256 da versão conferida: `ed7545c232b5df2271d48f59ef4c733c798de1ab54399e5f61e6e3f07b3a60ed`.

- Os 100 SHAs completos são distintos. Cada linha projetada encontrou uma única correspondência por `commit_sha` com a ordem invertida. As duas linhas preservadas coincidem com as posições 1 e 2 do recorte.
- `position` correspondeu a `commit_order` de 1 a 100. Os 99 vínculos consecutivos pelo primeiro pai, os SHAs e as 100 datas de committer em UTC conferiram com o histórico Git do Commons Lang.
- A projeção preservou 99 registros `pending`, um `eligible`, `exclusion_reason` vazio nas 100 linhas e os indicadores de mudança de build e de testes. O mapeamento do CSV oficial para o contrato conferiu em todas as linhas.
- Em relação à versão do workspace compartilhado, as mudanças ocorreram somente na posição 100. `eligibility_status` passou de `pending` para `eligible`, `eligibility_evidence` ganhou a referência à execução completa em UTC da KAN-9 e `pending_checks` ficou vazio. Essa execução serve de evidência operacional para a KAN-10. A tentativa de referência do T0 e a coleta por teste pertencem à KAN-16. [Suíte em UTC](../KAN-9/resultados/utc/suite.log)
- As outras 99 revisões aguardam confirmação operacional de checkout, dependências, compilação, descoberta de testes e início da suíte.

Quando houver dados das demais etapas, confira que cada FK encontra exatamente um registro referenciado e verifique a cobertura dos conjuntos de teste. Exclua registros órfãos da avaliação até resolver a origem.

## Aceite

- [x] Dicionário revisado e com aceite técnico, conforme os critérios da KAN-15.
- [x] Exemplos sem dados inventados. As tabelas sem fonte rastreável têm somente cabeçalho.
- [x] Cabeçalho e associação por SHA conferidos na amostra de duas linhas da KAN-10.
- [x] Mapeamento conferido nos 100 registros do recorte candidato da KAN-10.
- A confirmação operacional das 99 revisões pendentes pertence à auditoria. A cobertura das exportações históricas, incluindo associação por método e disponibilidade de ordem global, será verificada na KAN-16.
- [x] Unidade experimental definida como método de teste.
- [x] Política aprovada de identidade e agregação por método incorporada a partir da KAN-17.
