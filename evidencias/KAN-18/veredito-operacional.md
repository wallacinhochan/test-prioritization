# KAN-18 — Veredito rápido

**Avançar com DIRTS + expansão direta no congelamento experimental de T2/T3.** Manter DIRTS puro e T0 como braços de comparação. A decisão aplica a [regra registrada](regra-veredito.md) no commit `4b0fbfd`, anterior à conferência desta rodada.

| Evidência | T0 | DIRTS puro | DIRTS + expansão |
|---|---:|---:|---:|
| Detecções observadas no replay 26 e 50 | 7/7 | 6/7 | 7/7 |
| Métodos no alvo 49 | 4.657 | 295 | 295 |
| Métodos no alvo 50 | 4.657 | 72 | 416 |
| Invocações observadas no alvo 49 | 59.953 | 304, conjunto comum | 304 |
| Invocações observadas no alvo 50 | 59.953 | sem medição física | 51.172 |
| Custo total no trecho 49–50 | 667,540 s | sem medição física completa | 467,370 s |

Os braços incrementais compartilham o estado do DIRTS. A seleção incremental coincidiu com a isolada nos dois alvos. Na posição 49, o hash dos dois conjuntos coincide, e a execução física comum levou 16,640 s para Maven test e coleta de XML. Na posição 50, o DIRTS puro seleciona duas classes-raiz e a expansão seleciona nove. Tempo e invocações das duas classes carecem de execução física própria. O ganho de **200,170 s (30,0%)** é frente a T0, com **118,754 s** de inicialização e sem cobrar controles experimentais. A perda do DIRTS puro ocorre na posição 50. Um quarto mutante rotulado nessa posição ficou sem detector observado no T0.

O fallback integral de configuração reteve **4.663 métodos** na posição 100, para os dois seletores. A injeção com Maven instrumentado confirmou a chamada sem filtro de classe. O controle documental da posição 4 passou de **0 para 1.018 métodos** com a expansão. O filtro léxico manteve a expansão nesse caso por causa de escapes Unicode. O custo físico dessa revisão segue em aberto. Se documentação, fallback ou reinicializações frequentes consumirem a margem em um recorte representativo, a escolha precisa ser revista. Rótulos adicionais também podem alterar a conclusão sobre detecção. [Validação cronológica e controles](reuso-filtro.md) · [Replay rotulado](filtro-resultado.json)

O Git confirmou a sequência adicional candidata 24 → 25 → 26, com 24 para inicialização e 25–26 para comparação. A rodada foi dispensada pelo critério de parada. A posição 26 já tem empate de detecção (4/4), a perda que separa as variantes está na 50 e a candidata não resolve a lacuna de custo documental da 4. Um cronômetro exclusivo do DIRTS puro na 50 acrescentaria informação de custo, mas a regra de preservação continuaria determinando a escolha observada.

## Congelamento experimental para T2/T3

1. Fixar por SHA a variante de seleção, o primeiro pai, a imagem e versão do DIRTS, a regra de união, a política de fallback, o inventário JUnit, o grafo jdeps e a lista ordenada de IDs. Registrar SHA-256 dos artefatos, raiz Surefire de cada ID, casos de fallback e a linhagem do estado incremental. Conservar os conjuntos do DIRTS puro e do T0 para comparação.
2. Usar exatamente os mesmos candidatos da expansão para alimentar T2 e T3. Regenerar os vetores do KAN-19 para os IDs acrescentados, registrar a versão e ordem das features e verificar igualdade das chaves `(commit_sha, test_id)` com o conjunto congelado em ambos os rankings. Registrar features ausentes como lacunas explícitas.
3. Fixar os cortes cronológicos e a janela de treino, as versões, configurações, sementes e hashes do dataset e dos modelos. Gerar e validar postos contíguos antes de cruzar resultados com o oráculo. Preservar o holdout e registrar seleção, extração de features, treinamento, inferência e execução conforme o contrato KAN-15.
4. Usar uma identificação nova para o replay experimental e preservar os artefatos já publicados de T2/T3. A efetivação no protocolo principal depende de Wallace.
