#Requires -Version 7.3
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Fonte,

    [Parameter(Mandatory)]
    [ValidatePattern('\A[0-9a-f]{40}\z')]
    [string]$Sha,

    [Parameter(Mandatory)]
    [string]$Saida,

    [ValidatePattern('\A[\w.$]+#[\w$]+\z')]
    [string]$Teste
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$PSNativeCommandArgumentPassing = 'Standard'

$inicio = [DateTimeOffset]::UtcNow
$shaNormalizado = $Sha.ToLowerInvariant()
$id = '{0:yyyyMMddTHHmmssfffZ}-{1}' -f $inicio, [guid]::NewGuid().ToString('N')
$execucao = Join-Path $Saida $shaNormalizado $id
$logs = Join-Path $execucao 'maven.log'
$json = Join-Path $execucao 'ambiente.json'
$arquivo = Join-Path $execucao 'fonte.tar'
$relatorios = Join-Path $execucao 'surefire'
$null = New-Item -ItemType Directory -Path $relatorios -Force
$arquivo = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($arquivo)
$relatorios = (Resolve-Path -LiteralPath $relatorios).Path
$imagem = 'test-prioritization/commons-lang:kan13'
$argumentosMaven = @(
    '--batch-mode', '--no-transfer-progress', '-Dstyle.color=never',
    '-Dmaven.repo.local=/maven-cache', '-Duser.timezone=UTC', 'clean', 'test'
)
if ($Teste) {
    $argumentosMaven += "-Dtest=$Teste"
}

$ambiente = [ordered]@{
    id_execucao = $id
    sha_solicitado = $shaNormalizado
    sha_verificado = $null
    fonte_tar_sha256 = $null
    imagem = $imagem
    imagem_id = $null
    base_imagem = $null
    plataforma = 'linux/amd64'
    java = $null
    maven = $null
    locale = $null
    sistema = $null
    fuso_configurado = 'UTC'
    cache_maven = [ordered]@{ caminho = '/maven-cache'; estado_inicial = $null }
    inicio_utc = $inicio.ToString('o')
    fim_utc = $null
    duracao_segundos = $null
    comando_maven = @('mvn') + $argumentosMaven
    codigo_maven = $null
    codigo_saida = 1
    xml_surefire = 0
    conteiner = $null
    conteiner_removido = $null
    erro = $null
}

$roteiro = @'
set -eu
mkdir -p /evidencia/surefire
tar -xf /fonte.tar
mkdir /maven-cache
printf '%s\n' 'KAN-13 cache Maven inicial: frio'
mvn --version
set +e
mvn "$@"
codigo=$?
printf 'KAN-13 código Maven: %s\n' "$codigo"
if [ -d target/surefire-reports ]; then
    cp -a target/surefire-reports/. /evidencia/surefire/ || exit 125
fi
exit "$codigo"
'@
$roteiro = $roteiro.Replace("`r`n", "`n")

"Comando: $($ambiente.comando_maven -join ' ')" | Set-Content -LiteralPath $logs
$ambiente | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $json
Write-Host "Saída da execução: $execucao"

