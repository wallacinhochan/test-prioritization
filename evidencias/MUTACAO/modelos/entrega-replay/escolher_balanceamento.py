"""Compara estratégias de balanceamento e registra a escolha.

Regra de decisão (fixada ANTES de executar):
  - Orçamento principal: 50% do tempo-base T0 (média histórica das revisões de treino).
  - Folds: (a) oficial: treino 15/26/42 -> validação 50;
           (b) desenvolvimento: deixa uma de {15,26,42} de fora, treina nas outras duas.
  - Métrica de decisão: soma, nos 4 folds, de mutantes detectados no orçamento principal,
    média sobre N sementes (balanceamento e Random Forest variam juntos).
  - Desempate: menor posto médio da primeira detecção; depois menor overhead.
  - A estratégia escolhida precisa superar a baseline; senão, mantém-se a baseline (sem balancear).
  - Modelos: Random Forest e KNN (StandardScaler + 15 vizinhos). O KNN do scikit-learn não aceita
    sample_weight; por isso a ponderação só se aplica à Random Forest.
Uso: python escolher_balanceamento.py --dados dados --saida registro-balanceamento [--sementes 10]
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import comparar_balanceamento as cb

ESTR = cb.ESTRATEGIAS
ORC = 0.50
FOLDS = [('oficial: teste 50', (15, 26, 42), 50), ('dev: teste 15', (26, 42), 15),
         ('dev: teste 26', (15, 42), 26), ('dev: teste 42', (15, 26), 42)]


def novo_modelo(modelo, seed):
    if modelo == 'knn':
        return make_pipeline(StandardScaler(), KNeighborsRegressor(n_neighbors=15, weights='uniform', metric='euclidean'))
    return RandomForestRegressor(n_estimators=200, min_samples_leaf=5, max_features=1.0, random_state=seed, n_jobs=1)


def rodar(m, obs, tr_pos, te_pos, estrategia, seed, razao, modelo='rf'):
    sel = m[m.selecionado_t1 == 1]
    treino = sel[sel.posicao.isin(tr_pos) & sel.alvo.notna()].reset_index(drop=True)
    teste = sel[sel.posicao == te_pos].reset_index(drop=True)
    t0 = time.perf_counter()
    bal, w, _ = cb.balancear(treino, estrategia, seed=seed, razao=razao)
    rf = novo_modelo(modelo, seed)
    if modelo == 'rf':
        rf.fit(bal[cb.FEATURES].to_numpy(), bal.alvo.to_numpy(), sample_weight=w)
    else:
        rf.fit(bal[cb.FEATURES].to_numpy(), bal.alvo.to_numpy())
    escore = rf.predict(teste[cb.FEATURES].to_numpy())
    ovh = (time.perf_counter() - t0) * 1000
    rk = (teste[['test_id']].assign(escore=escore)
          .sort_values(['escore', 'test_id'], ascending=[False, True], kind='mergesort').reset_index(drop=True))
    base = float(sel[sel.posicao.isin(tr_pos)].groupby('posicao').duracao_intacto_ms.sum().mean())
    limites = {p: base * p for p in cb.ORCAMENTOS}
    sha = m[m.posicao == te_pos].sha.iloc[0]
    intacto = m[m.posicao == te_pos].set_index('test_id').duracao_intacto_ms.to_dict()
    res, _ = cb.detectar(rk, obs[obs.sha == sha], intacto, ovh, list(limites.values()))
    pos_rank = {t: i for i, t in enumerate(rk.test_id)}
    ranks = []
    for mid, g in obs[obs.sha == sha].groupby('mutation_id'):
        f = g[g.label == 'induced_failure'].test_id.map(pos_rank)
        if len(f):
            ranks.append(int(f.min()) + 1)
    linha = {f'det_{int(p*100)}': sum(r[l] == 'detectado' for r in res.values()) for p, l in limites.items()}
    linha.update(mutantes=len(res), posto_medio=float(np.mean(ranks)) if ranks else np.nan, overhead_ms=ovh)
    return linha


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dados', required=True)
    ap.add_argument('--saida', required=True)
    ap.add_argument('--sementes', type=int, default=10)
    ap.add_argument('--razao', type=float, default=1.0)
    a = ap.parse_args()
    m, obs = cb.carregar(a.dados)
    linhas = []
    for modelo in ('rf', 'knn'):
        for nome, tr, te in FOLDS:
            for e in ESTR:
                if modelo == 'knn' and e == 'ponderacao':
                    continue  # KNeighborsRegressor.fit não aceita sample_weight
                for sd in range(a.sementes if modelo == 'rf' or e != 'baseline' else 1):
                    linhas.append({'modelo': modelo, 'fold': nome, 'estrategia': e, 'semente': cb.SEED + sd,
                                   **rodar(m, obs, tr, te, e, cb.SEED + sd, a.razao, modelo)})
    df = pd.DataFrame(linhas)
    cols = ['det_25', 'det_50', 'det_75', 'posto_medio', 'overhead_ms']
    por_fold = df.groupby(['modelo', 'fold', 'estrategia'], sort=False)[cols].mean()
    resumo = df.groupby(['modelo', 'estrategia'], sort=False)[['posto_medio', 'overhead_ms']].mean()
    for c in ('det_25', 'det_50', 'det_75'):
        resumo[c + '_total'] = df.groupby(['modelo', 'estrategia', 'semente'])[c].sum().groupby(['modelo', 'estrategia']).mean()
        resumo[c + '_dp'] = df.groupby(['modelo', 'estrategia', 'semente'])[c].sum().groupby(['modelo', 'estrategia']).std()
    escolhidas = {}
    for modelo in ('rf', 'knn'):
        r = resumo.loc[modelo]
        base50 = r.loc['baseline', 'det_50_total']
        cand = r.drop('baseline')
        cand = cand[cand.det_50_total > base50]
        escolhidas[modelo] = 'baseline' if cand.empty else cand.sort_values(
            ['det_50_total', 'posto_medio', 'overhead_ms'], ascending=[False, True, True]).index[0]
    saida = Path(a.saida); saida.mkdir(parents=True, exist_ok=True)
    df.to_csv(saida / 'execucoes.csv', index=False)
    por_fold.round(2).to_csv(saida / 'por_fold.csv')
    resumo.round(2).to_csv(saida / 'resumo.csv')
    reg = {'regra': __doc__.split('Uso:')[0].strip(), 'sementes': a.sementes, 'razao': a.razao,
           'resumo': {f'{k[0]}|{k[1]}': v for k, v in json.loads(resumo.round(3).to_json(orient='index')).items()} if False else
                     {f'{mo}|{es}': {c: round(float(v), 3) for c, v in row.items()} for (mo, es), row in resumo.iterrows()},
           'escolhida_por_regra': escolhidas}
    (saida / 'decisao.json').write_text(json.dumps(reg, indent=2, ensure_ascii=False))
    pd.set_option('display.width', 200)
    print(por_fold.round(2).to_string()); print()
    print(resumo.round(2).to_string()); print('\nESCOLHIDA (regra literal):', escolhidas)


if __name__ == '__main__':
    main()