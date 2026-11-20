#Requires -Version 7.5
[CmdletBinding()]
param([switch]$Extremos)

$ErrorActionPreference = 'Stop'
$raiz = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
. (Join-Path $PSScriptRoot 'ler-lote.ps1')
$invariante = [Globalization.CultureInfo]::InvariantCulture
$utf8 = [Text.UTF8Encoding]::new($false)
$imagem = 'sha256:6e15bf7fd834e6998883afacb56e4b6de6b180fff899bf3fb0474840f5ac93d6'
$base = 'eclipse-temurin:21.0.11_10-jdk-noble@sha256:d435e5eb685fa668f894f20710bfc12608ec65f8509fec480da3f278f2382081'
$comando = 'mvn --batch-mode --no-transfer-progress -Dstyle.color=never -Dmaven.repo.local=/maven-cache -Duser.timezone=UTC clean test'
$classeJava = '[a-zA-Z_$][\w$]*(?:\.[a-zA-Z_$][\w$]*)+'
$metodoJava = '[a-zA-Z_$][\w$]*'
$tipoJava = "(?:$classeJava|boolean|byte|short|int|long|char|float|double)(?:\[\])*"
$local = 'evidencias/KAN-16/local'
$escopo = if ($Extremos) { 'extremos' } else { 'lote' }
$saida = "$local/$escopo"
$tentativas = @(Get-Kan16Lote $raiz -Extremos:$Extremos)

function Get-Sha256([string]$Ref) {
    (Get-FileHash -LiteralPath (Join-Path $raiz $Ref)).Hash.ToLowerInvariant()
}

function ConvertTo-Ms([decimal]$Segundos) {
    if ($Segundos -lt 0) { throw 'Duração negativa.' }
    [long]([decimal]::Round($Segundos * 1000, 0, [MidpointRounding]::AwayFromZero))
}

