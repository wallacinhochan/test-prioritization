# Relatório científico provisório

## Objetivo e desenho

Investigar em Apache Commons Lang o trade-off entre reduzir a suíte e preservar detecção e o efeito de reordenar a seleção quando o tempo é limitado. A RQ1 trata de tempo, redução, detecção e overhead. A RQ2 trata de feedback sob limites iguais de tempo. O método de teste é a unidade e o SHA é a unidade do pareamento. T0 é a suíte completa, T1 é a seleção em ordem de referência, T2 usa KNN e T3 usa Random Forest. O protocolo define os recortes cronológicos e o contrato KAN-15 0.1.0 governa as junções por SHA e método. [Protocolo aprovado](https://docs.google.com/document/d/13vJhblJTfYqXugi6Vey-nF3gxNk_Um_n/edit) · [Contrato KAN-15](https://cin-team-test-prioritization.atlassian.net/browse/KAN-15) · [Critérios KAN-32](https://cin-team-test-prioritization.atlassian.net/browse/KAN-32)

## Coleta, processamento e auditoria das fontes

Os comandos Git abaixo podem ser executados neste worktree para localizar as fontes versionadas no repositório compartilhado. Os comandos de reprodução nos READMEs devem ser executados no checkout do produtor, fixado na revisão correspondente, com os pré-requisitos e caminhos de saída indicados. A reprodução do relatório completo depende do futuro manifesto KAN-29.

| Fonte Git e arquivo | Evidência auditada e condição de uso |
|---|---|
| `670381c:evidencias/KAN-18/veredito-operacional.md` e `ba7f204:evidencias/KAN-18/entrega-treino-03.md` | Piloto do DIRTS em 49–50, replay de mutantes em 26 e 50 e decisão experimental pela expansão direta. Lotes `ef57715`, `41a22e3` e `ba7f204` fixam seleção, ranking T1 e custo quando medido. Em 15 e 42, foram 318 e 153 selecionados pela expansão e zero pelo DIRTS puro. Os três lotes documentam seleção materializada para 15 de 100 posições e 85 lacunas naquele instantâneo. O denominador é o universo listado e a cobertura é de seleção. |
| `d2c0e7a:evidencias/KAN-19/avaliacao-expansao50.json` | Replay sintético auxiliar da revisão 50, sobre rankings congelados em `a06d381`. Os hashes, IDs e postos antecedem a junção aos rótulos. O pacote versionado tem hash de rótulos-fonte diferente do resumo histórico. Usar os registros do pacote efetivamente avaliado. A síntese por mutante está na [análise](../KAN-30/analise-provisoria.md). |
| `edf1259:evidencias/KAN-22/validacao-dirts.json` | Três features de assinatura reproduzem 416 vetores da revisão 50. O treino congelado tem 524 alvos conhecidos, 181 positivos, em 15, 26 e 42. No replay técnico, o marco experimental habilita ajuste em 51 e reuso em 61, 71, 81 e 91. Rankings técnicos em 64, 75 e 100 têm 26, 7 e 4.663 métodos por cenário, com custo de seleção desconhecido. O exercício histórico com disponibilidade vazia produz zero rankings históricos. A posição 96 figura somente na cronologia dessa fonte. |
| `c6e1ca1:evidencias/KAN-23/README.md` e `8e91fa5:evidencias/KAN-23/coleta/resultado-piloto-50.json` | Replay determinístico de prefixos e piloto físico de uma classe na revisão 50. O piloto registra 351 eventos, 164 casos conciliados com XML, 12 invocações parametrizadas e um skip. A classe é uma verificação do instrumento. |
| `8bf6ebc:evidencias/KAN-25/README.md`, `evidencias/KAN-26/README.md` e `evidencias/KAN-27/README.md` | Fixture controlada com quatro métodos elegíveis, dois falhos e três selecionados em T1–T3. Tempos T0/T1/T2/T3 de 99/55/60/71 ms, redução de 0/25/25/25%. Referência sintética de 103 ms produz 25/51/77 ms. Falhas nos três cortes são T0 0/2/2, T1 0/1/2, T2 1/2/2 e T3 0/2/2. APFDc de T1/T2/T3 é 0,25/0,75/0,694444… sobre a população comum. São verificações de fórmula. |

Na inspeção local, `ba7f204` e `8e91fa5` eram as pontas dos worktrees produtores. O worktree do DIRTS tinha trabalho local de lote 04 com seleção para 58–60. O da coleta tinha alterações locais para ensaios de suíte em 49–50, com reconciliação JUnit/XML e ancoragem de relógios proposta. São pontos de integração sujeitos a publicar revisão, validar os artefatos e confirmar a proveniência. Os totais versionados acima correspondem aos SHAs indicados.

## Reprodução dos componentes

| Componente | Comando ou instrução no checkout produtor |
|---|---|
| Congelamento do treino KAN-18 | Seguir a seção Reprodução de `git show ba7f204:evidencias/KAN-18/entrega-treino-03.md`, com Docker Linux e tarballs das revisões e primeiros pais. |
| Avaliação sintética em 50 | `python -B evidencias/KAN-19/avaliar_expansao50.py` conforme o README em `d2c0e7a`. |
| Janela expansiva | `python -B evidencias/KAN-22/validar_dirts.py dirts-consumo` conforme o README em `edf1259`. |
| Simulação e métricas controladas | `python -B evidencias/KAN-23/simular.py evidencias/KAN-23/fixtures` no checkout KAN-23. Passar os mesmos dados e o JSON gerado ao CLI `python -B evidencias/KAN-25/metricas.py <dados> <replay.json>` em `8bf6ebc`. |
| Piloto físico | Seguir a seção do piloto em `git show 8e91fa5:evidencias/KAN-23/README.md`, com a imagem KAN-13 e pasta nova para os rastros. |

## Integração do pacote KAN-29

1. Registrar caminho, commit e hashes do manifesto e das entradas. Identificar universo, período, partições e elegibilidade, ordem cronológica, parâmetros, versões, seeds, referências de coleta e exclusões. Identificar separadamente as entradas principais e complementares. O holdout permanece fechado nesta rodada.
2. Por SHA e cenário, unir inventário e resultados T0, seleção, postos e overhead pelo contrato KAN-15. Conferir igualdade das chaves em T1–T3 e postos contíguos. Documentar versão e ordem das features, janela, disponibilidade e evento de treino. Preservar origem dos dados, tentativas, timestamps, configuração, duração, custos de inicialização e lacunas.
3. Exigir reconciliação do oráculo e evidência de validação física KAN-28. De cada limite, rastrear referência histórica, corte de publicação e prefixo. Publicar resultados brutos, saídas reproduzíveis e o comando executado, com versão e hash. A trilha deve permitir refazer cada tabela por SHA, cenário e limite. [KAN-29](https://cin-team-test-prioritization.atlassian.net/browse/KAN-29)
4. Inserir tabelas e figuras usando a matriz da [análise](../KAN-30/analise-provisoria.md). Redigir respostas diretas, com denominadores e limites. Atualizar o registro de [ameaças](../KAN-31/ameacas-validade.md) conforme as lacunas reais, reconciliar unidade, períodos, features e budgets com o protocolo e registrar a revisão do relatório. Só então fechar a versão científica e integrar as conclusões ao [roteiro](../KAN-33/roteiro.md).
