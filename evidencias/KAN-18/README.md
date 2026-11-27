# KAN-18 — Seleção estática T1 com DIRTS

O seletor T1 2.0.0 usa **DIRTS 1.0**, compilado do commit `62efcec2f909f93fffdd4ae1da24b0aee1071749`. No estudo de dez revisões, o DIRTS reteve 4.904 métodos, ante 14.602 do STARTS e 32.649 do T1 anterior. A redução relativa ao T1 foi de **84,98%** na amostra e de **98,75%** no subconjunto de cinco revisões com alterações no código de produção além de comentários e formatação. O DIRTS venceu o STARTS em quatro revisões e empatou nas outras seis. Esse é o critério da substituição. As porcentagens medem tamanho da seleção. [Estudo comparativo](estudo-reducao-t1.md) · [Piloto STARTS](poc-starts.md) · [Projeto DIRTS](https://github.com/tum-i4/dirts)

## Regra de seleção

1. Confirme o SHA alvo e seu primeiro pai pelo manifesto KAN-10. Exporte o alvo para descobrir os métodos com JUnit Launcher e preparar o inventário de bytecode. Para mudanças suportadas, exporte também a árvore do pai e os arquivos Java adicionados ou modificados no alvo.
2. No mesmo diretório Linux, execute `method_level_select -Dstandalone=true` no pai para gerar o estado `.dirts`. Repita no pai e confirme que o controle sem mudanças exclui todas as raízes presentes. Sobreponha os arquivos do alvo e execute o seletor. Cada fase limpa o arquivo `Excludes` antes da chamada, preservando o grafo. Isso evita que as exclusões antigas se acumulem, comportamento observado no piloto quando o Surefire não fornece um caminho explícito.
3. Forme o conjunto selecionado com o complemento das exclusões da rodada alvo sobre as raízes do inventário JUnit. Inclua todos os IDs `classe#metodo(tipos)` da raiz selecionada, inclusive os descritores aninhados. A análise DIRTS opera por método no código fonte e sua saída Maven exclui por classe.
4. Use o inventário integral em alterações de POM, configuração, recursos, remoções, renomeações ou classes alteradas sem bytecode mapeado. Uma modificação isolada em `src/changes/changes.xml` também cai no fallback por falta de semente. Esse changelog pode acompanhar uma mudança Java elegível. Aplique fallback igualmente em caso de erro DIRTS, falha do controle, arquivo de exclusões inválido, referência interna sem resolução, diagnóstico incompleto, ausência de seleção com recálculo indicado ou omissão de uma raiz de teste alterada quando há recálculo. Um diff Java sem alterações reconhecidas pelo DIRTS pode produzir seleção vazia, como observado nas revisões de documentação.
5. Exija inventário JUnit válido para publicar. As linhas seguem o contrato KAN-15, com razões `dependency`, `no_dependency` e `fallback`. T1 mantém postos ordinais por `test_id` e escore vazio. Cada cenário derivado deve consumir exatamente o conjunto publicado para sua versão de T1.

[Recorte KAN-10](../KAN-10/commits.csv) · [Contrato KAN-15](../KAN-15/README.md) · [Identidade KAN-17](../KAN-17/README.md)

## Reprodução

Use Git, Node, PowerShell, Docker Linux/amd64, acesso ao Maven Central e o clone do Commons Lang da KAN-10. A imagem base usa o Dockerfile KAN-13 com Temurin 21.0.11, Maven 3.9.11 e UTC. A segunda imagem instala o DIRTS no cache Maven privado a partir do arquivo do commit fixado.

```powershell
docker build --platform linux/amd64 -t test-prioritization/commons-lang:kan18-reconstruida infra/commons-lang
$ctx = New-Item -Force -ItemType Directory evidencias/KAN-18/local/imagem-dirts
$codigo = Join-Path (Resolve-Path evidencias/KAN-18/local).Path 'codigo-dirts'
git clone https://github.com/tum-i4/dirts.git $codigo
git -C $codigo archive --format=tar --output="$($ctx.FullName)/dirts.tar" 62efcec2f909f93fffdd4ae1da24b0aee1071749
docker build --platform linux/amd64 -t test-prioritization/commons-lang:kan18-dirts -f infra/commons-lang/Dockerfile.dirts $ctx.FullName
```

Confira o código de saída de cada comando antes do próximo. Ao repetir o bootstrap, reutilize o Git já clonado ou escolha um contexto vazio. Use um diretório de contexto dedicado, com o arquivo `dirts.tar` como única entrada do Dockerfile derivado.

```powershell
$kan18 = './evidencias/KAN-18'
$fonte = 'C:/caminho/kan10-commons-lang.git'
$posicoes = 75,50,100
foreach ($posicao in $posicoes) {
    & "$kan18/descobrir.ps1" -Fonte $fonte -Posicao $posicao
    node "$kan18/selecionar.mjs" $posicao $fonte
    if ($LASTEXITCODE -ne 0) { throw "Seleção falhou na posição $posicao" }
}
& "$kan18/verificar.ps1" -Posicoes $posicoes -SemT0
```

Omita `-SemT0` para reconciliar com a saída real da KAN-16, usando `-Oraculo` se estiver em outro diretório. A descoberta grava `local/dirts/entradas/<sha>/` com logs, inventário, arquivos exportados, ID da imagem e saídas do DIRTS. A seleção escreve `local/dirts/selecao/<sha>/` com `selection.csv`, `rankings.csv`, `overhead.csv`, `decisoes.json`, `diff.patch` e `manifesto.json`. A publicação é por diretório e preserva resultados de tentativas anteriores. Use novos destinos locais após guardar a rodada existente.

O manifesto registra a versão, o commit DIRTS, a imagem efetiva e hashes das entradas e saídas. O custo de seleção soma a janela DIRTS (preparo do pai, controle e alvo, com as fases Maven correspondentes) à transformação no host. Compilação e descoberta do inventário ocorrem em outra janela. A medição anterior do T1 começa com entradas já preparadas e tem escopo distinto.

## Validação da integração

As três posições abaixo passaram pelo fluxo completo em Docker Linux. O verificador conferiu hashes, contagens, chaves e ordenação dos CSVs. Os IDs selecionados coincidiram exatamente com os do piloto. A validação usou `-SemT0`, sem execução da suíte. [Hashes e SHAs da integração](verificacao-dirts.json)

| Posição | Caso | Inventário | Métodos selecionados |
|---:|---|---:|---:|
| 50 | Mudanças de produção e teste | 4.657 | 72 |
| 75 | Controle positivo com uma classe de teste alterada | 4.659 | 7 |
| 100 | Fallback integral por `pom.xml` | 4.663 | 4.663 |

Em uma reprodução isolada dos artefatos do piloto, a posição 4 publicou um ranking vazio para a mudança de Javadoc e a posição 39 publicou 13 métodos. Ao inserir uma linha inválida nas exclusões da posição 39, o seletor publicou todos os 4.657 métodos com motivo `fallback`. Os três testes existentes do piloto T1 também passaram.

## Publicações anteriores

A evidência versionada em `verificacao.json` e os resultados vinculados à KAN-19 e KAN-20 seguem associados ao seletor 1.0.0. Seus consumidores fixados leem os caminhos históricos `local/entradas` e `local/selecao`. A publicação DIRTS tem caminhos próprios. Sua adoção nos resultados derivados requer gerar os novos conjuntos e refazer os cenários que usam essas chaves. [Documentação do T1 1.0.0](https://github.com/wallacinhochan/test-prioritization/blob/260c1af381b3137b1591af9f33e47e987ac7b2b2/evidencias/KAN-18/README.md) · [Verificação histórica](verificacao.json)
