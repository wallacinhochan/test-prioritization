# KAN-18 — T1 experimental congelado para KAN-19–21

A variante `dirts-expansao-direta-reuso/1.0.0` congela a união da seleção DIRTS com os métodos JUnit de classes-raiz que dependem diretamente de classes Java de produção alteradas. A ordenação T1 é ordinal por `test_id` em cada SHA. A expansão se aplica também ao diff documental da posição 4. A posição 100 usa o inventário integral como fallback de configuração. O lote segue o veredito `670381c27d7ff48983e8fd097d52ba3878b94a1e` e mantém a versão **0.1.0** do contrato KAN-15. [Veredito](veredito-operacional.md) · [Contrato](../KAN-15/README.md)

## Entrega e cobertura

| Arquivo | Conteúdo |
|---|---|
| [commits.csv](congelado-expansao-v1/commits.csv) | 100 posições auditadas, com os estados de elegibilidade originais |
| [selection.csv](congelado-expansao-v1/selection.csv) | 51.225 candidatos de 11 revisões, com motivo de seleção ou exclusão |
| [rankings.csv](congelado-expansao-v1/rankings.csv) | 6.689 candidatos selecionados, com postos contíguos |
| [overhead.csv](congelado-expansao-v1/overhead.csv) | 11 registros de seleção, dois medidos e nove desconhecidos |
| [manifesto.json](congelado-expansao-v1/manifesto.json) | SHA e pai, política, fallback, hashes de entradas e saídas, linhagem e tempos brutos |
| [cobertura.csv](congelado-expansao-v1/cobertura.csv) | 100 SHAs, com partição, estado da seleção, continuidade, holdout e contagens |
| [rotas.csv](congelado-expansao-v1/rotas.csv) | 278 pares revisão–classe-raiz selecionada, com arestas diretas disponíveis e seleção DIRTS puro |

O Git confirmou os 100 SHAs, seus primeiros pais, horários de commit e 99 vínculos consecutivos. O reuso cronológico ficou comprovado apenas em **49–50**, a partir do estado criado na posição 48. Os conjuntos de 4, 26 e 75 provêm de execuções isoladas. Os de 11, 39, 46, 64 e 96 provêm do piloto histórico com estado reancorado, sem equivalência cronológica comprovada para esses pares. A posição 100 provém do fallback integral. Os **89 SHAs restantes** têm seleção indisponível e nenhuma linha em seleção, ranking ou overhead. A continuidade verificada do recorte Git e a continuidade demonstrada do estado aparecem separadamente.

A seleção cobre 4, 11, 26 e 39 no treino, 46, 49 e 50 na validação, e 64, 75, 96 e 100 na avaliação. O holdout 96 preserva apenas candidatos e evidência de seleção. O exportador não usa rótulos, duração, ordem ou desfecho do T0. O inventário T0 e o conjunto DIRTS puro são recuperáveis por SHA, respectivamente da população de `selection.csv` e das classes marcadas como DIRTS em `rotas.csv`. Os hashes dos dois conjuntos constam no manifesto.

## Custo medido

| Fase | Posição 49 | Posição 50 |
|---|---:|---:|
| Inicialização do estado na posição 48 | 118,754 s | — |
| Preparação da árvore e validação do estado anterior | 0,372 s | 0,673 s |
| DIRTS | 40,212 s | 35,549 s |
| Selo do estado | 0,035 s | 0,034 s |
| Compilação, inventário e jdeps | 54,608 s | 42,067 s |
| Validação da seleção e expansão | 0,267 s | 0,253 s |
| **Overhead KAN-15 de seleção** | **214.246 ms** | **78.575 ms** |
| Maven test da expansão e coleta de XML | 16,640 s | 157,909 s |
| Referência T0, extração mais Maven test e coleta de XML | 356,991 s | 310,550 s |

A fase KAN-15 `selection` inclui o custo inicial onde ele foi incorrido, até a lista estar pronta. Os valores brutos em nanossegundos permitem recalcular custos em regime. A execução de testes e os controles de validação ficam fora de `overhead.csv`. O lote ainda carece de medições de features, inferência e treinamento. Os tempos do piloto histórico têm outro escopo e ficam vazios no contrato deste lote. [Medição física](reuso-filtro.md)

## Handoff para KAN-19–21

1. KAN-19 deve importar `selection.csv` e `rankings.csv` pelo par `(commit_sha, test_id)`. As features de assinatura continuam deriváveis dos IDs. Em 1.693 métodos há aresta direta de bytecode verificável por `rotas.csv`. Em 333 métodos há inclusão sem evidência de rota nessa exportação. Outros 4.663 entram por fallback integral. Uma aresta jdeps suporta distância direta na hipótese experimental. Ela não fornece a rota lexical do vetor antigo. As features `distancia_rota`, `rota_ausente`, `arestas_lexicais` e `classe_semente` precisam de política de extração versionada para este T1. Evidência ausente deve permanecer distinguível de ausência de rota comprovada. Os modelos antigos exigem compatibilidade do vetor antes do uso.
2. Para a primeira execução técnica de ranking, priorizar a posição 50, com 416 IDs congelados e sobreposição com os dados de KAN-19. Os 56 IDs da posição 26 dão um primeiro conjunto cronologicamente anterior. As posições de treino 15 e 42 do piloto anterior ainda carecem de seleção da nova variante. Conservar a janela de treino aprovada e registrar qualquer execução técnica com janela reduzida como experimento novo. Preservar o holdout 96 fora de treino, ajuste e escolha de features.
3. KAN-20 e KAN-21 devem usar a mesma população e a mesma versão do vetor, verificar igualdade das chaves e postos contíguos e transportar a linha `selection` para T2/T3. Registrar suas fases próprias de features e inferência, além do evento de treino quando aplicável. Fixar rankings antes de juntar o oráculo. O lote destrava a integração por chave. A avaliação completa depende da cobertura de features e rótulos.

## Reprodução e verificações

Na raiz do worktree, em PowerShell, use uma pasta de saída nova:

```powershell
python -B evidencias/KAN-18/congelar-expansao.py ../KAN-18-checkout ../KAN-10-upstream.git evidencias/KAN-18/local/reuso-49-50-v2 evidencias/KAN-18/local/congelamento-repetido
```

Duas exportações produziram os mesmos bytes para todas as saídas. Uma checagem independente validou os cabeçalhos KAN-15, SHA-256, UTF-8 sem BOM, unicidade e chaves, pós-condições de seleção, igualdade do ranking com o conjunto selecionado, reconstrução dos conjuntos DIRTS/T0, cobertura de rotas e preservação do holdout. A reprodução bruta usa os artefatos locais já coletados. A leitura das tabelas congeladas pelos consumidores é independente desses diretórios locais.
