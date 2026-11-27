# KAN-19 — Dataset temporal por revisão e método

## Expansão direta congelada na revisão 50

`expansao50.py` lê as tabelas diretamente do commit KAN-18 `ef577158bc012d87784bbfab1b9ccb4ee80cf812`. Confere os hashes, a identidade do SHA e primeiro pai, e a igualdade do ranking com os 416 IDs selecionados em T1. O hash SHA-256 do conjunto canônico é `89405dc449113d63f2394ee4dbf506a34505f31721403fdc9bf11ce34a37dcb7`.

A política `expansao-direta/assinatura-v1` usa comprimento do nome, número de parâmetros e indicador de classe aninhada, derivados da identidade JUnit antes da execução. O CSV de auditoria preserva a evidência separadamente. Nos 368 métodos com aresta direta de bytecode, a auditoria registra distância 1 e `rota_ausente=0`. Nos 48 métodos com `sem_evidencia_rota`, os dois campos ficam vazios. Esse estado indica desconhecimento. `arestas_lexicais` e `classe_semente` ficam vazias em todas as linhas, pois a exportação fornece a aresta e as sementes de destino, sem as medidas do vetor anterior.

### Compatibilidade do treino

A janela sintética é 15, 26 e 42. `auditar_treino_expansao.py` importa os CSVs de replay do PR #2 em `1070e62788e9a180539c9df7ca10b65d48ee978c`. Valida os checksums, a proveniência, os inventários, as chaves dos mutantes e os alvos recalculados a partir das observações. Deriva novamente as três features de assinatura e confere sua igualdade com as colunas correspondentes do pacote. O cálculo usa `induced_failure / (induced_failure + pass)`.

| Posição | Métodos no pacote | Alvos conhecidos | Alvos positivos | Cruzamento com o novo T1 |
| ---: | ---: | ---: | ---: | --- |
| 15 | 4.651 | 4.640 | 185 | Seleção indisponível |
| 26 | 4.652 | 4.641 | 10 | 56 IDs, 53 alvos conhecidos, 9 positivos |
| 42 | 4.657 | 4.646 | 15 | Seleção indisponível |

Na posição 26, a interseção tem 11 falhas induzidas, 201 aprovações e 12 observações desconhecidas. Três métodos ficam com alvo vazio. O hash do inventário concorda com o resumo do replay histórico. O hash dos rótulos-fonte informado pelo pacote concorda com o resumo versionado; a proveniência registra outro hash para o resumo local. Na posição 15, o pacote representa a coleta alternativa documentada, com 203 falhas induzidas frente às 280 do resumo histórico. Na 42, as contagens concordam e os hashes de rótulos identificam coletas distintas. A auditoria mantém o pacote do PR #2 como fonte única e expõe as diferenças.

```powershell
python -B evidencias/KAN-19/auditar_treino_expansao.py
python -B -m unittest discover -s evidencias/KAN-19 -p test_auditar_treino_expansao.py -v
```

Para uma publicação que complete a janela, execute o mesmo auditor com `--t1 SHA_COMPLETO --rodada NOME`. O ajuste experimental exige alvos conhecidos em todas as três posições, pelo menos 15 exemplos, alvos positivos e alvos zero. A saída inclui treino por chave, rankings e overhead com hashes em um diretório novo. O alvo continua sendo a revisão 50 original de 416 IDs. O fluxo atual recusa o ajuste com a publicação incompleta.

O fluxo técnico ajusta KNN com `StandardScaler` e Random Forest com os parâmetros do piloto sobre os mesmos 16 exemplos artificiais, sem balanceamento. O treino usa apenas a fixture. O oráculo e os rótulos do holdout 96 ficam fora do fluxo. Os resultados são gravados em `rankings_fixture.csv` e `overhead_fixture.csv`, com manifesto marcado `teste_tecnico_fixture_sem_ranking_experimental`.

### Reprodução e custos

Na raiz do worktree, com o commit congelado disponível no Git e nomes de rodada novos:

