function Get-Kan16Lote([string]$Raiz, [switch]$Extremos) {
    $lote = @(Import-Csv -LiteralPath (Join-Path $Raiz 'evidencias/KAN-14/lote.csv'))
    $auditoria = @(Import-Csv -LiteralPath (Join-Path $Raiz 'evidencias/KAN-10/commits.csv'))
    if (($lote.posicao -join ',') -cne '1,26,50,75,100' -or
        @($lote.sha | Sort-Object -Unique).Count -ne $lote.Count) {
        throw 'Recorte ou ordem divergente da KAN-14.'
    }
    foreach ($linha in $lote) {
        $commit = @($auditoria | Where-Object commit_sha -CEQ $linha.sha)
        if ($linha.sha -cnotmatch '\A[0-9a-f]{40}\z' -or $commit.Count -ne 1 -or
            $commit[0].position -ne $linha.posicao) {
            throw "FK ou posição divergente da KAN-10: $($linha.sha)."
        }
    }

    $manifesto = $null
    $ref = 'resultados/KAN-14/execucoes.json'
    if ($Extremos) {
        $ref = 'evidencias/KAN-14/lote.csv'
        $lote = @($lote[0], $lote[4])
    } else {
        if (!(Test-Path -LiteralPath (Join-Path $Raiz $ref) -PathType Leaf)) {
            $ref = 'evidencias/KAN-14/execucoes.json'
        }
        $manifesto = Get-Content -LiteralPath (Join-Path $Raiz $ref) -Raw | ConvertFrom-Json -DateKind String
        $selecionadas = @($manifesto.selecionadas)
        if (($selecionadas.posicao -join ',') -cne ($lote.posicao -join ',') -or
            ($selecionadas.sha -join ',') -cne ($lote.sha -join ',')) {
            throw 'O manifesto ainda não confirma as cinco referências na ordem aprovada.'
        }
    }

    for ($i = 0; $i -lt $lote.Count; $i++) {
        $linha = $lote[$i]
        $registro = if ($manifesto) { $selecionadas[$i] }
        $id = if ($manifesto) { $registro.tentativa } else { $linha.tentativa_reutilizada }
        if ($id -cnotmatch '\A[0-9]{8}T[0-9]{9}Z-[0-9a-f]{32}\z' -or
            ($linha.tentativa_reutilizada -and $id -cne $linha.tentativa_reutilizada) -or
            $linha.origem -cnotin 'KAN-13','KAN-14') {
            throw "Referência inválida na posição $($linha.posicao)."
        }
        $diretorio = "resultados/$($linha.origem)/$($linha.sha)/$id"
        if ($manifesto) {
            $historico = @($manifesto.tentativas | Where-Object { $_.sha -ceq $linha.sha -and $_.tentativa -ceq $id })
            if ($registro.ambiente -cne "$diretorio/ambiente.json" -or $registro.maven_log -cne "$diretorio/maven.log" -or
                $registro.surefire -cne "$diretorio/surefire/" -or $historico.Count -ne 1 -or
                ($historico[0] | ConvertTo-Json -Compress) -cne ($registro | ConvertTo-Json -Compress) -or
                $registro.status -cnotin 'suite_aprovada','suite_com_falhas') {
                throw "Proveniência divergente no manifesto: $id."
            }
        }
        [pscustomobject]@{
            posicao = [int]$linha.posicao; sha = $linha.sha; id = $id; diretorio = $diretorio
            manifesto_ref = $ref; registro = $registro
        }
    }
}
