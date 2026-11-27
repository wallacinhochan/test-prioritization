"""Gera datasets de treino balanceados a partir de entrega-replay/dados/metodos.csv.

Usa as funções de comparar_balanceamento.py (mesma pasta), as mesmas da comparação.
Uso (de dentro de entrega-replay):
    python balancear_dataset.py --dados dados --saida dados-balanceados [--estrategia ponderacao] [--razao 1.0] [--seed 20261122]

Sem --estrategia: grava treino_<estrategia>.csv para todas. Com --estrategia: grava só treino_balanceado.csv.
Colunas: as de metodos.csv + `peso` (1.0 salvo na ponderação) + `sintetico` (1 nas linhas criadas por SMOTE).
Só o treino (posições 15, 26, 42; selecionado_t1 == 1; alvo conhecido) é balanceado; a validação não é alterada.
"""
import argparse
import json
from pathlib import Path

import pandas as pd

import comparar_balanceamento as cb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dados', required=True)
    ap.add_argument('--saida', required=True)
    ap.add_argument('--razao', type=float, default=1.0, help='positivos/negativos desejado (over/under/SMOTE)')
    ap.add_argument('--seed', type=int, default=cb.SEED)
    ap.add_argument('--estrategia', choices=cb.ESTRATEGIAS,
                    help='exporta só esta estratégia, como treino_balanceado.csv')
    a = ap.parse_args()

    metodos, _ = cb.carregar(a.dados)
    treino, _ = cb.particionar(metodos)
    saida = Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)
    conta = lambda d: {'linhas': int(len(d)), 'zeros': int((d.alvo == 0).sum()), 'positivos': int((d.alvo > 0).sum())}
    resumo = {'seed': a.seed, 'razao': a.razao, 'origem': 'metodos.csv', 'antes': conta(treino), 'estrategias': {}}
    for e in ((a.estrategia,) if a.estrategia else cb.ESTRATEGIAS):
        out, peso, cfg = cb.balancear(treino, e, seed=a.seed, razao=a.razao)
        out = out.assign(peso=peso, sintetico=out.test_id.str.startswith('sintetico#').astype(int))
        nome = 'treino_balanceado.csv' if a.estrategia else f'treino_{e}.csv'
        out.to_csv(saida / nome, index=False, lineterminator='\n')
        cfg = {k: v for k, v in cfg.items() if k not in ('antes', 'seed')}
        resumo['estrategias'][e] = {**cfg, 'depois': conta(out)}
        print(e, resumo['estrategias'][e])
    (saida / 'balanceamento.json').write_text(json.dumps(resumo, indent=2))


if __name__ == '__main__':
    main()