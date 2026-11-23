$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Get-Budgets([Nullable[long]] $ReferenceMs) {
    if ($null -eq $ReferenceMs -or $ReferenceMs -le 0) { return }
    foreach ($percent in 25, 50, 75) {
        [long][decimal]::Floor([decimal]$ReferenceMs * $percent / 100)
    }
}

# Exemplo serial. A ordem e o oráculo já estão congelados.
function Get-Prefix([long] $Budget, [object[]] $Phases, [object[]] $Methods) {
    [long]$elapsed = 0
    foreach ($phase in $Phases) {
        if ($null -eq $phase -or $phase -lt 0) { return 'indisponivel' }
        $elapsed += $phase
    }
    $completed = @()
    $failures = @()
    if ($elapsed -le $Budget) {
        foreach ($method in $Methods) {
            if ($method.Outcome -eq 'skip') { continue }
            if ($null -eq $method.Ms -or $method.Ms -lt 0) { return 'indisponivel' }
            $elapsed += $method.Ms
            if ($elapsed -gt $Budget) { break }
            $completed += $method.Name
            if ($method.Outcome -eq 'fail') { $failures += $method.Name }
        }
    }
    return "$($completed -join ',')|$($failures -join ',')"
}

function Assert-Equal($Expected, $Actual) {
    if ($Expected -cne $Actual) { throw "Esperado [$Expected], obtido [$Actual]" }
}

$a = @{ Name = 'A'; Ms = 20; Outcome = 'pass' }
$b = @{ Name = 'B'; Ms = 15; Outcome = 'fail' }
$c = @{ Name = 'C'; Ms = 10; Outcome = 'fail' }
$d = @{ Name = 'D'; Ms = 36; Outcome = 'pass' }
$skip = @{ Name = 'S'; Ms = $null; Outcome = 'skip' }
$zero = @{ Name = 'Z'; Ms = 0; Outcome = 'pass' }
$unknown = @{ Name = 'U'; Ms = $null; Outcome = 'fail' }
$budgets = @(Get-Budgets 103)
Assert-Equal '25,51,77' ($budgets -join ',')
Assert-Equal '0,0,0' ((Get-Budgets 1) -join ',')
Assert-Equal 0 @(Get-Budgets $null).Count
Assert-Equal 0 @(Get-Budgets 0).Count

# Primeira fase = preparação comum. As demais seguem seleção, features e inferência.
$cases = @(
    @{ Scenario = 'T0'; Phases = @(5); Methods = @($a, $b, $c, $d); Expected = @('A|', 'A,B,C|B,C', 'A,B,C|B,C') }
    @{ Scenario = 'T1'; Phases = @(5, 5); Methods = @($a, $b, $c); Expected = @('|', 'A,B|B', 'A,B,C|B,C') }
    @{ Scenario = 'T2'; Phases = @(5, 5, 4, 1); Methods = @($c, $b, $a); Expected = @('C|C', 'C,B|C,B', 'C,B,A|C,B') }
    @{ Scenario = 'T3'; Phases = @(5, 5, 4, 12); Methods = @($b, $c, $a); Expected = @('|', 'B,C|B,C', 'B,C,A|B,C') }
)
foreach ($case in $cases) {
    for ($i = 0; $i -lt $budgets.Count; $i++) {
        $result = Get-Prefix $budgets[$i] $case.Phases $case.Methods
        Assert-Equal $case.Expected[$i] $result
        Write-Output "$($case.Scenario) $($budgets[$i]) ms $result"
    }
    Assert-Equal 'indisponivel' (Get-Prefix 77 ($case.Phases + @($null)) $case.Methods)
    Assert-Equal 'indisponivel' (Get-Prefix 77 $case.Phases @($unknown))
}
Assert-Equal 'Z|' (Get-Prefix 5 @(5) @($skip, $zero))
Assert-Equal '|' (Get-Prefix 25 @(5) @($d, $b, $unknown))

$source = Join-Path $PSScriptRoot '../KAN-16/resumo-lote.json'
$runs = (Get-Content -LiteralPath $source -Raw -Encoding utf8 | ConvertFrom-Json).revisoes
$expected = @('72870,145741,218611', '70796,141592,212388', '73099,146199,219298', '72912,145824,218736', '76728,153456,230184')
Assert-Equal $expected.Count $runs.Count
for ($i = 0; $i -lt $runs.Count; $i++) {
    $run = $runs[$i]
    Assert-Equal 'complete' $run.run_status
    $limits = (Get-Budgets $run.suite_duration_ms) -join ','
    Assert-Equal $expected[$i] $limits
    Write-Output "Calibracao T0 $($run.posicao) $($run.commit_sha) $limits ms"
}
