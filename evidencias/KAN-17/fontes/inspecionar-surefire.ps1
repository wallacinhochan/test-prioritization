param(
    [Parameter(Mandatory)]
    [string]$Relatorios
)

$ErrorActionPreference = 'Stop'
$files = @(Get-ChildItem -LiteralPath $Relatorios -File -Filter 'TEST-*.xml')
if ($files.Count -eq 0) {
    throw "Nenhum TEST-*.xml em $Relatorios"
}

$counts = [ordered]@{
    reports = $files.Count
    headerTests = 0
    cases = 0
    failures = 0
    errors = 0
    skipped = 0
    indexed = 0
    signatureIndexed = 0
    signatureUnindexed = 0
    displayClass = 0
    missingTime = 0
    suiteZeroWithCases = 0
    otherNames = 0
}
$timezones = @{}
$ordinal = [StringComparer]::Ordinal
$literalNames = [Collections.Generic.HashSet[string]]::new($ordinal)
$baseNames = [Collections.Generic.Dictionary[string, Collections.Generic.HashSet[string]]]::new($ordinal)
$pattern = '^(?<method>[^\[(]+)(?<signature>\(.*\))?(?<index>\[\d+\])?$'

foreach ($file in $files) {
    [xml]$doc = Get-Content -LiteralPath $file.FullName -Raw
    $suite = $doc.testsuite
    $cases = $suite.SelectNodes('testcase')
    $counts.headerTests += [int]$suite.GetAttribute('tests')
    $counts.suiteZeroWithCases += [int]($suite.GetAttribute('tests') -eq '0' -and $cases.Count -gt 0)
    $zone = $suite.SelectSingleNode("properties/property[@name='user.timezone']")
    $zoneLabel = if ($null -eq $zone) { '(ausente)' } else { $zone.GetAttribute('value') }
    $timezones[$zoneLabel]++

    foreach ($case in $cases) {
        $counts.cases++
        $counts.failures += [int]($null -ne $case.SelectSingleNode('failure'))
        $counts.errors += [int]($null -ne $case.SelectSingleNode('error'))
        $counts.skipped += [int]($null -ne $case.SelectSingleNode('skipped'))
        $counts.missingTime += [int](-not $case.HasAttribute('time'))
        $class = $case.GetAttribute('classname')
        $name = $case.GetAttribute('name')
        $counts.displayClass += [int]($class -notmatch '^org\.apache\.commons\.lang3\.')
        [void]$literalNames.Add("$class#$name")

        $match = [regex]::Match($name, $pattern)
        if (-not $match.Success) {
            $counts.otherNames++
            continue
        }
        $hasIndex = $match.Groups['index'].Success
        $hasSignature = $match.Groups['signature'].Success
        $counts.indexed += [int]$hasIndex
        $counts.signatureIndexed += [int]($hasIndex -and $hasSignature)
        $counts.signatureUnindexed += [int](-not $hasIndex -and $hasSignature)
        $key = "$class#$($match.Groups['method'].Value)"
        if (-not $baseNames.ContainsKey($key)) {
            $baseNames[$key] = [Collections.Generic.HashSet[string]]::new($ordinal)
        }
        [void]$baseNames[$key].Add($match.Groups['signature'].Value)
    }
}

$counts['timezones'] = $timezones
$counts['literalKeys'] = $literalNames.Count
$counts['keysWithoutSignature'] = $baseNames.Count
$counts['groupsWithDifferentSignatures'] = @($baseNames.Values | Where-Object Count -gt 1).Count
[PSCustomObject]$counts | ConvertTo-Json
