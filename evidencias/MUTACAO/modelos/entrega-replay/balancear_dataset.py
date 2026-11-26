"""Gera datasets de treino balanceados a partir de entrega-replay/dados/metodos.csv.

Uso (de dentro de entrega-replay):
    python balancear_dataset.py --dados dados --saida dados-balanceados [--razao 1.0] [--seed 20261122]

Saídas (uma por estratégia), mesmas colunas de metodos.csv + coluna `peso`:
    treino_baseline.csv, treino_ponderacao.csv, treino_oversampling.csv, treino_undersampling.csv
    balanceamento.json   (semente, razões, pesos e contagens antes/depois)
Somente o treino (posições 15, 26, 42; selecionado_t1 == 1; alvo conhecido) é balanceado.
A validação (posição 50) NÃO é alterada. O alvo contínuo é preservado.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

TREINO = (15, 26, 42)


def contagem(df):
    return {'linhas': int(len(df)), 'zeros': int((df.alvo == 0).sum()), 'positivos': int((df.alvo > 0).sum())}


def balancear(treino, estrategia, seed, razao):
    rng = np.random.default_rng(seed)
    pos = np.flatnonzero((treino.alvo > 0).to_numpy())
    neg = np.flatnonzero((treino.alvo == 0).to_numpy())
    peso = np.ones(len(treino))
    cfg = {}
    if estrategia == 'baseline':
        idx = np.arange(len(treino))
    elif estrategia == 'ponderacao':
        cfg['peso_positivo'] = len(neg) / len(pos)
        peso[pos] = cfg['peso_positivo']
        idx = np.arange(len(treino))
    elif estrategia == 'oversampling':
        n = int(round(razao * len(neg)))
        idx = np.concatenate([np.arange(len(treino)), rng.choice(pos, max(n - len(pos), 0), replace=True)])
        cfg['razao_pos_neg'] = razao
    elif estrategia == 'undersampling':
        n = min(int(round(len(pos) / razao)), len(neg))
        idx = np.sort(np.concatenate([pos, rng.choice(neg, n, replace=False)]))
        cfg['razao_pos_neg'] = razao
    else:
        raise ValueError(estrategia)
    out = treino.iloc[idx].assign(peso=peso[idx]).reset_index(drop=True)
    return out, cfg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dados', required=True)
    ap.add_argument('--saida', required=True)
    ap.add_argument('--razao', type=float, default=1.0, help='positivos/negativos desejado (over/undersampling)')
    ap.add_argument('--seed', type=int, default=20261122)
    ap.add_argument('--estrategia', choices=('baseline', 'ponderacao', 'oversampling', 'undersampling'),
                    help='exporta só esta estratégia, como treino_balanceado.csv (a escolhida)')
    a = ap.parse_args()

    m = pd.read_csv(Path(a.dados) / 'metodos.csv')
    t = m[(m.selecionado_t1 == 1) & m.posicao.isin(TREINO) & m.alvo.notna()].reset_index(drop=True)
    saida = Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)
    resumo = {'seed': a.seed, 'razao': a.razao, 'origem': 'metodos.csv', 'antes': contagem(t), 'estrategias': {}}
    for e in ((a.estrategia,) if a.estrategia else ('baseline', 'ponderacao', 'oversampling', 'undersampling')):
        out, cfg = balancear(t, e, a.seed, a.razao)
        nome = 'treino_balanceado.csv' if a.estrategia else f'treino_{e}.csv'
        out.to_csv(saida / nome, index=False, lineterminator='\n')
        resumo['estrategias'][e] = {**cfg, 'depois': contagem(out)}
        print(e, contagem(out), cfg)
    (saida / 'balanceamento.json').write_text(json.dumps(resumo, indent=2))


if __name__ == '__main__':
    main()