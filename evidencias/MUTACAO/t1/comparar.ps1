#Requires -Version 7.5
param(
    [string]$Congelamento = '0d3cd01e68bf223eca124332f74d4486ae6bd6f7',
    [ValidateSet(15,26,42,50,96)][int[]]$Posicoes = @(15,26,42,50,96)
)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$avaliador = Join-Path $PSScriptRoot avaliar.mjs
node $avaliador $Congelamento --verificar
$mutantes = Join-Path $PSScriptRoot ../mutantes
$revisoes = Get-Content -LiteralPath (Join-Path $PSScriptRoot revisoes.json) -Raw | ConvertFrom-Json -AsHashtable

function Get-Digest([string]$Arquivo) {
    (Get-FileHash -LiteralPath $Arquivo -Algorithm SHA256).Hash.ToLowerInvariant()
}

$variantes = [Collections.Generic.List[object]]::new()
$observacoes = [Collections.Generic.List[object]]::new()
$publicacoes = [ordered]@{}
foreach ($posicao in ($Posicoes | Sort-Object -Unique)) {
    $sha = $revisoes["$posicao"].sha
    $publico = Join-Path $mutantes "pos-$posicao"
    $arquivoResumo = Join-Path $publico resumo.json
    if (!(Test-Path -LiteralPath $arquivoResumo -PathType Leaf)) {
        $publicacoes["$posicao"] = [ordered]@{ estado = 'resumo_indisponivel' }
        continue
    }

    $resumo = Get-Content -LiteralPath $arquivoResumo -Raw | ConvertFrom-Json
    if ($resumo.sha -cne $sha -or $resumo.posicao -ne $posicao) {
        throw "Resumo com revisão divergente na posição $posicao."
    }
    if (!$resumo.equivalencia_controle -or !$resumo.repeticao_coincidente -or !$resumo.restauracao) {
        $publicacoes["$posicao"] = [ordered]@{ estado = 'validacao_insuficiente' }
        continue
    }
    $ref = "evidencias/MUTACAO/mutantes/pos-$posicao"
    $caminhoManifesto = Join-Path $publico manifesto.json
    $caminhoRotulos = Join-Path $mutantes "local/$posicao/rotulos.csv"
    if (!(Test-Path -LiteralPath $caminhoManifesto -PathType Leaf) -or
        !(Test-Path -LiteralPath $caminhoRotulos -PathType Leaf)) {
        $publicacoes["$posicao"] = [ordered]@{ estado = 'dados_locais_indisponiveis' }
        continue
    }
    if ($resumo.rotulos -cne "local/$posicao/rotulos.csv" -or
        (Get-Digest $caminhoManifesto) -cne $resumo.manifesto_sha256 -or
        (Get-Digest $caminhoRotulos) -cne $resumo.rotulos_sha256) {
        throw "Proveniência divergente na posição $posicao."
    }
    $manifesto = Get-Content -LiteralPath $caminhoManifesto -Raw | ConvertFrom-Json
    if ($manifesto.sha -cne $sha -or $manifesto.pai -cne $revisoes["$posicao"].pai -or
        $manifesto.protocolo -cne 'tp-mutation-v1' -or !$manifesto.selecionados.Count) {
        throw "Manifesto incompatível na posição $posicao."
    }
    foreach ($mutante in $manifesto.selecionados) {
        $variantes.Add([ordered]@{ commit_sha = $sha; mutation_id = $mutante.mutation_id; source_ref = "$ref/manifesto.json" })
    }
    $contagens = @{ induced_failure = 0; pass = 0; unknown = 0 }
    $linha = 1
    Import-Csv -LiteralPath $caminhoRotulos | ForEach-Object {
        $linha++
        if ($_.sha -cne $sha -or $_.label -cnotin 'pass','induced_failure','unknown') {
            throw "Rótulo incompatível na posição $posicao, linha $linha."
        }
        $contagens[$_.label]++
        $label = if ($_.label -ceq 'pass') { 'no_induced_failure' } else { $_.label }
        $observacoes.Add([ordered]@{
            commit_sha = $sha; mutation_id = $_.mutation_id; test_id = $_.test_id; label = $label
            source_ref = "evidencias/MUTACAO/mutantes/$($resumo.rotulos)#linha=$linha"
        })
    }
    foreach ($label in $contagens.Keys) {
        if ($contagens[$label] -ne $resumo.contagens.$label) {
            throw "Contagem divergente na posição $posicao para $label."
        }
    }
    $publicacoes["$posicao"] = [ordered]@{
        estado = 'disponivel'
        resumo_ref = "$ref/resumo.json"
        resumo_sha256 = Get-Digest $arquivoResumo
        rotulos_sha256 = $resumo.rotulos_sha256
    }
}

$matriz = [ordered]@{
    schema_version = '1.0.0'; mutants = $variantes.ToArray(); observations = $observacoes.ToArray()
    publicacoes = $publicacoes
}
$json = $matriz | ConvertTo-Json -Depth 6 -Compress
$json | node $avaliador $Congelamento -