try {
    $fonteLocal = (Resolve-Path -LiteralPath $Fonte).Path
    $revisao = git -C $fonteLocal rev-parse --verify "${shaNormalizado}^{commit}" 2>&1
    if ($LASTEXITCODE -ne 0 -or $revisao -cne $shaNormalizado) {
        throw "O Git não resolveu o SHA para um commit exato: $revisao"
    }
    $ambiente.sha_verificado = $revisao

    $detalhes = docker image inspect $imagem 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Não foi possível inspecionar a imagem local. Consulte o bootstrap. $detalhes"
    }
    $inspecao = ($detalhes -join "`n") | ConvertFrom-Json
    $base = $inspecao.Config.Labels.'org.opencontainers.image.base.name'
    if ($inspecao.Os -ne 'linux' -or $inspecao.Architecture -ne 'amd64' -or $base -notmatch '@sha256:[0-9a-f]{64}$') {
        throw 'A imagem local deve ser Linux/amd64 e registrar o digest da base.'
    }
    $ambiente.imagem_id = $inspecao.Id
    $ambiente.base_imagem = $base

    $exportacao = git -C $fonteLocal archive --format=tar "--output=$arquivo" $shaNormalizado 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao exportar o commit com git archive: $exportacao"
    }
    $ambiente.fonte_tar_sha256 = (Get-FileHash -LiteralPath $arquivo -Algorithm SHA256).Hash.ToLowerInvariant()

    $conteiner = docker create --platform linux/amd64 --workdir /trabalho --entrypoint /bin/sh $ambiente.imagem_id -c $roteiro kan13 @argumentosMaven 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao criar o contêiner: $conteiner"
    }
    $ambiente.conteiner = $conteiner
    $ambiente | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $json

    $envio = docker cp $arquivo "${conteiner}:/fonte.tar" 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao transferir a revisão ao contêiner: $envio"
    }

    docker start --attach $conteiner 2>&1 |
        ForEach-Object { "$_" } |
        Add-Content -LiteralPath $logs
    $codigoDocker = $LASTEXITCODE

    switch -Regex -File $logs {
        '^Apache Maven ' { $ambiente.maven = $_ }
        '^Java version: ' { $ambiente.java = $_ }
        '^Default locale: ' { $ambiente.locale = $_ }
        '^OS name: ' { $ambiente.sistema = $_ }
        '^KAN-13 cache Maven inicial: frio$' { $ambiente.cache_maven.estado_inicial = 'frio' }
        '^KAN-13 código Maven: ([0-9]+)$' { $ambiente.codigo_maven = [int]$Matches[1] }
    }

    $estado = docker inspect --format '{{.State.Status}}' $conteiner 2>&1
    if ($LASTEXITCODE -ne 0 -or $estado -ne 'exited') {
        throw "O contêiner não confirmou o término. Código Docker: $codigoDocker. Estado: $estado"
    }
    $copia = docker cp "${conteiner}:/evidencia/surefire/." $relatorios 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao copiar os relatórios do Surefire. Contêiner preservado: $conteiner. $copia"
    }
    $ambiente.xml_surefire = @(Get-ChildItem -LiteralPath $relatorios -Filter 'TEST-*.xml' -File).Count
    $remocao = docker rm $conteiner 2>&1
    $ambiente.conteiner_removido = $LASTEXITCODE -eq 0
    if (-not $ambiente.conteiner_removido) {
        Add-Content -LiteralPath $logs -Value "Falha ao remover o contêiner concluído: $remocao"
    }

    if ($null -eq $ambiente.codigo_maven -or $codigoDocker -ne $ambiente.codigo_maven) {
        throw "A execução terminou sem confirmar o código do Maven. Código Docker: $codigoDocker."
    }
    if ($ambiente.java -notmatch '^Java version: 21\.0\.11,' -or $ambiente.maven -notmatch '^Apache Maven 3\.9\.11\s') {
        throw 'O Maven registrou versões diferentes de JDK 21.0.11 ou Maven 3.9.11.'
    }
    if ($ambiente.codigo_maven -eq 0 -and $ambiente.xml_surefire -eq 0) {
        throw 'O Maven informou sucesso sem gerar XML do Surefire.'
    }
    $ambiente.codigo_saida = $ambiente.codigo_maven
}
catch {
    $ambiente.erro = $_.Exception.Message
    Add-Content -LiteralPath $logs -Value $ambiente.erro
    [Console]::Error.WriteLine($ambiente.erro)
}
finally {
    $fim = [DateTimeOffset]::UtcNow
    $ambiente.fim_utc = $fim.ToString('o')
    $ambiente.duracao_segundos = [math]::Round(($fim - $inicio).TotalSeconds, 3)
    $ambiente | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $json
    if (Test-Path -LiteralPath $arquivo) {
        Remove-Item -LiteralPath $arquivo -ErrorAction Continue
    }
}

exit $ambiente.codigo_saida
