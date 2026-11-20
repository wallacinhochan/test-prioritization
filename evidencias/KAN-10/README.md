# KAN-10 — Recorte candidato do Apache Commons Lang

O recorte tem 100 revisões consecutivas e termina no commit `598dfc163b8b410fb3bb8794521206ec8dcec82a` da tag `rel/commons-lang-3.20.0`, conforme a âncora registrada pela KAN-9. [Cartão KAN-10](https://cin-team-test-prioritization.atlassian.net/browse/KAN-10) · [Evidência da KAN-9](../KAN-9/README.md) · [Tag no Apache Commons Lang](https://github.com/apache/commons-lang/tree/rel/commons-lang-3.20.0)

## Critérios de elegibilidade

Critérios fixados na etapa da amostra, antes da consulta a resultados de testes para esta auditoria.

1. Percorrer até 100 commits consecutivos, incluindo a âncora. Seguir apenas o primeiro pai e apresentar a sequência do mais antigo ao mais recente pela ancestralidade. Um merge ocupa uma posição e seu diff usa o primeiro pai. Commits alcançáveis apenas pelos demais pais ficam fora do percurso.
2. A triagem estática exige o `pom.xml` na raiz e pelo menos um arquivo `.java` sob `src/test/java/` na árvore da revisão.
3. Para confirmar a elegibilidade operacional, verificar checkout exato, resolução de dependências, compilação do código e dos testes, descoberta de testes e início da suíte em ambiente versionado. Falhas de asserção ou erros observados em testes executados são resultados do experimento e preservam a inclusão. Um impedimento que inviabilize a coleta, como dependência indisponível, falha de compilação ou suíte que não inicia, deve ter motivo, evidência e verificação pendente registrados para o SHA. Em todos os casos, manter a linha e a posição originais. Alterações de build ou teste são campos descritivos.

## Arquivo e auditoria

O [commits.csv](commits.csv) contém o recorte completo. As posições 1 e 2 são a amostra publicada primeiro para a KAN-15. A tabela usa UTF-8 sem BOM, vírgula como separador e aspas nos valores. Campos vazios representam ausência de valor ou lista vazia, conforme o campo.

| Campo | Regra |
| --- | --- |
| `position` | Inteiro a partir de 1 na sequência auditada. |
| `commit_sha`, `first_parent_sha` | SHAs Git completos e minúsculos. O pai da posição 1 está fora do recorte. `commit_sha` é a chave de integração. |
| `committer_date_utc` | Data do committer em UTC, com precisão de segundos e sufixo `Z`. |
| `is_merge` | `true` se o commit tem dois ou mais pais. |
| `build_changed`, `build_paths` | Indicador e caminhos alterados de configuração e automação de build. Abrange arquivos Maven, Ant e Gradle identificados pelos nomes abaixo, Maven Wrapper, workflow Maven e configurações de ferramentas invocadas pelo build sob `src/conf/`. |
| `tests_changed`, `test_paths` | Indicador e caminhos alterados sob `src/test/` ou `src/it/`, incluindo recursos. Um ajuste em `pom.xml` que afete a execução aparece em build e deve ser inspecionado pelo diff quando relevante. |
| `eligibility_status` | `pending` quando a triagem estática passa e a confirmação operacional está em aberto. `eligible` quando a validação operacional está documentada. `blocked` indica um impedimento observado que inviabiliza a coleta. |
| `blocker_reason`, `eligibility_evidence`, `pending_checks` | Motivo de impedimento observado, evidência por SHA da triagem estática e da execução quando disponível, e verificações operacionais ainda em aberto. |

Os caminhos vêm de `git diff --name-only --no-renames` entre o primeiro pai e a revisão, com `|` entre caminhos. Uma renomeação conta pelos caminhos removido e adicionado. A regra de build cobre `pom.xml`, `build.xml`, `build.gradle[.kts]`, `settings.gradle[.kts]` e `gradle.properties` em qualquer diretório, além de `.mvn/`, `mvnw`, `mvnw.cmd`, `.github/workflows/maven.yml` ou `maven.yaml` e `src/conf/` na raiz. Os indicadores registram mudanças nesses caminhos.

- A posição 1 é [`921c1b4e09ed7b6900ad7243cffb33b373980cc5`](https://github.com/apache/commons-lang/commit/921c1b4e09ed7b6900ad7243cffb33b373980cc5), em `2025-09-24T13:51:27Z`. Seu primeiro pai é `562cc561dc9b6329eb005156cbe1608a6e3cc8d9`.
- A posição 100 é [`598dfc163b8b410fb3bb8794521206ec8dcec82a`](https://github.com/apache/commons-lang/commit/598dfc163b8b410fb3bb8794521206ec8dcec82a), em `2025-11-12T19:55:59Z`. O commit coincide com o SHA da KAN-9 e com o commit obtido da tag.
- Conferência do CSV contra o Git local. 100 SHAs completos e distintos, posições de 1 a 100, 99 vínculos consecutivos pelo primeiro pai e o primeiro pai externo presente no histórico. Há 3 merges, 19 revisões com mudanças de build e 22 com mudanças de teste. Os dois indicadores podem coincidir.
## Triagem estática e validação operacional

- **Triagem estática.** As 100 revisões têm `pom.xml` na raiz e pelo menos um arquivo Java sob `src/test/java/`. A triagem encontrou zero impedimentos estáticos.
- **Validação operacional.** A revisão 100 está como `eligible`. Na KAN-9, `mvn clean test` compilou código e testes e executou a suíte no SHA exato com JDK 21.0.11 e Maven 3.9.11 em UTC. O Surefire registrou 59.960 casos, com 59.946 aprovados e 14 ignorados. [Ambiente e SHA](../KAN-9/resultados/utc/ambiente.txt) · [Log da suíte em UTC](../KAN-9/resultados/utc/suite.log)
- **Ocorrência observada.** Na mesma revisão, `DurationFormatUtilsTest#testFourYears` falhou em `America/Sao_Paulo` e passou em UTC. A suíte compilou e executou nos dois fusos, e a falha observada preserva a revisão no recorte. O CSV mantém `blocker_reason` vazio em todas as linhas, pois a auditoria não constatou impedimentos à coleta. [Log no fuso local](../KAN-9/resultados/fuso-local/suite.log) · [Diagnóstico em UTC](../KAN-9/resultados/diagnostico-utc/duration-format.log)
- **Verificações pendentes.** As posições 1 a 99 permanecem `pending`. Para cada SHA, falta confirmar checkout exato, resolução de dependências, compilação, descoberta de testes e início da suíte em ambiente versionado. Essas verificações em aberto constam em `pending_checks`.

## Reprodução do recorte

PowerShell com Git. O clone raso usa 101 níveis para incluir também o primeiro pai da revisão mais antiga, necessário para o primeiro diff.

```powershell
$anchor = '598dfc163b8b410fb3bb8794521206ec8dcec82a'
$source = Join-Path ([IO.Path]::GetTempPath()) ('kan10-commons-lang-' + [guid]::NewGuid())
git clone --bare --single-branch --no-tags --depth 101 --branch rel/commons-lang-3.20.0 https://github.com/apache/commons-lang.git $source
if ($LASTEXITCODE -ne 0) { throw 'Falha ao obter o Git do Commons Lang' }
if ((git -C $source rev-parse 'refs/tags/rel/commons-lang-3.20.0^{commit}') -ne $anchor) { throw 'SHA da tag divergente' }

git -C $source log --first-parent --max-count=100 --reverse '--format=%H|%P|%cI' $anchor

# Exemplo de diff e inspeção da árvore na primeira revisão
$sha = '921c1b4e09ed7b6900ad7243cffb33b373980cc5'
git -C $source diff --name-status --no-renames "${sha}^1" $sha --
git -C $source ls-tree -r --name-only $sha -- pom.xml src/test/java
```

Para refazer os indicadores, aplique as regras de caminhos ao diff de cada revisão contra o primeiro SHA em `%P`. Normalize `%cI` para UTC ao preencher a data.

## Integração e pendências

- **KAN-15.** Juntar por igualdade exata de `commit_sha`. Para carregar a tabela experimental, mapear `position` para `commit_order`, `committer_date_utc` para `committed_at` e manter os indicadores `build_changed` e `tests_changed`. `source_ref` aponta para `evidencias/KAN-10/commits.csv#commit_sha=<sha>`. A junção pelo SHA foi revalidada no repositório oficial. As duas linhas da amostra preservada e as duas do exemplo da KAN-15 correspondem aos mesmos SHAs no CSV consolidado, inclusive com a ordem dos exemplos invertida. A projeção dos 100 registros segue o mapeamento do contrato. A amostra permanece como registro da verificação inicial. O contrato atualizado preserva `pending` em `eligibility_status`. Uma decisão operacional favorável vai para `eligible`. Um impedimento registrado como `blocked` na auditoria vai para `ineligible` quando a exclusão for decidida, com `blocker_reason` em `exclusion_reason`. [Contrato da KAN-15](../KAN-15/README.md)
- **KAN-11.** Usar o recorte e os caminhos alterados de testes para buscar evidências por SHA. A falha de fuso na revisão 100 tem reprodução controlada e serve como evidência ambiental. A auditoria ainda precisa verificar cobertura temporal e resultados por teste, distinguir falhas naturais, ambientais e Defects4J e contar episódios independentes. [Sequência auditada](commits.csv) · [Diagnóstico da KAN-9](../KAN-9/README.md#diagnóstico-do-fuso) · [Cartão KAN-11](https://cin-team-test-prioritization.atlassian.net/browse/KAN-11)
- **KAN-14.** Usar os SHAs na ordem auditada para checkout exato e os indicadores e caminhos alterados para orientar o diagnóstico. A execução da revisão 100 em UTC fornece uma referência do ambiente. Ainda falta automatizar e registrar a execução histórica do T0 por SHA e versão de ambiente, com logs de execução e de eventuais impedimentos. [SHAs e indicadores](commits.csv) · [Receita da KAN-9](../KAN-9/README.md) · [Cartão KAN-14](https://cin-team-test-prioritization.atlassian.net/browse/KAN-14)

## Aceite

- [x] Intervalo reproduzível, critérios de elegibilidade e tratamento de merges documentados.
- [x] Lista auditável de 100 revisões com ordem, SHA, mudanças de build e testes, triagem estática e evidência operacional disponível.
- [x] Junção com a amostra e o exemplo da KAN-15 conferida pelo `commit_sha` no repositório oficial.
- [ ] Versionar os arquivos consolidados e registrar o aceite no Jira.
- [ ] Confirmar a elegibilidade operacional das 99 revisões pendentes na execução histórica. A revisão do contrato da KAN-15 pelo grupo tem aceite próprio.
