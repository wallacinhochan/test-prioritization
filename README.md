# Test Prioritization — Apache Commons Lang

Pesquisa reproduzível de seleção e priorização de testes sobre o Apache Commons
Lang. A árvore separa código reutilizável, infraestrutura, documentação e
evidências históricas; resultados congelados permanecem nos caminhos em que
foram publicados.

## Comece aqui

1. Leia o [guia de continuidade](docs/CONTINUIDADE.md) para conhecer o estado
   validado, o protocolo e os bloqueios.
2. Consulte a [arquitetura do repositório](docs/ARQUITETURA.md) antes de criar
   código ou mover evidências.
3. Confira a [fonte congelada do estudo](studies/commons-lang/source-lock.json)
   e o [inventário de artefatos locais](docs/ARTEFATOS-LOCAIS.md).
4. Use os READMEs em `evidencias/KAN-*` como registro por ticket Jira.

## Estrutura

| Caminho | Responsabilidade |
|---|---|
| `src/test_prioritization/` | código Python reutilizável |
| `scripts/` | pontos de entrada estáveis para operadores |
| `tests/` | invariantes da estrutura e dos entrypoints |
| `infra/` | ambientes e executores reproduzíveis |
| `studies/commons-lang/` | identidade e recorte da fonte estudada |
| `docs/` | arquitetura, operação e relatórios navegáveis |
| `evidencias/` | registros históricos por ticket e releases congelados |

## Comandos seguros de validação

Na raiz, sem executar a campanha experimental:

```powershell
python -B -m unittest discover -s tests -v
python -B -m unittest discover -s evidencias/KAN-19 -v
python -B -m unittest discover -s evidencias/KAN-22 -v
python -B -m unittest discover -s evidencias/KAN-23 -v
python -B -m unittest discover -s evidencias/KAN-25 -v
node --test evidencias/MUTACAO/t1/t1.test.mjs
```

O entrypoint novo das métricas é `python -B scripts/metricas.py --help`. O
caminho histórico `evidencias/KAN-25/metricas.py` continua aceito.

## Regras de preservação

- Não editar CSVs, JSONs, patches ou manifests congelados para adequá-los ao
  layout novo.
- Não usar `evidencias/*/local` como única fonte de um resultado publicado.
- Toda execução deve registrar SHA do Commons Lang, versão do produtor,
  parâmetros, hashes das entradas e localização das saídas.
- `KAN-10-upstream.git` é uma fonte externa local, não parte deste repositório.
- Jira registra coordenação; o repositório guarda protocolo, código e evidência.

O relatório preliminar permanece em
[`evidencias/ENTREGA-3/README.md`](evidencias/ENTREGA-3/README.md), e a
apresentação histórica permanece em [`APRESENTACAO.md`](APRESENTACAO.md).
