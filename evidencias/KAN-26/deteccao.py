"""Métricas da RQ2 a partir dos eventos de conclusão da KAN-23."""


def deteccao(corte, falhas):
    registro = dict(corte)
    contagem = proporcao = primeira = curva = None
    motivo = None
    if corte["status"] == "unavailable":
        motivo = corte["gap"]["reason"]
    elif falhas is None:
        motivo = "oraculo_incompleto"
    else:
        limite = corte["budget_ms"]
        if limite is None:
            raise ValueError("corte disponível sem orçamento")
        pontos = {0: 0}
        vistos = set()
        tempo_anterior = 0
        for evento in corte["prefix"]:
            teste = evento["test_id"]
            tempo = evento["completed_at_ms"]
            if teste in vistos or not tempo_anterior <= tempo <= limite:
                raise ValueError("prefixo com evento repetido ou tempo fora do corte")
            vistos.add(teste)
            tempo_anterior = tempo
            if (evento["outcome"] == "fail") != (teste in falhas):
                raise ValueError("desfecho do prefixo diverge do oráculo")
            if teste in falhas:
                pontos[tempo] = pontos.get(tempo, 0) + 1
                if primeira is None:
                    primeira = tempo
        pontos.setdefault(limite, 0)
        contagem = 0
        curva = []
        for tempo, novas in sorted(pontos.items()):
            contagem += novas
            curva.append({"tempo_ms": tempo, "detectadas": contagem,
                          "proporcao": contagem / len(falhas) if falhas else None})
        proporcao = contagem / len(falhas) if falhas else None
    registro.update({
        "falhas_t0": len(falhas) if falhas is not None else None,
        "detectadas": contagem,
        "proporcao": proporcao,
        "primeira_falha_ms": primeira,
        "estado_primeira_falha": ("indisponivel" if motivo else
                                 "nao_observada" if primeira is None else "observada"),
        "curva": curva,
        "motivo": motivo,
    })
    return registro