```powershell
python -B evidencias/KAN-19/expansao50.py rodada-a
python -B evidencias/KAN-19/expansao50.py rodada-b
python -B -m unittest discover -s evidencias/KAN-19 -p test_expansao50.py -v
```

O teste compara as chaves, escores e postos dos dois cenários em duas execuções, além dos bytes do vetor e dos hashes de saída. Os 416 IDs de cada cenário coincidiram exatamente com T1 e os postos foram contíguos, com empate ordinal. As rodadas locais usaram Python 3.11.0 e scikit-learn 1.9.1.

| Fase | Rodada A (ms) | Rodada B (ms) |
| --- | ---: | ---: |
| Seleção herdada da KAN-18 | 78.575 | 78.575 |
| Extração compartilhada | 4,857 | 4,416 |
| Ajuste KNN com fixture | 944,168 | 107,178 |
| Inferência T2 | 5,039 | 3,720 |
| Ajuste RF com fixture | 252,536 | 329,908 |
| Inferência T3 | 19,269 | 28,026 |

A extração mede a montagem dos vetores e das linhas de auditoria em memória uma vez por SHA. A inferência mede preparo da matriz, predição, ordenação e montagem das linhas. Medições locais excluem I/O, verificações, descoberta JUnit e jdeps. O manifesto registra nanossegundos. A fase `selection` preserva a referência e a medição publicada.

Para a KAN-22, a validação de contrato e tempos de integração está disponível. A emissão de escores experimentais depende de congelar as seleções das posições 15 e 42 e verificar a cobertura rotulada por chave. Uma janela reduzida exige decisão específica e evidência própria. A junção ao oráculo vem após o congelamento dos rankings experimentais.

## DIRTS provisório

`dirts.py` vincula cada seleção à [verificação DIRTS publicada](../KAN-18/verificacao-dirts.json). Confere posição, SHA, primeiro pai, hash do recorte, versão, imagem, hashes das cinco saídas e hash do inventário JUnit. Confere a seleção completa por `(commit_sha, test_id)`, a raiz de execução, o motivo por classe e a ordem de T1. As posições 50, 75 e 100 forneceram respectivamente 72, 7 e 4.663 métodos.

O vetor provisório usa comprimento do nome, quantidade de parâmetros e classe aninhada, disponíveis na identidade descoberta antes da execução. As quatro features de rota ou semente da publicação anterior ficam fora deste vetor. A rematerialização oficial depende do parecer da KAN-18, da aprovação do contrato de features e de treino sintético compatível e congelado.

Na raiz do worktree, aponte para os artefatos locais da publicação verificada. Para os rankings de integração, o programa usa 16 exemplos de fixture com alvos fabricados e os parâmetros dos modelos do piloto. O fluxo usa apenas as entradas do seletor, o recorte e essa fixture.

```powershell
$env:KAN18_DIRTS = (Resolve-Path ../KAN-18-checkout/evidencias/KAN-18/local/dirts).Path
python -B evidencias/KAN-19/dirts.py rodada-a --kan18-local $env:KAN18_DIRTS
python -B evidencias/KAN-19/dirts.py rodada-b --kan18-local $env:KAN18_DIRTS
python -B -m unittest discover -s evidencias/KAN-19 -v
python -B -m unittest discover -s evidencias/MUTACAO/modelos -v
```

Use nomes de rodada novos. Cada uma gera `features_inferencia.csv`, `rankings.csv`, `overhead.csv` e `manifesto.json` em `local/dirts-provisorio-<rodada>/`. O manifesto marca `provisorio_fixture` e registra hashes, ambiente, cobertura e custos. O teste reproduz vetores, escores e postos em duas execuções e rejeita um ranking T1 alterado. A execução local usou Windows x64, Python 3.11.0 e scikit-learn 1.9.1. As versões completas constam no manifesto gerado.

### Custos do teste de integração

