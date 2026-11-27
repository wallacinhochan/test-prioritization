"""Reconcilia eventos Jupiter e XML do Surefire com cobertura explícita."""

import argparse
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from validar import decodificar, validar


TICK_NS = 10_000_000
COMPARABLE = "org.apache.commons.lang3.compare.ComparableUtilsTest"
# Rótulos @DisplayName de ComparableUtilsTest nas árvores auditadas 49 e 50.
COMPARABLE_ALIASES = {
    "B is 0 (B < A)": "B_is_0",
    "B is 1 (B = A)": "B_is_1",
    "B is 10 (B > A)": "B_is_10",
    "C is 0 ([B=C] < A)": "B_is_0$C_is_0",
    "C is 1 (B < A = C)": "B_is_0$C_is_1",
    "C is 10 (B < A < C)": "B_is_0$C_is_10",
    "C is 0 (B = A > C)": "B_is_1$C_is_0",
    "C is 1 (B = A = C)": "B_is_1$C_is_1",
    "C is 10 (B = A < C)": "B_is_1$C_is_10",
    "C is 0 (B > A > C)": "B_is_10$C_is_0",
    "C is 1 (B > A = C)": "B_is_10$C_is_1",
    "C is 10 ([B,C] > A)": "B_is_10$C_is_10",
}


def uptime_ns(valor):
    return int(Decimal(valor) * 1_000_000_000)


