# KAN-18 — Lote 04 para KAN-29

A coleta amplia a materialização do T1 experimental DIRTS + expansão direta no recorte principal e preserva os lotes congelados. A KAN-18 pede seleção rastreável, custo e fallback. A KAN-29 pede registros auditáveis por SHA e cenário, com dados ausentes explícitos. Este lote entrega artefatos do T1 para essa consolidação. [KAN-18](https://cin-team-test-prioritization.atlassian.net/browse/KAN-18) · [KAN-29](https://cin-team-test-prioritization.atlassian.net/browse/KAN-29)

| Papel | Posição | SHA |
|---|---:|---|
| Âncora | 57 | `1e3629c6ef9d4dd1d96327254bb88e62fd2f4aac` |
| Alvo | 58 | `c04469163d86bdd10f4aa409c1a694c87c467d2a` |
| Alvo | 59 | `7b77ea4cfb73399e0dde72a8ab7742a2da5796d0` |
| Alvo | 60 | `21e65f8b312c6608b554e4f551315fb0651c3277` |

As três posições são consecutivas pelo primeiro pai, estavam sem seleção nas publicações anteriores e têm diffs Java elegíveis. A coleta começa depois do POM alterado na posição 56. Cada passo verifica o SHA e o selo do estado do pai antes de transferir `.dirts`. O exportador confere também os SHAs embutidos nos arquivos Git tar. As saídas isoladas e os controles sem alterações ficam fora do relógio de produção. A política de fallback é a da base `ef57715`.

A primeira tentativa encontrou o motor Docker Linux indisponível. A tentativa seguinte, durante a inicialização do motor, recebeu HTTP 500. Após o motor responder pela imagem fixada, a coleta retomou os tarballs já preparados. Esses erros de infraestrutura antecederam os relógios da seleção.

| Posição | Candidatos | DIRTS puro | DIRTS + expansão | Overhead de seleção |
|---:|---:|---:|---:|---:|
| 58 | 4.658 | 21 | 75 | 520.303 ms |
| 59 | 4.658 | 21 | 75 | 148.021 ms |
| 60 | 4.658 | 0 | 241 | 151.683 ms |
| **Total** | **13.974** | **42** | **391** | **820.007 ms** |

O valor total soma as linhas KAN-15 já arredondadas. A soma bruta foi de 820,008 s, com 370,404 s de inicialização na posição 57 e 449,604 s em regime. São tempos de parede de uma coleta em ambiente compartilhado. O manifesto contém os tempos brutos por fase.

Os três alvos usaram estado incremental e passaram sem fallback. Os controles sem diff selecionaram zero. Os conjuntos DIRTS coincidiram com os isolados nos três SHAs. O selo exportado por cada alvo coincide com o recebido pelo filho. Ao fechar o lote, a sessão original já não estava acessível e o endpoint Linux do Docker estava indisponível. Os registros locais continham todos os controles concluídos e códigos de retorno zero. A verificação de fechamento usou esses registros, sem reiniciar o motor.

O checkpoint local da posição 60 está no diretório bruto da coleta. O exportador conferiu o SHA do alvo, o selo e cada arquivo do tar. O arquivo auxiliar de selo foi recuperado do registro original do alvo porque o nome copiado tinha um caractere de retorno de carro. O hash do checkpoint e o hash do selo estão no manifesto.

O acumulado tem **18 de 100 SHAs**, **83.821 candidatos** e **10.926 métodos selecionados**. Nove SHAs têm custo de seleção medido e nove têm custo desconhecido. As **82 lacunas** estão identificadas individualmente na tabela de disponibilidade. Duas exportações produziram os mesmos hashes. O verificador confirmou cabeçalhos, chaves e postos, equivalência entre ranking e seleção, cadeia de pais, encadeamento dos selos e ausência de colisões entre os lotes. Os lotes anteriores preservaram os mesmos bytes.

## Consumo na KAN-29

- Usar o [manifesto](congelado-expansao-lote-04/manifesto.json), a [disponibilidade consolidada](congelado-expansao-lote-04/disponibilidade.csv) e o `commits.csv` da publicação base. Anexar [seleção](congelado-expansao-lote-04/selection.csv), [ranking](congelado-expansao-lote-04/rankings.csv) e [overhead](congelado-expansao-lote-04/overhead.csv) como delta. As chaves seguem KAN-15 e a ordenação cronológica usa `commit_order`.
- Replicar a população do T1 em T2 e T3 após a validação das features. Preservar a partição de avaliação e manter análise complementar de falhas separada. O holdout 96 foi mantido sem leitura de rótulos.
- A cobertura é de seleção pré-execução. T0 físico, execução dos testes escolhidos, extração de features, rankings T2/T3 e métricas da KAN-29 seguem fora deste lote. As posições restantes precisam de inventário íntegro e decisão de seleção ou fallback, com custo e falhas registrados por SHA.

## Reprodução

Na raiz do worktree, em PowerShell, com Docker Linux e caminhos de saída novos:

```powershell
$d = 'evidencias/KAN-18'
python -B "$d/preparar-kan29.py" ../KAN-10-upstream.git "$d/local/kan29-58-60"
python -B "$d/exportar-kan29.py" "$d/local/kan29-58-60" ../KAN-10-upstream.git "$d/local/kan29-exportado"
python -B "$d/verificar-kan29.py" $d
```

O verificador lê as quatro publicações congeladas. A exportação repetida usa o diretório local de coleta e pode ser comparada com o delta congelado na branch. Para reproduzir byte a byte manifestos de lotes anteriores, usar o exportador da revisão que os congelou.
