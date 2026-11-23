# Piloto de mutação no Apache Commons Lang

As cinco suítes da Entrega 3 produziram 23.280 registros por método e revisão com zero falhas observadas. Este piloto complementar introduz alterações no código de produção, uma por variante, para medir a detecção sintética e testar a viabilidade de treinar rankings. Os testes permanecem inalterados. [Entrega 3](../ENTREGA-3/README.md) · [PIT](https://pitest.org/quickstart/basic_concepts/) · [Luo et al.](https://arxiv.org/abs/1807.08823)

O [relatório final do piloto](RELATORIO.md) consolida os replays, a preservação pelo T1 e os postos de detecção com os modelos congelados.

## Revisões fixadas

| Posição | SHA | Primeiro pai | Uso |
| ---: | --- | --- | --- |
| 15 | `970e4d66452c146165233129c913616ff666ff77` | `d96a28a7e282e090dba3f54779e78db6e68c7107` | Treino |
| 26 | `04cc0339d6510ffdcb47db4676c34b40ecff6b28` | `a5585689a31f47b3f95808f8666d062e18097707` | Viabilidade e treino |
| 42 | `7a55ebb455857756d81056dd879e38dfb4d84d66` | `e1da3a23a177e73a0d22ec95ac319d7956cf417a` | Treino |
| 50 | `f24c027ff83b90beab2ec28696721200abb4f9e9` | `cc5ecf5db64abf0d2a2f59be16f9dc49a520dca9` | Validação |
| 96 | `5454931eb735deb59e9b671fd8a14cd4c14d8272` | `0cebd847c3ce33c634050fb02c307acb106e0b55` | Teste final |

## Protocolo inicial

1. Na posição 26, use PIT com suporte a JUnit 5 e exportação de bytecode para `LocaleUtils`. Fixe as versões da ferramenta e registre a imagem Docker da KAN-13, JDK, Maven e UTC. Restrinja a geração às classes de produção modificadas pelo diff pai → SHA. Limite a quatro mutantes de efeito único por revisão. Escolha em ordem determinística pelo SHA-256 da concatenação de uma semente fixa com o identificador canônico do mutante. Deduplicate por classe e hash do bytecode exportado. Use a semente `tp-mutation-v1`. Fixe a seleção sem consultar os desfechos do PIT. Preserve o conjunto elegível, a regra, os hashes e o manifesto escolhido.
2. Execute um controle sem mutação e reproduza os candidatos isoladamente, usando o mesmo SHA, o mesmo conjunto de testes e a mesma configuração do executor. Preserve o bytecode original e teste a restauração. O rótulo é por `SHA × mutation_id × test_id`. Uma falha induzida requer aprovação no controle e falha observada na variante. Registre aprovação apenas se observada. Skip, execução ausente, associação ambígua e erro de infraestrutura ficam desconhecidos. Registre tempo de execução e replay separadamente do custo do PIT. Só amplie para os outros SHAs após controle íntegro, ao menos um positivo e um negativo verificados, repetição com rótulos coincidentes e restauração confirmada.
3. Congele a seleção T1 exploratória por SHA a partir do diff real e das dependências de produção e teste, antes de acessar rótulos. Use fallback conservador para incertezas materiais. O T1 mantém seu conjunto de métodos para todos os mutantes do SHA. Na comparação, use o mesmo mutante nos dois cenários e reporte taxa de preservação entre os detectados pelo T0, redução do conjunto e custo da seleção. Se o T0 não detectar nenhum mutante, a taxa fica indisponível. A dependência formal da KAN-18 permanece com a KAN-12.
4. Para ranking, agregue por SHA e método a razão entre falhas sintéticas e observações positivas ou negativas conhecidas. Use atributos pré-execução e histórico estritamente anterior. Treine KNN e Random Forest para estimar esse alvo e ordenar exclusivamente o conjunto T1. Use a posição 50 para validar decisões de modelo e preserve a 96 para avaliação final depois de congelar o protocolo e as configurações. Compare a primeira posição de detecção com a ordem de referência congelada do T1 e reporte mutantes sem detecção. Se alguma partição não tiver positivos e negativos verificáveis, reporte suficiência e mantenha a avaliação de modelos pendente.

## Registro e coordenação

O chat de mutantes registra código, manifesto, replay e rótulos em `mutantes/`. O chat de seleção registra implementação, lista congelada e comparação em `t1/`. O chat de dataset e modelos começa após a validação da posição 26 e registra partições, configuração, rankings e métricas em `modelos/`. Os dados brutos grandes ficam locais, com referências e hashes versionados. Cada alteração de protocolo recebe motivo e versão. Resultados sintéticos ficam fora dos dados históricos da Entrega 3.
