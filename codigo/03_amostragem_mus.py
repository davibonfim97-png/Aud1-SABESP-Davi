#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
03_amostragem_mus.py - PT 530: amostragem por unidade monetaria (MUS) sobre a base SINTETICA do intangivel.
Autor: Davi Fernandes Bonfim - Matricula 241003473. Dados SINTETICOS.

Resultado do teste de detalhe (existencia/valorizacao) e SIMULADO: o valor 'correto' de cada item vem do arquivo
verdade_terreno_valores_corretos.csv.gz, que representa o que uma inspecao e a revisao de documentos revelariam.
"""
import pandas as pd, numpy as np, json, os
D = os.path.join(os.path.dirname(__file__), '..', 'dados'); R = os.path.join(os.path.dirname(__file__), '..', 'resultados')
SEED = 241003473
b = pd.read_csv(os.path.join(D, 'base_intangivel_sintetica.csv.gz'), keep_default_na=False,
                usecols=['id_unidade', 'classe_contabil', 'tipo_ativo', 'municipio_cod', 'valor_liquido_brl'])
tv = pd.read_csv(os.path.join(D, 'verdade_terreno_valores_corretos.csv.gz'))
b = b.merge(tv, on='id_unidade', how='left')
# ---------------- Parametros (R$ mil) ----------------
POP = b.valor_liquido_brl.sum() / 1000                 # 50.492.473
MG, ME = 585093.0, 409565.0
TM = ME                                                # distorcao toleravel = materialidade para execucao
RF = 3.00                                              # fator de confianca, 95%, zero erros (Poisson)
EF = 1.6                                               # fator de expansao, 95%
EM = 40000.0                                           # distorcao esperada (julgamento do aluno)
SI = (TM - EM * EF) / RF                               # intervalo de amostragem
N_ESP = POP / SI
rng = np.random.default_rng(SEED)
START = float(rng.uniform(0, SI))
# ---------------- Selecao ----------------
vl = b.valor_liquido_brl.values / 1000.0
chave = vl >= SI
resto = b[~chave].reset_index(drop=True)
vl_r = resto.valor_liquido_brl.values / 1000.0
cum = np.cumsum(vl_r)
pts = START + SI * np.arange(int((cum[-1] - START) // SI) + 1)
ix = np.unique(np.searchsorted(cum, pts, side='left'))
amostra = pd.concat([b[chave].assign(selecao='ITEM-CHAVE (>= intervalo)'), resto.iloc[ix].assign(selecao='MUS')], ignore_index=True)
amostra['vl_registrado_mil'] = amostra.valor_liquido_brl / 1000
amostra['vl_correto_mil'] = amostra.vl_correto_brl / 1000
amostra['distorcao_mil'] = amostra.vl_registrado_mil - amostra.vl_correto_mil
amostra['taint'] = np.where(amostra.selecao == 'MUS', amostra.distorcao_mil / amostra.vl_registrado_mil, np.nan)
amostra.drop(columns=['valor_liquido_brl', 'vl_correto_brl']).to_csv(os.path.join(R, 'PT530_amostra_e_resultados.csv'), index=False)
# ---------------- Avaliacao ----------------
PGW = [3.00, 4.75, 6.30, 7.76, 9.16, 10.52, 11.85, 13.15, 14.44, 15.71, 16.97, 18.21, 19.44, 20.67, 21.89]
mus = amostra[amostra.selecao == 'MUS']
t = np.sort(mus.taint[mus.taint > 1e-12].values)[::-1]
mlm = float((t * SI).sum())                                   # distorcao mais provavel projetada
bp = RF * SI                                                  # precisao basica
uml = bp + sum(ti * SI * (PGW[min(k + 1, len(PGW) - 1)] - PGW[min(k, len(PGW) - 1)] - 1) for k, ti in enumerate(t))
chave_err = float(amostra[amostra.selecao != 'MUS'].distorcao_mil.sum())
res = dict(populacao_mil=round(POP, 1), n_itens_populacao=int(len(b)), tolerable_mil=TM, confianca=0.95, fator_confianca=RF, fator_expansao=EF,
           distorcao_esperada_mil=EM, intervalo_mil=round(SI, 3), n_esperado=round(N_ESP, 1), inicio_aleatorio_mil=round(START, 3),
           itens_chave=int(chave.sum()), itens_mus=int(len(mus)), itens_total=int(len(amostra)),
           itens_com_distorcao=int((amostra.distorcao_mil.abs() > 1e-6).sum()), distorcao_total_nos_itens_mil=round(float(amostra.distorcao_mil.sum()), 3),
           distorcao_itens_chave_mil=round(chave_err, 3), taints=[round(float(x), 5) for x in t],
           distorcao_projetada_mil=round(mlm, 1), precisao_basica_mil=round(bp, 1), limite_superior_stringer_mil=round(float(uml), 1),
           conclusao_amostral='LUS abaixo da distorcao tolerável' if uml + chave_err < TM else 'LUS acima da distorção tolerável',
           distorcao_real_inserida_mil=round(float(pd.read_csv(os.path.join(D, 'registro_erros_inseridos.csv')).distorcao_brl.sum() / 1000), 1),
           inserida_em_itens_amostrados_mil=round(float(amostra.distorcao_mil.abs().sum()), 1))
json.dump(res, open(os.path.join(R, 'PT530_resumo.json'), 'w'), indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
