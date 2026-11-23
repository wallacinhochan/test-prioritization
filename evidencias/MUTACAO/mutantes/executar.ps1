#Requires -Version 7.5
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet(15, 26, 42, 50, 96)]
    [int]$Posicao,

    [Parameter(Mandatory)]
    [ValidateSet('controle', 'pit', 'replay', 'encerrar')]
    [string]$Fase,

    [string]$Fonte = (Join-Path ([IO.Path]::GetTempPath()) 'kan10-commons-lang-598dfc163b8b.git'),

    [string]$Congelamento,

    [string]$Liberacao
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$rev = Import-Csv (Join-Path $PSScriptRoot revisoes.csv) | Where-Object posicao -eq $Posicao
$local = Join-Path $PSScriptRoot "local/$Posicao"
$entrada = Join-Path $local entrada
$imagem = 'sha256:6e15bf7fd834e6998883afacb56e4b6de6b180fff899bf3fb0474840f5ac93d6'
$nome = "tp-mutacao-v1-$Posicao"
$null = New-Item -ItemType Directory -Force $local
$lock = [IO.File]::Open((Join-Path $local execucao.lock), 'OpenOrCreate', 'ReadWrite', 'None')
$utf8 = [Text.UTF8Encoding]::new($false)

function Invoke-Docker {
    docker @args
    if ($LASTEXITCODE) { throw "Docker retornou $LASTEXITCODE na operação $($args[0])." }
}

function Send-File([string]$Arquivo, [string]$Destino) {
    Invoke-Docker cp $Arquivo "${nome}:$Destino"
}

function Invoke-Rodada([string]$Rodada, [string[]]$Argumentos) {
    $saida = Join-Path $local $Rodada
    if (Test-Path -LiteralPath $saida) { throw "Evidência já existente em $saida." }
    $null = New-Item -ItemType Directory $saida
    $destino = "/evidencia/$Rodada"
    docker exec $nome sh /entrada/executar.sh $Rodada @Argumentos
    $codigo = $LASTEXITCODE
    Invoke-Docker cp "${nome}:$destino/." $saida
    $registro = Get-Content -LiteralPath (Join-Path $saida execucao.json) -Raw | ConvertFrom-Json
    if ($codigo -ne $registro.codigo) { throw "Código da rodada $Rodada diverge do Docker." }
    $registro
}

