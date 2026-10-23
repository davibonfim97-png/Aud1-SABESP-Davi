#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
01_gerar_base.py - Gera a base SINTETICA do Intangivel da SABESP (31/12/2025).

Autor: Davi Fernandes Bonfim - Matricula 241003473 - Auditoria 1 (UnB, CCA0024, Turma 02)
ATENCAO: todos os registros sao SINTETICOS. Nao sao dados reais da SABESP.

Calibracao: custo, amortizacao acumulada e valor liquido de cada classe batem com a
Nota 14 da DFP 2025 consolidada (valores em R$ mil). Ver dossie, secao 6.
"""
import numpy as np, pandas as pd, json, os, sys, time
from datetime import date, timedelta

SEED = 241003473                      # matricula do aluno
DATA_BASE = date(2025, 12, 31)
OUT = os.path.join(os.path.dirname(__file__), '..', 'dados')
rng = np.random.default_rng(SEED)
t0 = time.time()

# ---------------- Classes (Nota 14, consolidado, R$ mil) ----------------
CLASSES = {
 'URAE1':        dict(nome='Contratos de Concessao URAE-1',          n=450000, custo=69281545, amort=23335074, ano0=1990, ano1=2025),
 'COMPROMISSOS': dict(nome='Compromissos de Contratos',              n=30000,  custo=4437857,  amort=707736,   ano0=2024, ano1=2024),
 'SOFTWARE':     dict(nome='Licenca de uso de software',             n=20000,  custo=1696773,  amort=1145671,  ano0=2017, ano1=2025),
 'DIREITO_USO':  dict(nome='Direito de uso - Outros ativos',         n=10000,  custo=240646,   amort=188681,   ano0=2019, ano1=2025),
 'OUTROS':       dict(nome='Contratos de concessao - outros',        n=5000,   custo=135470,   amort=60381,    ano0=2008, ano1=2025),
 'NOVOS':        dict(nome='Contratos de concessao - novos contratos', n=5000, custo=148000,   amort=10275,    ano0=2024, ano1=2024),
}
# tipo: (peso, vida_padrao_anos_base, mediana_custo_R$, sigma)
TIPOS = {
 'URAE1': {'REDE_AGUA':(.215,40,45e3,1.4),'REDE_ESGOTO':(.195,40,50e3,1.4),'LIGACAO_AGUA':(.18,30,3e3,.6),
           'LIGACAO_ESGOTO':(.12,30,4e3,.6),'HIDROMETRO':(.10,10,.5e3,.4),'ESTACAO_ELEVATORIA':(.045,20,600e3,1.1),
           'RESERVATORIO':(.03,40,900e3,1.2),'ETA':(.002,30,6e6,1.2),'ETE':(.002,30,8e6,1.2),
           'EQUIPAMENTO_OPERACIONAL':(.06,15,120e3,1.1),'SISTEMA_TELEMETRIA':(.049,10,70e3,1.0)},
 'COMPROMISSOS': {'COMPROMISSO_OUTORGA':(1.0,30,150e3,1.3)},
 'SOFTWARE':     {'LICENCA_SOFTWARE':(1.0,5,60e3,1.3)},
 'DIREITO_USO':  {'DIREITO_USO_IMOVEL':(.6,5,20e3,1.0),'DIREITO_USO_VEICULO':(.4,5,15e3,0.8)},
 'OUTROS':       {'CONCESSAO_OUTROS':(1.0,25,30e3,1.2)},
 'NOVOS':        {'CONCESSAO_NOVOS':(1.0,30,30e3,1.0)},
}
N_MUN = 375                         # municipios SINTETICOS (MUN-001..MUN-375)
N_FORN = 1200
USERS_PRIV = [f'USR-{i:03d}' for i in range(1, 6)]
USERS_ALL = [f'USR-{i:03d}' for i in range(1, 81)]
KEYWORDS_MANUT = ['MANUTENCAO CORRETIVA', 'REPARO EMERGENCIAL', 'CONSERTO DE', 'REPOSICAO CORRETIVA']

def rand_dates(n, y0, y1, recent_bias=True, d0=None, d1=None):
    if d0 is not None:
        span = (d1 - d0).days
        return np.array([d0 + timedelta(days=int(x)) for x in rng.integers(0, span + 1, n)])
    years = np.arange(y0, y1 + 1)
    w = (np.arange(len(years)) + 3.0) ** 1.8 if recent_bias else np.ones(len(years))
    w = w / w.sum()
    yy = rng.choice(years, n, p=w)
    doy = rng.integers(0, 365, n)
    return np.array([date(int(y), 1, 1) + timedelta(days=int(d)) for y, d in zip(yy, doy)])

# ---------------- 1. Gera linhas normais ----------------
frames = []
for cod, c in CLASSES.items():
    n = c['n']
    tipos = list(TIPOS[cod].keys())
    w = np.array([TIPOS[cod][t][0] for t in tipos]); w = w / w.sum()
    tp = rng.choice(len(tipos), n, p=w)
    med = np.array([TIPOS[cod][t][2] for t in tipos])[tp]
    sg = np.array([TIPOS[cod][t][3] for t in tipos])[tp]
    vida_b = np.array([TIPOS[cod][t][1] for t in tipos], dtype=float)[tp]
    custo = med * np.exp(sg * rng.standard_normal(n))
    if cod in ('COMPROMISSOS', 'NOVOS'):
        concl = rand_dates(n, 0, 0, d0=date(2024, 7, 23), d1=date(2024, 12, 20))
    else:
        concl = rand_dates(n, c['ano0'], c['ano1'])
        concl = np.array([min(d, DATA_BASE - timedelta(days=45)) for d in concl])
    lag = rng.integers(0, 46, n)
    reg = np.array([d + timedelta(days=int(l)) for d, l in zip(concl, lag)])
    df = pd.DataFrame(dict(classe_cod=cod, classe_contabil=c['nome'], tipo_ativo=np.array(tipos)[tp],
                           custo=custo, vida_base=vida_b, data_conclusao_obra=concl, data_registro=reg))
    frames.append(df)
df = pd.concat(frames, ignore_index=True)
df['err'] = ''
N0 = len(df)

# municipios / fornecedores / origem
is_u = df.classe_cod.eq('URAE1').values
mun = np.where(is_u, ['MUN-%03d' % m for m in rng.integers(1, N_MUN + 1, N0)], 'SEDE')
df['municipio_cod'] = mun
df['fornecedor_obra_cod'] = np.where(df.classe_cod.isin(['URAE1', 'OUTROS', 'NOVOS']),
                                     ['F-%04d' % f for f in rng.integers(1, N_FORN + 1, N0)], 'N/A')
manual = rng.random(N0) < 0.03
df['origem_lancamento'] = np.where(manual, 'MANUAL', 'AUTOMATICO_TRANSF_AC')
df['usuario_registro'] = np.where(manual, rng.choice(USERS_ALL[5:], N0), 'SISTEMA')
df['descricao_gasto'] = 'IMOBILIZACAO ' + df.tipo_ativo.str.replace('_', ' ') + ' ' + df.municipio_cod
# decoys legitimos (falsos positivos para T-04, T-05, T-07)
idx_u = np.where(is_u)[0]
dec_manut = rng.choice(idx_u, 200, replace=False)                      # texto parecido, mas capitalizavel
df.loc[dec_manut, 'descricao_gasto'] = 'AMPLIACAO DE CAPACIDADE APOS MANUTENCAO ' + df.loc[dec_manut, 'municipio_cod']
dec_corte = rng.choice(idx_u, 300, replace=False)                      # conclusao legitima no fim de dezembro
d_c = rand_dates(300, 0, 0, d0=date(2025, 12, 18), d1=date(2025, 12, 30))
df.loc[dec_corte, 'data_conclusao_obra'] = d_c
df.loc[dec_corte, 'data_registro'] = [d + timedelta(days=int(rng.integers(0, 2))) for d in d_c]
dec_man = rng.choice(idx_u, 400, replace=False)                        # lancamento manual legitimo de fim de ano
df.loc[dec_man, 'origem_lancamento'] = 'MANUAL'
df.loc[dec_man, 'usuario_registro'] = rng.choice(USERS_PRIV, 400)
df.loc[dec_man, 'data_registro'] = rand_dates(400, 0, 0, d0=date(2025, 12, 20), d1=date(2025, 12, 31))
df['data_registro'] = pd.to_datetime(df['data_registro'])
df['data_conclusao_obra'] = pd.to_datetime(df['data_conclusao_obra'])

# ---------------- 2. Escolhe linhas de erro ----------------
pool = np.setdiff1d(idx_u, np.concatenate([dec_manut, dec_corte, dec_man]))
rng.shuffle(pool)
s01 = pool[:45]; s02 = pool[45:205]; pool_rest = pool[205:]
df.loc[s01, 'err'] = 'S-01'; df.loc[s02, 'err'] = 'S-02'
# S-01: obras concluidas em jan/2026, capitalizadas em dez/2025 (corte)
df.loc[s01, 'data_conclusao_obra'] = pd.to_datetime(rand_dates(len(s01), 0, 0, d0=date(2026, 1, 5), d1=date(2026, 1, 25)))
df.loc[s01, 'data_registro'] = pd.to_datetime(rand_dates(len(s01), 0, 0, d0=date(2025, 12, 26), d1=date(2025, 12, 31)))
df.loc[s01, 'origem_lancamento'] = np.where(rng.random(len(s01)) < 0.85, 'MANUAL', 'AUTOMATICO_TRANSF_AC')
df.loc[s01, 'usuario_registro'] = np.where(df.loc[s01, 'origem_lancamento'].eq('MANUAL'), rng.choice(USERS_PRIV, len(s01)), 'SISTEMA')
# S-02: gastos de manutencao capitalizados
df.loc[s02, 'descricao_gasto'] = [rng.choice(KEYWORDS_MANUT) + ' ' + m for m in df.loc[s02, 'municipio_cod']]
df.loc[s02, 'data_registro'] = pd.to_datetime(rand_dates(len(s02), 0, 0, d0=date(2025, 10, 1), d1=date(2025, 12, 30)))
df.loc[s02, 'data_conclusao_obra'] = df.loc[s02, 'data_registro'] - pd.to_timedelta(rng.integers(0, 20, len(s02)), unit='D')
df.loc[s02, 'origem_lancamento'] = np.where(rng.random(len(s02)) < 0.6, 'MANUAL', 'AUTOMATICO_TRANSF_AC')
df.loc[s02, 'usuario_registro'] = np.where(df.loc[s02, 'origem_lancamento'].eq('MANUAL'), rng.choice(USERS_ALL[5:], len(s02)), 'SISTEMA')
# valores exatos de S-01 e S-02 (R$ mil -> R$)
def fix_total(idx, total_brl):
    w = df.loc[idx, 'custo'].values; w = w / w.sum()
    df.loc[idx, 'custo'] = w * total_brl
fix_total(s01, 61000e3); fix_total(s02, 38000e3)

# ---------------- 3. Idade, vida padrao e amortizacao ----------------
frac_days = (pd.Timestamp(DATA_BASE) - df['data_registro']).dt.days.clip(lower=0).values
df['idade_anos'] = frac_days / 365.25
fr25 = np.minimum(frac_days, 365) / 365.0
# escala da vida util: faz a soma de custo/vida x fracao em 2025 igualar a amortizacao do exercicio (Nota 14: R$ 2.161.112 mil)
# (calculada com custo ja escalado por classe abaixo; fazemos custo primeiro)
fixed = df.err.isin(['S-01', 'S-02']).values
for cod, c in CLASSES.items():
    m = (df.classe_cod == cod).values
    tgt = c['custo'] * 1000.0 - df.loc[m & fixed, 'custo'].sum()
    mm = m & ~fixed
    df.loc[mm, 'custo'] *= tgt / df.loc[mm, 'custo'].sum()
S0 = (df.custo.values * fr25 / df.vida_base.values)[~df.err.isin(['S-01', 'S-02']).values].sum()
ESC = S0 / (2161112e3)
df['vida_padrao_anos'] = (df.vida_base * ESC).round(1).clip(lower=1.0)
df['vida_util_registrada_anos'] = df['vida_padrao_anos']

# S-03: lote com vida util registrada maior que a padrao (amortizacao acumulada a menor)
def calib_lambda(mask, vida_reg, target_amort, excl):
    mm = mask & ~excl
    c = df.custo.values[mm]; a = df.idade_anos.values[mm]; v = vida_reg[mm]
    lo, hi = 0.01, 400.0
    for _ in range(60):
        mid = (lo + hi) / 2
        s = (c * np.clip(mid * a / v, 0, 1)).sum()
        if s < target_amort: lo = mid
        else: hi = mid
    return (lo + hi) / 2

lam = {}
for cod, c in CLASSES.items():
    m = (df.classe_cod == cod).values
    lam[cod] = calib_lambda(m, df.vida_util_registrada_anos.values, c['amort'] * 1000.0, fixed)
# escolhe lote S-03 (um conjunto de municipios, tipos de vida longa, idade > 6 anos)
cand = df[(df.classe_cod == 'URAE1') & df.err.eq('') & df.tipo_ativo.isin(['REDE_AGUA', 'REDE_ESGOTO', 'RESERVATORIO']) & (df.idade_anos > 6)]
cand = cand[~cand.index.isin(np.concatenate([dec_manut, dec_corte, dec_man]))]
lote_mun = rng.choice(cand.municipio_cod.unique(), 12, replace=False)
lote = cand[cand.municipio_cod.isin(lote_mun)].sample(frac=1.0, random_state=SEED)
delta_est = (lote.custo * np.clip(lam['URAE1'] * lote.idade_anos / lote.vida_padrao_anos, 0, 1)
             - lote.custo * np.clip(lam['URAE1'] * lote.idade_anos / (lote.vida_padrao_anos * 1.5), 0, 1))
cum = delta_est.cumsum()
k = int((cum < 24000e3).sum()) + 1
s03 = lote.index[:k]
df.loc[s03, 'err'] = 'S-03'
df.loc[s03, 'vida_util_registrada_anos'] = (df.loc[s03, 'vida_padrao_anos'] * 1.5).round(1)
for cod, c in CLASSES.items():
    m = (df.classe_cod == cod).values
    lam[cod] = calib_lambda(m, df.vida_util_registrada_anos.values, c['amort'] * 1000.0, fixed)

# amortizacao acumulada e do exercicio (valores registrados)
ratio = np.clip(df.classe_cod.map(lam).values * df.idade_anos.values / df.vida_util_registrada_anos.values, 0, 1)
amort = df.custo.values * ratio
amort[fixed] = 0.0
df['amort_ac'] = amort
am_ex = np.minimum(df.custo.values * fr25 / df.vida_util_registrada_anos.values, amort)
am_ex[fixed] = 0.0
df['amort_ex'] = am_ex
# correcao fina da amortizacao acumulada por classe (residuo de arredondamento do bisection)
for cod, c in CLASSES.items():
    m = ((df.classe_cod == cod) & ~df.err.isin(['S-01', 'S-02'])).values
    df.loc[m, 'amort_ac'] *= (c['amort'] * 1000.0) / df.loc[(df.classe_cod == cod).values, 'amort_ac'].sum() if True else 1
# verdade (valores corretos) antes de duplicidades
df['custo_correto'] = df.custo
df['amort_correta'] = df.amort_ac
am_true = df.custo.values * np.clip(df.classe_cod.map(lam).values * df.idade_anos.values / df.vida_padrao_anos.values, 0, 1)
df.loc[s03, 'amort_correta'] = am_true[df.index.get_indexer(s03)]
df.loc[s01, ['custo_correto', 'amort_correta']] = 0.0     # ativo nao existia em 31/12/2025
df.loc[s02, ['custo_correto', 'amort_correta']] = 0.0     # gasto deveria ser despesa

# ---------------- 4. S-04: duplicidades ----------------
df['vl'] = df.custo - df.amort_ac
mid = df[(df.classe_cod == 'URAE1') & df.err.eq('') & df.vl.between(40e3, 220e3)]
mid = mid[~mid.index.isin(np.concatenate([dec_manut, dec_corte, dec_man]))].sample(frac=1.0, random_state=SEED)
cum = mid.vl.cumsum()
orig_idx = mid.index[: int((cum < 12500e3).sum()) + 1]
dup = df.loc[orig_idx].copy()
dup['err'] = 'S-04'
dup['data_registro'] = dup['data_registro'] + pd.Timedelta(days=3)
dup['usuario_registro'] = rng.choice(USERS_ALL[5:], len(dup))
dup['origem_lancamento'] = 'MANUAL'
dup['custo_correto'] = 0.0; dup['amort_correta'] = 0.0
dup['dup_de'] = df.loc[orig_idx].index
df['dup_de'] = -1
df = pd.concat([df, dup], ignore_index=True)
df['dup_de'] = df['dup_de'].astype(int)
# compensacao (calibracao) em linhas de maior custo da URAE-1, fora das originais
cd = dup.custo.sum(); ad = dup.amort_ac.sum()
bal = df[(df.classe_cod == 'URAE1') & df.err.eq('') & ~df.index.isin(orig_idx)].nlargest(3000, 'custo').index
f_c = 1 - cd / df.loc[bal, 'custo'].sum(); f_a = 1 - ad / df.loc[bal, 'amort_ac'].sum()
df.loc[bal, 'custo'] *= f_c; df.loc[bal, 'amort_ac'] *= f_a
df.loc[bal, 'custo_correto'] *= f_c; df.loc[bal, 'amort_correta'] *= f_a
df.loc[bal, 'amort_ex'] *= f_c

# ---------------- 5. Arredonda em centavos e fecha totais por classe ----------------
def cents(x): return np.round(np.asarray(x, dtype=float) * 100).astype('int64')
cu = cents(df.custo); am = cents(df.amort_ac)
cuc = cents(df.custo_correto); amc = cents(df.amort_correta)
for cod, c in CLASSES.items():
    m = (df.classe_cod == cod).values
    last = np.where(m & df.index.isin(bal) | (m & df.err.eq('').values))[0]
    li = last[np.argmax(cu[last])]
    cu[li] += int(round(c['custo'] * 1000 * 100)) - cu[m].sum()
    am[li] += int(round(c['amort'] * 1000 * 100)) - am[m].sum()
    cuc[li] = cu[li] if True else cuc[li]
    amc[li] = am[li]
df['custo_brl'] = cu / 100.0; df['amort_acum_brl'] = am / 100.0
df['valor_liquido_brl'] = (cu - am) / 100.0
df['amort_exercicio_2025_brl'] = np.round(df.amort_ex.values, 2)
df['custo_correto_brl'] = cuc / 100.0; df['amort_correta_brl'] = amc / 100.0
df['vl_correto_brl'] = (cuc - amc) / 100.0

# ---------------- 6. Identificadores e saida ----------------
df = df.sample(frac=1.0, random_state=SEED).reset_index(drop=True)   # embaralha ordem de arquivo
df['id_unidade'] = ['U%07d' % (i + 1) for i in range(len(df))]
# ordens de imobilizacao agrupam ~3 unidades; duplicatas reusam a ordem da original
ordem = rng.integers(1, len(df) // 3, len(df))
df['id_ordem_imobilizacao'] = ['OI-%07d' % o for o in ordem]
orig_map = dict(zip(df.index, df.id_unidade))
old2new = {}  # reaponta duplicata para a ordem da original (indice antigo perdido apos shuffle): usa chave natural
key = df[['classe_cod', 'tipo_ativo', 'municipio_cod', 'custo_brl', 'data_conclusao_obra']].astype(str).agg('|'.join, axis=1)
is_dup = df.err.eq('S-04')
first = key[~is_dup].drop_duplicates().to_frame('k'); first['ordem'] = df.loc[first.index, 'id_ordem_imobilizacao']
kmap = dict(zip(first.k, first.ordem))
df.loc[is_dup, 'id_ordem_imobilizacao'] = key[is_dup].map(kmap).fillna(df.loc[is_dup, 'id_ordem_imobilizacao'])
df['origem_dado'] = 'SINTETICO'
df['data_conclusao_obra'] = df.data_conclusao_obra.dt.strftime('%Y-%m-%d')
df['data_registro_lancamento'] = df.data_registro.dt.strftime('%Y-%m-%d')
cols = ['id_unidade', 'id_ordem_imobilizacao', 'classe_contabil', 'tipo_ativo', 'municipio_cod', 'fornecedor_obra_cod',
        'descricao_gasto', 'data_conclusao_obra', 'data_registro_lancamento', 'origem_lancamento',
        'usuario_registro', 'vida_util_registrada_anos', 'custo_brl', 'amort_acumulada_brl' if False else 'amort_acum_brl',
        'valor_liquido_brl', 'amort_exercicio_2025_brl', 'origem_dado']
base = df[cols].copy()
os.makedirs(OUT, exist_ok=True)
base.to_csv(os.path.join(OUT, 'base_intangivel_sintetica.csv.gz'), index=False, compression='gzip')

# registro de erros inseridos (verdade de terreno) - NAO faz parte da base entregue ao "auditor"
reg = df[df.err != ''][['id_unidade', 'err', 'classe_contabil', 'valor_liquido_brl', 'vl_correto_brl']].copy()
reg['distorcao_brl'] = reg.valor_liquido_brl - reg.vl_correto_brl
reg = reg.rename(columns={'err': 'codigo_erro'})
nat = {'S-01': 'Corte: obra concluida em jan/2026 capitalizada em dez/2025', 'S-02': 'Classificacao: gasto de manutencao capitalizado',
       'S-03': 'Amortizacao: vida util registrada maior que a padrao (lote)', 'S-04': 'Duplicidade de registro de unidade'}
reg['natureza'] = reg.codigo_erro.map(nat)
reg.to_csv(os.path.join(OUT, 'registro_erros_inseridos.csv'), index=False)
# valores corretos de todas as linhas (usado so para simular o resultado de testes de detalhe)
df[['id_unidade', 'vl_correto_brl']].to_csv(os.path.join(OUT, 'verdade_terreno_valores_corretos.csv.gz'), index=False, compression='gzip')

# resumo e conciliacao
res = dict(linhas=int(len(base)), vl_total_brl=float(base.valor_liquido_brl.sum()), lam={k: round(float(v), 4) for k, v in lam.items()},
           escala_vida=round(float(ESC), 4), amort_ex_total_brl=float(base.amort_exercicio_2025_brl.sum()),
           erros={k: dict(n=int((reg.codigo_erro == k).sum()), distorcao_brl=float(reg[reg.codigo_erro == k].distorcao_brl.sum())) for k in nat},
           segundos=round(time.time() - t0, 1))
json.dump(res, open(os.path.join(OUT, '..', 'resultados', 'resumo_geracao.json'), 'w'), indent=1)
print(json.dumps(res, indent=1))
