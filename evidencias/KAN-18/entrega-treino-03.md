# KAN-18 — Lote 03 de treino

Este lote congela o T1 experimental DIRTS + expansão direta nas duas posições de treino solicitadas. Usa o contrato KAN-15 `0.1.0`, o mesmo critério de união e ordenação da publicação `ef57715` e a imagem Docker Linux do piloto. O manifesto fixa os hashes das publicações anteriores, das entradas, do código de exportação e dos CSVs deste lote.

| Posição | SHA | Primeiro pai |
|---:|---|---|
| 15 | `970e4d66452c146165233129c913616ff666ff77` | `d96a28a7e282e090dba3f54779e78db6e68c7107` |
| 42 | `7a55ebb455857756d81056dd879e38dfb4d84d66` | `e1da3a23a177e73a0d22ec95ac319d7956cf417a` |

A coleta ancorou cada SHA em estado DIRTS novo, criado com a árvore arquivada do próprio primeiro pai. O exportador conferiu a cadeia no Git e a identidade dos quatro tarballs. O coletor selou arquivos de estado, validou SHA e hashes ao preparar o alvo e registrou o selo do alvo. As posições 15 e 42 são descontínuas, portanto a coleta não propagou estado de 15 para 42. O primeiro controle relocou a cópia selada da posição 15 e teve seleção não vazia. A auditoria repetiu pai e alvo no mesmo diretório, checou o controle sem diff e restaurou o selo anterior ao controle antes de selecionar o alvo. O manifesto guarda as duas evidências e o tempo dos controles fica separado do custo de seleção.

| Posição | Candidatos | DIRTS puro | Expansão direta | Classes-raiz na expansão | Overhead de seleção |
|---:|---:|---:|---:|---:|---:|
| 15 | 4.651 | 0 | 318 | 20 | 246.425 ms |
| 42 | 4.657 | 0 | 153 | 8 | 159.931 ms |
| **Total** | **9.308** | **0** | **471** | **28 pares revisão–classe** | **406.356 ms** |

A auditoria com caminho estável retornou zero sem diff e confirmou os conjuntos DIRTS da coleta nos dois SHAs. Os dois alvos passaram sem fallback. A inicialização custou 141,065 s e 92,930 s, respectivamente. Os inventários por SHA coincidiram exatamente com os inventários do piloto de treino. Todos os 471 IDs selecionados pertencem à seleção antiga desse piloto. A comparação é de chaves e dispensa leitura de rótulos.

Duas exportações produziram arquivos idênticos. A verificação independente conferiu hashes, esquemas, chaves dos três lotes sem colisões, igualdade dos rankings com a seleção e postos contíguos.

## Consumo para KAN-19–21

- Validar os hashes no [manifesto](congelado-expansao-lote-03/manifesto.json) e anexar [selection.csv](congelado-expansao-lote-03/selection.csv), [rankings.csv](congelado-expansao-lote-03/rankings.csv) e [overhead.csv](congelado-expansao-lote-03/overhead.csv) às tabelas da base e do lote 02, preservando as chaves KAN-15. Atualizar apenas as linhas 15 e 42 na [cobertura](congelado-expansao-lote-03/cobertura.csv). Ordenar pelo `commit_order` da base.
- Derivar o mesmo vetor versionado para KNN e Random Forest. Conferir a população com as chaves `(commit_sha,test_id)` da seleção. Usar [rotas.csv](congelado-expansao-lote-03/rotas.csv) como evidência de bytecode e conservar a distinção entre inclusão DIRTS sem rota evidenciada e aresta direta. A sobreposição do inventário com o piloto anterior está no manifesto. Uma junção de rótulos para treino deve verificar cobertura própria e registrar IDs sem alvo.
- Manter estas revisões no treino e 50 na validação. A coleta e a exportação deste lote não leram rótulos. O holdout 96 permaneceu intacto. A combinação da base e dos lotes 02–03 cobre **15 dos 100 SHAs** e deixa **85** como lacunas.

O overhead medido inclui a inicialização de cada pai, seleção, descoberta, grafo e expansão. Tempos de T0 físico, execução dos testes escolhidos e features permanecem indisponíveis nesta coleta.

## Reprodução

Na raiz do worktree, em PowerShell, com a imagem do piloto presente no Docker Linux e caminhos de saída novos:

```powershell
$d = 'evidencias/KAN-18'
python -B "$d/preparar-treino.py" ../KAN-10-upstream.git "$d/local/treino-15-42"
python -B "$d/controlar-treino.py" "$d/local/treino-15-42" "$d/local/treino-controle-estavel"
python -B "$d/exportar-treino.py" "$d/local/treino-15-42" "$d/local/treino-controle-estavel" ../KAN-10-upstream.git "$d/local/treino-exportado"
```

Os artefatos brutos ficam no diretório local da coleta. Para reproduzir byte a byte o lote 02, usar os scripts do commit `41a22e3`. Os CSVs e manifestos anteriormente publicados foram preservados.