function Read-Inventario($Tentativa, $Ambiente) {
    $mapa = [Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
    $ref = "$local/inventarios/$($Tentativa.sha)-$($Tentativa.id)/metodos.tsv"
    $arquivo = Join-Path $raiz $ref
    $logRef = $ref -replace 'metodos.tsv$', 'descoberta.log'
    if (!(Test-Path -LiteralPath (Join-Path $raiz $logRef) -PathType Leaf)) { $logRef = $null }
    if (!(Test-Path -LiteralPath $arquivo -PathType Leaf)) {
        return @{ mapa = $mapa; ref = $null; meta_ref = $null; log_ref = $logRef }
    }
    $metaRef = $ref -replace 'metodos.tsv$', 'descoberta.json'
    $meta = Get-Content -LiteralPath (Join-Path $raiz $metaRef) -Raw | ConvertFrom-Json
    if ($meta.sha -cne $Tentativa.sha -or $meta.tentativa -cne $Tentativa.id -or
        $meta.fonte_tar_sha256 -cne $Ambiente.fonte_tar_sha256 -or $meta.imagem_id -cne $Ambiente.imagem_id -or
        $meta.ambiente_sha256 -cne (Get-Sha256 "$($Tentativa.diretorio)/ambiente.json") -or
        $meta.maven_log_sha256 -cne (Get-Sha256 "$($Tentativa.diretorio)/maven.log") -or
        $meta.inventario_sha256 -cne (Get-Sha256 $ref) -or !$logRef -or
        $meta.log_sha256 -cne (Get-Sha256 $logRef) -or $meta.codigo_saida -ne 0) {
        throw "Inventário sem proveniência válida: $ref."
    }
    $ids = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($linha in Import-Csv -LiteralPath $arquivo -Delimiter ([char]9)) {
        $id = "$($linha.classe)#$($linha.metodo)($($linha.tipos))"
        if ($id -cnotmatch "\A$classeJava#$metodoJava\((?:$tipoJava(?:,$tipoJava)*)?\)\z" -or
            $linha.raiz -cnotmatch "\A$classeJava\z" -or !$linha.descritor -or !$ids.Add($linha.descritor)) {
            throw "Descritor inválido ou duplicado em $ref ($id)."
        }
        $linha | Add-Member -NotePropertyName test_id -NotePropertyValue $id
        $chave = "$($linha.raiz)#$($linha.metodo)"
        if (!$mapa.ContainsKey($chave)) { $mapa[$chave] = [Collections.Generic.List[object]]::new() }
        $mapa[$chave].Add($linha)
    }
    @{ mapa = $mapa; ref = $ref; meta_ref = $metaRef; log_ref = $logRef }
}

function Find-Metodo($Inventario, [string]$ClasseRaiz, [string]$ClasseXml, [string]$NomeXml) {
    if (!$Inventario.ref) { return @{ motivo = 'inventario_da_tentativa_indisponivel' } }
    $nome = [regex]::Match($NomeXml, "\A(?<metodo>$metodoJava)(?:\((?<tipos>[^()]*)\))?(?:\[(?<indice>[0-9]+)\])?\z")
    if (!$nome.Success) { return @{ motivo = 'nome_xml_sem_origem_de_metodo_comprovavel' } }
    $candidatos = $Inventario.mapa["$ClasseRaiz#$($nome.Groups['metodo'].Value)"]
    if (!$candidatos) { return @{ motivo = 'metodo_ausente_no_inventario_da_tentativa' } }
    $correspondencias = [Collections.Generic.List[object]]::new()
    $classeConfirmada = $false
    foreach ($candidato in $candidatos) {
        if ($candidato.classe -cne $ClasseXml -and $candidato.rotulo_classe -cne $ClasseXml) { continue }
        $classeConfirmada = $true
        if ($nome.Groups['tipos'].Success) {
            $tipos = $nome.Groups['tipos'].Value -creplace '\s+', ''
            if ($tipos -cne $candidato.tipos -and $tipos -cne $candidato.tipos_curtos) { continue }
        } elseif ($candidato.tipos -and $candidato.rotulo_metodo -cne $NomeXml) {
            continue
        }
        if ($nome.Groups['indice'].Success -and $candidato.tipo_descritor -cnotin 'test-template','test-factory') { continue }
        $correspondencias.Add($candidato)
    }
    if ($correspondencias.Count -eq 1) { return @{ metodo = $correspondencias[0] } }
    $motivo = if (!$classeConfirmada) { 'contexto_de_classe_nao_confirmado' }
        elseif ($correspondencias.Count -gt 1) { 'origem_ambigua_no_inventario' }
        else { 'assinatura_ou_tipo_de_descritor_nao_confirmado' }
    @{ motivo = $motivo }
}

function Read-Tentativa($Tentativa, [IO.TextWriter]$Invocacoes, [IO.TextWriter]$HashesXml) {
    $prefixo = $Tentativa.diretorio
    $envRef = "$prefixo/ambiente.json"
    $logRef = "$prefixo/maven.log"
    $ambiente = Get-Content -LiteralPath (Join-Path $raiz $envRef) -Raw | ConvertFrom-Json -DateKind String
    if ($ambiente.id_execucao -cne $Tentativa.id -or $ambiente.sha_solicitado -cne $Tentativa.sha) {
        throw "Identidade da tentativa divergente: $envRef."
    }
    $duracao = $null
    if ($ambiente.fim_utc) {
        $inicio = [DateTimeOffset]::Parse($ambiente.inicio_utc, $invariante)
        $fim = [DateTimeOffset]::Parse($ambiente.fim_utc, $invariante)
        $duracao = ConvertTo-Ms ([decimal](($fim - $inicio).Ticks) / [TimeSpan]::TicksPerSecond)
        if ($inicio.Offset -ne [TimeSpan]::Zero -or $fim.Offset -ne [TimeSpan]::Zero -or
            $null -eq $ambiente.duracao_segundos -or
            [math]::Abs($duracao - (ConvertTo-Ms ([decimal]$ambiente.duracao_segundos))) -gt 1) {
            throw "Intervalo de medição inconsistente: $envRef."
        }
    }
    $log = Get-Content -LiteralPath (Join-Path $raiz $logRef) -Raw
    $build = [regex]::Matches($log, '(?m)^\[INFO\] BUILD (SUCCESS|FAILURE)[ \t\r]*$')
    $totais = [regex]::Matches($log, '(?m)^\[(?:INFO|WARNING|ERROR)\] Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)[ \t\r]*$')
    $codigo = $ambiente.codigo_maven
    $falhaDeTeste = $log -cmatch '(?m)^\[ERROR\] Failed to execute goal .*maven-surefire-plugin:[^\r\n]*:test[^\r\n]*There are test failures'
    $status = 'incomplete'
    $diagnostico = 'Término de suíte completa sem confirmação.'
    if ($ambiente.erro -or ($ambiente.fim_utc -and $log -cmatch
        '(?mi)^\[ERROR\].*(could not resolve dependencies|non-resolvable parent POM|could not transfer artifact|the forked VM terminated|no space left on device)')) {
        $status = 'environment_error'
        $diagnostico = if ($ambiente.erro) { $ambiente.erro } else { 'Infraestrutura: consultar o log Maven.' }
    } elseif ($ambiente.fim_utc -and $null -ne $codigo -and $codigo -eq $ambiente.codigo_saida -and
        $log -cmatch "(?m)^KAN-13 código Maven: $codigo[ \t\r]*$" -and
        $log -cmatch '(?m)^KAN-13 cache Maven inicial: frio[ \t\r]*$' -and $build.Count -eq 1 -and
        (($codigo -eq 0) -eq ($build[0].Groups[1].Value -ceq 'SUCCESS')) -and $totais.Count -eq 1 -and
        ($codigo -eq 0 -or $falhaDeTeste)) {
        $status = 'complete'
        $diagnostico = $null
    }
    if ($status -cne 'complete') {
        throw "Referência de T0 sem suíte completa ($status). $diagnostico $envRef"
    }
    if ($ambiente.sha_verificado -cne $Tentativa.sha -or $ambiente.fonte_tar_sha256 -cnotmatch '\A[0-9a-f]{64}\z' -or
        $ambiente.imagem_id -cne $imagem -or $ambiente.base_imagem -cne $base -or
        $ambiente.plataforma -cne 'linux/amd64' -or $ambiente.fuso_configurado -cne 'UTC' -or
        $ambiente.cache_maven.estado_inicial -cne 'frio' -or $ambiente.cache_maven.caminho -cne '/maven-cache' -or
        $ambiente.java -cnotmatch '^Java version: 21\.0\.11, vendor: Eclipse Adoptium,' -or
        $ambiente.maven -cnotmatch '^Apache Maven 3\.9\.11 ' -or ($ambiente.comando_maven -join ' ') -cne $comando) {
        throw "SHA verificado, comando ou ambiente divergente: $envRef."
    }
    if ($Tentativa.registro -and ($Tentativa.registro.codigo_maven -ne $codigo -or
        $Tentativa.registro.codigo_executor -ne $ambiente.codigo_saida -or
        $Tentativa.registro.inicio_utc -cne $ambiente.inicio_utc -or $Tentativa.registro.fim_utc -cne $ambiente.fim_utc -or
        $Tentativa.registro.duracao_segundos -ne $ambiente.duracao_segundos -or
        $Tentativa.registro.fonte_tar_sha256 -cne $ambiente.fonte_tar_sha256 -or
        (($codigo -eq 0) -ne ($Tentativa.registro.status -ceq 'suite_aprovada')))) {
        throw "Metadados divergentes do manifesto: $envRef."
    }

    $inventario = Read-Inventario $Tentativa $ambiente
    $grupos = [Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
    $cache = [Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
    $contagem = [ordered]@{ total = 0; pass = 0; failure = 0; error = 0; skip = 0 }
    $lacunas = [ordered]@{}
    $testesCabecalho = 0
    $divergencias = [Collections.Generic.List[object]]::new()
    $associadas = 0
    $somaBruta = [decimal]0
    $semTempo = 0
    $duracoesNegativas = 0
    $arquivos = [string[]]@(Get-ChildItem -LiteralPath (Join-Path $raiz "$prefixo/surefire") -Filter 'TEST-*.xml' -File |
        Select-Object -ExpandProperty Name)
    [array]::Sort($arquivos, [StringComparer]::Ordinal)
    $opcoes = [Xml.XmlReaderSettings]::new()
    $opcoes.DtdProcessing = [Xml.DtdProcessing]::Prohibit
    foreach ($nomeArquivo in $arquivos) {
        $xmlRef = "$prefixo/surefire/$nomeArquivo"
        $HashesXml.WriteLine(('{0}  {1}' -f (Get-Sha256 $xmlRef), $xmlRef))
        $xml = [xml]::new()
        $leitor = [Xml.XmlReader]::Create((Join-Path $raiz $xmlRef), $opcoes)
        try { $xml.Load($leitor) } finally { $leitor.Dispose() }
        $suite = $xml.DocumentElement
        if ($suite.LocalName -cne 'testsuite' -or
            $suite.SelectSingleNode("properties/property[@name='user.timezone']/@value").Value -cne 'UTC') {
            throw "XML fora da configuração esperada: $xmlRef."
        }
        $itens = $suite.SelectNodes('testcase')
        $atributoTests = [int]$suite.GetAttribute('tests')
        $testesCabecalho += $atributoTests
        if ($atributoTests -ne $itens.Count) {
            $divergencias.Add([ordered]@{ ref = $xmlRef; atributo_tests = $atributoTests; elementos = $itens.Count })
        }
        $classeRaiz = $nomeArquivo -creplace '\ATEST-','' -creplace '\.xml\z',''
        $indice = 0
        foreach ($item in $itens) {
            $indice++
            $contagem.total++
            $estados = $item.SelectNodes('failure | error | skipped')
            if ($estados.Count -gt 1) { throw "Estados conflitantes em $xmlRef, testcase $indice." }
            $bruto = if (!$estados.Count) { 'pass' } elseif ($estados[0].LocalName -ceq 'skipped') { 'skip' } else { $estados[0].LocalName }
            $contagem[$bruto]++
            $classeXml = $item.GetAttribute('classname')
            $nomeXml = $item.GetAttribute('name')
            if (!$classeXml -or !$nomeXml) { throw "Testcase sem nome ou classe em $xmlRef, índice $indice." }
            $tempo = $item.GetAttribute('time')
            $segundos = $null
            $situacaoTempo = if ($bruto -ceq 'skip') { 'inaplicavel_skip' } else { 'ausente' }
            if ($tempo) {
                if ($tempo -cnotmatch '\A-?[0-9]+(?:\.[0-9]+)?\z') { throw "Duração inválida em $xmlRef, testcase $indice." }
                $valor = [decimal]::Parse($tempo, $invariante)
                if ($valor -lt 0) {
                    $duracoesNegativas++
                    $situacaoTempo = 'negativa_no_xml'
                } elseif ($bruto -cne 'skip') {
                    $segundos = $valor
                    $situacaoTempo = 'medida'
                }
            }
            if ($bruto -cne 'skip') {
                if ($null -eq $segundos) { $semTempo++ } else { $somaBruta += $segundos }
            }
            if ($item.SelectSingleNode('flakyFailure | flakyError | rerunFailure | rerunError')) {
                $associacao = @{ motivo = 'rerun_sem_tempo_e_resultado_individual_comprovaveis' }
            } else {
                $chave = "$classeRaiz$([char]0)$classeXml$([char]0)$nomeXml"
                if (!$cache.ContainsKey($chave)) { $cache[$chave] = Find-Metodo $inventario $classeRaiz $classeXml $nomeXml }
                $associacao = $cache[$chave]
            }
            $id = $associacao.metodo.test_id
            if ($id) {
                $associadas++
                if (!$grupos.ContainsKey($id)) {
                    $grupos[$id] = @{ pass = 0; fail = 0; skip = 0; segundos = [decimal]0; sem_tempo = 0 }
                }
                $grupo = $grupos[$id]
                if ($bruto -cin 'failure','error') { $grupo.fail++ } else { $grupo[$bruto]++ }
                if ($bruto -cne 'skip') {
                    if ($null -eq $segundos) { $grupo.sem_tempo++ } else { $grupo.segundos += $segundos }
                }
            } else {
                $lacunas[$associacao.motivo]++
            }
            $campos = [string[]]@($Tentativa.sha, $xmlRef, "/testsuite/testcase[$indice]", $classeXml, $nomeXml,
                $bruto, $tempo, $situacaoTempo, $id, $associacao.metodo.descritor, $associacao.motivo)
            $Invocacoes.WriteLine('"' + (($campos -creplace '"', '""') -join '","') + '"')
        }
    }
    if ($arquivos.Count -ne $ambiente.xml_surefire) { throw "Número de XML divergente: $envRef." }
    $vetor = @($contagem.total, $contagem.failure, $contagem.error, $contagem.skip) -join ','
    $maven = ($totais[0].Groups | Select-Object -Skip 1 -ExpandProperty Value) -join ','
    if ($contagem.total -eq 0 -or $maven -cne $vetor -or
        (($codigo -eq 0) -ne (($contagem.failure + $contagem.error) -eq 0))) {
        throw "Maven e Surefire não reconciliados: $logRef (Maven $maven, XML $vetor)."
    }
    if ($Tentativa.registro -and ($Tentativa.registro.xml -ne $arquivos.Count -or
        $Tentativa.registro.testsuite_atributo_tests -ne $testesCabecalho -or
        (@($Tentativa.registro.casos, $Tentativa.registro.falhas, $Tentativa.registro.erros, $Tentativa.registro.ignorados) -join ',') -cne $vetor)) {
        throw "Maven e Surefire divergem do manifesto: $logRef."
    }
    $metodos = [ordered]@{ total = $grupos.Count; pass = 0; fail = 0; skip = 0; com_tempo = 0; sem_tempo = 0; zero_ms = 0; soma_ms_conhecidos = [long]0 }
    $ids = [string[]]@($grupos.Keys)
    [array]::Sort($ids, [StringComparer]::Ordinal)
    $agrupadas = 0
    $resultado = foreach ($id in $ids) {
        $grupo = $grupos[$id]
        $agrupadas += $grupo.pass + $grupo.fail + $grupo.skip
        $outcome = if ($grupo.fail) { 'fail' } elseif ($grupo.pass) { 'pass' } else { 'skip' }
        $metodos[$outcome]++
        $ms = $null
        if ($grupo.sem_tempo -or $outcome -ceq 'skip') {
            $metodos.sem_tempo++
        } else {
            $ms = ConvertTo-Ms $grupo.segundos
            $metodos.com_tempo++
            if ($ms -eq 0) { $metodos.zero_ms++ }
            $metodos.soma_ms_conhecidos += $ms
        }
        [pscustomobject][ordered]@{
            commit_sha = $Tentativa.sha; scenario = 'T0'; test_id = $id; outcome = $outcome
            duration_ms = $ms; execution_order = $null
            source_ref = "$saida/invocacoes.csv#commit_sha=$($Tentativa.sha)&test_id=$([uri]::EscapeDataString($id))"
        }
    }
    $semAssociacao = $contagem.total - $associadas
    if ($agrupadas -ne $associadas -or [long]($lacunas.Values | Measure-Object -Sum).Sum -ne $semAssociacao) {
        throw "Cobertura de invocações não reconciliada: $envRef."
    }
    [pscustomobject]@{
        run = [pscustomobject][ordered]@{
            commit_sha = $Tentativa.sha; scenario = 'T0'; run_status = $status
            suite_duration_ms = $duracao; source_ref = $envRef
        }
        results = @($resultado)
        resumo = [ordered]@{
            posicao = $Tentativa.posicao; commit_sha = $Tentativa.sha; tentativa = $Tentativa.id
            run_status = $status; suite_duration_ms = $duracao; ambiente_ref = $envRef; ambiente_sha256 = Get-Sha256 $envRef
            maven_ref = $logRef; maven_sha256 = Get-Sha256 $logRef; fonte_tar_sha256 = $ambiente.fonte_tar_sha256
            inventario_ref = $inventario.ref; inventario_metadados_ref = $inventario.meta_ref
            inventario_sha256 = if ($inventario.ref) { Get-Sha256 $inventario.ref }
            descoberta_log_ref = $inventario.log_ref
            descoberta_log_sha256 = if ($inventario.log_ref) { Get-Sha256 $inventario.log_ref }
            xml = $arquivos.Count; testsuite_atributo_tests = $testesCabecalho; xml_cabecalho_divergente = $divergencias.ToArray()
            casos_xml = $contagem; maven_reconciliado = $true; soma_segundos_xml_executados_com_tempo = $somaBruta
            casos_executados_sem_tempo = $semTempo; tempos_negativos_xml = $duracoesNegativas
            invocacoes_associadas = $associadas; invocacoes_nao_associadas = $semAssociacao
            cobertura_identidade = if ($semAssociacao) { 'parcial' } else { 'integral' }
            lacunas = $lacunas; metodos = $metodos; metodos_com_ordem_observada = 0
        }
    }
}

$pasta = Join-Path $raiz $saida
$null = New-Item -ItemType Directory -Path $pasta -Force
$trava = [IO.File]::Open((Join-Path $pasta '.exportacao.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
$temporaria = Join-Path $pasta ('.exportacao-' + [guid]::NewGuid().ToString('N'))
try {
    $null = New-Item -ItemType Directory -Path $temporaria
    $inv = [IO.StreamWriter]::new((Join-Path $temporaria 'invocacoes.csv'), $false, $utf8)
    $hash = [IO.StreamWriter]::new((Join-Path $temporaria 'xml.sha256'), $false, $utf8)
    try {
        $inv.WriteLine('commit_sha,xml_ref,xpath,classname_xml,name_xml,outcome_xml,time_xml_s,situacao_tempo,test_id,descritor_junit,motivo_lacuna')
        $dados = @(foreach ($tentativa in $tentativas) { Read-Tentativa $tentativa $inv $hash })
    } finally {
        $inv.Dispose()
        $hash.Dispose()
    }
    $runs = @($dados.run)
    $resultados = @($dados | ForEach-Object { $_.results })
    $pk = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $fk = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($run in $runs) {
        if (!$fk.Add($run.commit_sha) -or $run.scenario -cne 'T0' -or !$run.source_ref -or
            $run.run_status -cne 'complete' -or $null -eq $run.suite_duration_ms -or $run.suite_duration_ms -lt 0) {
            throw "t0_runs inválido: $($run.commit_sha)."
        }
    }
    foreach ($resultado in $resultados) {
        if (!$pk.Add("$($resultado.commit_sha)#$($resultado.test_id)") -or !$fk.Contains($resultado.commit_sha) -or
            $resultado.scenario -cne 'T0' -or $resultado.outcome -cnotin 'pass','fail','skip' -or !$resultado.source_ref -or
            $null -ne $resultado.execution_order -or ($null -ne $resultado.duration_ms -and $resultado.duration_ms -lt 0) -or
            ($resultado.outcome -ceq 'skip' -and $null -ne $resultado.duration_ms)) {
            throw "t0_results inválido: $($resultado.test_id)."
        }
    }
    $resultadosRef = Join-Path $temporaria 't0_results.csv'
    $runs | Export-Csv -LiteralPath (Join-Path $temporaria 't0_runs.csv') -Encoding utf8NoBOM
    if ($resultados.Count) {
        $resultados | Export-Csv -LiteralPath $resultadosRef -Encoding utf8NoBOM
    } else {
        Set-Content -LiteralPath $resultadosRef -Encoding utf8NoBOM -Value 'commit_sha,scenario,test_id,outcome,duration_ms,execution_order,source_ref'
    }
    $artefatos = @('t0_runs.csv','t0_results.csv','invocacoes.csv','xml.sha256')
    $hashes = [ordered]@{}
    foreach ($nome in $artefatos) {
        $hashes[$nome] = (Get-FileHash -LiteralPath (Join-Path $temporaria $nome)).Hash.ToLowerInvariant()
    }
    $fonte = $tentativas[0].manifesto_ref
    $historico = @()
    if (!$Extremos) {
        $manifesto = Get-Content -LiteralPath (Join-Path $raiz $fonte) -Raw | ConvertFrom-Json -DateKind String
        $referencias = @($tentativas.id)
        $historico = @(foreach ($anterior in $manifesto.tentativas) {
            if ($anterior.tentativa -cin $referencias) { continue }
            [ordered]@{
                posicao = $anterior.posicao; commit_sha = $anterior.sha; tentativa = $anterior.tentativa
                status_kan14 = $anterior.status; diagnostico = $anterior.diagnostico
                ambiente_ref = $anterior.ambiente; maven_ref = $anterior.maven_log
            }
        })
    }
    $resumo = [ordered]@{
        contrato = '0.1.0'; escopo = $escopo; fonte_lote_ref = $fonte; fonte_lote_sha256 = Get-Sha256 $fonte
        auditoria_ref = 'evidencias/KAN-10/commits.csv'; auditoria_sha256 = Get-Sha256 'evidencias/KAN-10/commits.csv'
        intervalo_suite = 'Início do executor até o bloco de fechamento após Docker/Maven e cópia, por timestamps UTC de ambiente.json.'
        ordem_global = 'não observada'; sha256 = $hashes; revisoes = @($dados.resumo)
        tentativas_sem_referencia = $historico
    }
    $resumo | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $temporaria 'resumo.json') -Encoding utf8NoBOM
    foreach ($nome in ($artefatos + 'resumo.json')) {
        [IO.File]::Move((Join-Path $temporaria $nome), (Join-Path $pasta $nome), $true)
    }
    $dados.resumo | ForEach-Object {
        "Posição $($_.posicao) com $($_.casos_xml.total) casos, $($_.metodos.total) métodos e $($_.invocacoes_nao_associadas) casos sem associação."
    }
    "Saída em $saida"
} finally {
    if (Test-Path -LiteralPath $temporaria) {
        Get-ChildItem -LiteralPath $temporaria -File | Remove-Item
        [IO.Directory]::Delete($temporaria)
    }
    $trava.Dispose()
}
