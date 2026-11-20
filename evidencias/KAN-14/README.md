# KAN-14 — Piloto histórico do T0 para a Entrega 3

O lote aprovado contém as posições 1, 26, 50, 75 e 100 do [recorte de 100 revisões da KAN-10](../KAN-10/commits.csv). O [lote fixado por SHA](lote.csv) identifica as duas tentativas reaproveitadas. A posição 1 provém da primeira suíte histórica da KAN-14 e a posição 100 provém da [suíte completa da âncora da KAN-13](../KAN-13/pilotos/ancora/README.md). [Cartão KAN-14](https://cin-team-test-prioritization.atlassian.net/browse/KAN-14)

## Resultado de 20 de novembro de 2026

| Posição | Tentativa | XML | Casos | Aprovados | Ignorados | Falhas | Erros | Ponta a ponta (s) |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Reaproveitada da KAN-14 | 227 | 59.449 | 59.436 | 13 | 0 | 0 | 291,482 |
| 26 | Executada na KAN-14 | 227 | 59.452 | 59.439 | 13 | 0 | 0 | 283,184 |
| 50 | Executada na KAN-14 | 227 | 59.953 | 59.940 | 13 | 0 | 0 | 292,398 |
| 75 | Executada na KAN-14 | 227 | 59.956 | 59.943 | 13 | 0 | 0 | 291,649 |
| 100 | Reaproveitada da KAN-13 | 228 | 59.960 | 59.946 | 14 | 0 | 0 | 306,912 |
| **Total** | | **1.136** | **298.770** | **298.704** | **66** | **0** | **0** | |

As cinco tentativas registraram `BUILD SUCCESS` e código 0 no Maven e no executor. A conferência independente reconciliou os 1.136 XML com os resumos do Maven e confirmou que as novas tentativas ocorreram em série. Uma chamada adicional no modo normal reutilizou os cinco IDs, e `-SomenteVerificar` reproduziu o mesmo manifesto. O verificador também reconciliou uma falha de asserção no controle da KAN-13 e rejeitou evidência com hash divergente. O controle fica fora das métricas do piloto.

## Manifesto para a KAN-16

O [manifesto versionado](execucoes.json) lista as cinco entradas em `selecionadas`, com SHAs, IDs, hashes da fonte, códigos de saída, contagens e caminhos reais de `ambiente.json`, `maven.log` e `surefire/` relativos à raiz do repositório. Os arquivos brutos permanecem sob `resultados/KAN-13/` e `resultados/KAN-14/` no repositório local. Use o `sha` como chave de integração e os campos `surefire` e `tentativa` para localizar os XML da revisão.

## Reprodução e retomada

Use PowerShell 7.3 ou superior e um clone do Commons Lang com os cinco commits. Para preparar um clone, siga o [bootstrap da KAN-13](../../infra/commons-lang/README.md#bootstrap). Para rodar as suítes pendentes em ambiente comparável, a tag local `test-prioritization/commons-lang:kan13` precisa apontar para a imagem aprovada `sha256:6e15bf7fd834e6998883afacb56e4b6de6b180fff899bf3fb0474840f5ac93d6`. Use a imagem aprovada no Docker Desktop e acesso ao Maven Central.

Na raiz do repositório, com `$fonte` apontando para o clone:

```powershell
./evidencias/KAN-14/executar-lote.ps1 -Fonte $fonte
./evidencias/KAN-14/executar-lote.ps1 -Fonte $fonte -SomenteVerificar
```

O primeiro comando confere as posições no CSV, resolve os cinco SHAs como commits exatos e calcula o SHA-256 das exportações antes de chamar o [executor da KAN-13](../../infra/commons-lang/executar.ps1). O executor roda `mvn clean test` em Docker Linux/amd64 com Eclipse Temurin 21.0.11, Maven 3.9.11, UTC e cache Maven frio. A chamada serial grava uma pasta por SHA e tentativa, com `ambiente.json`, `maven.log` e `surefire/`. A trava em `resultados/KAN-14/lote.lock` impede duas chamadas simultâneas do fluxo no mesmo repositório.

Ao repetir o primeiro comando, o fluxo procura e revalida as tentativas existentes. As posições 1 e 100 usam exclusivamente os IDs fixados em `lote.csv`. Se faltar evidência dessas posições, recupere os arquivos das tentativas originais. Para as outras posições, o fluxo reaproveita a primeira tentativa válida em ordem de ID ou abre uma nova tentativa quando necessário. Ele preserva as saídas anteriores. Se uma tentativa deixar o contêiner ativo ou com estado indeterminado, o fluxo interrompe a sequência e indica o contêiner a inspecionar antes de retomar. O modo `-SomenteVerificar` reconta as evidências e regenera `resultados/KAN-14/execucoes.json` sem chamar o executor ou o Docker. O fluxo devolve código diferente de zero enquanto alguma posição estiver sem suíte validada.

## Conferência da evidência

O verificador compara o SHA solicitado, o SHA resolvido e o hash do `git archive` com os metadados. Confere a imagem, as versões, o comando da suíte completa, o cache frio, o fuso configurado e o `user.timezone` dos XML. Ele reconcilia os códigos de saída e o resumo final do Maven com a contagem de elementos `testcase`, incluindo os estados `failure`, `error` e `skipped`. A soma dos atributos `testsuite/@tests` é registrada à parte, pois há relatórios com `tests="0"` que contêm casos.

Uma suíte pode ser validada com falhas quando o Maven atribui o `BUILD FAILURE` a falhas no Surefire e os totais coincidem com os XML. Se faltar confirmação de uma suíte completa, o fluxo guarda o diagnóstico e as saídas para inspeção. Um erro do executor, uma interrupção, um impedimento de build ou uma divergência de evidência ficam fora dos totais do T0. O tempo de ponta a ponta inclui inicialização, resolução de dependências e coleta dos relatórios.

Para a coleta por método, use a regra da [KAN-17](../KAN-17/README.md) para associar os casos aos métodos. O piloto cobre cinco das 100 posições. As outras 95 revisões, a duração e os resultados agregados por método e a comparação com estratégias de seleção ficam fora deste lote.
