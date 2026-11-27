#Requires -Version 7.3
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Fonte,
    [Parameter(Mandatory)][string]$ClasspathJUnit,
    [Parameter(Mandatory)][string]$Saida,
    [ValidateSet(49, 50)][int[]]$Posicao = @(50, 49)
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$PSNativeCommandArgumentPassing = 'Standard'
$imagem = 'test-prioritization/commons-lang:kan13'
$dados = docker image inspect $imagem
if ($LASTEXITCODE) { throw 'A imagem KAN-13 precisa estar disponível localmente.' }
$inspecao = ($dados -join "`n" | ConvertFrom-Json)[0]
if ($inspecao.Os -ne 'linux' -or $inspecao.Architecture -ne 'amd64' -or
    $inspecao.Config.Labels.'org.opencontainers.image.base.name' -notmatch '@sha256:[0-9a-f]{64}$') {
    throw 'A imagem deve ser Linux/amd64 e registrar o digest da base.'
}

$shas = @{
    49 = 'cc5ecf5db64abf0d2a2f59be16f9dc49a520dca9'
    50 = 'f24c027ff83b90beab2ec28696721200abb4f9e9'
}
$raiz = (New-Item -ItemType Directory -Path $Saida).FullName
$classes = (New-Item -ItemType Directory -Path (Join-Path $raiz 'classes')).FullName
javac -cp $ClasspathJUnit -d $classes (Join-Path $PSScriptRoot 'RastroJUnit.java')
if ($LASTEXITCODE) { throw 'Falha ao compilar o coletor.' }
Copy-Item (Join-Path $PSScriptRoot 'META-INF') $classes -Recurse

$falhas = @()
foreach ($pos in $Posicao) {
    $sha = $shas[$pos]
    $tentativa = (New-Item -ItemType Directory -Path (Join-Path $raiz $sha)).FullName
    $evidencia = (New-Item -ItemType Directory -Path (Join-Path $tentativa 'evidencia')).FullName
    $fonteTar = Join-Path $tentativa 'fonte.tar'
    git -C $Fonte archive --format=tar "--output=$fonteTar" $sha
    if ($LASTEXITCODE) { throw "Falha no git archive para $sha." }
    $inicio = [DateTimeOffset]::UtcNow
    docker run --rm --platform linux/amd64 `
        --mount "type=bind,source=$fonteTar,target=/fonte.tar,readonly" `
        --mount "type=bind,source=$classes,target=/coletor,readonly" `
        --mount "type=bind,source=$evidencia,target=/evidencia" `
        --mount "type=bind,source=$PSScriptRoot,target=/roteiros,readonly" `
        $inspecao.Id sh /roteiros/piloto-surefire.sh *> (Join-Path $tentativa 'maven.log')
    $codigo = $LASTEXITCODE
    @{
        sha = $sha
        position = $pos
        image = $inspecao.Id
        start = $inicio.ToString('o')
        finish = [DateTimeOffset]::UtcNow.ToString('o')
        exit_code = $codigo
    } | ConvertTo-Json | Set-Content (Join-Path $tentativa 'tentativa.json')
    Write-Output "$sha exit=$codigo"
    if ($codigo) { $falhas += $sha }
}
if ($falhas) { throw "Tentativas com erro: $($falhas -join ', ')" }
