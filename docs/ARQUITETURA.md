# Arquitetura do repositório

## Regra de classificação

Um componente pertence a `src/` quando implementa uma regra reutilizada por
mais de um ticket ou forma parte estável do pipeline. `scripts/` contém apenas
entrypoints e orquestração. `evidencias/` preserva a publicação de um ticket,
incluindo scripts cuja interface, caminho ou hash façam parte da proveniência.

Nesta etapa, somente as métricas KAN-25–27 foram extraídas para
`src/test_prioritization/metrics`. Os caminhos antigos são wrappers leves, pois
testes, documentação e reproduções já os invocam. Os pipelines KAN-18–24 e os
modelos de `evidencias/MUTACAO` continuam no lugar: seus manifests, imports e
hashes ainda estão acoplados aos caminhos históricos. Uma extração futura deve
primeiro versionar uma interface e provar equivalência de saída.

## Dependências

```text
studies/commons-lang/source-lock.json
        └── infra/commons-lang
                └── evidencias/KAN-9..24
                        └── src/test_prioritization/metrics
                                └── relatórios KAN-25..33
```

`infra/commons-lang/executar.ps1` recebe uma fonte Git e um SHA completo; não
depende do nome do checkout. Em contraste, vários manifests históricos guardam
caminhos relativos sob `evidencias/` e `resultados/`. Eles são dados, não
configuração migrável.

## Política para código histórico

- Extraia lógica, não dados congelados.
- Preserve o caminho antigo com wrapper enquanto houver documentação ou teste
  que o invoque.
- O wrapper não deve transformar argumentos ou saídas.
- Remova um wrapper apenas numa versão declaradamente incompatível, após
  atualizar todas as referências versionadas.
- Não altere um arquivo coberto por hash; publique nova versão e novo manifesto.
