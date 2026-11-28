# KAN-18 — Lote 05 (posições 61, 62 e 63)

A coleta amplia a materialização do T1 experimental DIRTS + expansão direta para as posições consecutivas **61, 62 e 63** (âncora na posição **60**), logo após o [Lote 04](entrega-kan29-04.md), preservando intactos os quatro lotes congelados anteriores e o holdout `96`. [KAN-18](https://cin-team-test-prioritization.atlassian.net/browse/KAN-18) · [KAN-29](https://cin-team-test-prioritization.atlassian.net/browse/KAN-29)

| Papel | Posição | SHA |
|---|---:|---|
| Âncora | 60 | `21e65f8b312c6608b554e4f551315fb0651c3277` |
| Alvo | 61 | `a22cfcd0539b5fb208415ae118783fc9dc1f902d` |
| Alvo | 62 | `b5cb40c16ce29ae3bf22c0434f9ed520ce2495f0` |
| Alvo | 63 | `817d50f746adfb485355d8d3a3ae4b9833ed3f63` |

## Resultados do Lote 05

| Posição | Continuidade | Candidatos | DIRTS puro | DIRTS + expansão | Fallback | Overhead de seleção |
|---:|---|---:|---:|---:|---|---:|
| 61 | `incremental` | 4.658 | 21 | 21 | `false` | 132.832 ms* |
| 62 | `incremental` | 4.658 | 0 | 241 | `false` | 29.207 ms |
| 63 | `fallback` | 4.658 | — | 4.658 | `true` (`selecao_invalida`) | 32.639 ms |
| **Total Lote 05** | — | **13.974** | **21** | **4.920** | **1 fallback** | **194.678 ms** |

*\*Na posição 61, o custo de seleção inclui a inicialização do estado `.dirts` na âncora 60. Na posição 62, em regime incremental, o DIRTS puro retornou zero e a expansão por dependências diretas recuperou 241 métodos em `29.207 ms`. Na posição 63, o seletor acionou corretamente a política de segurança com `fallback = selecao_invalida`, selecionando o inventário integral (`4.658` métodos).*

## Acumulado nos 100 commits (Lotes v1 + 02 + 03 + 04 + 05)

- **Disponíveis (T1 congelado):** **21 de 100 SHAs** (`79` lacunas explicitadas em [disponibilidade.csv](congelado-expansao-lote-05/disponibilidade.csv)).
- **Linhas acumuladas:** `97.795` em `selection.csv`, `15.846` em `rankings.csv`, `21` em `overhead.csv` (**12 com custo de seleção medido**, 9 com custo desconhecido).
- **Holdout 96:** preservado fechado (`rotulos_lidos = false`).
- **Determinismo e integridade:** duas exportações consecutivas a partir de `evidencias/KAN-18/local/kan29-61-63` produziram o mesmo SHA-256 do manifesto (`0dc5c26025f4a07fe593779f8a0cfffc109b8b3f35941be241c4009166bdf451`). Os verificadores `verificar-lote05.py` e `verificar-kan29.py` confirmaram que os quatro lotes anteriores permaneceram byte a byte inalterados.

## Reprodução

Na raiz do repositório, com Docker Linux (`test-prioritization/commons-lang:kan18-dirts`, `sha256:e575b64a339b089d4dc7eedf0d3508422cfe5b21b2404e250212eee9277ffdc1`) e `../KAN-10-upstream.git`:

```powershell
$d = 'evidencias/KAN-18'
python -B "$d/preparar-lote05.py" ../KAN-10-upstream.git "$d/local/kan29-61-63-novo"
python -B "$d/exportar-lote05.py" "$d/local/kan29-61-63-novo" ../KAN-10-upstream.git "$d/local/kan29-61-63-exportado"
python -B "$d/verificar-lote05.py" $d
python -B "$d/verificar-kan29.py" $d
```
