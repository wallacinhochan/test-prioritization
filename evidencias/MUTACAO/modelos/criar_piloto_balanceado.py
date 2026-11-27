"""Cria piloto_balanceado.py a partir de piloto.py (que NÃO é alterado).

Mudança única no treino: a Random Forest usa sample_weight (peso = zeros/positivos nos exemplos
com alvo > 0, a ponderação escolhida em REGISTRO-BALANCEAMENTO.md). O KNN continua sem balanceamento
(o KNeighborsRegressor não aceita sample_weight e o balanceamento piorou o KNN na comparação).
O manifesto passa a registrar o hash do piloto_balanceado.py e o campo `balanceamento`.

Uso (de dentro de evidencias/MUTACAO/modelos):  python criar_piloto_balanceado.py
"""
from pathlib import Path

base = Path(__file__).resolve().parent
src = (base / 'piloto.py').read_text(encoding='utf-8')

trocas = [
    ("        model.fit(x_train, y_train)\n",
     "        if name == 'RandomForest':\n"
     "            n_pos = sum(1 for y in y_train if y > 0)\n"
     "            peso_pos = (len(y_train) - n_pos) / n_pos\n"
     "            model.fit(x_train, y_train, sample_weight=[peso_pos if y > 0 else 1.0 for y in y_train])\n"
     "            print(f'RandomForest ponderada: peso dos positivos = {peso_pos:.4f}')\n"
     "        else:\n"
     "            model.fit(x_train, y_train)\n"),
    ("for name in ('piloto.py', 'requirements.txt')}",
     "for name in ('piloto_balanceado.py', 'requirements.txt')}"),
    ("'parametros': {'KNN': KNN, 'RandomForest': FOREST},",
     "'parametros': {'KNN': KNN, 'RandomForest': FOREST},\n"
     "                'balanceamento': {'RandomForest': 'ponderacao (peso = zeros/positivos)', 'KNN': 'nenhum'},"),
]
for antigo, novo in trocas:
    assert src.count(antigo) == 1, f'Trecho não encontrado exatamente uma vez: {antigo!r}'
    src = src.replace(antigo, novo)
(base / 'piloto_balanceado.py').write_text(src, encoding='utf-8')
print('Criado:', base / 'piloto_balanceado.py')