Uma rodada local produziu as medições abaixo em milissegundos. A extração mede a montagem dos vetores e linhas com as identidades em memória. É uma medição compartilhada por SHA, registrada nos dois cenários para leitura isolada de cada cenário. A inferência inclui preparar a matriz, escalonar no KNN, prever, ordenar e montar as linhas. As duas janelas excluem I/O, hashes, verificação de contrato e descoberta JUnit. A seleção é herdada da KAN-18. O ajuste com fixture é registrado separadamente.

| Posição | Métodos | Extração (ms) | Inferência T2 (ms) | Inferência T3 (ms) |
| ---: | ---: | ---: | ---: | ---: |
| 50 | 72 | 0,480 | 4,009 | 30,952 |
| 75 | 7 | 0,056 | 2,474 | 38,567 |
| 100 | 4.663 | 25,730 | 99,318 | 79,358 |

Os resultados das seções seguintes pertencem às publicações históricas da KAN-19.

O dataset mantém o Apache Commons Lang, os 100 SHAs da KAN-10 e a identidade exata `classe#metodo(tipos)` da KAN-17. As entradas de KNN e Random Forest são as mesmas sete features estáticas sobre os métodos selecionados em T1. A decisão da KAN-12 destina os rótulos sintéticos ao treino. [Cartão KAN-19](https://cin-team-test-prioritization.atlassian.net/browse/KAN-19) · [Decisão KAN-12](../KAN-12/README.md) · [Contrato KAN-15](../KAN-15/README.md) · [Identidade KAN-17](../KAN-17/README.md)

## Inferência e cobertura do estudo principal

`principal.py` usa a publicação da KAN-18 em `260c1af381b3137b1591af9f33e47e987ac7b2b2`. Confere posição, SHA, primeiro pai e hash da KAN-10. Compara o manifesto de cada seleção em `KAN-18/local/selecao/<sha>/` com a verificação versionada, valida os cinco hashes de saída e confere o hash do inventário em `KAN-18/local/entradas/<sha>/metodos.tsv`. Valida chaves do inventário, da seleção e do ranking, caminhos das referências, decisões por classe e postos ordinais. Usa a classe raiz da descoberta nas features de rota e a assinatura exata nas features do método. [KAN-18](../KAN-18/README.md) · [Verificação publicada](../KAN-18/verificacao.json)

| Posição KAN-10 | Métodos selecionados com features | Métodos T0 completo | Pares T1–T0 |
| ---: | ---: | ---: | ---: |
| 1 | 4.649 | 4.649 | 4.649 |
| 2 | 4.649 | — | — |
| 26 | 4.648 | 4.652 | 4.648 |
| 50 | 4.653 | 4.657 | 4.653 |
| 75 | 7 | 4.659 | 7 |
| 100 | 4.663 | 4.663 | 4.663 |
| **Total** | **23.269** | **23.280** | **18.620** |

- `features_inferencia.csv` contém as mesmas chaves e ordem de cada `rankings.csv` formal. SHA, posição e método identificam a linha. As sete colunas preditivas estão preenchidas nas 23.269 linhas e seguem a proveniência e a codificação da tabela abaixo.
- `cobertura_principal.csv` contém os 100 SHAs. A seleção está disponível em 6, dos quais 5 têm T0 completo. A posição 2 tem features e uma lacuna no oráculo. As 94 posições restantes têm seleção e T0 indisponíveis.
- `juncao_t1_t0.csv` contém a interseção por `(commit_sha, test_id)` com o oráculo completo, em arquivo próprio. Preserva `pass`, `skip`, duração, ordem e referência da KAN-16. Os 18.620 pares pertencem aos cinco SHAs com T0. Houve zero falhas e zero positivos naturais observados. A ordem global segue indisponível.

Os cortes 42 e 50 classificam somente a auditoria inicial abaixo. Os CSVs do estudo principal registram posição cronológica e cobertura para os seis SHAs formais, sem atribuir partições. Detecção e antecipação de falhas naturais continuam sem suporte na amostra.

Na raiz do repositório, com os arquivos locais da publicação KAN-18 e os CSVs KAN-16 disponíveis, execute com nomes novos:

```powershell
$kanPython = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
& $kanPython -B evidencias/KAN-19/principal.py principal-a
& $kanPython -B evidencias/KAN-19/principal.py principal-b
Get-FileHash evidencias/KAN-19/local/principal-a/resumo_principal.json
Get-FileHash evidencias/KAN-19/local/principal-b/resumo_principal.json
```

As duas execuções produziram resumos idênticos e os mesmos hashes dos três CSVs. A verificação comparou as chaves do inventário com as do oráculo em cada T0 completo e reconciliou falhas, falhas retidas e durações ausentes com a publicação da KAN-18. Uma checagem independente comparou os CSVs com os rankings e o T0 originais e confirmou que a leitura de um ranking com bytes alterados era rejeitada pelo hash. O resumo identifica a tentativa de seleção publicada. Para usar uma nova execução da KAN-18 com hashes de overhead ou logs diferentes, é preciso vinculá-la à sua própria verificação. [Resumo principal](resumo_principal.json)

## Variáveis e observabilidade na auditoria inicial

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

## Partições e saídas da auditoria inicial

Nesta auditoria, os limites de posição 42 e 50 refletem a divisão congelada no piloto. Os limites classificam todos os 100 SHAs, inclusive os sem dados. As contagens T1 abaixo usam exclusivamente as seleções do piloto de mutação. As features e os rótulos sintéticos de validação (50) e teste (96) seguem como evidência auxiliar nos artefatos verificados do piloto. [Validação e teste do piloto](../MUTACAO/modelos/README.md)

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

Na auditoria inicial, as seleções do piloto geram pares com T0 nas posições 26 e 50. O conjunto formal da KAN-18 amplia essa cobertura para os cinco T0 completos. A janela expansiva e o reajuste a cada dez commits ficam com a etapa de treinamento prevista na Entrega 2.

## Reprodução e verificação do treino sintético

Na raiz do repositório, use CPython 3.12.14 e Git no PATH. São necessários os CSVs locais da KAN-16 em `evidencias/KAN-16/local/lote/` e os replays publicados das posições 15, 26 e 42 em `evidencias/MUTACAO/mutantes/local/`. O procedimento da KAN-16 descreve como reexportar os CSVs a partir das referências brutas. Um replay indisponível ou reprovado fica registrado no resumo e deixa o treino parcial. Um CSV de T0 ausente ou hash divergente interrompe a exportação. [Reprodução KAN-16](../KAN-16/README.md#reprodução) · [Replays e rótulos](../MUTACAO/mutantes/README.md)

```powershell
$kanPython = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
& $kanPython -B evidencias/KAN-19/dataset.py confirmacao
& $kanPython -B evidencias/KAN-19/dataset.py repeticao
Get-FileHash evidencias/KAN-19/local/confirmacao/resumo.json
Get-FileHash evidencias/KAN-19/local/repeticao/resumo.json
```

Use nomes de execução novos. As duas execuções produziram resumos idênticos com os mesmos hashes dos cinco CSVs. O [resumo versionado](resumo.json) registra código, entradas, população e fontes verificadas. Os CSVs gerados ficam em `local/`, ignorado pelo Git. O commit local de implementação é `17cf974b4e0d27f18066af366b1ac3513c2dee94`.

O pipeline compara cada linha da auditoria com o cálculo sobre o prefixo anterior isolado e com um cálculo que substitui todos os resultados da posição alvo em diante por falhas e durações artificiais. Os valores e a proveniência permaneceram idênticos nas cinco posições T1. A verificação independente conferiu unicidade das chaves, 9.301 pares T1–T0, identidade dos vetores entre features e treino, treino restrito a 15/26/42 e anterioridade estrita por posição das fontes históricas. Um caso de controle confirmou que o histórico reage a uma falha anterior, preserva a duração zero e mantém ausências vazias. As features operacionais são calculadas somente na função que recebe recorte e seleção estática congelada. Os resultados T0 e os rótulos entram nos seus próprios fluxos depois dessa seleção. A reprodução feita após o encaixe com a KAN-18 produziu o mesmo resumo versionado, incluindo o hash do treino sintético.
