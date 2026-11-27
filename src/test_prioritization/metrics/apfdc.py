"""APFDc com peso unitário por método falho."""


def apfdc(ordens, selecionados, resultados, falhas):
    motivo = None
    medidas = None
    falhas_selecionadas = None
    if falhas is None:
        motivo = "oraculo_incompleto"
    elif selecionados is None:
        motivo = "selecao_indisponivel"
    else:
        falhas_selecionadas = selecionados & falhas
        if not selecionados <= resultados.keys():
            motivo = "populacao_nao_comparavel"
        elif any(ordem is None for ordem in ordens.values()):
            motivo = "ordem_indisponivel"
        elif not falhas_selecionadas:
            motivo = "sem_falhas_na_populacao"
        else:
            custos = {t: resultados[t][1] for t in selecionados
                      if resultados[t][0] != "skip"}
            if None in custos.values():
                motivo = "duracao_indisponivel"
            elif sum(custos.values()) == 0:
                motivo = "custo_total_zero"
            else:
                medidas = {}
                total = sum(custos.values())
                for cenario, ordem in ordens.items():
                    tempo = numerador_dobrado = 0
                    for teste in ordem:
                        custo = custos.get(teste, 0)
                        if teste in falhas_selecionadas:
                            numerador_dobrado += 2 * (total - tempo) - custo
                        tempo += custo
                    medidas[cenario] = numerador_dobrado / (2 * total * len(falhas_selecionadas))
    return {
        "apfdc": medidas,
        "motivo": motivo,
        "falhas_selecionadas": len(falhas_selecionadas) if falhas_selecionadas is not None else None,
        "falhas_excluidas": len(falhas - selecionados) if falhas_selecionadas is not None else None,
    }
