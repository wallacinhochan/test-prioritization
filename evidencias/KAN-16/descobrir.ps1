#Requires -Version 7.5
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Fonte)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$raiz = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$Fonte = (Resolve-Path -LiteralPath $Fonte).Path
. (Join-Path $PSScriptRoot 'ler-lote.ps1')
$pastaLote = Join-Path $raiz 'resultados/KAN-14'
$trava = [IO.File]::Open((Join-Path $pastaLote 'lote.lock'), 'Open', 'ReadWrite', 'None')
$utf8 = [Text.UTF8Encoding]::new($false)

function Get-Hash([string]$Arquivo) {
    (Get-FileHash -LiteralPath $Arquivo).Hash.ToLowerInvariant()
}

function New-Inventario($Tentativa) {
    $origem = Join-Path $raiz $Tentativa.diretorio
    $pasta = Join-Path $PSScriptRoot 'local/inventarios' "$($Tentativa.sha)-$($Tentativa.id)"
    if (Test-Path -LiteralPath (Join-Path $pasta 'descoberta.json')) {
        "Inventário já registrado para a posição $($Tentativa.posicao)."
        return
    }
    $null = New-Item -ItemType Directory -Path $pasta -Force
    $ambienteRef = Join-Path $origem 'ambiente.json'
    $mavenRef = Join-Path $origem 'maven.log'
    $ambiente = Get-Content -LiteralPath $ambienteRef -Raw | ConvertFrom-Json
    $maven = Get-Content -LiteralPath $mavenRef -Raw
    $provedor = [regex]::Matches($maven, '(?m)^\[INFO\] Using .+ provider ([^\s]+)')
    if ($ambiente.imagem_id -cne 'sha256:6e15bf7fd834e6998883afacb56e4b6de6b180fff899bf3fb0474840f5ac93d6' -or
        $provedor.Count -ne 1 -or $provedor[0].Groups[1].Value -cne 'org.apache.maven.surefire.junitplatform.JUnitPlatformProvider') {
        throw "Imagem ou provedor não reconhecido na posição $($Tentativa.posicao)."
    }
    $classes = [Collections.Generic.List[string]]::new()
    $classpath = $null
    $opcoes = [Xml.XmlReaderSettings]::new()
    $opcoes.DtdProcessing = [Xml.DtdProcessing]::Prohibit
    foreach ($arquivo in Get-ChildItem -LiteralPath (Join-Path $origem 'surefire') -Filter 'TEST-*.xml' -File) {
        $xml = [xml]::new()
        $leitor = [Xml.XmlReader]::Create($arquivo.FullName, $opcoes)
        try { $xml.Load($leitor) } finally { $leitor.Dispose() }
        $suite = $xml.DocumentElement
        $classe = $suite.GetAttribute('name')
        $cp = $suite.SelectSingleNode("properties/property[@name='surefire.test.class.path']/@value").Value
        if ($classe -cnotmatch '\Aorg\.apache\.commons\.[a-zA-Z0-9_.$]+\z' -or $arquivo.Name -cne "TEST-$classe.xml" -or
            $cp -cnotmatch '\A/trabalho/target/test-classes:/trabalho/target/classes(?::/maven-cache/[A-Za-z0-9_./+-]+)+:?\z' -or
            ($classpath -and $classpath -cne $cp)) {
            throw "Contexto de suíte ou classpath incompatível: $($arquivo.Name)."
        }
        $classes.Add($classe)
        $classpath = $cp
    }
    if (!$classes.Count -or $classes.Count -ne $ambiente.xml_surefire) { throw 'Quantidade de relatórios divergente.' }
    $classes.Sort([StringComparer]::Ordinal)
    [IO.File]::WriteAllLines((Join-Path $pasta 'classes.txt'), $classes, $utf8)
    [IO.File]::WriteAllText((Join-Path $pasta 'classpath.txt'), $classpath, $utf8)
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'DescobertaT0.java') -Destination $pasta
    $roteiro = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'descobrir.sh') -Raw
    [IO.File]::WriteAllText((Join-Path $pasta 'descobrir.sh'), $roteiro.Replace([string][char]13, ''), $utf8)
    $tar = Join-Path $pasta 'fonte.tar'
    $log = Join-Path $pasta 'descoberta.log'
    $inventario = Join-Path $pasta 'metodos.tsv'
    try {
        git -c "safe.directory=$($Fonte.Replace('\','/'))" -C $Fonte archive --format=tar "--output=$tar" $Tentativa.sha
        if ($LASTEXITCODE -ne 0 -or (Get-Hash $tar) -cne $ambiente.fonte_tar_sha256) {
            throw "O tar do SHA $($Tentativa.sha) não confere com a execução."
        }
        "Descobrindo métodos da posição $($Tentativa.posicao) em compilação auxiliar."
        $argumentos = @('run','--rm','--pull','never','--platform','linux/amd64','--workdir','/trabalho',
            '--mount',"type=bind,source=$pasta,target=/entrada",'--entrypoint','/bin/sh',
            $ambiente.imagem_id,'/entrada/descobrir.sh')
        docker @argumentos *> $log
        if ($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath $inventario -PathType Leaf)) {
            throw "Descoberta incompleta. Consulte $log."
        }
        [ordered]@{
            sha = $Tentativa.sha; tentativa = $Tentativa.id; fonte_tar_sha256 = $ambiente.fonte_tar_sha256
            imagem_id = $ambiente.imagem_id; ambiente_sha256 = Get-Hash $ambienteRef
            maven_log_sha256 = Get-Hash $mavenRef; codigo_saida = 0
            classes_sha256 = Get-Hash (Join-Path $pasta 'classes.txt')
            classpath_sha256 = Get-Hash (Join-Path $pasta 'classpath.txt')
            inventario_sha256 = Get-Hash $inventario; log_sha256 = Get-Hash $log
            sonda_sha256 = Get-Hash (Join-Path $pasta 'DescobertaT0.java')
            roteiro_sha256 = Get-Hash (Join-Path $pasta 'descobrir.sh')
        } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $pasta 'descoberta.json') -Encoding utf8NoBOM
    } finally {
        if (Test-Path -LiteralPath $tar) { Remove-Item -LiteralPath $tar }
        if (!(Test-Path -LiteralPath (Join-Path $pasta 'descoberta.json')) -and
            (Test-Path -LiteralPath $inventario)) { Remove-Item -LiteralPath $inventario }
    }
}

try {
    $tentativas = @(Get-Kan16Lote $raiz)
    $falhas = @(foreach ($tentativa in $tentativas) {
        try {
            New-Inventario $tentativa | Out-Host
        } catch {
            Write-Warning "Posição $($tentativa.posicao): $($_.Exception.Message)"
            $tentativa.posicao
        }
    })
    if ($falhas.Count) { throw "Descoberta indisponível nas posições $($falhas -join ', ')." }
} finally {
    $trava.Dispose()
}
