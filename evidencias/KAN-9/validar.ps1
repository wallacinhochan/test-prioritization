param(
    [Parameter(Mandatory)][string]$Fonte,
    [Parameter(Mandatory)][string]$Jdk,
    [Parameter(Mandatory)][string]$Saida,
    [string]$Maven = 'mvn.cmd',
    [string]$CacheMaven,
    [ValidateSet('UTC')][string]$Fuso,
    [switch]$SomenteDiagnostico
)

$ErrorActionPreference = 'Stop'
$commitEsperado = '598dfc163b8b410fb3bb8794521206ec8dcec82a'
$commit = git -C $Fonte rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $commit -ne $commitEsperado) {
    throw "A fonte deve estar no commit $commitEsperado."
}
$alteracoes = git -C $Fonte status --porcelain
if ($LASTEXITCODE -ne 0 -or $alteracoes) {
    throw 'A validação requer uma cópia de trabalho limpa.'
}

$compilador = Join-Path $Jdk 'bin/javac.exe'
if (-not (Test-Path -LiteralPath $compilador -PathType Leaf)) {
    throw "Compilador não encontrado em $compilador."
}
if (Test-Path -LiteralPath $Saida) {
    throw 'Informe uma pasta de saída nova para preservar a execução anterior.'
}
$diretorio = (New-Item -ItemType Directory -Path $Saida).FullName
$jdkResolvido = (Resolve-Path -LiteralPath $Jdk).Path
$javaHomeAnterior = $env:JAVA_HOME
$mavenArgsAnterior = $env:MAVEN_ARGS
$mvn = (Get-Command $Maven -CommandType Application | Select-Object -First 1).Source
$cache = if ($CacheMaven) { (Resolve-Path -LiteralPath $CacheMaven).Path } else { Join-Path $diretorio 'cache-maven' }
$propriedades = '"-Dstyle.color=never" "-Dmaven.repo.local={0}"' -f $cache
if ($Fuso) {
    $propriedades += ' "-Duser.timezone={0}"' -f $Fuso
}

Push-Location -LiteralPath $Fonte
try {
    $env:JAVA_HOME = $jdkResolvido
    $env:MAVEN_ARGS = ''
    $versaoMaven = & $mvn '-version'
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao consultar a versão do Maven.' }
    $versaoJavac = & $compilador '-version'
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao consultar a versão do compilador.' }
    $fusoWindows = (Get-TimeZone).Id
    @("Commit: $commit", "Início UTC: $([DateTimeOffset]::UtcNow.ToString('o'))", "Fuso do Windows: $fusoWindows", "Fuso solicitado ao Maven: $Fuso", $versaoJavac) + $versaoMaven |
        Set-Content -LiteralPath (Join-Path $diretorio 'ambiente.txt') -Encoding UTF8

    $execucoes = if ($SomenteDiagnostico) {
        @{ Nome = 'duration-format'; Metas = @('test'); Teste = 'DurationFormatUtilsTest#testFourYears' }
    } else {
        @{ Nome = 'suite'; Metas = @('clean', 'test'); Teste = '' }
        @{ Nome = 'string-utils'; Metas = @('test'); Teste = 'StringUtilsTest#testReverse_String' }
        @{ Nome = 'array-utils'; Metas = @('test'); Teste = 'ArrayUtilsTest#testIsEmptyObject' }
    }
    $resultados = foreach ($execucao in $execucoes) {
        $log = Join-Path $diretorio "$($execucao.Nome).log"
        # O mvn.cmd encaminha MAVEN_ARGS com as aspas para o Maven.
        $env:MAVEN_ARGS = $propriedades
        if ($execucao.Teste) {
            $env:MAVEN_ARGS += ' "-Dtest={0}"' -f $execucao.Teste
        }
        $tempo = [Diagnostics.Stopwatch]::StartNew()
        & $mvn '-B' '-ntp' '-l' $log @($execucao.Metas) | Out-Host
        $codigo = $LASTEXITCODE
        $tempo.Stop()
        Write-Host "$($execucao.Nome) concluída com código $codigo."
        [pscustomobject]@{
            execucao = $execucao.Nome
            metas = $execucao.Metas
            teste = $execucao.Teste
            codigoSaida = $codigo
            segundos = [Math]::Round($tempo.Elapsed.TotalSeconds, 3)
            log = [IO.Path]::GetFileName($log)
        }
    }
    ConvertTo-Json -InputObject @($resultados) -Depth 4 |
        Set-Content -LiteralPath (Join-Path $diretorio 'execucoes.json') -Encoding UTF8
    if ($resultados | Where-Object codigoSaida -NE 0) { exit 1 }
} finally {
    $env:JAVA_HOME = $javaHomeAnterior
    $env:MAVEN_ARGS = $mavenArgsAnterior
    Pop-Location
}
