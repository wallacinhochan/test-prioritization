#Requires -Version 7.5
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet(15, 26, 42, 50, 96)]
    [int]$Posicao,

    [switch]$Controles
)

$ErrorActionPreference = 'Stop'
$local = Join-Path $PSScriptRoot "local/$Posicao"
$publico = Join-Path $PSScriptRoot "pos-$Posicao"
$manifesto = Get-Content -LiteralPath (Join-Path $publico manifesto.json) -Raw | ConvertFrom-Json
if ($Posicao -eq 96 -and !(Test-Path -LiteralPath (Join-Path $local congelamento.json))) {
    throw 'Rótulos do holdout aguardam o registro de congelamento do modelo.'
}

function Get-HashArquivo([string]$Arquivo) {
    (Get-FileHash -LiteralPath $Arquivo -Algorithm SHA256).Hash.ToLowerInvariant()
}

$inventario = Join-Path $local 'inventario/metodos.tsv'
$cp = (Get-Content -LiteralPath (Join-Path $local 'entrada/classpath.txt') -Raw).Trim()
$mapa = [Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
$porRaiz = [Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
$ids = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
foreach ($linha in Import-Csv -LiteralPath $inventario -Delimiter ([char]9)) {
    $id = "$($linha.classe)#$($linha.metodo)($($linha.tipos))"
    $null = $ids.Add($id)
    $linha | Add-Member -NotePropertyName test_id -NotePropertyValue $id
    $chave = "$($linha.raiz)#$($linha.metodo)"
    if (!$mapa.ContainsKey($chave)) { $mapa[$chave] = [Collections.Generic.List[object]]::new() }
    $mapa[$chave].Add($linha)
    if (!$porRaiz.ContainsKey($linha.raiz)) { $porRaiz[$linha.raiz] = [Collections.Generic.List[object]]::new() }
    $porRaiz[$linha.raiz].Add($linha)
}

# Regra de associação em evidencias/KAN-16/exportar.ps1, derivada da KAN-17.
function Find-Metodo([string]$Raiz, [string]$Classe, [string]$Nome) {
    $nomeXml = [regex]::Match($Nome, '\A(?<metodo>[a-zA-Z_$][\w$]*)(?:\((?<tipos>[^()]*)\))?(?:\[(?<indice>[0-9]+)\])?\z')
    $candidatos = if ($nomeXml.Success) { $mapa["$Raiz#$($nomeXml.Groups['metodo'].Value)"] }
    $matches = @(foreach ($candidato in $candidatos) {
        if ($candidato.classe -cne $Classe -and $candidato.rotulo_classe -cne $Classe) { continue }
        if ($nomeXml.Groups['tipos'].Success) {
            $tipos = $nomeXml.Groups['tipos'].Value -creplace '\s+', ''
            if ($tipos -cne $candidato.tipos -and $tipos -cne $candidato.tipos_curtos) { continue }
        } elseif ($candidato.tipos -and $candidato.rotulo_metodo -cne $Nome) { continue }
        if ($nomeXml.Groups['indice'].Success -and $candidato.tipo_descritor -cnotin 'test-template','test-factory') { continue }
        $candidato.test_id
    })
    if ($matches.Count -eq 1) { return @{ id = $matches[0]; possiveis = $matches } }
    $possiveis = if ($matches.Count) { $matches }
        elseif ($candidatos) { $candidatos.test_id }
        elseif ($porRaiz.ContainsKey($Raiz)) { $porRaiz[$Raiz].test_id }
    @{ possiveis = @($possiveis) }
}

function Read-Rodada([string]$Nome) {
    $pasta = Join-Path $local $Nome
    $log = Join-Path $pasta maven.log
    $txt = Get-Content -LiteralPath $log -Raw
    $registro = Get-Content -LiteralPath (Join-Path $pasta execucao.json) -Raw | ConvertFrom-Json
    $ja = [regex]::Match($txt, '(?m)^\[INFO\] argLine set to (?<args>[^\r\n]+)').Groups['args'].Value
    $totais = [regex]::Matches($txt, '(?m)^\[(?:INFO|WARNING|ERROR)\] Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)[ \t\r]*$')
    $build = [regex]::Matches($txt, '(?m)^\[INFO\] BUILD (SUCCESS|FAILURE)[ \t\r]*$')
    $falha = $txt -cmatch '(?m)^\[ERROR\] Failed to execute goal .*maven-surefire-plugin:3\.5\.4:test \(default-test\).*There are test failures'
    $erroDeTeste = $totais.Count -eq 1 -and [int]$totais[0].Groups[2].Value -eq 0 -and
        [int]$totais[0].Groups[3].Value -gt 0 -and
        $txt -cmatch '(?m)^\[ERROR\] Failed to execute goal .*maven-surefire-plugin:3\.5\.4:test \(default-test\) on project commons-lang3:[ \t\r]*$' -and
        $txt -cmatch '(?m)^\[ERROR\] See /trabalho/target/surefire-reports for the individual test results\.'
    $sinaisDeInfra = $txt -cmatch '(?mi)^\[ERROR\].*(forked VM terminated|error occurred in starting fork|could not resolve dependencies|could not transfer artifact|no space left on device)'
    $contagem = [ordered]@{ total = 0; failure = 0; error = 0; skip = 0; pass = 0; sem_associacao = 0 }
    $metodos = [Collections.Generic.Dictionary[string,string]]::new([StringComparer]::Ordinal)
    $ambiguidade = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $invocacoes = [Collections.Generic.List[string]]::new()
    $evidencias = [Collections.Generic.List[string]]::new()
    $problemas = [Collections.Generic.List[string]]::new()
    $arquivos = @(Get-ChildItem -LiteralPath (Join-Path $pasta surefire) -Filter 'TEST-*.xml' -File -ErrorAction SilentlyContinue |
        Sort-Object Name -CaseSensitive)
    $dumps = @(Get-ChildItem -LiteralPath (Join-Path $pasta surefire) -File -ErrorAction SilentlyContinue |
        Where-Object Extension -cin '.dump','.dumpstream')
    $config = [Xml.XmlReaderSettings]::new()
    $config.DtdProcessing = [Xml.DtdProcessing]::Prohibit
    foreach ($arquivo in $arquivos) {
        $xml = [xml]::new()
        $leitor = [Xml.XmlReader]::Create($arquivo.FullName, $config)
        try { $xml.Load($leitor) } finally { $leitor.Dispose() }
        $suite = $xml.DocumentElement
        if ($suite.LocalName -cne 'testsuite' -or
            $suite.SelectSingleNode("properties/property[@name='user.timezone']/@value").Value -cne 'UTC' -or
            $suite.SelectSingleNode("properties/property[@name='surefire.test.class.path']/@value").Value -cne $cp -or
            $suite.SelectSingleNode("properties/property[@name='java.version']/@value").Value -cne '21.0.11') {
            $problemas.Add("Configuração inesperada em $($arquivo.Name).")
        }
        $evidencias.Add("$(Get-HashArquivo $arquivo.FullName)  $($arquivo.Name)")
        $raiz = $arquivo.Name -creplace '^TEST-|\.xml$', ''
        $i = 0
        foreach ($item in $suite.SelectNodes('testcase')) {
            $i++
            $contagem.total++
            $estados = $item.SelectNodes('failure | error | skipped')
            if ($estados.Count -gt 1) { $problemas.Add("Estados conflitantes em $($arquivo.Name)[$i].") }
            $estado = if (!$estados.Count) { 'pass' }
                elseif ($estados[0].LocalName -ceq 'skipped') { 'skip' } else { $estados[0].LocalName }
            $contagem[$estado]++
            $classe = $item.GetAttribute('classname')
            $nomeXml = $item.GetAttribute('name')
            $associacao = Find-Metodo $raiz $classe $nomeXml
            $id = $associacao.id
            if ($item.SelectSingleNode('flakyFailure | flakyError | rerunFailure | rerunError')) { $id = $null }
            $invocacoes.Add("$raiz`t$classe`t$nomeXml`t$estado`t$id")
            if (!$id) {
                $contagem.sem_associacao++
                foreach ($possivel in $associacao.possiveis) { if ($possivel) { $null = $ambiguidade.Add($possivel) } }
                continue
            }
            $resultado = if ($estado -cin 'failure','error') { 'fail' } else { $estado }
            $anterior = $metodos[$id]
            if ($resultado -ceq 'fail' -or !$anterior -or ($resultado -ceq 'pass' -and $anterior -ceq 'skip')) {
                $metodos[$id] = $resultado
            }
        }
    }
    $xmlHashes = Join-Path $pasta xml.sha256
    [IO.File]::WriteAllLines($xmlHashes, $evidencias)
    $invocacoes.Sort([StringComparer]::Ordinal)
    $fingerprint = [Convert]::ToHexStringLower([Security.Cryptography.SHA256]::HashData(
        [Text.Encoding]::UTF8.GetBytes(($invocacoes -join "`n"))))
    $completa = !$sinaisDeInfra -and !$dumps.Count -and $arquivos.Count -gt 0 -and
        $totais.Count -eq 1 -and $build.Count -eq 1 -and $ja -and
        $txt -cmatch '(?m)^\[INFO\] Using auto detected provider org\.apache\.maven\.surefire\.junitplatform\.JUnitPlatformProvider' -and
        (($registro.codigo -eq 0 -and $build[0].Groups[1].Value -ceq 'SUCCESS') -or
            ($registro.codigo -eq 1 -and $build[0].Groups[1].Value -ceq 'FAILURE' -and ($falha -or $erroDeTeste)))
    if ($completa) {
        $observados = @($contagem.total, $contagem.failure, $contagem.error, $contagem.skip)
        for ($i = 0; $i -lt $observados.Count; $i++) {
            if ($observados[$i] -ne [int]$totais[0].Groups[$i+1].Value) { $problemas.Add('Totais Maven/XML divergentes.'); break }
        }
    } else { $problemas.Add('Término da suíte sem confirmação pelo Surefire. Consulte maven.log.') }
    if ($Nome -cne 'controle') {
        foreach ($sufixo in 'antes','executado','apos','restaurado') {
            if (!(Test-Path -LiteralPath (Join-Path $pasta "$sufixo.sha256"))) {
                $problemas.Add("Hashes de $sufixo ausentes.")
            }
        }
        if (!$problemas.Count -and ((Get-HashArquivo (Join-Path $pasta 'antes.sha256')) -cne
                (Get-HashArquivo (Join-Path $pasta 'restaurado.sha256')) -or
            (Get-HashArquivo (Join-Path $pasta 'executado.sha256')) -cne
                (Get-HashArquivo (Join-Path $pasta 'apos.sha256')))) {
            $problemas.Add('Bytecode ou fontes de teste divergentes nos hashes da rodada.')
        }
    }
    $estadoRodada = if ($problemas.Count) { 'environment_error' } else { 'complete' }
    @{
        metodos = $metodos; ambiguos = $ambiguidade; jacoco_args = $ja
        resumo = [ordered]@{
            rodada = $Nome; estado = $estadoRodada; codigo = $registro.codigo; duracao_ms = $registro.duracao_ms
            xml = $arquivos.Count; contagem = $contagem; diagnostico = $problemas.ToArray()
            invocacoes_sha256 = $fingerprint; maven_log_sha256 = Get-HashArquivo $log
            xml_manifesto_sha256 = Get-HashArquivo $xmlHashes
        }
    }
}

function Test-Controle($Controle, $Copia) {
    $Copia.resumo.estado -ceq 'complete' -and $Copia.resumo.codigo -eq 0 -and
        $Copia.resumo.invocacoes_sha256 -ceq $Controle.resumo.invocacoes_sha256 -and
        $Copia.jacoco_args -ceq $Controle.jacoco_args
}

$controle = Read-Rodada controle
$intacto = Read-Rodada intacto
if ($controle.resumo.estado -cne 'complete' -or $controle.resumo.codigo -ne 0 -or
    $controle.resumo.contagem.sem_associacao -ne 0 -or !(Test-Controle $controle $intacto)) {
    throw 'Controle ou equivalência da suíte com binários reutilizados rejeitados.'
}
if ($Controles) { return }

function Get-Rotulos($Variante, $Mutante, [string[]]$Testes) {
    foreach ($id in $Testes) {
        $antes = $controle.metodos[$id]
        $depois = $Variante.metodos[$id]
        $rotulo = 'unknown'
        $motivo = if ($Variante.resumo.estado -cne 'complete' -or $Variante.jacoco_args -cne $controle.jacoco_args) { 'environment_error' }
            elseif ($Variante.ambiguos.Contains($id)) { 'associacao_ambigua' }
            elseif ($antes -cne 'pass' -or $depois -cnotin 'pass','fail') { 'controle_ou_replay_sem_execucao_associada' }
            else {
                $rotulo = if ($depois -ceq 'fail') { 'induced_failure' } else { 'pass' }
                ''
            }
        [pscustomobject][ordered]@{
            sha = $manifesto.sha; mutation_id = $Mutante.mutation_id; test_id = $id
            label = $rotulo; motivo = $motivo; controle = $antes; replay = $depois
        }
    }
}

$testes = [string[]]@($ids)
[array]::Sort($testes, [StringComparer]::Ordinal)
$rotulos = [Collections.Generic.List[object]]::new()
$rodadas = [Collections.Generic.List[object]]::new()
$rodadas.Add($controle.resumo)
$rodadas.Add($intacto.resumo)
for ($i = 0; $i -lt $manifesto.selecionados.Count; $i++) {
    $variante = Read-Rodada "variante-$($i + 1)"
    $lote = @(Get-Rotulos $variante $manifesto.selecionados[$i] $testes)
    if ($i -eq 0) { $primeiro = $lote }
    $rotulos.AddRange([object[]]$lote)
    $rodadas.Add($variante.resumo)
}
$repeticao = Read-Rodada repeticao
$rotulosRepeticao = @(Get-Rotulos $repeticao $manifesto.selecionados[0] $testes)
$iguais = !(@(Compare-Object $primeiro $rotulosRepeticao -Property test_id,label,motivo -CaseSensitive).Count)
$rodadas.Add($repeticao.resumo)
$restaurado = Read-Rodada restaurado
$rodadas.Add($restaurado.resumo)
$hashOriginal = Get-HashArquivo (Join-Path $local 'variante-1/original.class')
$restauracao = (Test-Controle $controle $restaurado) -and
    (Get-HashArquivo (Join-Path $local 'restaurado/original.class')) -ceq $hashOriginal -and
    (Get-HashArquivo (Join-Path $local 'restaurado/antes.sha256')) -ceq
        (Get-HashArquivo (Join-Path $local 'restaurado/restaurado.sha256')) -and
    (Get-HashArquivo (Join-Path $local 'intacto/executado.sha256')) -ceq
        (Get-HashArquivo (Join-Path $local 'restaurado/executado.sha256'))
$positivos = @($rotulos | Where-Object label -ceq induced_failure).Count
$negativos = @($rotulos | Where-Object label -ceq pass).Count
$problemas = @($rodadas | Where-Object estado -cne complete).Count
$arquivoRotulos = Join-Path $local rotulos.csv
$rotulos | Export-Csv -LiteralPath $arquivoRotulos -NoTypeInformation
$resumo = [ordered]@{
    posicao = $Posicao; sha = $manifesto.sha
    gate_aprovado = $positivos -gt 0 -and $negativos -gt 0 -and $iguais -and $restauracao -and !$problemas
    equivalencia_controle = $true; repeticao_coincidente = $iguais; restauracao = $restauracao
    rotulos = "local/$Posicao/rotulos.csv"; rotulos_sha256 = Get-HashArquivo $arquivoRotulos
    manifesto_sha256 = Get-HashArquivo (Join-Path $publico manifesto.json)
    inventario_sha256 = Get-HashArquivo $inventario
    original_primeira_variante_sha256 = $hashOriginal
    contagens = [ordered]@{ induced_failure = $positivos; pass = $negativos; unknown = $rotulos.Count - $positivos - $negativos }
    pit_duracao_ms = (Get-Content -LiteralPath (Join-Path $local 'pit/execucao.json') -Raw | ConvertFrom-Json).duracao_ms
    rodadas = $rodadas.ToArray()
}
if ($Posicao -eq 96) {
    $resumo.congelamento_modelo = Get-Content -LiteralPath (Join-Path $local congelamento.json) -Raw |
        ConvertFrom-Json
}
$json = $resumo | ConvertTo-Json -Depth 8
[IO.File]::WriteAllText((Join-Path $publico resumo.json), $json.Replace("`r`n", "`n") + "`n")
