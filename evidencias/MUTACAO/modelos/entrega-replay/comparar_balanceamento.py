"""Compara estratégias de balanceamento da Random Forest sobre os CSVs de entrega-replay.

Estratégias: baseline, ponderacao, oversampling, undersampling.
Treino: posições 15/26/42 (selecionado_t1 == 1, alvo conhecido).
Avaliação: posição 50, ranking de todos os métodos T1, detecção de mutantes sob
orçamento de 25/50/75% de um tempo-base T0 histórico.

Uso (na raiz do repositório):
    python comparar_balanceamento.py --dados evidencias/MUTACAO/modelos/entrega-replay/dados
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

FEATURES = ['distancia_rota', 'rota_ausente', 'arestas_lexicais', 'classe_semente',
            'comprimento_nome', 'quantidade_parametros', 'classe_aninhada']
SEED = 20261122
ESTRATEGIAS = ('baseline', 'ponderacao', 'oversampling', 'undersampling')
ORCAMENTOS = (0.25, 0.50, 0.75)
POS_TREINO = (15, 26, 42)
POS_VALIDACAO = 50


# ---------------------------------------------------------------- dados
def carregar(pasta):
    pasta = Path(pasta)
    metodos = pd.read_csv(pasta / 'metodos.csv')
    obs = pd.read_csv(pasta / 'observacoes.csv')
    return metodos, obs


def particionar(metodos):
    sel = metodos[metodos.selecionado_t1 == 1]
    treino = sel[sel.posicao.isin(POS_TREINO) & sel.alvo.notna()].reset_index(drop=True)
    valid = sel[sel.posicao == POS_VALIDACAO].reset_index(drop=True)
    return treino, valid


# ---------------------------------------------------------- balanceamento
def balancear(treino, estrategia, seed=SEED, razao=1.0, peso_positivo=None):
    """Devolve (treino_balanceado, sample_weight, config).

    razao: positivos/negativos desejados após over/undersampling (1.0 = 50/50).
    peso_positivo: peso dos exemplos alvo>0 na ponderação (padrão: n_neg/n_pos).
    O alvo contínuo é preservado; só linhas são repetidas/removidas ou pesadas.
    """
    rng = np.random.default_rng(seed)
    pos = np.flatnonzero((treino.alvo > 0).to_numpy())
    neg = np.flatnonzero((treino.alvo == 0).to_numpy())
    cfg = {'estrategia': estrategia, 'seed': seed,
           'antes': {'zeros': int(len(neg)), 'positivos': int(len(pos))}}
    pesos = np.ones(len(treino))

    if estrategia == 'baseline':
        idx = np.arange(len(treino))
    elif estrategia == 'ponderacao':
        w = peso_positivo if peso_positivo is not None else len(neg) / len(pos)
        pesos[pos] = w
        idx = np.arange(len(treino))
        cfg['peso_positivo'] = float(w)
    elif estrategia == 'oversampling':
        n = int(round(razao * len(neg)))
        extra = rng.choice(pos, size=max(n - len(pos), 0), replace=True)
        idx = np.concatenate([np.arange(len(treino)), extra])
        cfg['razao'] = razao
    elif estrategia == 'undersampling':
        n = min(int(round(len(pos) / razao)), len(neg))
        keep = rng.choice(neg, size=n, replace=False)
        idx = np.sort(np.concatenate([pos, keep]))
        cfg['razao'] = razao
    else:
        raise ValueError(f'Estratégia desconhecida: {estrategia}')

    out = treino.iloc[idx].reset_index(drop=True)
    w_out = pesos[idx]
    cfg['depois'] = {'zeros': int((out.alvo == 0).sum()), 'positivos': int((out.alvo > 0).sum())}
    return out, w_out, cfg


# ------------------------------------------------------------------ modelo
def novo_modelo():
    return RandomForestRegressor(n_estimators=200, min_samples_leaf=5, max_features=1.0,
                                 random_state=SEED, n_jobs=1)


def treinar_e_ranquear(treino, valid, estrategia, **kw):
    t0 = time.perf_counter()
    bal, pesos, cfg = balancear(treino, estrategia, **kw)
    modelo = novo_modelo()
    modelo.fit(bal[FEATURES].to_numpy(), bal.alvo.to_numpy(), sample_weight=pesos)
    t_treino = time.perf_counter() - t0
    t1 = time.perf_counter()
    escore = modelo.predict(valid[FEATURES].to_numpy())
    ranking = (valid[['test_id']].assign(escore=escore)
               .sort_values(['escore', 'test_id'], ascending=[False, True], kind='mergesort')
               .reset_index(drop=True))
    t_rank = time.perf_counter() - t1
    cfg['tempo_treino_ms'] = t_treino * 1000
    cfg['tempo_ranking_ms'] = t_rank * 1000
    return ranking, cfg


# ----------------------------------------------------------- orçamento/tempo
def tempo_base_ms(metodos):
    """Média, nas revisões de treino, da soma de duracao_intacto_ms dos métodos T1.
    Usa só informação anterior à posição avaliada (15, 26, 42)."""
    sel = metodos[(metodos.selecionado_t1 == 1) & metodos.posicao.isin(POS_TREINO)]
    return float(sel.groupby('posicao').duracao_intacto_ms.sum().mean())


def detectar(ranking, obs_sha, intacto, overhead_ms, limites_ms):
    """Para cada mutante, o primeiro teste induced_failure concluído dentro de cada limite.

    Retorna {mutation_id: {limite: 'detectado'|'sem_deteccao'|'indeterminado'}}.
    Duração: duracao_ms do mutante; se ausente, cai em duracao_intacto_ms.
    Ausência de linha em observacoes conta como 'ausente' (indeterminado)."""
    ordem = ranking.test_id.to_numpy()
    resultado, fallback = {}, 0
    for mid, g in obs_sha.groupby('mutation_id'):
        rot = g.set_index('test_id')
        res = {}
        t, primeiro_ok, tempos, estados = overhead_ms, None, [], []
        for tid in ordem:
            if tid in rot.index:
                d, lab = rot.at[tid, 'duracao_ms'], rot.at[tid, 'label']
                if pd.isna(d):
                    d, fallback = intacto.get(tid, 0.0), fallback + 1
            else:
                d, lab = intacto.get(tid, 0.0), 'ausente'
                fallback += 1
            t += d
            tempos.append(t)
            estados.append(lab)
        tempos, estados = np.array(tempos), np.array(estados)
        for lim in limites_ms:
            dentro = tempos <= lim
            if (dentro & (estados == 'induced_failure')).any():
                res[lim] = 'detectado'
            elif (dentro & np.isin(estados, ['unknown', 'ausente'])).any():
                res[lim] = 'indeterminado'
            else:
                res[lim] = 'sem_deteccao'
        resultado[mid] = res
    return resultado, fallback


def avaliar(rankings, metodos, obs, overhead_extra_ms=0.0):
    base = tempo_base_ms(metodos)
    limites = {p: base * p for p in ORCAMENTOS}
    valid_sha = metodos[metodos.posicao == POS_VALIDACAO].sha.iloc[0]
    obs_sha = obs[obs.sha == valid_sha]
    intacto = (metodos[(metodos.posicao == POS_VALIDACAO)]
               .set_index('test_id').duracao_intacto_ms.to_dict())
    linhas = []
    for nome, (ranking, cfg) in rankings.items():
        overhead = cfg['tempo_treino_ms'] + cfg['tempo_ranking_ms'] + overhead_extra_ms
        res, fb = detectar(ranking, obs_sha, intacto, overhead, list(limites.values()))
        linha = {'estrategia': nome, 'overhead_ms': round(overhead, 1),
                 'mutantes': len(res), 'duracoes_substituidas': fb}
        for p, lim in limites.items():
            estados = [r[lim] for r in res.values()]
            linha[f'detectados_{int(p * 100)}'] = estados.count('detectado')
            linha[f'indeterminados_{int(p * 100)}'] = estados.count('indeterminado')
        linhas.append(linha)
    tab = pd.DataFrame(linhas)
    for p in ORCAMENTOS:
        col = f'detectados_{int(p * 100)}'
        tab[f'delta_{int(p * 100)}'] = tab[col] - tab.loc[tab.estrategia == 'baseline', col].iloc[0]
    return tab, base


# -------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dados', required=True)
    ap.add_argument('--razao', type=float, default=1.0,
                    help='positivos/negativos após over/undersampling (padrão 1.0)')
    ap.add_argument('--overhead-extra-ms', type=float, default=0.0,
                    help='custo de seleção T1 a somar ao overhead (ms)')
    ap.add_argument('--saida', default=None, help='JSON de saída (opcional)')
    a = ap.parse_args()

    metodos, obs = carregar(a.dados)
    treino, valid = particionar(metodos)
    print(f'Treino: {len(treino)} linhas | zeros={(treino.alvo == 0).sum()} '
          f'positivos={(treino.alvo > 0).sum()} | validação: {len(valid)} métodos')

    rankings = {}
    for e in ESTRATEGIAS:
        rankings[e] = treinar_e_ranquear(treino, valid, e, razao=a.razao)
        print(e, rankings[e][1]['antes'], '->', rankings[e][1]['depois'])

    tab, base = avaliar(rankings, metodos, obs, a.overhead_extra_ms)
    print(f'\nTempo-base T0 (média histórica 15/26/42): {base / 1000:.1f} s')
    print(tab.to_string(index=False))
    if a.saida:
        Path(a.saida).write_text(json.dumps({
            'tempo_base_ms': base, 'tabela': tab.to_dict('records'),
            'configs': {k: v[1] for k, v in rankings.items()}}, indent=2, default=float))


if __name__ == '__main__':
    main()