param(
    [Parameter(Mandatory)][string]$Fonte,
    [Parameter(Mandatory)][ValidateRange(1,100)][int]$Posicao,
    [string]$Imagem = 'test-prioritization/commons-lang:kan18-dirts'
)
$ErrorActionPreference = 'Stop'
$Fonte = (Resolve-Path -LiteralPath $Fonte).Path.Replace('\','/')
$revisao = Import-Csv -LiteralPath (Join-Path $PSScriptRoot '../KAN-10/commits.csv') | Where-Object position -eq "$Posicao"
$sha = $revisao.commit_sha
$pai = $revisao.first_parent_sha
if ($sha -cnotmatch '^[0-9a-f]{40}$' -or $pai -cnotmatch '^[0-9a-f]{40}$') { throw "SHA inválido para a posição $Posicao." }
function Invoke-Git {
    & git -c "safe.directory=$Fonte" -C $Fonte @args
    if ($LASTEXITCODE) { throw "Git encerrou com código $LASTEXITCODE." }
}
$real = Invoke-Git rev-parse "$sha^1"
if ($real -cne $pai) { throw 'Primeiro pai divergente do recorte.' }
$inspecao = docker image inspect $Imagem
if ($LASTEXITCODE) { throw 'Imagem DIRTS indisponível. Confira o bootstrap da KAN-18.' }
$detalhe = ($inspecao -join "`n" | ConvertFrom-Json)
$id = $detalhe.Id
if ($id -cnotmatch '^sha256:[0-9a-f]{64}$' -or $detalhe.Os -cne 'linux' -or $detalhe.Architecture -cne 'amd64' -or
    $detalhe.Config.Labels.'org.opencontainers.image.revision' -cne '62efcec2f909f93fffdd4ae1da24b0aee1071749') {
    throw 'Imagem DIRTS inválida. Confira o bootstrap da KAN-18.'
}
$entradas = Join-Path $PSScriptRoot 'local/dirts/entradas'
$destino = Join-Path $entradas $sha
if (Test-Path -LiteralPath $destino) { throw "Descoberta já publicada em $destino." }
$pasta = Join-Path $entradas "$sha-$([guid]::NewGuid())"
$null = New-Item -ItemType Directory -Path $pasta -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot '../KAN-16/DescobertaT0.java') -Destination $pasta
foreach ($item in @(@('../MUTACAO/t1/descobrir.sh','descobrir.sh'), @('dirts.sh','dirts.sh'))) {
    $script = [IO.File]::ReadAllText((Join-Path $PSScriptRoot $item[0])).Replace("`r`n", "`n")
    [IO.File]::WriteAllText((Join-Path $pasta $item[1]), $script)
}
$alteracoes = @(Invoke-Git diff --no-renames --name-status $pai $sha | Where-Object { $_ -cne "M`tsrc/changes/changes.xml" })
Invoke-Git archive --format=tar "--output=$pasta/fonte.tar" $sha
if ($alteracoes.Count -and @($alteracoes | Where-Object { $_ -cnotmatch '^[AM]\tsrc/(main|test)/java/[A-Za-z0-9_$/]+\.java$' }).Count -eq 0) {
    $caminhos = @($alteracoes | ForEach-Object { ($_ -split "`t", 2)[1] })
    Invoke-Git archive --format=tar "--output=$pasta/pai.tar" $pai
    Invoke-Git archive --format=tar "--output=$pasta/alteracoes.tar" $sha -- @caminhos
}
[IO.File]::WriteAllText((Join-Path $pasta 'imagem.txt'), $id)
docker run --rm --pull never --platform linux/amd64 --mount "type=bind,source=$pasta,target=/entrada" $id sh /entrada/dirts.sh
if ($LASTEXITCODE) { throw "Descoberta falhou. Verifique $pasta." }
[IO.File]::WriteAllText((Join-Path $pasta 'compilacao-ok'), $sha)
[IO.Directory]::Move($pasta, $destino)
