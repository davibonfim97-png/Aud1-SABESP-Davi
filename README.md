# Dossiê de auditoria da SABESP — exercício de 2025

**UnB — Auditoria 1 (CCA0024), Turma 02, 2026.2 — Professor Lucas Oliveira Gomes Ferreira**
**P2 — entrega em 25/10/2026 — trabalho individual**

| Campo | Informação |
|---|---|
| Aluno | Davi Fernandes Bonfim |
| Matrícula | 241003473 |
| Empresa atribuída | Companhia de Saneamento Básico do Estado de São Paulo — SABESP (SBSP3) |
| Documentos base | DFP 2025 (versão 2) e DFP 2024 (versão 3), CVM |

> **Aviso.** Este é um trabalho acadêmico. Não é opinião de auditoria independente nem trabalho de asseguração. Os dados reais vêm de documentos públicos (DFP/CVM). **A base de dados e os resultados dos testes de detalhe são sintéticos** e não representam registros da SABESP. Nenhuma confirmação, entrevista, inspeção ou acesso a sistema foi realizado.

## O que há no repositório

```
.
├── README.md                          este arquivo
├── matriz_cobertura_normas.csv        norma -> papel de trabalho -> arquivos de apoio
├── dossie/
│   ├── Dossie_de_Auditoria_SABESP_2025_v1.0.pdf    dossiê (PDF, 72 páginas)
│   └── Dossie_de_Auditoria_SABESP_2025_v1.0.docx   mesma versão, editável
├── dados/
│   ├── base_intangivel_sintetica.csv.gz            520.126 linhas SINTÉTICAS (conta: Intangível)
│   ├── dicionario_variaveis.csv                    dicionário de variáveis
│   ├── registro_erros_inseridos.csv                erros inseridos de propósito (verdade de terreno)
│   └── verdade_terreno_valores_corretos.csv.gz     valor correto de cada unidade (simula a inspeção)
├── codigo/
│   ├── 01_gerar_base.py          gera a base sintética (semente = matrícula)
│   ├── 02_testes_auditoria.py    testes T-01 a T-09 e comparação com os erros inseridos
│   ├── 03_amostragem_mus.py      PT 530: amostragem por unidade monetária
│   ├── 04_gerar_planilhas.py     planilhas editáveis, com fórmulas
│   ├── 05_executar_tudo.sh       roda tudo em sequência
│   └── requirements.txt
├── planilhas/Papeis_de_trabalho_calculos.xlsx      materialidade, conciliações, analíticos, sensibilidade, amostragem, erros e distorções
├── resultados/                   saídas dos testes e da amostragem (CSV e JSON)
└── fontes/relacao_fontes.md      documentos usados, links, datas de acesso e páginas
```

## Conteúdo do dossiê (PDF)

1. Identificação da entidade, fontes, versões das normas e convenções.
2. Compreensão inicial do exercício de 2025.
3. Escolha da conta da base simulada.
4. Papéis de trabalho: PT EC, 200, 210, 220, 230, 240, 250, 260, 265, 300, 315, 320, 330, 402, 450, 500, 501, 505, 510, 520, 530, 540, 550, 560, 570, 580 e 600, cada um com a estrutura mínima do roteiro e campo de revisão em branco.
5. Programas de auditoria por ciclo (receitas, disponibilidades, estoques, imobilizado e intangível, passivos e estimativas).
6. Base de dados simulada: justificativa, premissas, dicionário, conciliação, erros inseridos, testes e comparação.
7. Conclusão integrada.
8. Matriz de cobertura e histórico de versões.

Todo procedimento é classificado como **Realizado com evidência pública**, **Planejado por falta de acesso** ou **Simulado para fins didáticos**.

## Como reproduzir

Requisitos: Python 3.12 (testado), `numpy`, `pandas` e `openpyxl`. Para recalcular as fórmulas da planilha é preciso LibreOffice (opcional: o arquivo já vem calculado).

```bash
pip install -r codigo/requirements.txt
bash codigo/05_executar_tudo.sh          # cerca de 2 minutos
```

O script executa, em ordem: geração da base (`dados/`), testes (`resultados/`), amostragem (`resultados/PT530_*`) e planilhas (`planilhas/`). A semente do gerador é a matrícula (241003473), então a base é a mesma a cada execução.

Conferência da base: o SHA-256 do arquivo **descomprimido** `base_intangivel_sintetica.csv` é
`eda8a19e276e84b4def40591499569997de05e4a79ec219290a08ba64bb84ad8` (com as versões usadas: Python 3.12.3, numpy 2.4.4, pandas 3.0.2). Em outras versões das bibliotecas, os totais por classe continuam batendo com a Nota 14, mas os valores linha a linha podem diferir.

Passo a passo individual:

```bash
cd codigo
python3 01_gerar_base.py         # dados/base_intangivel_sintetica.csv.gz e registro de erros
python3 02_testes_auditoria.py   # resultados/T0x_*.csv e comparação erros inseridos x identificados
python3 03_amostragem_mus.py     # resultados/PT530_*
python3 04_gerar_planilhas.py    # planilhas/Papeis_de_trabalho_calculos.xlsx
```

## Resumo dos resultados (base sintética)

- Conta: **Intangível**, R$ 50.492.473 mil (48,46% do ativo consolidado de 31/12/2025), classes conforme a Nota 14 da DFP 2025.
- 520.126 unidades; valor líquido da base = saldo contábil, com diferença zero por construção (por classe e no total).
- Erros inseridos: S-01 corte (45 unidades, R$ 61.000 mil), S-02 classificação (160, R$ 38.000 mil), S-03 amortização (1.400, R$ 24.088 mil), S-04 duplicidade (126, R$ 12.546 mil). Os testes T-03 a T-06 identificaram todos.
- Amostragem MUS: 439 itens; limite superior de distorção de R$ 362.072 mil, abaixo da distorção tolerável (R$ 409.565 mil); a amostra projetou R$ 27.187 mil contra R$ 135.635 mil de distorção real inserida.
- Materialidade global R$ 585.093 mil (5% do LAIR); para execução R$ 409.565 mil.

## Limite de tamanho do GitHub

`base_intangivel_sintetica.csv.gz` tem cerca de 22 MB, abaixo do limite de 100 MB por arquivo do GitHub (`git push`). O envio pelo navegador aceita no máximo 25 MB por arquivo. Se algum arquivo ultrapassar o limite, use o link de download indicado aqui e mantenha o código de geração, que reproduz a base:

- Link alternativo para download da base: *(preencher, se necessário)*

## Versões das normas e fontes

As versões das NBC TA usadas estão na seção 1.3 do dossiê. A relação completa de fontes, com endereços, datas de acesso e páginas, está em `fontes/relacao_fontes.md`.

## Limitações

Sem acesso à companhia, toda evidência real é pública e já auditada. A estrutura interna da base é hipótese do aluno; a conciliação com o saldo contábil é exata por calibração e não valida o saldo real. Fontes de mercado do PT 560 são secundárias e devem ser confirmadas na CVM ou no RI.
