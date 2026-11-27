"""Valida o rastro de um plano JUnit serial e resume os eventos observados."""

import base64
import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


def decodificar(valor):
    return base64.b64decode(valor, validate=True).decode("utf-8")


def conciliar_classe(arquivo, xml):
    """Concilia métodos e templates do piloto com o relatório do Surefire."""
    observados = Counter()
    identidades = {}
    with arquivo.open(encoding="utf-8", newline="") as entrada:
        for linha in csv.DictReader(entrada, delimiter="\t"):
            fonte = decodificar(linha["source_b64"])
            if not fonte or linha["event"] not in {"finish", "skip"}:
                continue
            terminal = decodificar(linha["unique_id_b64"]).rsplit("/", 1)[-1]
            invocacao = re.fullmatch(r"\[test-template-invocation:#(\d+)\]", terminal)
            classe, metodo = fonte.split("#", 1)
            nome, parametros = metodo[:-1].split("(", 1)
            if invocacao:
                tipos = ", ".join(p.strip().rsplit(".", 1)[-1] for p in parametros.split(","))
                nome = f"{nome}({tipos})[{invocacao[1]}]"
            elif not terminal.startswith("[method:"):
                continue
            chave = (classe, nome)
            if identidades.setdefault(chave, fonte) != fonte:
                raise ValueError(f"identidade ambígua no relatório: {chave}")
            estado = ("SKIPPED" if linha["event"] == "skip"
                      else decodificar(linha["detail_b64"]))
            observados[chave, estado] += 1
    esperados = Counter()
    for caso in ET.parse(xml).getroot().findall("testcase"):
        chave = (caso.attrib["classname"], caso.attrib["name"])
        if caso.find("skipped") is not None:
            estado = "SKIPPED"
        elif caso.find("failure") is not None or caso.find("error") is not None:
            estado = "FAILED"
        else:
            estado = "SUCCESSFUL"
        esperados[chave, estado] += 1
    if not esperados or esperados != observados:
        raise ValueError("rastro e XML da classe divergem por método ou desfecho")
    return dict(Counter(estado for (_, estado) in esperados.elements()))


def validar(arquivo):
    with arquivo.open(encoding="utf-8", newline="") as entrada:
        linhas = list(csv.DictReader(entrada, delimiter="\t"))
    eventos = [r["event"] for r in linhas]
    if (eventos[:1] != ["plan_start"] or eventos[-1:] != ["plan_finish"]
            or set(eventos[1:-1]) - {"register", "start", "finish", "skip"}):
        raise ValueError("esperado um plano fechado")
    ativos = {}
    vistos = set()
    fontes = {}
    metodos = {}
    anterior = -1
    ignorados = 0
    dinamicos = 0
    for seq, linha in enumerate(linhas, 1):
        ns = int(linha["ns"])
        if int(linha["seq"]) != seq or ns < anterior:
            raise ValueError("sequência ou relógio inválido")
        anterior = ns
        evento = linha["event"]
        uid = decodificar(linha["unique_id_b64"])
        fonte = decodificar(linha["source_b64"])
        detalhe = decodificar(linha["detail_b64"])
        if fonte:
            fontes[uid] = fonte
        if evento == "register":
            dinamicos += 1
        # Eventos de contêiner não são invocações. Templates, fábricas e
        # filhos dinâmicos permanecem no rastro para conciliação posterior.
        if evento == "start":
            if uid in vistos or any(not uid.startswith(pai + "/") for pai in ativos):
                raise ValueError("invocações duplicadas ou sobrepostas")
            ativos[uid] = ns
            vistos.add(uid)
            if fonte:
                metodos.setdefault(fonte, {"first_start_seq": seq, "first_start_ns": ns})
        elif evento == "finish":
            if (not ativos or uid != next(reversed(ativos))
                    or detalhe not in {"SUCCESSFUL", "ABORTED", "FAILED"}):
                raise ValueError("conclusão sem início correspondente ou fora da pilha")
            ativos.pop(uid)
        elif evento == "skip":
            ignorados += 1
    if ativos or not fontes or not metodos:
        raise ValueError("rastro incompleto ou sem métodos identificáveis")
    return {"plan_elapsed_ns": anterior, "events": len(linhas), "skip_events": ignorados,
            "dynamic_registrations": dinamicos, "method_source_starts": metodos}


if __name__ == "__main__":
    rastro = Path(sys.argv[1])
    resumo = validar(rastro)
    if len(sys.argv) == 3:
        resumo["matched_xml_outcomes"] = conciliar_classe(rastro, Path(sys.argv[2]))
    print(json.dumps(resumo, indent=2))
