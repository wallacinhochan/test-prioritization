# KAN-19 — Dataset temporal por revisão e método

O dataset mantém o Apache Commons Lang, os 100 SHAs da KAN-10 e a identidade exata `classe#metodo(tipos)` da KAN-17. As entradas de KNN e Random Forest são as mesmas sete features estáticas sobre os métodos selecionados em T1. A decisão da KAN-12 destina os rótulos sintéticos ao treino. Os resultados de validação e teste sintéticos do piloto permanecem nas evidências de mutação. [Cartão KAN-19](https://cin-team-test-prioritization.atlassian.net/browse/KAN-19) · [Decisão KAN-12](../KAN-12/README.md) · [Contrato KAN-15](../KAN-15/README.md) · [Identidade KAN-17](../KAN-17/README.md) · [Piloto de mutação](../MUTACAO/modelos/README.md)

## Variáveis e observabilidade

| Variável | Proveniência e instante de observação | Disponibilidade e ausência |
| --- | --- | --- |
| `distancia_rota` | Número de arestas na rota estática do T1 entre a classe de teste e a semente, calculável após descoberta e diff com o primeiro pai, antes dos testes do SHA alvo. | 23.260/23.260 linhas T1. Sem rota, codifica 0 junto com `rota_ausente=1`. |
| `rota_ausente` | Indicador de classe sem rota nas decisões pré-execução do T1. | 23.260/23.260. Distingue ausência de rota de distância zero até a própria semente. |
| `arestas_lexicais` | Arestas da rota cuja evidência vem de referência no fonte, antes da execução. | 23.260/23.260. Sem rota, codifica 0 junto com `rota_ausente=1`. |
| `classe_semente` | Indicador de classe semente no grafo do T1, disponível após diff e análise estática. | 23.260/23.260. |
| `comprimento_nome` | Comprimento do nome Java na identidade descoberta do método, antes da execução. | 23.260/23.260. |
| `quantidade_parametros` | Número de tipos de parâmetros na assinatura descoberta, antes da execução. | 23.260/23.260. |
| `classe_aninhada` | Indicador de `$` no nome binário da classe da identidade descoberta, antes da execução. | 23.260/23.260. |
| `recent_failures` | Contagem de falhas de teste nas dez posições anteriores do recorte, por chave exata e apenas entre T0 completos com aprovação ou falha observada. Uso preditivo exigiria resultados publicados antes do ranking. | Disponibilidade pré-ranking histórica 0/23.260. Até no replay hipotético, 0/23.260 têm observações nessa janela. Vazio se o denominador é zero. |
| `past_failure_rate` | Falhas de teste divididas pelas observações `pass` ou `fail` em T0 completos, acumuladas nas posições estritamente anteriores. | Disponibilidade pré-ranking histórica 0/23.260. No replay hipotético, 23.184/23.260 têm denominador, com taxa zero observada. Vazio sem denominador. |
| `past_mean_ms` | Média da duração agregada do método em posições estritamente anteriores, entre resultados executados, medidos e de T0 completo. | Disponibilidade pré-ranking histórica 0/23.260. No replay hipotético, 23.184/23.260 têm duração histórica. Vazio sem medição, zero preservado quando medido. |

A KAN-11 encontrou lacunas nas fontes históricas. As cinco execuções KAN-16 foram coletadas em 2026 para commits de 2025. A posição KAN-10 ordena a simulação pelo primeiro pai. Dispor de um resultado mais antigo nessa ordem não comprova que ele estivesse publicado no instante histórico da decisão. Em `historico_replay.csv`, simula-se a disponibilização de cada T0 completo ao terminar sua posição. Essa tabela é uma auditoria de cobertura. Seu uso em um protocolo futuro exigiria registrar a disponibilidade antes do ranking e contabilizar a coleta de T0. [KAN-11](../KAN-11/README.md) · [KAN-16](../KAN-16/README.md)

O vetor compartilhado é a lista `features_modelo` no resumo. SHA, posição, identidade, partição, alvos, contagens de rótulos e auditoria de histórico são metadados ou saídas auxiliares. As sete entradas estão completas na população disponível. Zero com indicador de rota ausente é uma codificação estrutural. A exportação preserva os valores brutos. Para reproduzir a transformação do piloto, ajuste o escalonamento padrão do KNN exclusivamente nos exemplos de treino de cada janela e aplique os mesmos parâmetros às revisões posteriores. A Random Forest usa as mesmas colunas sem escalonamento. Uma revisão sem inventário T1 fica sem vetor e um método sem observações sintéticas conhecidas fica sem alvo. [Implementação de referência do piloto](../MUTACAO/modelos/README.md)

## Partições e saídas

Para este dataset, adotei os limites de posição 42 e 50 para refletir a divisão já congelada no piloto. Os limites classificam todos os 100 SHAs, inclusive os sem dados. A avaliação principal depende de seleção e oráculo comparáveis na mesma revisão.

| Partição | Posições do recorte | T0 completos | Métodos T0 `pass` / `skip` | T1 congelado disponível | Pares T1 com T0 |
| --- | --- | --- | --- | --- | ---: |
| Treino | 1–42 | 1, 26 | 9.279 / 22 | 15, 26, 42 | 4.648 |
| Validação | 43–50 | 50 | 4.646 / 11 | 50 | 4.653 |
| Avaliação | 51–100 | 75, 100 | 9.299 / 23 | 96 | 0 |

- `features_t1.csv` contém uma linha por `(commit_sha,test_id)` selecionado em T1. A população e as rotas vêm do artefato congelado do piloto e seus hashes são conferidos contra o manifesto por revisão.
- `treino_sintetico.csv` junta as features ao alvo `induced_failure / (induced_failure + pass)` das posições 15, 26 e 42. Reutiliza as verificações de chave, inventário, hashes, controle, repetição e restauração do piloto. Das 13.948 linhas T1 de treino, 13.915 têm alvo, sendo 290 com alvo maior que zero. Os replays registram 309 falhas induzidas, 55.351 aprovações, 132 observações desconhecidas e zero linhas de rótulo ausentes em T1. Desconhecidos e ausências ficam fora do denominador. Um conjunto de treino para replay deve estar preparado e congelado antes do ranking das revisões posteriores.
- `oraculo_t0.csv` preserva tentativa, desfecho, duração, ordem e referência KAN-16. O rótulo natural é 0 para aprovação em T0 completo e fica vazio para skip, tentativa incompleta ou falha sem atribuição. Nesta evidência, há zero falhas de teste em T0. Para uma futura exportação com falhas, a classificação de positivos exige análise por causa e confirmação de episódios independentes conforme KAN-11. As 95 posições sem T0 conservam a lacuna em `cobertura.csv`.
- `historico_replay.csv` enumera os denominadores e posições-fonte por método selecionado. A lista usa posições da KAN-10 e inclui somente resultados executados que contribuem ao denominador histórico.
- `cobertura.csv` registra cobertura por SHA dos 100 candidatos, com o estado de elegibilidade original da KAN-10 e contagens das referências disponíveis. T1 ausente fica vazio. T1 disponível com zero junções tem contagem zero.

A janela de avaliação tem dois T0 completos sem positivos naturais e nenhum par T1–T0. A validação tem pares comparáveis na posição 50 e zero positivos naturais. A ordem global de T0 continua indisponível. A evidência atual permite verificar o dataset e a integração de rótulos sintéticos. A avaliação natural de detecção e a suficiência de episódios entre janelas continuam sem suporte. A janela expansiva e o reajuste a cada dez commits ficam com a etapa de treinamento prevista na Entrega 2.

## Reprodução e verificação

Na raiz do repositório, use CPython 3.12.14 e Git no PATH. São necessários os CSVs locais da KAN-16 em `evidencias/KAN-16/local/lote/` e os replays publicados das posições 15, 26 e 42 em `evidencias/MUTACAO/mutantes/local/`. O procedimento da KAN-16 descreve como reexportar os CSVs a partir das referências brutas. Um replay indisponível ou reprovado fica registrado no resumo e deixa o treino parcial. Um CSV de T0 ausente ou hash divergente interrompe a exportação. [Reprodução KAN-16](../KAN-16/README.md#reprodução) · [Replays e rótulos](../MUTACAO/mutantes/README.md)

```powershell
$kanPython = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
& $kanPython -B evidencias/KAN-19/dataset.py confirmacao
& $kanPython -B evidencias/KAN-19/dataset.py repeticao
Get-FileHash evidencias/KAN-19/local/confirmacao/resumo.json
Get-FileHash evidencias/KAN-19/local/repeticao/resumo.json
```

Use nomes de execução novos. As duas execuções produziram resumos idênticos com os mesmos hashes dos cinco CSVs. O [resumo versionado](resumo.json) registra código, entradas, população e fontes verificadas. Os CSVs gerados ficam em `local/`.

O pipeline compara cada linha da auditoria com o cálculo sobre o prefixo anterior isolado e com um cálculo que substitui todos os resultados da posição alvo em diante por falhas e durações artificiais. Os valores e a proveniência permaneceram idênticos nas cinco posições T1. A verificação independente conferiu unicidade das chaves, 9.301 pares T1–T0, identidade dos vetores entre features e treino, treino restrito a 15/26/42 e ancestralidade estrita por posição das fontes históricas. Um caso de controle confirmou que o histórico reage a uma falha anterior, preserva a duração zero e mantém ausências vazias. As features operacionais são calculadas somente na função que recebe recorte e seleção estática congelada. Os resultados T0 e os rótulos entram nos seus próprios fluxos depois dessa seleção.
