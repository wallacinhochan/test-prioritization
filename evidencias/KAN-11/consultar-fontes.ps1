# Execute na raiz do repositório com PowerShell 7.
param([System.Security.SecureString]$GitHubToken)

$ErrorActionPreference = 'Stop'
$rows = Import-Csv evidencias/KAN-10/commits.csv
$shas = @{}
foreach ($row in $rows) { $shas[$row.commit_sha] = $true }

$api = 'https://api.github.com/repos/apache/commons-lang'
$bench = 'https://raw.githubusercontent.com/rjust/defects4j/v3.0.1/framework/projects/Lang'
$rest = @{ TimeoutSec = 25 }
if ($GitHubToken) {
    $rest.Authentication = 'Bearer'
    $rest.Token = $GitHubToken
}

$consultas = foreach ($row in $rows) {
    $sha = $row.commit_sha
    $runs = Invoke-RestMethod -Uri "$api/actions/runs?head_sha=$sha&per_page=25" @rest
    $checks = Invoke-RestMethod -Uri "$api/commits/$sha/check-runs?per_page=25" @rest
    $statuses = Invoke-RestMethod -Uri "$api/commits/$sha/status?per_page=25" @rest
    [ordered]@{
        posicao = [int]$row.position
        head_sha = $sha
        total = $runs.total_count
        checks = @{ total = $checks.total_count; resultados = @($checks.check_runs) }
        statuses = @{ total = $statuses.total_count; resultados = @($statuses.statuses) }
        execucoes = @($runs.workflow_runs)
    }
}
$defects4j = foreach ($arquivo in @('active-bugs.csv','deprecated-bugs.csv')) {
    $url = "$bench/$arquivo"
    $linhas = (Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 25).Content | ConvertFrom-Csv
    $matches = @($linhas | Where-Object {
        $shas.ContainsKey($_.'revision.id.buggy') -or $shas.ContainsKey($_.'revision.id.fixed')
    })
    [ordered]@{ arquivo = $arquivo; url = $url; total = $linhas.Count; correspondencias = $matches }
}
[ordered]@{
    consultado_utc = [DateTime]::UtcNow.ToString('o')
    repositorio = 'apache/commons-lang'
    endpoint_runs = "$api/actions/runs?head_sha={sha}&per_page=25"
    endpoint_checks = "$api/commits/{sha}/check-runs?per_page=25"
    endpoint_statuses = "$api/commits/{sha}/status?per_page=25"
    consultas = $consultas
    defects4j = $defects4j
} | ConvertTo-Json -Depth 12
