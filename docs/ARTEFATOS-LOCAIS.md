# Inventário de artefatos locais

Este inventário descreve classes de dados, não publica o conteúdo bruto.

| Local histórico | Estado num clone | Classificação | Ação |
|---|---|---|---|
| `resultados/KAN-13/` | ausente/ignorado | logs e Surefire do executor | preservar externamente se citados; regenerável com fonte, imagem e rede |
| `resultados/KAN-14/` | ausente/ignorado | lote T0 | evidência primária citada; exigir cópia verificada |
| `evidencias/KAN-16/local/` | ausente/ignorado | inventários e exportações | parcialmente regenerável a partir de XML e fonte |
| `evidencias/KAN-18/local/` | ausente/ignorado | clones, caches e execuções DIRTS | misto; classificar antes de descarte |
| `evidencias/KAN-19..22/local/` | ausente/ignorado | datasets, modelos e rankings | regenerável somente se todas as entradas congeladas existirem |
| `evidencias/MUTACAO/*/local/` | ausente/ignorado | mutantes, modelos e execuções | não necessário ao clone para ler resultados publicados |

Na máquina inspecionada antes desta reorganização,
`evidencias/KAN-18/local` tinha aproximadamente 24.268 arquivos e 809,3 MiB.
Esse valor é diagnóstico, não um checksum nem garantia de completude.

## Manifesto externo obrigatório

Antes de mover ou apagar dados locais, produzir fora desta mudança uma tabela
com: caminho relativo, ticket, classificação, quantidade de arquivos, bytes,
SHA-256 de cada artefato preservado, produtor, commit do produtor, SHA do Commons
Lang, comando de reprodução, restrição de acesso e localização da cópia.

Caches Maven, checkouts de fonte e bytecode reconstruível podem ser descartados
depois da validação. Logs, XML Surefire, matrizes de rótulos, inventários únicos
e qualquer arquivo referenciado por hash devem permanecer disponíveis ou ter a
indisponibilidade explicitamente documentada.