try {
    if ($Posicao -ne 26) {
        $gate = Join-Path $PSScriptRoot 'pos-26/resumo.json'
        if (!(Test-Path -LiteralPath $gate) -or
            !(Get-Content -LiteralPath $gate -Raw | ConvertFrom-Json).gate_aprovado) {
            throw 'A ampliação depende da aprovação do gate na posição 26.'
        }
    }
    if ($Posicao -eq 96 -and $Fase -ceq 'replay') {
        if ([string]::IsNullOrWhiteSpace($Liberacao)) {
            throw 'O replay da posição 96 requer a referência da liberação pela coordenação.'
        }
        if (!$Congelamento -or !(Test-Path -LiteralPath $Congelamento -PathType Leaf)) {
            throw 'O replay da posição 96 requer a referência ao registro de congelamento do modelo.'
        }
        $repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
        $refModelo = 'evidencias/MUTACAO/modelos/congelamento.json'
        $registroModelo = (Resolve-Path -LiteralPath $Congelamento).Path
        if ($registroModelo -ine (Join-Path $repo $refModelo)) {
            throw 'Informe o congelamento versionado pela frente de modelos.'
        }
        $commitModelo = git -C $repo log -1 --format=%H -- $refModelo
        if ($LASTEXITCODE -or $commitModelo -cnotmatch '\A[0-9a-f]{40}\z') {
            throw 'O Git ainda não registra o congelamento do modelo.'
        }
        git -C $repo diff --quiet $commitModelo -- $refModelo
        if ($LASTEXITCODE) { throw 'O congelamento local diverge do commit.' }
        $registroGit = Join-Path $local congelamento-modelo-git.json
        git -C $repo show "${commitModelo}:$refModelo" > $registroGit
        if ($LASTEXITCODE) { throw 'Falha ao recuperar o congelamento a partir do Git.' }
        $modelo = Get-Content -LiteralPath $registroGit -Raw | ConvertFrom-Json
        if ($modelo.versao -ne 1 -or !$modelo.treino.suficiente -or !$modelo.validacao.suficiente) {
            throw 'O congelamento não confirma suficiência de treino e validação.'
        }
        [ordered]@{
            commit = $commitModelo
            referencia = $refModelo
            sha256 = (Get-FileHash -LiteralPath $registroGit).Hash.ToLowerInvariant()
            liberacao = $Liberacao.Trim()
        } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $local congelamento.json)
    }
    if ($Fase -ceq 'encerrar') {
        Invoke-Docker stop $nome
        return
    }
    if ($Fase -ceq 'controle') {
        if (Test-Path -LiteralPath $entrada) { throw "Já há uma árvore de entrada em $entrada." }
        $fonteResolvida = (Resolve-Path -LiteralPath $Fonte).Path
        $gitArgs = @('-c', "safe.directory=$($fonteResolvida.Replace('\','/'))", '-C', $fonteResolvida)
        $sha = $rev.sha
        $verificado = git @gitArgs rev-parse "${sha}^{commit}" "${sha}^1"
        if ($LASTEXITCODE -or $verificado.Count -ne 2 -or
            $verificado[0] -cne $sha -or $verificado[1] -cne $rev.pai) {
            throw 'O Git não confirmou a revisão e o primeiro pai fixados.'
        }
        $diff = @(git @gitArgs diff --diff-filter=AMR --name-only $rev.pai $sha -- src/main/java)
        if ($LASTEXITCODE) { throw 'Falha ao ler o diff de produção.' }
        $classes = @($diff | Where-Object { $_ -cmatch '^src/main/java/.+\.java$' } |
            ForEach-Object { ($_ -creplace '^src/main/java/|\.java$','').Replace('/','.') })
        if (!$classes.Count -or ($Posicao -eq 26 -and ($classes -join ',') -cne 'org.apache.commons.lang3.LocaleUtils')) {
            throw 'Escopo de classes ausente ou divergente na posição 26.'
        }
        $id = Invoke-Docker image inspect --format '{{.Id}}' $imagem
        if ($id -cne $imagem) { throw 'A imagem local difere da referência KAN-13.' }
        $null = New-Item -ItemType Directory $entrada
        $tar = Join-Path $entrada fonte.tar
        git @gitArgs archive --format=tar "--output=$tar" $sha
        if ($LASTEXITCODE) { throw 'Falha no git archive.' }
        [ordered]@{
            posicao = $Posicao; sha = $sha; pai = $rev.pai; imagem = $imagem
            classes = $classes; fonte_tar_sha256 = (Get-FileHash -LiteralPath $tar).Hash.ToLowerInvariant()
        } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $entrada fonte.json)
        Invoke-Docker create --name $nome --platform linux/amd64 --env TZ=UTC --entrypoint /bin/sleep $imagem infinity
        Invoke-Docker start $nome
        Invoke-Docker exec $nome mkdir /entrada /evidencia
        Send-File $tar /entrada/fonte.tar
    }

    $roteiro = Join-Path $entrada executar.sh
    [IO.File]::WriteAllText($roteiro, [IO.File]::ReadAllText((Join-Path $PSScriptRoot executar.sh)).Replace("`r`n", "`n"), $utf8)
    Send-File $roteiro /entrada/executar.sh
    if ($Fase -ceq 'controle') {
        if ((Invoke-Rodada controle).codigo) { throw "Controle rejeitado. Consulte $local/controle/maven.log." }
    } elseif ($Fase -ceq 'pit') {
        $fonteInfo = Get-Content -LiteralPath (Join-Path $entrada fonte.json) -Raw | ConvertFrom-Json
        Send-File (Join-Path $PSScriptRoot pit.xml) /entrada/pit.xml
        if ((Invoke-Rodada pit @($fonteInfo.classes -join ',')).codigo) { throw "PIT falhou. Consulte $local/pit/maven.log." }
    } else {
        $manifesto = Get-Content -LiteralPath (Join-Path $PSScriptRoot "pos-$Posicao/manifesto.json") -Raw |
            ConvertFrom-Json
        if ($manifesto.sha -cne $rev.sha -or !$manifesto.selecionados -or $manifesto.selecionados.Count -gt 4) {
            throw 'Manifesto ausente ou com seleção inválida.'
        }
        $relatorios = @(Get-ChildItem -LiteralPath (Join-Path $local 'controle/surefire') -Filter 'TEST-*.xml' -File)
        $classpaths = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        $classesSurefire = foreach ($relatorio in $relatorios) {
            $xml = [xml]::new()
            $xml.Load($relatorio.FullName)
            $classpath = $xml.SelectSingleNode("/testsuite/properties/property[@name='surefire.test.class.path']/@value").Value
            if (!$classpath) { throw "Classpath ausente em $($relatorio.Name)." }
            $null = $classpaths.Add($classpath)
            $relatorio.Name -creplace '^TEST-|\.xml$', ''
        }
        if ($classpaths.Count -ne 1) { throw 'Esperava-se um classpath comum registrado pelo Surefire.' }
        foreach ($nomeArquivo in 'classpath.txt','classes-surefire.txt') {
            $valores = if ($nomeArquivo -ceq 'classpath.txt') { $classpaths } else { $classesSurefire }
            $arquivo = Join-Path $entrada $nomeArquivo
            [IO.File]::WriteAllText($arquivo, ($valores -join "`n") + "`n", $utf8)
            Send-File $arquivo "/entrada/$nomeArquivo"
        }
        Send-File (Join-Path $PSScriptRoot '../../KAN-16/DescobertaT0.java') /entrada/DescobertaT0.java
        foreach ($rodada in 'inventario','intacto') {
            if ((Invoke-Rodada $rodada).codigo) { throw "Falha em $rodada. Consulte o log." }
        }
        & (Join-Path $PSScriptRoot rotular.ps1) -Posicao $Posicao -Controles
        for ($i = 0; $i -lt $manifesto.selecionados.Count; $i++) {
            $variante = $manifesto.selecionados[$i]
            $argumentos = @($variante.classe.Replace('.','/'), $variante.bytecode,
                $variante.bytecode_sha256, $variante.original_sha256)
            if ($argumentos[0] -cnotmatch '\A(?:[\w$]+/)+[\w$]+\z' -or
                $argumentos[1] -cnotmatch '\A(?:[\w$]+/)+[\w$.]+\.class\z' -or
                $argumentos[2] -cnotmatch '\A[0-9a-f]{64}\z' -or
                $argumentos[3] -cnotmatch '\A[0-9a-f]{64}\z') { throw 'Variante inválida no manifesto.' }
            $registro = Invoke-Rodada "variante-$($i + 1)" $argumentos
            Write-Host "Variante $($i + 1) concluída com código Maven $($registro.codigo)."
        }
        $primeira = $manifesto.selecionados[0]
        $primeirosArgs = @($primeira.classe.Replace('.','/'), $primeira.bytecode,
            $primeira.bytecode_sha256, $primeira.original_sha256)
        $null = Invoke-Rodada repeticao $primeirosArgs
        if ((Invoke-Rodada restaurado $primeirosArgs).codigo) { throw 'Falha na suíte após restauração.' }
    }
} finally {
    $lock.Dispose()
}
