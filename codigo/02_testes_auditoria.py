#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
02_testes_auditoria.py - Executa os testes de auditoria (T-01 a T-09) sobre a base SINTETICA.
Autor: Davi Fernandes Bonfim - Matricula 241003473. Dados SINTETICOS (nao sao registros reais da SABESP).
"""
import pandas as pd, numpy as np, json, os, sys
D = os.path.join(os.path.dirname(__file__), '..', 'dados'); R = os.path.join(os.path.dirname(__file__), '..', 'resultados')
os.makedirs(R, exist_ok=True)
b = pd.read_csv(os.path.join(D, 'base_intangivel_sintetica.csv.gz'), keep_default_na=False, parse_dates=['data_conclusao_obra', 'data_registro_lancamento'])
reg = pd.read_csv(os.path.join(D, 'registro_erros_inseridos.csv'))
ME_MIL, MG_MIL, TRIV_MIL = 409565, 585093, 29255
CORTE = pd.Timestamp('2025-12-31')
res = []
def log(cod, nome, status, resultado, nota=''):
    res.append(dict(teste=cod, descricao=nome, classificacao='Simulado para fins didaticos', resultado=resultado, observacao=nota))
    print(f'{cod} | {nome} | {resultado}')

# ---- T-01 Conciliacao com a Nota 14 (R$ mil)
nota14 = {'Contratos de Concessao URAE-1': (69281545, 23335074, 45946471), 'Compromissos de Contratos': (4437857, 707736, 3730121),
          'Licenca de uso de software': (1696773, 1145671, 551102), 'Direito de uso - Outros ativos': (240646, 188681, 51965),
          'Contratos de concessao - outros': (135470, 60381, 75089), 'Contratos de concessao - novos contratos': (148000, 10275, 137725)}
g = b.groupby('classe_contabil')[['custo_brl', 'amort_acum_brl', 'valor_liquido_brl']].sum() / 1000
rows = []
for k, (c, a, v) in nota14.items():
    rows.append(dict(classe=k, custo_base_mil=g.loc[k, 'custo_brl'], custo_nota14_mil=c, amort_base_mil=g.loc[k, 'amort_acum_brl'], amort_nota14_mil=a,
                     vl_base_mil=g.loc[k, 'valor_liquido_brl'], vl_nota14_mil=v))
t1 = pd.DataFrame(rows); t1['dif_vl_mil'] = t1.vl_base_mil - t1.vl_nota14_mil
tot = dict(classe='TOTAL', **{c: t1[c].sum() for c in t1.columns if c != 'classe'})
t1 = pd.concat([t1, pd.DataFrame([tot])], ignore_index=True)
t1.round(3).to_csv(os.path.join(R, 'T01_conciliacao_nota14.csv'), index=False)
log('T-01', 'Conciliacao da base com a Nota 14 e o balanco (R$ 50.492.473 mil)', 'ok', f"diferenca total = R$ {t1.iloc[-1].dif_vl_mil:.3f} mil", 'Zero por construcao (calibracao); ver dossie, secao 6')

# ---- T-02 Integridade
chk = dict(
    nulos=int(b.isna().sum().sum()),
    id_duplicado=int(b.id_unidade.duplicated().sum()),
    vl_difere=int(((b.custo_brl - b.amort_acum_brl - b.valor_liquido_brl).abs() > 0.011).sum()),
    vl_negativo=int((b.valor_liquido_brl < 0).sum()),
    amort_maior_custo=int((b.amort_acum_brl > b.custo_brl + 0.01).sum()),
    custo_nao_positivo=int((b.custo_brl <= 0).sum()),
    data_registro_futura=int((b.data_registro_lancamento > CORTE).sum()))
log('T-02', 'Integridade (nulos, ids, VL = custo - amortizacao, sinais, datas)', 'ok', json.dumps(chk))

# ---- T-03 Duplicidade
key = ['id_ordem_imobilizacao', 'tipo_ativo', 'municipio_cod', 'custo_brl', 'data_conclusao_obra']
b['_n'] = b.groupby(key)['id_unidade'].transform('size')
dup = b[b._n > 1].sort_values(key + ['data_registro_lancamento'])
dup_flag = dup[dup.duplicated(key, keep='first')]          # a segunda ocorrencia (registro posterior)
dup_flag[['id_unidade', 'id_ordem_imobilizacao', 'tipo_ativo', 'municipio_cod', 'custo_brl', 'valor_liquido_brl', 'data_registro_lancamento']].to_csv(os.path.join(R, 'T03_duplicidades.csv'), index=False)
log('T-03', 'Duplicidade por ordem, tipo, municipio, custo e data de conclusao', 'ok', f'{len(dup_flag)} unidades; VL R$ {dup_flag.valor_liquido_brl.sum()/1000:,.0f} mil')

# ---- T-04 Corte
cut = b[(b.data_conclusao_obra > CORTE) & (b.data_registro_lancamento <= CORTE)]
cut[['id_unidade', 'tipo_ativo', 'municipio_cod', 'data_conclusao_obra', 'data_registro_lancamento', 'origem_lancamento', 'usuario_registro', 'valor_liquido_brl']].to_csv(os.path.join(R, 'T04_corte.csv'), index=False)
near = b[(b.data_conclusao_obra >= '2025-12-18') & (b.data_conclusao_obra <= CORTE)]
log('T-04', 'Corte: conclusao da obra apos 31/12/2025 e registro ate 31/12/2025', 'ok', f'{len(cut)} unidades; VL R$ {cut.valor_liquido_brl.sum()/1000:,.0f} mil', f'{len(near)} obras concluidas em 18-31/12 listadas para revisao e consideradas regulares')

# ---- T-05 Classificacao (capex x despesa)
kw = 'MANUTENCAO CORRETIVA|REPARO EMERGENCIAL|CONSERTO DE|REPOSICAO CORRETIVA|MANUTENCAO'
t5a = b[b.descricao_gasto.str.contains(kw, regex=True)]
t5b = t5a[~t5a.descricao_gasto.str.contains('AMPLIACAO')]          # revisao do texto: ampliacao de capacidade e capitalizavel
t5a[['id_unidade', 'descricao_gasto', 'data_registro_lancamento', 'origem_lancamento', 'valor_liquido_brl']].to_csv(os.path.join(R, 'T05_classificacao_estagio1.csv'), index=False)
log('T-05', 'Classificacao: palavras de manutencao na descricao (estagio 1 = automatico; estagio 2 = apos leitura do texto)', 'ok',
    f'estagio 1: {len(t5a)} unidades; estagio 2: {len(t5b)} unidades, custo R$ {t5b.custo_brl.sum()/1000:,.0f} mil', 'Estagio 1 inclui falsos positivos (ampliacao de capacidade apos manutencao)')

# ---- T-06 Vida util x padrao do tipo
pad = b.groupby('tipo_ativo').vida_util_registrada_anos.agg(lambda s: s.mode().iloc[0])
b['_pad'] = b.tipo_ativo.map(pad)
t6 = b[b.vida_util_registrada_anos > b._pad * 1.05].copy()
# efeito estimado: amortizacao acumulada proporcional a 1/vida (aproximacao, sem teto)
t6['amort_estimada'] = np.minimum(t6.custo_brl, t6.amort_acum_brl * t6.vida_util_registrada_anos / t6._pad)
t6['efeito_estimado_brl'] = t6.amort_estimada - t6.amort_acum_brl
t6[['id_unidade', 'tipo_ativo', 'municipio_cod', 'vida_util_registrada_anos', 'custo_brl', 'amort_acum_brl', 'efeito_estimado_brl']].to_csv(os.path.join(R, 'T06_vida_util.csv'), index=False)
log('T-06', 'Vida util registrada acima da padrao do tipo (> 5%)', 'ok', f'{len(t6)} unidades; efeito estimado R$ {t6.efeito_estimado_brl.sum()/1000:,.0f} mil em amortizacao a menor', f'{t6.municipio_cod.nunique()} municipios no lote')

# ---- T-07 Lancamentos manuais de fim de periodo por usuario privilegiado (NBC TA 240, item 33)
priv = [f'USR-{i:03d}' for i in range(1, 6)]
t7 = b[(b.origem_lancamento == 'MANUAL') & b.usuario_registro.isin(priv) & (b.data_registro_lancamento >= '2025-12-20') & (b.data_registro_lancamento <= CORTE)]
t7[['id_unidade', 'descricao_gasto', 'data_registro_lancamento', 'usuario_registro', 'valor_liquido_brl']].to_csv(os.path.join(R, 'T07_lancamentos_manuais.csv'), index=False)
log('T-07', 'Lancamentos manuais, 20-31/12/2025, por usuarios privilegiados (criterios i, ii e iii do PT 240)', 'ok', f'{len(t7)} unidades; VL R$ {t7.valor_liquido_brl.sum()/1000:,.0f} mil', 'Indicador de risco; nao e erro por si so')

# ---- T-08 Benford (primeiro digito de custo_brl)
fd = b.custo_brl[b.custo_brl >= 1].astype(str).str.lstrip('0.').str[0].astype(int)
obs = fd.value_counts(normalize=True).reindex(range(1, 10)).fillna(0).values
exp = np.log10(1 + 1 / np.arange(1, 10))
chi2 = float((len(fd) * (obs - exp) ** 2 / exp).sum())
log('T-08', 'Primeiro digito do custo (Benford), informativo', 'ok', f'qui-quadrado = {chi2:,.0f} (8 gl); maior desvio = {np.max(np.abs(obs-exp))*100:.2f} p.p.', 'Valores sinteticos seguem lognormal; usar so como exploracao')

# ---- T-09 Analitico da amortizacao do exercicio
am = b.amort_exercicio_2025_brl.sum() / 1000
log('T-09', 'Amortizacao do exercicio da base x Nota 14 (R$ 2.161.112 mil)', 'ok', f'base R$ {am:,.0f} mil; diferenca {am-2161112:+,.0f} mil ({(am/2161112-1)*100:+.2f}%)', f'limite de investigacao R$ {int(ME_MIL*0.25):,} mil')

# ---- Comparacao: erros inseridos x identificados
ids = lambda df_: set(df_.id_unidade)
det = {'S-01': ids(cut), 'S-02': ids(t5b), 'S-03': ids(t6), 'S-04': ids(dup_flag)}
estag1 = {'S-02': ids(t5a)}
nome_t = {'S-01': 'T-04', 'S-02': 'T-05 (estagio 2)', 'S-03': 'T-06', 'S-04': 'T-03'}
rows = []
for s in ['S-01', 'S-02', 'S-03', 'S-04']:
    ins = reg[reg.codigo_erro == s]; i_ids = set(ins.id_unidade); d = det[s]
    tp = len(i_ids & d); fp = len(d - i_ids); fn = len(i_ids - d)
    val_ins = ins.distorcao_brl.sum() / 1000
    if s == 'S-03':
        val_id = t6.efeito_estimado_brl.sum() / 1000
    elif s == 'S-01' or s == 'S-04':
        val_id = b[b.id_unidade.isin(d)].valor_liquido_brl.sum() / 1000
    else:
        val_id = b[b.id_unidade.isin(d)].valor_liquido_brl.sum() / 1000
    rows.append(dict(codigo=s, teste=nome_t[s], inseridas=len(i_ids), identificadas=len(d), verdadeiros_positivos=tp, falsos_positivos=fp, falsos_negativos=fn,
                     precisao=round(tp / len(d), 4) if len(d) else None, cobertura=round(tp / len(i_ids), 4), distorcao_inserida_mil=round(val_ins, 1), distorcao_identificada_mil=round(val_id, 1)))
cmp_ = pd.DataFrame(rows)
if 'S-02' in estag1:
    s2 = reg[reg.codigo_erro == 'S-02']; e1 = estag1['S-02']
    cmp_.loc[cmp_.codigo == 'S-02', 'falsos_positivos_estagio1'] = len(e1 - set(s2.id_unidade))
cmp_.to_csv(os.path.join(R, 'comparacao_erros_inseridos_vs_identificados.csv'), index=False)
print(cmp_.to_string())
pd.DataFrame(res).to_csv(os.path.join(R, 'testes_resumo.csv'), index=False)
agg = dict(inserida_total_mil=float(cmp_.distorcao_inserida_mil.sum()), identificada_total_mil=float(cmp_.distorcao_identificada_mil.sum()),
           indicador_T07_unidades=int(len(t7)), indicador_T07_dentro_dos_erros=int(len(ids(t7) & set(reg.id_unidade))))
json.dump(agg, open(os.path.join(R, 'comparacao_totais.json'), 'w'), indent=1); print(agg)
