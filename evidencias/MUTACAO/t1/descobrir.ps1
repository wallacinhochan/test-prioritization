#Requires -Version 7.5
param([Parameter(Mandatory)][string]$Fonte, [ValidateSet(15,26,42,50,96)][int]$Posicao = 26)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$Fonte = (Resolve-Path -LiteralPath $Fonte).Path.Replace('\','/')
$revisoes = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'revisoes.json') -Raw | ConvertFrom-Json -AsHashtable
$sha = $revisoes["$Posicao"].sha
$pasta = Join-Path $PSScriptRoot "local/$Posicao"
if (Test-Path -LiteralPath (Join-Path $pasta 'compilacao-ok')) { throw "Descoberta já concluída em $pasta." }
$null = New-Item -ItemType Directory -Path $pasta -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot '../../KAN-16/DescobertaT0.java') -Destination $pasta
$script = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'descobrir.sh') -Raw).Replace([string][char]13, '')
[IO.File]::WriteAllText((Join-Path $pasta 'descobrir.sh'), $script)
$tar = Join-Path $pasta 'fonte.tar'
git -c "safe.directory=$Fonte" -C $Fonte archive --format=tar "--output=$tar" $sha
$imagem = 'sha256:6e15bf7fd834e6998883afacb56e4b6de6b180fff899bf3fb0474840f5ac93d6'
docker run --rm --pull never --platform linux/amd64 --workdir /trabalho `
    --mount "type=bind,source=$pasta,target=/entrada" --entrypoint /bin/sh $imagem /entrada/descobrir.sh *> (Join-Path $pasta 'descoberta.log')
$sha | Set-Content -LiteralPath (Join-Path $pasta 'compilacao-ok') -Encoding utf8NoBOM
