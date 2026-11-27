# KAN-24 — Orçamentos de tempo para T0–T3

Regra da RQ2 para o Apache Commons Lang, com o método de teste como unidade. A Entrega 2 exige limites definidos por regra prévia e overhead incluído. A decisão de 22/11/2026 confirma o Commons Lang e o uso de mutações para gerar rótulos de treino de KNN e Random Forest. A avaliação sintética do piloto fornece evidência auxiliar, em separado da avaliação principal de falhas naturais. [Cartão KAN-24](https://cin-team-test-prioritization.atlassian.net/browse/KAN-24) · [Entrega 2, seções 3–6](https://docs.google.com/document/d/13vJhblJTfYqXugi6Vey-nF3gxNk_Um_n/edit) · [Decisão KAN-12](../KAN-12/README.md)

## Referência e cálculo

Para cada commit elegível avaliado, use o `suite_duration_ms` da tentativa T0 de referência **completa** e comparável do commit de maior `commit_order` estritamente anterior que já estivesse disponível ao iniciar a avaliação daquele commit. A tentativa deve estar fechada e publicada para o avaliador antes desse corte. Fixe a referência antes de consultar resultados do commit avaliado. Documente SHA alvo, SHA de referência, posição de ambos, tentativa, instante do corte, origem, ambiente e configuração. A escolha depende da ordem auditada, disponibilidade, completude e comparabilidade. Uma tentativa completa com falhas atribuíveis aos testes pode servir de referência.

Use tempo de parede inteiro em milissegundos, no intervalo do executor da KAN-16, do início do preparo até o fechamento após Maven e cópia dos relatórios. Exija o mesmo intervalo, escopo de suíte, ambiente e política de cache para a referência. Calcule, com aritmética exata e piso aplicado uma vez, **`B(p) = floor(p × suite_duration_ms / 100)`**, para `p = 25, 50, 75`. Os três valores são idênticos para T0, T1, T2 e T3 do mesmo SHA. O piso preserva o teto percentual e pode produzir 0 ms para uma referência positiva muito curta. Registre o T0 do SHA atual como oráculo da avaliação, com o seu próprio tempo de parede. [Contrato KAN-15](../KAN-15/README.md) · [Coleta KAN-16](../KAN-16/README.md)

Se um T0 anterior estiver incompleto, com erro ambiental, sem duração positiva, sem prova de disponibilidade ou com configuração incompatível, procure a referência anterior válida seguinte. Se nenhuma existir, marque os três limites indisponíveis para os quatro cenários e registre a causa. A regra se aplica inclusive à primeira revisão quando ainda não há referência anterior. Preserve a elegibilidade original e reporte a cobertura da RQ2.

## Relógio e corte

Inicie o relógio lógico no ponto equivalente ao início do executor, antes de qualquer preparo ou operação que o cenário precise para produzir resultados. Em execução física use tempo decorrido monotônico a partir desse ponto. Em simulação serial acumule preparo comum, overhead aplicável e durações de métodos na ordem fixada. Inclua custos de inicialização, compilação, descoberta e do runner quando ocorram antes da conclusão observada, contabilizados uma vez mesmo que coletados junto de outra fase. A cópia posterior ao último resultado integra a duração histórica do executor, mas ocorre depois das detecções. Uma conclusão de método exatamente em B conta. Um método que cruza B não entra no prefixo e os seguintes tampouco entram, ainda que sejam curtos. O cronograma é o mesmo para os três cortes.

| Cenário | Custos antes da execução dos testes, além do preparo comum | Ordem |
| --- | --- | --- |
| T0 | Nenhuma fase de seleção, features ou inferência | Suíte completa na ordem de referência observada |
| T1 | Seleção, inclusive fallback e geração da ordem-base quando aplicável | Ordem-base congelada |
| T2 | Seleção de T1, features e inferência KNN, incluindo ordenação | Ranking KNN congelado |
| T3 | Seleção de T1, features e inferência Random Forest, incluindo ordenação | Ranking Random Forest congelado |

Debite cada fase compartilhada uma vez em cada cenário que a usaria isoladamente, com a referência da medição registrada. Faça a medição por fases sem sobreposição para somas seriais. Se o cenário executar fases ou métodos em paralelo, use tempos de eventos no relógio comum para a execução física. Registre treinamento e seu custo amortizado separadamente, conforme a Entrega 2 e a KAN-15. Para a simulação por método, atribua a detecção ao fim do método, usando a agregação da KAN-17. Essa aproximação pode atrasar a primeira falha em métodos com várias invocações. [Agregação KAN-17](../KAN-17/README.md)

Duração medida igual a zero é válida para método executado ou fase aplicável. Fase inaplicável tem custo zero. Método comprovadamente todo ignorado fica fora dos testes executados e das detecções. Eventual custo do runner ao processar skips pertence ao relógio do runner. Uma fase aplicável sem duração, ordem não recuperável, preparo exigido sem medição, resultado sem associação ou duração faltante de método executado que alcance a fronteira de cálculo torna o corte afetado indisponível. Preserve prefixos conhecidos quando já se sabe que o corte terminou antes da lacuna. Ausência de linha de resultado também é lacuna. Evite imputação de zero, ordenação por arquivo e substituição do tempo do executor pela soma dos XML. Distinga um prefixo válido e vazio, por exemplo quando o overhead supera B, de um prefixo indisponível. Compare os quatro cenários no conjunto comum com dados válidos por limite e reporte os motivos e a cobertura dos demais.

## Verificação

Na condição controlada de execução serial, a referência anterior fictícia é 103 ms. Os métodos A, B, C e D custam 20, 15, 10 e 36 ms, com falhas em B e C. T0 executa A–D e T1–T3 compartilham A–C. Todos começam com 5 ms de preparo. A seleção custa 5 ms, as features custam 4 ms e as inferências KNN e Random Forest custam 1 e 12 ms, respectivamente. A tabela indica métodos concluídos e falhas creditadas.

| Cenário e ordem | 25 ms | 51 ms | 77 ms |
| --- | --- | --- | --- |
| T0 · A B C D | A / nenhuma | A B C / B C | A B C / B C |
| T1 · A B C | nenhum / nenhuma | A B / B | A B C / B C |
| T2 · C B A | C / C | C B / C B | C B A / C B |
| T3 · B C A | nenhum / nenhuma | B C / B C | B C A / B C |

T0 conclui A e T2 conclui C exatamente em 25 ms. T1 tem 15 ms disponíveis para testes nesse limite e seu primeiro método custa 20 ms. T3 consome 26 ms antes de começar os testes. O verificador também cobre piso para referência curta, ausência de referência, fase e duração faltantes em cada cenário, skip, zero medido e preservação do prefixo antes de uma lacuna.

A checagem somente leitura de `KAN-16/resumo-lote.json` calcula os seguintes valores para uso **como calibração de uma revisão posterior**, condicionado à disponibilidade anterior comprovada. Os SHAs completos e tentativas estão no resumo. O lote foi coletado em Linux/amd64, Temurin 21.0.11, Maven 3.9.11, UTC e cache Maven frio. [Resumo KAN-16](../KAN-16/resumo-lote.json) · [Entrega 3](../ENTREGA-3/README.md)

| Posição do T0 | SHA abreviado | Parede (ms) | 25% (ms) | 50% (ms) | 75% (ms) |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `921c1b4` | 291482 | 72870 | 145741 | 218611 |
| 26 | `04cc033` | 283184 | 70796 | 141592 | 212388 |
| 50 | `f24c027` | 292398 | 73099 | 146199 | 219298 |
| 75 | `bfcaa94` | 291649 | 72912 | 145824 | 218736 |
| 100 | `598dfc1` | 306912 | 76728 | 153456 | 230184 |

Execute da raiz do repositório:

```powershell
./evidencias/KAN-24/verificar.ps1
git diff --check HEAD -- evidencias/KAN-24
git log -1 --format=%H -- evidencias/KAN-24
```

## Integração com KAN-23 e KAN-26

O [replay serial da KAN-23](../KAN-23/README.md) aplica esta regra aos CSVs KAN-15 e inclui uma fixture controlada que reproduz a tabela acima.

No avaliador, resolva a referência histórica juntando `commits` e `t0_runs`, com proveniência da tentativa e corte de disponibilidade. Após congelar seleção e rankings, junte `t0_results` por `(commit_sha, test_id)`, leia `overhead` por SHA, cenário e fase, e incorpore as medições compatíveis de preparo e runner. Aplique os três cortes aos mesmos eventos de cada cenário. Entregue à KAN-26, por SHA, cenário e percentual, a referência do limite, seu valor, o estado de disponibilidade e o prefixo com instantes acumulados e desfechos. Limites, durações, resultados e derivados do próprio SHA avaliado ficam no avaliador. Features históricas seguem o corte de observabilidade da KAN-15/KAN-19.

O verificador exercita a aritmética e o corte serial. A aplicação principal depende de uma linha do tempo comparável e da integração com a KAN-23. A KAN-16 informa zero métodos com ordem global observada no lote, dois métodos executados sem duração válida e zero falhas naturais. Os tempos de parede e as somas por método cobrem intervalos diferentes. A coleta atual permite conferir a calibração, mas não sustenta uma comparação observada de detecção T0–T3 sob orçamento. As métricas da Entrega 2 permanecem as aprovadas, inclusive detecção relativa somente com denominador positivo, primeira falha não observada quando aplicável e APFDc complementar na população compartilhada de T1–T3. [KAN-23](https://cin-team-test-prioritization.atlassian.net/browse/KAN-23) · [KAN-26](https://cin-team-test-prioritization.atlassian.net/browse/KAN-26)
