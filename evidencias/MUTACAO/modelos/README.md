# Dataset e ranking do piloto de mutação

O alvo por SHA e método é `induced_failure / (induced_failure + pass)`. A importação verifica a chave completa `sha × mutation_id × test_id`, a identidade do inventário de métodos, os hashes e as contagens publicados pelo replay. `unknown` explícito e linha ausente têm contagens separadas. Um método sem observações conhecidas fica sem alvo. A tabela de alvos inclui todo o inventário descoberto e identifica a seleção T1. O ajuste usa apenas os métodos selecionados em T1 com alvo conhecido.

| Partição | Posições | Uso |
| --- | --- | --- |
| Treino | 15, 26, 42 | Ajuste do escalonador KNN e dos dois regressores |
| Validação | 50 | Comparação do ranking observado com o T1 |
| Teste final | 96 | Avaliação dos rankings congelados após a liberação coordenada |

A suficiência requer um replay publicado e verificado para cada revisão da partição, com positivos e negativos conhecidos no conjunto T1 da partição. As verificações de equivalência do controle, repetição e restauração são obrigatórias por revisão. Falhas de infraestrutura classificadas pelo produtor permanecem desconhecidas. O diagnóstico inclui denominadores T0 e T1 por revisão e os totais T1 de cada partição.

## Características, modelos e avaliação

As sete características vêm da assinatura do teste e das rotas estáticas do T1 congelado no commit `0d3cd01e68bf223eca124332f74d4486ae6bd6f7`. São distância da classe de teste até a semente, indicador sem rota, quantidade de arestas inferidas por referência no fonte, indicador de classe semente, comprimento do nome do método, quantidade de parâmetros e indicador de classe aninhada. Distância e contagem de arestas valem zero para classe sem rota. O cálculo usa apenas artefatos pré-execução. O piloto omite características de histórico.

O KNN usa escalonamento padrão ajustado no treino, 15 vizinhos, distância euclidiana e peso uniforme. A Random Forest usa 200 árvores, pelo menos cinco exemplos por folha, todas as características elegíveis em cada divisão, semente 20261122 e os padrões da versão fixada para os demais parâmetros. Ambos usam um trabalhador. Os parâmetros são fixos para a comparação na posição 50. Os rankings T1, KNN e Random Forest contêm exatamente os mesmos métodos de cada revisão. As predições são ordenadas em ordem decrescente e os empates seguem a ordem ordinal por `test_id`.

Por mutante e ranking, o resultado registra a primeira detecção observada e a primeira posição em que a detecção seria possível diante das lacunas. Uma ordem sem positivo fica como `sem_deteccao` se todos os métodos foram observados com resultado negativo, ou `indeterminado` se há lacunas. Os rótulos medem detecção de mutações sintéticas. Relações estáticas por classe aproximam dependências entre métodos e as cinco revisões e até quatro variantes por revisão limitam a generalização para regressões naturais.

## Reprodução

Na raiz do repositório, com CPython 3.12.14 e `uv` disponíveis:

```powershell
$modelos = 'evidencias/MUTACAO/modelos'
$python = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
$env:UV_CACHE_DIR = "$PWD/$modelos/local/uv-cache"
uv pip install --python $python --target "$modelos/local/deps" -r "$modelos/requirements.txt"
$env:PYTHONPATH = "$PWD/$modelos/local/deps"
& $python -m unittest discover -s $modelos -v
& $python "$modelos/piloto.py" diagnostico gate-26
& $python "$modelos/piloto.py" congelar piloto-v1
```

Use um identificador novo para cada execução. O diretório ignorado `local/` guarda alvos, características, modelos ajustados, predições e rankings, diagnósticos e resultados. A geração de `congelamento.json` exige suficiência de treino e validação. O manifesto inclui configuração, versões e hashes dos insumos e artefatos. Versione o manifesto em `modelos/congelamento.json` usando commit específico por caminho e comunique seu SHA completo à coordenação antes da liberação dos rótulos finais.

