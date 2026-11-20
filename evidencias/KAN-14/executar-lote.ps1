#Requires -Version 7.3
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Fonte,

    [switch]$SomenteVerificar
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$raiz = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$Fonte = (Resolve-Path -LiteralPath $Fonte).Path
$executor = Join-Path $raiz 'infra/commons-lang/executar.ps1'
$saida = Join-Path $raiz 'resultados/KAN-14'
$imagem = 'sha256:6e15bf7fd834e6998883afacb56e4b6de6b180fff899bf3fb0474840f5ac93d6'
$base = 'eclipse-temurin:21.0.11_10-jdk-noble@sha256:d435e5eb685fa668f894f20710bfc12608ec65f8509fec480da3f278f2382081'
$comando = 'mvn --batch-mode --no-transfer-progress -Dstyle.color=never -Dmaven.repo.local=/maven-cache -Duser.timezone=UTC clean test'

function Conferir-Tentativa($linha, [string]$id, [string]$hashEsperado) {
    $prefixo = "resultados/$($linha.origem)/$($linha.sha)/$id"
    $pasta = Join-Path $raiz $prefixo
    $registro = [ordered]@{
        posicao = [int]$linha.posicao
        sha = $linha.sha
        tentativa = $id
        reutilizada = [bool]$linha.tentativa_reutilizada
        ambiente = "$prefixo/ambiente.json"
        maven_log = "$prefixo/maven.log"
        surefire = "$prefixo/surefire/"
        status = 'evidencia_inconclusiva'
        diagnostico = $null
    }

    try {
        $ambiente = Get-Content -LiteralPath (Join-Path $pasta 'ambiente.json') -Raw | ConvertFrom-Json
        $registro.codigo_maven = $ambiente.codigo_maven
        $registro.codigo_executor = $ambiente.codigo_saida
        $registro.inicio_utc = ([DateTimeOffset]$ambiente.inicio_utc).ToUniversalTime().ToString('o')
        $registro.duracao_segundos = $ambiente.duracao_segundos
        if ($ambiente.conteiner -and -not $ambiente.conteiner_removido) {
            $registro.conteiner = $ambiente.conteiner
        }
        if (-not $ambiente.fim_utc) {
            $registro.status = 'interrompida'
            throw 'O executor não registrou término.'
        }
        $registro.fim_utc = ([DateTimeOffset]$ambiente.fim_utc).ToUniversalTime().ToString('o')
        if ($ambiente.erro) {
            $registro.status = 'erro_executor'
            throw $ambiente.erro
        }
        if ($ambiente.id_execucao -cne $id -or $ambiente.sha_solicitado -cne $linha.sha -or
            $ambiente.sha_verificado -cne $linha.sha -or $ambiente.fonte_tar_sha256 -cne $hashEsperado) {
            throw 'Identidade da tentativa, SHA ou hash da exportação divergente.'
        }
        $registro.fonte_tar_sha256 = $hashEsperado
        if ($ambiente.imagem_id -cne $imagem -or $ambiente.base_imagem -cne $base -or
            $ambiente.plataforma -cne 'linux/amd64' -or $ambiente.fuso_configurado -cne 'UTC' -or
            $ambiente.cache_maven.estado_inicial -cne 'frio' -or $ambiente.cache_maven.caminho -cne '/maven-cache' -or
            $ambiente.maven -notmatch '^Apache Maven 3\.9\.11 ' -or
            $ambiente.java -notmatch '^Java version: 21\.0\.11, vendor: Eclipse Adoptium,' -or
            ($ambiente.comando_maven -join ' ') -cne $comando) {
            throw 'Ambiente ou comando Maven divergente da KAN-13.'
        }

        $log = Get-Content -LiteralPath (Join-Path $pasta 'maven.log') -Raw
        $codigo = $ambiente.codigo_maven
        $build = [regex]::Matches($log, '(?m)^\[INFO\] BUILD (SUCCESS|FAILURE)\s*$')
        $resumo = [regex]::Matches($log, '(?m)^\[(?:INFO|WARNING|ERROR)\] Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)\s*$')
        $linhasLog = $log -split '\r?\n'
        if ($null -eq $codigo -or $codigo -ne $ambiente.codigo_saida -or
            $linhasLog[0] -cne "Comando: $comando" -or
            $ambiente.java -cnotin $linhasLog -or $ambiente.maven -cnotin $linhasLog -or
            $log -notmatch "(?m)^KAN-13 código Maven: ${codigo}\s*$" -or
            $log -notmatch '(?m)^KAN-13 cache Maven inicial: frio\s*$' -or
            $build.Count -ne 1 -or ($codigo -eq 0) -ne ($build[0].Groups[1].Value -eq 'SUCCESS')) {
            throw 'Término do Maven inconclusivo.'
        }

        $xmls = @(Get-ChildItem -LiteralPath (Join-Path $pasta 'surefire') -Filter 'TEST-*.xml' -File)
        if ($xmls.Count -ne $ambiente.xml_surefire) {
            throw 'Quantidade de XML divergente dos metadados do executor.'
        }
        $registro.xml = $xmls.Count
        $total = 0
        $falhas = 0
        $erros = 0
        $ignorados = 0
        $atributoTests = 0
        foreach ($arquivo in $xmls) {
            $xml = [System.Xml.XmlDocument]::new()
            $xml.XmlResolver = $null
            $xml.Load($arquivo.FullName)
            $fuso = $xml.SelectSingleNode('/testsuite/properties/property[@name="user.timezone"]/@value')
            if ($fuso.Value -cne 'UTC') {
                throw "XML sem fuso UTC: $($arquivo.Name)"
            }
            $atributoTests += [int]$xml.DocumentElement.GetAttribute('tests')
            $total += $xml.SelectNodes('/testsuite/testcase').Count
            $falhas += $xml.SelectNodes('/testsuite/testcase[failure]').Count
            $erros += $xml.SelectNodes('/testsuite/testcase[error]').Count
            $ignorados += $xml.SelectNodes('/testsuite/testcase[skipped]').Count
            if ($xml.SelectNodes('/testsuite/testcase[count(failure | error | skipped) > 1]').Count) {
                throw "XML com estados conflitantes: $($arquivo.Name)"
            }
        }
        $registro.testsuite_atributo_tests = $atributoTests
        if ($codigo -ne 0 -and ($resumo.Count -ne 1 -or $falhas + $erros -eq 0 -or
            $log -notmatch '(?m)^\[ERROR\] Failed to execute goal .*maven-surefire-plugin:[^\r\n]*:test[^\r\n]*There are test failures')) {
            $registro.status = 'build_sem_t0_validado'
            $causa = $linhasLog | Where-Object { $_ -match '^\[ERROR\] Failed to execute goal ' } | Select-Object -First 1
            throw "Maven terminou com BUILD FAILURE sem uma suíte validada. $causa"
        }

        $contagens = @($total, $falhas, $erros, $ignorados)
        if ($total -eq 0 -or $resumo.Count -ne 1 -or
            ($contagens -join ',') -ne (($resumo[0].Groups | Select-Object -Skip 1 -ExpandProperty Value) -join ',') -or
            ($codigo -eq 0 -and $falhas + $erros -ne 0)) {
            throw 'Resumo do Maven e casos dos XML não reconciliados.'
        }

        $registro.casos = $total
        $registro.aprovados = $total - $falhas - $erros - $ignorados
        $registro.ignorados = $ignorados
        $registro.falhas = $falhas
        $registro.erros = $erros
        $registro.status = if ($codigo -eq 0) { 'suite_aprovada' } else { 'suite_com_falhas' }
    }
    catch {
        $registro.diagnostico = $_.Exception.Message
    }

    [pscustomobject]$registro
}

