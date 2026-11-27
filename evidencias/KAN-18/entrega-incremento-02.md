# KAN-18 — Lote incremental 02

Este lote acrescenta as posições **47 e 48** à publicação base `ef577158bc012d87784bbfab1b9ccb4ee80cf812`. O conjunto base continua disponível na mesma pasta e com os mesmos hashes. A seleção segue a regra DIRTS + expansão direta e o contrato KAN-15 `0.1.0`.

| Papel | Posição | SHA |
|---|---:|---|
| Inicialização do estado | 46 | `1441ba9f3cd172ccfbd2d0c2ce336f4a9750a0a2` |
| Primeiro alvo novo | 47 | `df3e2715f41263d8998b7350301d106967748c0e` |
| Segundo alvo novo | 48 | `913225106ac80fdf01e5b0bbfe42991d424f2642` |

O trecho foi escolhido porque tem dois alvos adjacentes sem seleção publicada, entre posições já cobertas. O Git validou ambos os primeiros pais. A imagem Linux DIRTS é a mesma do piloto 49–50. A posição 46 foi usada como âncora nova. O estado contém grafo, checksums e mapeamento das unidades de compilação. O coletor confere o SHA declarado e os hashes dos arquivos do estado antes de selecionar cada alvo, e registra o selo recebido e o exportado. O custo de inicialização fica no primeiro alvo.

A política encaminha diffs incompatíveis e seleções inválidas ao inventário integral, registra o motivo e invalida o estado. Quando o estado anterior está ausente ou inválido, o coletor tenta reconstruir o primeiro pai antes de aplicar o fallback. Os controles isolados recompõem o estado de cada pai, exigem seleção vazia sem diff e comparam as classes-raiz no mesmo inventário. O manifesto separa tempos brutos de produção e controles.

| Posição | Candidatos | DIRTS puro | DIRTS + expansão | Classes-raiz T1 | Overhead KAN-15 |
|---:|---:|---:|---:|---:|---:|
| 47 | 4.657 | 3.358 | 3.358 | 143 | 219.194 ms |
| 48 | 4.657 | 0 | 17 | 1 | 64.493 ms |
| **Total** | **9.314** | **3.358** | **3.375** | **144 pares revisão–classe** | **283.687 ms** |

A inicialização levou **128,163 s**. Em regime, a seleção dos dois alvos somou **155,524 s**. DIRTS consumiu 40,251 s e 27,622 s, e a compilação, descoberta e jdeps consumiram 50,105 s e 36,354 s, respectivamente. Os controles isolados retornaram zero sem alteração e coincidiram com o DIRTS incremental nos dois alvos.

O selo exportado em 47 coincide byte a byte com o selo recebido em 48. Ambos os alvos usaram reuso incremental, sem reconstrução nem acionamento de fallback. Na posição 48, a expansão resultou em 17 métodos de uma classe com dependência direta. A auditoria registra os motivos de fallback como ausentes nas duas revisões. O controle instrumentado de encaminhamento ao T0 permanece documentado no piloto anterior. [Evidência do fallback anterior](fallback-reuso.json)

As duas exportações do incremento reproduziram saídas idênticas. A verificação independente confirmou hashes e cabeçalhos, ausência de colisões com a base, postos contíguos e igualdade entre ranking e seleção. A base mantém os mesmos arquivos do commit `ef57715`.

## Consumo por KAN-19–21

- Usar [o manifesto do lote](congelado-expansao-lote-02/manifesto.json) para validar os hashes. Anexar as linhas de [seleção](congelado-expansao-lote-02/selection.csv), [ranking](congelado-expansao-lote-02/rankings.csv) e [overhead](congelado-expansao-lote-02/overhead.csv) à base. Usar o `commits.csv` da base, ordenar por `commit_order` e validar ausência de colisões nas chaves KAN-15. Em cobertura, substituir apenas as entradas 47 e 48 pelas linhas do [delta](congelado-expansao-lote-02/cobertura.csv).
- Manter 47 e 48 na validação cronológica, antes da posição 50. Usar a mesma população congelada para KNN e Random Forest em cada SHA. [Rotas](congelado-expansao-lote-02/rotas.csv) fornece arestas diretas e distingue inclusão sem evidência de rota. As features de rota do vetor antigo continuam condicionadas à regra versionada da KAN-19.
- A cobertura consolidada chega a **13/100 SHAs**. Os outros **87** mantêm as lacunas da base. O holdout 96 permanece intocado. A coleta usa inventário pré-execução, sem abrir rótulos ou executar testes físicos. O T0 deste lote é referência de inventário. A comparação de custo de ponta a ponta executada no piloto anterior continua restrita a 49–50.

## Reprodução

Na raiz do worktree, em PowerShell, com a imagem já presente no Docker Linux e caminhos de saída novos:

```powershell
$d = 'evidencias/KAN-18'
python -B "$d/preparar-incremento.py" ../KAN-10-upstream.git "$d/local/incremento-47-48"
python -B "$d/exportar-incremento.py" "$d/local/incremento-47-48" ../KAN-10-upstream.git "$d/local/incremento-exportado"
```

O manifesto fornece os hashes das entradas comuns, evidências por alvo e CSVs de saída. As evidências brutas ficam no diretório local de coleta.