Depois da publicação coordenada pelo produtor:

```powershell
& $python "$modelos/piloto.py" final piloto-v1 --commit <sha-completo> --liberacao '<referência da liberação>'
```

O comando final verifica o manifesto a partir do Git, os hashes dos artefatos locais, o código e a ordem antes de abrir o replay final. O resumo publicado pelo produtor deve estar em um commit descendente do congelamento e registrar o mesmo caminho, commit e SHA-256 do manifesto, junto com a referência da liberação da coordenação. O teste final usa as predições gravadas no congelamento. Registre `teste-final.json` como evidência, inclusive se o teste final for insuficiente.

## Diagnóstico inicial

A posição 26 passou as verificações de controle, repetição e restauração no commit `41318d9`. Em T1, 12 falhas induzidas e 18.536 aprovações compõem um denominador de 18.548. Os 44 rótulos desconhecidos ficam de fora. Há alvo para 4.637 dos 4.648 métodos T1. No momento deste diagnóstico, 15, 42 e 50 ainda estavam sem resumo publicado. O treino e a validação ficaram pendentes. A execução `gate-26` registrou versões, contagens por escopo e SHA-256 consumidos. [Diagnóstico inicial](diagnostico-gate-26.json)

Os oito testes verificam o alvo com lacunas, a detecção com lacunas, a ordenação ordinal, as entradas T1 congeladas e o vínculo da publicação de 96 ao congelamento. Com dados fabricados, também verificam o congelamento e o diagnóstico de teste final insuficiente. Uma alteração no ranking congelado deve ser rejeitada antes de abrir o replay. O diagnóstico inicial usa o replay real da posição 26.

Após a publicação de 15 no commit `90f3143`, a execução `diagnostico treino-15-26` verificou 280 positivos e 18.264 negativos em T1 nessa revisão. Junto com 26, o treino parcial tem 292 positivos, 36.800 negativos e 88 desconhecidos, sem observações ausentes. O denominador conhecido é 37.092. Ainda faltam a revisão 42 no treino e a revisão 50 na validação. [Diagnóstico após a posição 15](diagnostico-treino-15-26.json)

Após a publicação de 42 no commit `2fbfccf`, a execução `diagnostico treino-15-26-42` confirmou a suficiência do treino. A revisão 42 tem 17 positivos e 18.551 negativos em T1. O treino completo tem 309 positivos, 55.351 negativos e 132 desconhecidos, com denominador de 55.660 e alvo conhecido em 13.915 de 13.948 pares SHA e método. A posição 50 ainda aguardava publicação. [Diagnóstico do treino completo](diagnostico-treino-15-26-42.json)

## Validação e congelamento

O replay de 50 foi publicado em `940d22d`. Foram observados 4 positivos e 18.564 negativos em T1, com 44 desconhecidos e nenhuma ausência. O denominador é 18.568, com 4.642 métodos com alvo de 4.653 selecionados. KNN antecipou os postos observados 1.693, 1.693 e 999 para 15, 15 e 221. A Random Forest os antecipou para 25, 25 e 268. O quarto mutante permaneceu indeterminado nas três ordens. O resultado distingue a primeira detecção observada das posições possíveis quando há lacunas. [Diagnóstico do desenvolvimento](diagnostico-validacao-50.json) · [Detecção por mutante](deteccao-validacao-50.json)

A execução `congelar piloto-v1` ajustou os modelos no treino e gravou as predições das cinco revisões. A repetição `congelar piloto-v1-repeticao` reproduziu os SHA-256 dos 21 artefatos, incluindo modelos serializados, características, alvos e rankings. Para a posição 96, cada ranking contém os 4.659 métodos T1 e usa somente entradas pré-execução e os modelos ajustados no treino. O acesso ao resultado final depende da publicação após a liberação da coordenação. [Manifesto de congelamento](congelamento.json)
