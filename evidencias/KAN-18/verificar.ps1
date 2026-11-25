param(
    [Parameter(Mandatory)][int[]]$Posicoes,
    [string]$Oraculo = (Join-Path $PSScriptRoot '../KAN-16/local/lote'),
    [switch]$SemT0
)
$ErrorActionPreference = 'Stop'
$recorte = Import-Csv -LiteralPath (Join-Path $PSScriptRoot '../KAN-10/commits.csv')
$runs = @{}
$resultados = @{}
if (!$SemT0) {
    $runs = Import-Csv -LiteralPath (Join-Path $Oraculo 't0_runs.csv') | Group-Object commit_sha -AsHashTable -AsString
    $resultados = Import-Csv -LiteralPath (Join-Path $Oraculo 't0_results.csv') | Group-Object commit_sha -AsHashTable -AsString
}
$relatorio = foreach ($posicao in $Posicoes) {
    $revisao = $recorte | Where-Object position -eq "$posicao"
    if (!$revisao) { throw "Posição ausente da KAN-10: $posicao" }
    $sha = $revisao.commit_sha
    $pasta = Join-Path $PSScriptRoot "local/dirts/selecao/$sha"
    $manifesto = Get-Content -LiteralPath (Join-Path $pasta 'manifesto.json') -Raw | ConvertFrom-Json
    if ($manifesto.sha -cne $sha -or $manifesto.pai -cne $revisao.first_parent_sha -or $manifesto.posicao -ne $posicao) {
        throw "Proveniência divergente: $sha"
    }
    if ($manifesto.seletor -cne '2.0.0' -or $manifesto.ferramenta.nome -cne 'DIRTS') {
        throw "Seletor inesperado: $sha"
    }
    $entradas = Join-Path $PSScriptRoot "local/dirts/entradas/$sha"
    foreach ($prop in $manifesto.entradas_sha256.PSObject.Properties) {
        $hash = (Get-FileHash -LiteralPath (Join-Path $entradas $prop.Name)).Hash.ToLowerInvariant()
        if ($hash -cne $prop.Value) { throw "Entrada divergente: $sha $($prop.Name)" }
    }
    foreach ($nome in 'diff.patch','selection.csv','rankings.csv','overhead.csv','decisoes.json') {
        $hash = (Get-FileHash -LiteralPath (Join-Path $pasta $nome)).Hash.ToLowerInvariant()
        if ($hash -cne $manifesto.saidas_sha256.$nome) { throw "Hash divergente: $sha $nome" }
    }

    $candidatos = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $selecionados = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($linha in (Import-Csv -LiteralPath (Join-Path $pasta 'selection.csv'))) {
        if ($linha.commit_sha -cne $sha -or $linha.scenario -cne 'T1' -or !$linha.test_id -or !$candidatos.Add($linha.test_id)) {
            throw "Chave de seleção inválida: $sha $($linha.test_id)"
        }
        switch -CaseSensitive ($linha.selected) {
            'true' {
                $motivo = if ($manifesto.fallback.Count) { 'fallback' } else { 'dependency' }
                if ($linha.selection_reason -cne $motivo) { throw "Motivo inválido: $sha $($linha.test_id)" }
                $null = $selecionados.Add($linha.test_id)
            }
            'false' {
                if ($manifesto.fallback.Count -or $linha.selection_reason -cne 'no_dependency') {
                    throw "Exclusão inválida: $sha $($linha.test_id)"
                }
            }
            default { throw "Decisão inválida: $sha $($linha.test_id)" }
        }
    }
    $ordem = [string[]]@($selecionados)
    [Array]::Sort($ordem, [StringComparer]::Ordinal)
    $i = 0
    foreach ($linha in (Import-Csv -LiteralPath (Join-Path $pasta 'rankings.csv'))) {
        if ($linha.commit_sha -cne $sha -or $linha.scenario -cne 'T1' -or $linha.score -or
            $linha.rank -cne [string]($i + 1) -or $linha.test_id -cne $ordem[$i]) {
            throw "Ranking divergente: $sha posto $($i + 1)"
        }
        $i++
    }
    if ($i -ne $selecionados.Count -or $i -ne $manifesto.selecionados -or $candidatos.Count -ne $manifesto.candidatos) {
        throw "Contagens divergentes: $sha"
    }
    $overhead = @(Import-Csv -LiteralPath (Join-Path $pasta 'overhead.csv'))
    if ($overhead.Count -ne 1 -or $overhead[0].commit_sha -cne $sha -or $overhead[0].scenario -cne 'T1' -or
        $overhead[0].phase -cne 'selection' -or $overhead[0].measurement_status -cne 'measured' -or
        $overhead[0].duration_ms -cne [string]$manifesto.custo.ms) { throw "Overhead divergente: $sha" }

    $par = @{
        estado = 'sem_t0_completo'; metodos_t0 = $null; so_t0 = $null; so_inventario = $null
        falhas_t0 = $null; falhas_retidas_t1 = $null; duracoes_ausentes_t1_executados = $null
    }
    if ($runs.ContainsKey($sha) -and $runs[$sha].Count -ne 1) { throw "T0 duplicado: $sha" }
    if ($runs.ContainsKey($sha) -and $runs[$sha][0].run_status -ceq 'complete') {
        $observados = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        $falhas = $retidas = $semTempo = 0
        foreach ($linha in $resultados[$sha]) {
            if ($linha.scenario -cne 'T0' -or !$linha.test_id -or !$observados.Add($linha.test_id) -or
                $linha.outcome -cnotin 'pass','skip','fail') { throw "Resultado T0 inválido: $sha $($linha.test_id)" }
            if ($linha.outcome -ceq 'fail') {
                $falhas++
                if ($selecionados.Contains($linha.test_id)) { $retidas++ }
            }
            if ($linha.outcome -cne 'skip' -and !$linha.duration_ms -and $selecionados.Contains($linha.test_id)) { $semTempo++ }
        }
        $soT0 = @($observados.Where({ !$candidatos.Contains($_) }))
        $soInventario = @($candidatos.Where({ !$observados.Contains($_) }))
        $par = @{
            estado = if ($observados.Count -and !$soT0.Count -and !$soInventario.Count) { 'chaves_iguais' } else { 'chaves_divergentes' }
            metodos_t0 = $observados.Count; so_t0 = @($soT0 | Sort-Object -CaseSensitive); so_inventario = @($soInventario | Sort-Object -CaseSensitive)
            falhas_t0 = $falhas; falhas_retidas_t1 = $retidas; duracoes_ausentes_t1_executados = $semTempo
        }
    }
    [ordered]@{
        posicao = $posicao; sha = $sha; pai = $manifesto.pai
        candidatos = $candidatos.Count; selecionados = $selecionados.Count
        fallback = $manifesto.fallback; custo = $manifesto.custo
        saidas_sha256 = $manifesto.saidas_sha256; entradas_sha256 = $manifesto.entradas_sha256; codigo_sha256 = $manifesto.codigo_sha256
        t0 = [ordered]@{
            estado = $par.estado; metodos = $par.metodos_t0; so_t0 = $par.so_t0; so_inventario = $par.so_inventario
            falhas = $par.falhas_t0; retidas = $par.falhas_retidas_t1
            duracoes_ausentes_t1_executados = $par.duracoes_ausentes_t1_executados
        }
    }
}
ConvertTo-Json -InputObject @($relatorio) -Depth 8