function Confirmar-ContêinerParado([string]$conteiner) {
    $estado = docker container inspect --format '{{.State.Status}}' $conteiner 2>&1
    if (($LASTEXITCODE -eq 0 -and $estado -in 'running','restarting','paused','created') -or
        ($LASTEXITCODE -ne 0 -and "$estado" -notmatch 'No such (?:object|container)')) {
        throw "Estado pendente no contêiner ${conteiner}: $estado"
    }
}

$lote = @(Import-Csv -LiteralPath (Join-Path $PSScriptRoot 'lote.csv'))
$recorte = @(Import-Csv -LiteralPath (Join-Path $raiz 'evidencias/KAN-10/commits.csv'))
if (($lote.posicao -join ',') -cne '1,26,50,75,100') {
    throw 'Posições diferentes do lote aprovado.'
}

$null = New-Item -ItemType Directory -Path $saida -Force
$trava = [IO.File]::Open((Join-Path $saida 'lote.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
$trabalho = Join-Path $saida ('.verificacao-' + [guid]::NewGuid().ToString('N'))
try {
    $null = New-Item -ItemType Directory -Path $trabalho
    $tar = Join-Path $trabalho 'fonte.tar'
    $hashes = @{}
    foreach ($linha in $lote) {
        $origem = @($recorte | Where-Object position -eq $linha.posicao)
        if ($origem.Count -ne 1 -or $origem[0].commit_sha -cne $linha.sha -or $linha.sha -cnotmatch '\A[0-9a-f]{40}\z') {
            throw "Posição $($linha.posicao) divergente do CSV da KAN-10."
        }
        $sha = $linha.sha
        $revisao = git -C $Fonte rev-parse --verify "${sha}^{commit}"
        if ($LASTEXITCODE -ne 0 -or $revisao -cne $sha) {
            throw "O clone não resolveu o SHA $sha."
        }
        git -C $Fonte archive --format=tar "--output=$tar" $sha
        if ($LASTEXITCODE -ne 0) {
            throw "Falha ao exportar $sha para conferência."
        }
        $hashes[$sha] = (Get-FileHash -LiteralPath $tar -Algorithm SHA256).Hash.ToLowerInvariant()
    }

    $selecionadas = @()
    $historico = @()
    foreach ($linha in $lote) {
        $sha = $linha.sha
        $pastaSha = Join-Path $raiz "resultados/$($linha.origem)/$sha"
        $ids = if ($linha.tentativa_reutilizada) {
            $linha.tentativa_reutilizada
        } elseif (Test-Path -LiteralPath $pastaSha) {
            Get-ChildItem -LiteralPath $pastaSha -Directory | Sort-Object Name | Select-Object -ExpandProperty Name
        }

        $tentativas = @(foreach ($id in $ids) { Conferir-Tentativa $linha $id $hashes[$sha] })
        $valida = $tentativas | Where-Object status -in 'suite_aprovada','suite_com_falhas' | Select-Object -First 1
        if ($valida) {
            Write-Host "Posição $($linha.posicao): tentativa $($valida.tentativa) verificada; execução dispensada."
        } elseif (-not $SomenteVerificar -and -not $linha.tentativa_reutilizada) {
            foreach ($anterior in $tentativas | Where-Object conteiner) {
                Confirmar-ContêinerParado $anterior.conteiner
            }
            $idTag = docker image inspect test-prioritization/commons-lang:kan13 --format '{{.Id}}'
            if ($LASTEXITCODE -ne 0 -or $idTag -cne $imagem) {
                throw 'A tag do executor precisa apontar para o ID Docker aprovado.'
            }

            Write-Host "Executando a posição $($linha.posicao): $sha"
            & $executor -Fonte $Fonte -Sha $sha -Saida $saida
            $codigoExecutor = $LASTEXITCODE
            $novas = @(Get-ChildItem -LiteralPath $pastaSha -Directory | Where-Object Name -notin @($ids))
            if ($novas.Count -ne 1) {
                throw "Esperava uma nova tentativa para $sha, encontrei $($novas.Count)."
            }
            $nova = Conferir-Tentativa $linha $novas[0].Name $hashes[$sha]
            if ($nova.codigo_executor -ne $codigoExecutor) {
                $nova.status = 'evidencia_inconclusiva'
                $nova.diagnostico = 'Retorno do executor divergente do código registrado em ambiente.json.'
            }
            if ($nova.conteiner) {
                Confirmar-ContêinerParado $nova.conteiner
            }
            $tentativas += $nova
            if ($nova.status -in 'suite_aprovada','suite_com_falhas') {
                $valida = $nova
            }
        }

        $historico += $tentativas
        if ($valida) {
            $selecionadas += $valida
            Write-Host "Posição $($linha.posicao): $($valida.status), $($valida.casos) casos."
        } else {
            Write-Warning "Posição $($linha.posicao) sem evidência válida. Consulte as tentativas em $saida."
        }
    }

    $relatorio = [ordered]@{
        imagem_id = $imagem
        base_imagem = $base
        ambiente = 'Linux/amd64, Eclipse Temurin 21.0.11, Maven 3.9.11, UTC, cache Maven frio'
        comando = $comando
        selecionadas = $selecionadas
        tentativas = $historico
    }
    $temporario = Join-Path $trabalho 'execucoes.json'
    $relatorio | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $temporario
    [IO.File]::Move($temporario, (Join-Path $saida 'execucoes.json'), $true)
    if ($selecionadas.Count -ne $lote.Count) {
        exit 1
    }
}
finally {
    foreach ($nome in 'fonte.tar','execucoes.json') {
        $arquivo = Join-Path $trabalho $nome
        if (Test-Path -LiteralPath $arquivo) { Remove-Item -LiteralPath $arquivo }
    }
    if (Test-Path -LiteralPath $trabalho) { [IO.Directory]::Delete($trabalho) }
    $trava.Dispose()
}

exit 0
