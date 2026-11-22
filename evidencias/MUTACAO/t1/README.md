# Seleção T1 exploratória

O protocolo do piloto está fixado no commit `af6bdfc`. A interface segue o contrato KAN-15 0.1.0 e a identidade da KAN-17. A análise usa só a árvore, o diff Git e artefatos de compilação e descoberta anteriores à suíte. [Protocolo](../README.md) · [Contrato](../../KAN-15/README.md) · [Identidade](../../KAN-17/README.md)

## Ordem de referência para os modelos

Em `congelado/<posição>/selection.csv`, cada método descoberto recebe uma decisão. Em `rankings.csv`, `rank` começa em 1 e segue `test_id` crescente por ordem ordinal sensível a maiúsculas. Todos os candidatos têm a mesma prioridade inicial. T2 e T3 podem reordenar esses métodos. Fixe a versão dos CSVs pelo commit Git e valide os SHA-256 do manifesto. Use a mesma lista para todos os mutantes do SHA.

## Reprodução

A partir da raiz do repositório de pesquisa, use PowerShell 7.5+, Node 24 e o clone Git da KAN-10. A posição 26 é compilada e congelada antes das demais. O contêiner da KAN-13 usa JDK 21.0.11, Maven 3.9.11, Linux/amd64, UTC e cache Maven inicialmente vazio em cada chamada.

```powershell
$t1 = 'evidencias/MUTACAO/t1'
$fonte = Join-Path $env:TEMP 'kan10-commons-lang-598dfc163b8b.git'
& "$t1/descobrir.ps1" -Fonte $fonte -Posicao 26
node "$t1/selecionar.mjs" 26 $fonte
```

Execute a reprodução em uma cópia de trabalho com a pasta de saída da posição livre. A descoberta reutiliza `DescobertaT0.java` da KAN-16 sobre `target/test-classes` da compilação limpa. Os inventários anteriores da KAN-16 usavam os XML para enumerar classes e obter o classpath. A entrada daqui é o classpath Maven pré-execução com o launcher da versão da plataforma JUnit resolvida. O POM efetivo preserva o Surefire e seus filtros para conferência. O único fonte de teste no recorte que corresponde aos outros padrões padrão do Surefire sem terminar em `Test.java` é `TestClassBuilder.java`, um auxiliar ASM sem descritores de teste. Classes aninhadas entram pelo plano da raiz. [Sonda e proveniência da KAN-16](../../KAN-16/README.md)

## Regra do seletor 1.0.0

O seletor exige que o primeiro pai do Git coincida com o protocolo. Cada Java de produção ou de testes adicionado ou modificado e com classe compilada mapeável vira uma semente. Alterações de Javadoc na classe também geram sementes. `src/changes/changes.xml` é o changelog do projeto e tem exceção explícita.

Uma aresta vai de uma classe à sua dependência. O grafo combina referências do `jdeps` com nomes de classes locais no fonte, incluindo referências apagadas pelo compilador e nomes literais. Classes internas de bytecode são atribuídas à classe raiz. A inferência admite arestas de supertipo para subtipo de produção como aproximação conservadora para despacho. Em testes, as dependências incluem classes-base e auxiliares alcançados na direção direta. A busca inversa segue as arestas transitivamente a partir das sementes e preserva uma rota mais curta e determinística por classe. Todos os métodos de uma raiz de teste recebem a decisão da classe. A granularidade de dependência pode ampliar a seleção quando utilitários de uso geral ligam classes que chamam métodos distintos.

Fallback inclui a suíte descoberta quando o diff contém Java removido ou outro caminho sem mapeamento, inclusive recursos e configuração, quando o jdeps deixa uma referência interna sem resolução, quando falta uma classe de execução no grafo ou quando nenhum candidato alcança uma semente. Uma falha de descoberta ou inventário ilegível impede o congelamento, pois a população de fallback depende do inventário. A aproximação lexical pode fundir homônimos. Reflexão calculada, despacho por bibliotecas externas e efeitos indiretos de estado global podem escapar à análise. Uma rota estática é motivo de inclusão, sem afirmar cobertura dos métodos ou linhas alterados.

`overhead.csv` registra a janela do seletor Node, da consulta ao primeiro pai até a construção das linhas, incluindo diff, leitura das entradas, grafo, busca e ordenação. Os manifestos guardam a duração bruta e a política de cache. Compilação, resolução Maven, descoberta JUnit, geração do jdeps, gravação de evidências e PIT ficam fora dessa janela. O custo registrado pressupõe inventário e jdeps preparados para o SHA e não mede a latência de ponta a ponta.

## Comparação

A etapa de avaliação lê os conjuntos congelados no Git e verifica os hashes antes de abrir a matriz local. A projeção identifica uma detecção quando há ao menos uma falha induzida no escopo. Para concluir ausência de detecção, exige observação negativa em todos os métodos daquele escopo. Skip, falta de linha, ambiguidade e infraestrutura permanecem desconhecidos. A preservação é calculada entre os detectados por T0 com desfecho conhecido também em T1. O intervalo entre todos os detectados por T0 mostra o efeito dos casos T1 desconhecidos. Com denominador vazio, a taxa correspondente fica indisponível.

A projeção sobre a matriz T0 não mede fisicamente o tempo da execução T1. A redução refere-se à quantidade de métodos. Os resultados sintéticos ficam fora do histórico da Entrega 3. A KAN-18 continua formalmente bloqueada pela KAN-12. [KAN-18](https://cin-team-test-prioritization.atlassian.net/browse/KAN-18)

## Listas congeladas

| Posição | Métodos de T0 | Métodos de T1 | Redução | Seletor (ms) |
| ---: | ---: | ---: | ---: | ---: |
| [15](congelado/15/manifesto.json) | 4.651 | 4.647 | 0,086% | 399 |
| [26](congelado/26/manifesto.json) | 4.652 | 4.648 | 0,086% | 463 |
| [42](congelado/42/manifesto.json) | 4.657 | 4.653 | 0,086% | 400 |
| [50](congelado/50/manifesto.json) | 4.657 | 4.653 | 0,086% | 400 |
| [96](congelado/96/manifesto.json) | 4.663 | 4.659 | 0,086% | 404 |

O commit `78aa63f` fixou a posição 26 primeiro. As demais posições usam o mesmo seletor e ficam no commit de congelamento completo. Os cinco recortes preservaram caminhos de dependência e não acionaram fallback. A redução estreita vem do fechamento transitivo no nível de classe. Na posição 26, `BooleanUtilsTest → BooleanUtils → ObjectUtils → StringUtils → LocaleUtils` é um exemplo de rota compilada até o alvo.

Para executar os testes locais de identidade, transitividade e preservação com observações incompletas:

```powershell
node --test evidencias/MUTACAO/t1/t1.test.mjs
```
