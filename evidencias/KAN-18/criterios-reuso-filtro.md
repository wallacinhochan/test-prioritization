# KAN-18 — Critérios da rodada complementar

## Reuso cronológico

Usar 49 e 50, o menor trecho de dois alvos consecutivos que termina na posição da medição física anterior. As posições 48, 49 e 50 devem formar uma cadeia de primeiro pai. Medir inicialização na 48, seleção incremental na 49 e 50 e execução Maven das raízes selecionadas pela união DIRTS + expansão. Usar T0 nos mesmos dois alvos, com a mesma imagem, argumentos comuns e cópias do mesmo cache semeado. Reportar o acumulado incluindo inicialização, o acumulado em regime e o custo por alvo. Contabilizar compilação, inventário e jdeps quando utilizados. Separar validações experimentais, inclusive reprodução isolada e controle sem diffs. Registrar unidades separadamente.

Aceitar estado contínuo quando a identidade do pai, a integridade e a presença dos arquivos de estado, a saída DIRTS e o inventário forem válidos. Comparar com reconstrução independente do pai por igualdade dos IDs selecionados. Validar estado ausente, adulterado ou de outro pai, com reconstrução e T0 se a seleção continuar indisponível. Configuração não suportada encaminha a T0 antes de usar a seleção. Medir uma observação física por braço e não extrapolar para todo o recorte.

## Filtro de comentários e formatação

Manter os dez pares e o fallback já publicados. Suprimir somente a ampliação quando todas as mudanças além do changelog consistirem em modificações de arquivos Java regulares com os mesmos tokens Java em sequência, inclusive a grafia original dos literais, e a mesma marca de depreciação documental por token. Divergência léxica, erro, escape Unicode, ausência de evidência, modo diferente, arquivo novo, exclusão ou alteração funcional conservam o fluxo anterior. A decisão depende apenas de objetos Git e do lexer do JDK 21. Congelar as listas antes de abrir os rótulos e verificar os hashes dos CSVs. Conferir os controles para comentário, formatação, literais, operadores, depreciação, Unicode e erro léxico.
