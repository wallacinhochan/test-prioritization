#Requires -Version 7.5
param([Parameter(Mandatory)][string]$Fonte, [Parameter(Mandatory)][ValidateRange(1,100)][int]$Posicao)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$Fonte = (Resolve-Path -LiteralPath $Fonte).Path.Replace('\','/')
$revisao = Import-Csv -LiteralPath (Join-Path $PSScriptRoot '../KAN-10/commits.csv') | Where-Object position -eq "$Posicao"
$sha = $revisao.commit_sha
if ($sha -cnotmatch '^[0-9a-f]{40}$') { throw "SHA inválido para a posição $Posicao." }
$pasta = Join-Path $PSScriptRoot "local/entradas/$sha"
if (Test-Path -LiteralPath (Join-Path $pasta 'compilacao-ok')) { throw "Descoberta já concluída em $pasta." }
$null = New-Item -ItemType Directory -Path $pasta -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot '../KAN-16/DescobertaT0.java') -Destination $pasta
$script = (Get-Content -LiteralPath (Join-Path $PSScriptRoot '../MUTACAO/t1/descobrir.sh') -Raw).Replace([string][char]13, '')
[IO.File]::WriteAllText((Join-Path $pasta 'descobrir.sh'), $script)
$tar = Join-Path $pasta 'fonte.tar'
git -c "safe.directory=$Fonte" -C $Fonte archive --format=tar "--output=$tar" $sha
$imagem = 'sha256:6e15bf7fd834e6998883afacb56e4b6de6b180fff899bf3fb0474840f5ac93d6'
docker run --rm --pull never --platform linux/amd64 --workdir /trabalho `
    --mount "type=bind,source=$pasta,target=/entrada" --entrypoint /bin/sh $imagem /entrada/descobrir.sh *> (Join-Path $pasta 'descoberta.log')
$sha | Set-Content -LiteralPath (Join-Path $pasta 'compilacao-ok') -Encoding utf8NoBOM
