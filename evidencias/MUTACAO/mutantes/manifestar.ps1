#Requires -Version 7.5
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet(15, 26, 42, 50, 96)]
    [int]$Posicao
)

$ErrorActionPreference = 'Stop'
$local = Join-Path $PSScriptRoot "local/$Posicao"
$destino = Join-Path $PSScriptRoot "pos-$Posicao"
$fonte = Get-Content -LiteralPath (Join-Path $local 'entrada/fonte.json') -Raw | ConvertFrom-Json
$controle = Get-Content -LiteralPath (Join-Path $local 'controle/execucao.json') -Raw | ConvertFrom-Json
$pit = Get-Content -LiteralPath (Join-Path $local 'pit/execucao.json') -Raw | ConvertFrom-Json
if ($controle.codigo -or $pit.codigo) { throw 'Controle ou exportação PIT sem sucesso.' }

function Get-HashTexto([string]$Texto) {
    [Convert]::ToHexStringLower([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($Texto)))
}

function Get-HashArquivo([string]$Arquivo) {
    (Get-FileHash -LiteralPath $Arquivo -Algorithm SHA256).Hash.ToLowerInvariant()
}

$semente = 'tp-mutation-v1'
$exportacao = Join-Path $local 'pit/exportacao'
$arquivos = @(Get-ChildItem -LiteralPath $exportacao -Filter details.txt -File -Recurse)
if (!$arquivos.Count) { throw 'A exportação PIT não contém details.txt.' }
$candidatos = foreach ($arquivo in $arquivos) {
    $classes = @(Get-ChildItem -LiteralPath $arquivo.DirectoryName -Filter '*.class' -File)
    if ($classes.Count -ne 1) { throw "Exportação ambígua em $($arquivo.DirectoryName)." }
    $classe = $classes[0].BaseName
    if ($classe -cnotin $fonte.classes) { throw "Classe fora do escopo de produção: $classe." }
    $original = Join-Path $local "pit/originais/$($classe.Replace('.','/')).class"
    $detalhes = (Get-Content -LiteralPath $arquivo.FullName -Raw).Trim()
    # A estrutura da identidade vem do MutationIdentifier registrado pelo exportador.
    $id = [regex]::Match($detalhes,
        'MutationIdentifier \[location=Location \[clazz=(?<classe>[^,]+), method=(?<metodo>[^,]+), methodDesc=(?<desc>[^\]]+)\], indexes=\[(?<indices>\d+(?:, \d+)*)\], mutator=(?<operador>[^\]]+)\]')
    if (!$id.Success -or $id.Groups['classe'].Value.Replace('/','.') -cne $classe) {
        throw "Identidade PIT sem interpretação inequívoca em $($arquivo.FullName)."
    }
    $indices = @($id.Groups['indices'].Value -split ', ' | ForEach-Object { [int]$_ })
    $canonico = @($classe, $id.Groups['metodo'].Value, $id.Groups['desc'].Value,
        $id.Groups['operador'].Value, ($indices -join ',')) -join '|'
    [pscustomobject][ordered]@{
        mutation_id = $canonico
        classe = $classe
        metodo = $id.Groups['metodo'].Value
        descritor_jvm = $id.Groups['desc'].Value
        operador = $id.Groups['operador'].Value
        indices = $indices
        selecao_sha256 = Get-HashTexto ($semente + $canonico)
        bytecode_sha256 = Get-HashArquivo $classes[0].FullName
        original_sha256 = Get-HashArquivo $original
        detalhes_sha256 = Get-HashArquivo $arquivo.FullName
        bytecode = [IO.Path]::GetRelativePath($exportacao, $classes[0].FullName).Replace('\','/')
        detalhes = [IO.Path]::GetRelativePath($exportacao, $arquivo.FullName).Replace('\','/')
        elegivel = $indices.Count -eq 1
    }
}

# Este fluxo lê somente o bytecode e a identidade da exportação. O XML de resultados não é aberto.
$ordenados = @($candidatos | Sort-Object -Property selecao_sha256,mutation_id,bytecode -CaseSensitive)
$ids = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
$bytecodes = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
foreach ($candidato in $ordenados) {
    if (!$ids.Add($candidato.mutation_id)) { throw "Identidade PIT duplicada: $($candidato.mutation_id)." }
    $situacao = if (!$candidato.elegivel) { 'multiplos_indices' }
        elseif ($candidato.original_sha256 -ceq $candidato.bytecode_sha256) { 'identico_ao_original' }
        elseif (!$bytecodes.Add("$($candidato.classe)|$($candidato.bytecode_sha256)")) { 'bytecode_duplicado' }
        else { 'elegivel' }
    $candidato | Add-Member -NotePropertyName situacao -NotePropertyValue $situacao
}
$selecionados = @($ordenados | Where-Object situacao -ceq elegivel | Select-Object -First 4)
if (!$selecionados.Count) { throw 'Exportação sem candidato de efeito único.' }
if (Test-Path -LiteralPath (Join-Path $destino 'manifesto.json')) { throw 'O manifesto já está congelado.' }
$null = New-Item -ItemType Directory -Path $destino -Force
$tabela = Join-Path $destino 'candidatos.csv'
$linhas = $ordenados | Select-Object * -ExcludeProperty indices,elegivel | ConvertTo-Csv -NoTypeInformation
[IO.File]::WriteAllText($tabela, ($linhas -join "`n") + "`n")
$manifesto = [ordered]@{
    protocolo = 'tp-mutation-v1'
    posicao = $Posicao
    sha = $fonte.sha
    pai = $fonte.pai
    imagem = $fonte.imagem
    fonte_tar_sha256 = $fonte.fonte_tar_sha256
    classes = @($fonte.classes)
    pit = '1.19.4'
    pit_junit5 = '1.2.3'
    semente = $semente
    congelado_utc = [DateTimeOffset]::UtcNow.ToString('o')
    candidatos_csv_sha256 = Get-HashArquivo $tabela
    exportados = $ordenados.Count
    elegiveis = @($ordenados | Where-Object situacao -ceq elegivel).Count
    selecionados = $selecionados
} | ConvertTo-Json -Depth 6
[IO.File]::WriteAllText((Join-Path $destino 'manifesto.json'), $manifesto.Replace("`r`n", "`n") + "`n")