def alinhar(rastro, marcos, fim_plano):
    ancoras = [linha.split("\t") for linha in rastro.read_text().splitlines()]
    if [a[0] for a in ancoras] != ["start", "finish"]:
        raise ValueError("esperadas duas âncoras do mesmo plano")
    if not int(ancoras[0][3]) <= fim_plano <= int(ancoras[1][1]):
        raise ValueError("âncoras fora dos limites do plano")
    inferior, superior = [], []
    for _, antes, uptime, depois in ancoras:
        if not 0 <= int(antes) <= int(depois):
            raise ValueError("intervalo de amostragem da âncora inválido")
        inferior.append(uptime_ns(uptime) - int(depois))
        superior.append(uptime_ns(uptime) + TICK_NS - int(antes))
    minimo, maximo = max(inferior), min(superior)
    fases = [(k, uptime_ns(v)) for k, v in
             (linha.split("\t") for linha in marcos.read_text().splitlines())]
    if [k for k, _ in fases] != ["prepare_start", "runner_start",
                                 "reports_start", "reports_finish"]:
        raise ValueError("marcos do executor incompletos")
    preparo, runner, relatorios, fim = (v for _, v in fases)
    if not (preparo <= runner <= minimo < maximo
            and maximo + fim_plano <= relatorios + TICK_NS <= fim + TICK_NS):
        raise ValueError("relógios incompatíveis ou plano fora da fase runner")
    return {"plan_origin_lower_ns": minimo - preparo - TICK_NS,
            "plan_origin_upper_ns": maximo - preparo,
            "plan_origin_interval_width_ns": maximo - minimo + TICK_NS,
            "prepare_ms": (runner - preparo) // 1_000_000,
            "runner_ms": (relatorios - runner) // 1_000_000,
            "reports_ms": (fim - relatorios) // 1_000_000,
            "wall_ms": (fim - preparo) // 1_000_000}


def descritor(uid, fonte, ignorado=False):
    terminal = uid.rsplit("/", 1)[-1]
    if not fonte:
        return None
    classe, metodo = fonte.split("#", 1)
    # MethodSource pode nomear a classe declaradora de método herdado.
    executores = re.findall(r"\[(class|nested-class):([^\]]+)\]", uid)
    if executores:
        classe = executores[0][1] + "".join("$" + nome for _, nome in executores[1:])
    nome, tipos = metodo[:-1].split("(", 1)
    parametros = [t.strip() for t in tipos.split(",")] if tipos else []
    test_id = f"{classe}#{nome}({','.join(parametros)})"
    invocacao = re.fullmatch(r"\[test-template-invocation:#(\d+)\]", terminal)
    dinamico = re.fullmatch(r"\[dynamic-test:#(\d+)\]", terminal)
    if dinamico and "/[test-factory:" in uid and "/[dynamic-container:" not in uid:
        nome = f"{nome}({tipos})[{dinamico[1]}]"
    elif invocacao or (ignorado and terminal.startswith("[test-template:")):
        simples = ", ".join(t.rsplit(".", 1)[-1] for t in parametros)
        nome = f"{nome}({simples})" + (f"[{invocacao[1]}]" if invocacao else "")
    elif not terminal.startswith("[method:"):
        return None
    return (classe, nome), test_id


def eventos_por_caso(rastro):
    inicios = {}
    casos = defaultdict(list)
    lacunas = Counter()
    with rastro.open(encoding="utf-8", newline="") as arquivo:
        for r in csv.DictReader(arquivo, delimiter="\t"):
            evento = r["event"]
            uid = decodificar(r["unique_id_b64"])
            if evento == "start":
                inicios[uid] = (int(r["seq"]), int(r["ns"]))
            if evento not in {"finish", "skip"}:
                continue
            descrito = descritor(uid, decodificar(r["source_b64"]), evento == "skip")
            if descrito is None:
                terminal = uid.rsplit("/", 1)[-1]
                if terminal.startswith(("[dynamic-test:", "[test-template-invocation:")):
                    lacunas["unsupported_leaf_events"] += 1
                continue
            chave, metodo = descrito
            inicio = inicios.get(uid)
            estado = {"SUCCESSFUL": "pass", "FAILED": "fail", "ABORTED": "skip",
                      "": "skip"}["" if evento == "skip" else decodificar(r["detail_b64"])]
            casos[chave].append({"method": metodo, "outcome": estado, "junit_unique_id": uid,
                                 "start_seq": inicio[0] if inicio else None,
                                 "start_ns": inicio[1] if inicio else None,
                                 "end_ns": int(r["ns"]) if inicio else None})
    return casos, lacunas


def xml_por_caso(pasta):
    casos = defaultdict(list)
    for caminho in sorted(pasta.glob("TEST-*.xml")):
        for i, caso in enumerate(ET.parse(caminho).getroot().findall("testcase"), 1):
            estado = "pass"
            if caso.find("skipped") is not None:
                estado = "skip"
            elif caso.find("failure") is not None or caso.find("error") is not None:
                estado = "fail"
            classe = caso.attrib["classname"]
            if caminho.name == f"TEST-{COMPARABLE}.xml" and classe in COMPARABLE_ALIASES:
                classe = f"{COMPARABLE}$A_is_1${COMPARABLE_ALIASES[classe]}"
            chave = (classe, caso.attrib["name"])
            casos[chave].append((estado, caminho.name, i, caso.get("time")))
    return casos


def reconciliar(pasta):
    rastro = pasta / "eventos.tsv"
    plano = validar(rastro)
    relogio = alinhar(pasta / "eventos.tsv.clock.tsv", pasta / "marcos.tsv",
                     plano["plan_elapsed_ns"])
    eventos, lacunas = eventos_por_caso(rastro)
    casos = xml_por_caso(pasta / "surefire-reports")
    invocacoes = []
    metodos = defaultdict(list)
    xml_sem_par_por_classe = Counter()
    for chave in sorted(casos.keys() | eventos.keys()):
        xml, junit = casos.get(chave, ()), eventos.get(chave, ())
        if len(xml) != 1 or len(junit) != 1 or xml[0][0] != junit[0]["outcome"]:
            lacunas["unmatched_xml_cases"] += len(xml)
            lacunas["unmatched_described_events"] += len(junit)
            if xml:
                xml_sem_par_por_classe[chave[0]] += len(xml)
            continue
        _, arquivo, indice, segundos = xml[0]
        linha = {**junit[0], "xml": arquivo, "testcase_index": indice, "xml_seconds": segundos}
        invocacoes.append(linha)
        metodos[linha["method"]].append(linha)
    ordenados = sorted((min(r["start_seq"] for r in linhas if r["start_seq"] is not None), m)
                       for m, linhas in metodos.items()
                       if any(r["start_seq"] is not None for r in linhas))
    agregados = []
    for ordem, (primeiro, metodo) in enumerate(ordenados, 1):
        linhas = metodos[metodo]
        executadas = [r for r in linhas if r["outcome"] != "skip"]
        duracoes = [r["end_ns"] - r["start_ns"] for r in executadas]
        duracao = sum(duracoes) if duracoes else None
        desfecho = "fail" if any(r["outcome"] == "fail" for r in linhas) else (
            "pass" if executadas else "skip")
        agregados.append({"test_id": metodo, "matched_cases": len(linhas),
                          "first_start_seq": primeiro, "matched_execution_order": ordem,
                          "matched_outcome": desfecho,
                          "matched_duration_ns": duracao,
                          "matched_duration_ms": (duracao + 500_000) // 1_000_000
                          if duracao is not None else None})
    for metodo in sorted(metodos.keys() - {linha["test_id"] for linha in agregados}):
        agregados.append({"test_id": metodo, "matched_cases": len(metodos[metodo]),
                          "first_start_seq": None, "matched_execution_order": None,
                          "matched_outcome": "skip", "matched_duration_ns": None,
                          "matched_duration_ms": None})
    hashes = {str(c.relative_to(pasta)).replace("\\", "/"): hashlib.sha256(c.read_bytes()).hexdigest()
              for c in sorted(pasta.rglob("*")) if c.is_file()}
    resumo = {"events": plano["events"], "xml_cases": sum(map(len, casos.values())),
              "xml_outcomes": Counter(linha[0] for linhas in casos.values() for linha in linhas),
              "matched_cases": len(invocacoes), "matched_outcomes": Counter(
                  r["outcome"] for r in invocacoes), "methods_with_start": len(ordenados),
              "methods_with_duration": sum(r["matched_duration_ns"] is not None for r in agregados),
              "matched_method_duration_ns": sum(r["matched_duration_ns"] or 0 for r in agregados),
              "methods_skip_only_without_start": len(metodos) - len(ordenados),
              "gaps": dict(lacunas), "unmatched_xml_by_class": xml_sem_par_por_classe,
              "clock": relogio, "sha256": hashes}
    log = pasta.parent / "maven.log"
    if log.is_file():
        texto = log.read_text(encoding="utf-8-sig", errors="replace")
        totais = re.findall(r"Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)", texto)
        if totais:
            resumo["maven_totals"] = dict(zip(("tests", "failures", "errors", "skipped"),
                                             map(int, totais[-1])))
        resumo["maven_log_sha256"] = hashlib.sha256(log.read_bytes()).hexdigest()
    return resumo, invocacoes, agregados


def exportar_kan15(saida, resumo, metodos, sha, fonte):
    totais = resumo.get("maven_totals", {})
    xml = resumo["xml_outcomes"]
    if (resumo["gaps"] or resumo["matched_cases"] != resumo["xml_cases"]
            or resumo["xml_cases"] == 0 or totais.get("tests") != resumo["xml_cases"]
            or totais.get("skipped") != xml.get("skip", 0)
            or xml.get("fail", 0) != totais["errors"] + totais["failures"]):
        raise ValueError("T0 incompleto ou totais Maven/XML/rastro divergentes")
    if not re.fullmatch("[0-9a-f]{40}", sha):
        raise ValueError("SHA da tentativa inválido")
    with (saida / "t0_results.csv").open("x", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(("commit_sha", "scenario", "test_id", "outcome", "duration_ms",
                            "execution_order", "source_ref"))
        for r in metodos:
            escritor.writerow((sha, "T0", r["test_id"], r["matched_outcome"],
                                r["matched_duration_ms"], r["matched_execution_order"], fonte))
    with (saida / "t0_runs.csv").open("x", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(("commit_sha", "scenario", "run_status", "suite_duration_ms", "source_ref"))
        escritor.writerow((sha, "T0", "complete", resumo["clock"]["wall_ms"], fonte))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidencia", type=Path)
    parser.add_argument("saida", type=Path)
    parser.add_argument("--kan15-source-ref")
    args = parser.parse_args()
    resumo, invocacoes, metodos = reconciliar(args.evidencia)
    args.saida.mkdir()
    for nome, dados in (("resumo", resumo), ("invocacoes", invocacoes), ("metodos", metodos)):
        (args.saida / f"{nome}.json").write_text(json.dumps(dados, indent=2) + "\n", encoding="utf-8")
    if args.kan15_source_ref:
        tentativa = json.loads((args.evidencia.parent / "tentativa.json").read_text(encoding="utf-8-sig"))
        if tentativa["exit_code"] != 0:
            raise ValueError("a exportação desta coleta exige código zero no executor")
        exportar_kan15(args.saida, resumo, metodos, tentativa["sha"], args.kan15_source_ref)
        (args.saida / "contrato.json").write_text(
            '{"contract_version":"0.1.0","data_kind":"instrumented_technical_t0"}\n',
            encoding="utf-8")
