# ============================================================
#  JBS SNIPER — app.py  v4
#  Fixes: PDF/Excel geração corrigida, formato BR (R$ X.XXX,XX)
#         filtro combinatório restaurado
# ============================================================

import streamlit as st
import pandas as pd
import re
import itertools
import hashlib
import os
from io import BytesIO
from fpdf import FPDF
from datetime import datetime

_favicon = "logo_pdf.png" if os.path.exists("logo_pdf.png") else "🎯"

st.set_page_config(
    page_title="JBS SNIPER",
    page_icon=_favicon,
    layout="wide",
    initial_sidebar_state="collapsed",
)

GOLD   = "#84754e"
BEIGE  = "#ecece4"
BG     = "#0e1117"
CARD   = "#1c1f26"
BORDER = "#2e3340"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@300;400;600;700&family=Barlow+Condensed:wght@400;600;700&display=swap');
html, body, [class*="css"] {{ font-family: 'Barlow', sans-serif; }}
.stApp {{ background-color: {BG}; color: {BEIGE}; }}
.stButton > button {{
    width: 100%;
    background: linear-gradient(135deg, {GOLD} 0%, #6b5e3d 100%);
    color: #fff; border: none; border-radius: 8px;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.05rem; font-weight: 700;
    letter-spacing: 2px; text-transform: uppercase;
    padding: 14px 0; transition: all .2s ease;
    box-shadow: 0 4px 15px rgba(132,117,78,.3);
}}
.stButton > button:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(132,117,78,.45); }}
.stButton > button:active {{ transform: translateY(0); }}
.stTextArea textarea, .stNumberInput input, .stSelectbox > div > div {{
    background-color: {CARD} !important; color: {BEIGE} !important;
    border: 1px solid {BORDER} !important; border-radius: 8px !important;
    font-family: 'Barlow', sans-serif !important;
}}
.stTextArea textarea:focus, .stNumberInput input:focus {{
    border-color: {GOLD} !important;
    box-shadow: 0 0 0 2px rgba(132,117,78,.25) !important;
}}
label, .stSelectbox label, .stNumberInput label, .stTextArea label {{
    color: {BEIGE} !important; font-size: .78rem !important;
    font-weight: 600 !important; letter-spacing: 1px !important;
    text-transform: uppercase !important;
}}
h1, h2, h3, h4 {{
    font-family: 'Barlow Condensed', sans-serif !important;
    color: {GOLD} !important; letter-spacing: 1px;
}}
.stDataFrame {{ border: 1px solid {BORDER}; border-radius: 8px; overflow: hidden; }}
.streamlit-expanderHeader {{
    background-color: {CARD} !important; border: 1px solid {BORDER} !important;
    border-radius: 8px !important; color: {BEIGE} !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    font-weight: 600 !important; letter-spacing: 1px !important;
}}
[data-testid="metric-container"] {{
    background-color: {CARD}; border: 1px solid {BORDER};
    border-radius: 10px; padding: 14px 18px;
}}
[data-testid="metric-container"] label {{
    color: {GOLD} !important; font-size: .72rem !important; letter-spacing: 1.5px !important;
}}
[data-testid="metric-container"] [data-testid="stMetricValue"] {{
    color: {BEIGE} !important;
    font-family: 'Barlow Condensed', sans-serif !important; font-size: 1.6rem !important;
}}
hr {{ border-color: {BORDER}; margin: 8px 0 20px; }}
.stProgress > div > div > div {{ background-color: {GOLD} !important; }}
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: {BG}; }}
::-webkit-scrollbar-thumb {{ background: {BORDER}; border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: {GOLD}; }}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  CABEÇALHO
# ════════════════════════════════════════════════════════════
col_logo, col_title = st.columns([1, 5])
with col_logo:
    if os.path.exists("logo_app.png"):
        st.image("logo_app.png", width=200)
    else:
        st.markdown(f"<h1 style='font-size:3rem;margin:0;padding-top:8px'>{_favicon}</h1>", unsafe_allow_html=True)
with col_title:
    st.markdown(f"""
    <div style='padding-top:10px'>
        <h1 style='margin:0;font-size:2.4rem;letter-spacing:4px'>SISTEMA SNIPER</h1>
        <p style='color:{BEIGE};opacity:.6;margin:0;font-size:.9rem;letter-spacing:2px;text-transform:uppercase'>
            JBS Contempladas · Inteligência Comercial
        </p>
    </div>
    """, unsafe_allow_html=True)
st.markdown(f"<hr style='border:1px solid {GOLD};margin-top:4px'>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
#  FORMATAÇÃO BR  →  R$ 1.234.567,89
# ════════════════════════════════════════════════════════════
def fmt_brl(valor: float) -> str:
    """Formata número para padrão brasileiro: R$ 1.234.567,89"""
    try:
        s = f"{valor:,.2f}"          # 1,234,567.89  (padrão US)
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")  # 1.234.567,89
        return f"R$ {s}"
    except Exception:
        return "R$ 0,00"

def fmt_pct(valor: float) -> str:
    return f"{valor:.2f}%".replace(".", ",")


# ════════════════════════════════════════════════════════════
#  UTILITÁRIOS
# ════════════════════════════════════════════════════════════
def limpar_moeda(texto: str) -> float:
    if not texto:
        return 0.0
    try:
        t = (str(texto).lower().strip()
             .replace('\xa0','').replace('&nbsp;','')
             .replace('r$','').replace(' ',''))
        t = re.sub(r'[^\d\.,]', '', t)
        if not t:
            return 0.0
        if ',' in t and '.' in t:
            return float(t.replace('.','').replace(',','.'))
        if ',' in t:
            partes = t.split(',')
            if len(partes) == 2 and len(partes[1]) <= 2:
                return float(t.replace(',','.'))
            return float(t.replace(',',''))
        if '.' in t:
            partes = t.split('.')
            if len(partes) == 2 and len(partes[1]) == 2:
                return float(t)
            return float(t.replace('.',''))
        return float(t)
    except Exception:
        return 0.0


def _detectar_tipo(bloco_lower: str) -> str:
    if any(k in bloco_lower for k in ('imóvel','imovel','apartamento','casa','terreno','comercial')):
        return "Imóvel"
    if any(k in bloco_lower for k in ('caminhão','caminhao','pesado','truck','ônibus','onibus')):
        return "Pesados"
    if any(k in bloco_lower for k in ('automóvel','automovel','veículo','veiculo','carro','moto')):
        return "Automóvel"
    return "Geral"


# ════════════════════════════════════════════════════════════
#  EXTRAÇÃO
# ════════════════════════════════════════════════════════════
_RE_CREDITO = re.compile(
    r'(?:cr[eé]dito|bem|valor[\s_]do[\s_]bem|valor[\s_]carta)[^\d\n]{0,25}?R\$\s*([\d\.,]+)',
    re.IGNORECASE)
_RE_ENTRADA = re.compile(
    r'(?:entrada|[aá]gio|lance[\s_]fixo|pago|quero)[^\d\n]{0,25}?R\$\s*([\d\.,]+)',
    re.IGNORECASE)
_RE_PARCELA = re.compile(r'(\d+)\s*[xX]\s*R?\$?\s*([\d\.,]+)', re.IGNORECASE)
_RE_MOEDA   = re.compile(r'R\$\s*([\d\.,]+)', re.IGNORECASE)

_ADMINS = [
    'BRADESCO','SANTANDER','ITAÚ','ITAU','PORTO SEGURO','PORTO',
    'CAIXA','BANCO DO BRASIL','BB','RODOBENS','EMBRACON',
    'ANCORA','ÂNCORA','MYCON','SICREDI','SICOOB','MAPFRE',
    'HS','YAMAHA','ZEMA','BANCORBRÁS','BANCORBRAS','SERVOPA',
    'WOOP','SOMPO','MAGALU',
]


def extrair_dados_universal(texto_copiado: str, tipo_selecionado: str) -> list:
    lista_cotas = []
    if not texto_copiado or not texto_copiado.strip():
        return lista_cotas

    texto_limpo = "\n".join(
        ln.strip() for ln in texto_copiado.replace('\r\n','\n').replace('\r','\n').split('\n')
        if ln.strip()
    )
    blocos = re.split(
        r'(?i)(?=\b(?:imóvel|imovel|automóvel|automovel|veículo|veiculo|caminhão|caminhao|moto)\b)',
        texto_limpo
    )
    if len(blocos) < 2:
        blocos = re.split(r'\n\s*\n+', texto_limpo)
    if len(blocos) < 2:
        blocos = [texto_limpo]

    id_cota = 1
    for bloco in blocos:
        if len(bloco.strip()) < 20:
            continue
        try:
            bloco_lower = bloco.lower()
            admin = next(
                (adm.upper() for adm in _ADMINS if adm.lower() in bloco_lower),
                "OUTROS"
            )
            if admin == "OUTROS" and "r$" not in bloco_lower:
                continue

            tipo_cota = _detectar_tipo(bloco_lower)

            credito = 0.0
            m = _RE_CREDITO.search(bloco)
            if m:
                credito = limpar_moeda(m.group(1))
            if credito <= 0:
                todos_vals = sorted(
                    [limpar_moeda(v) for v in _RE_MOEDA.findall(bloco) if limpar_moeda(v) > 5000],
                    reverse=True
                )
                credito = todos_vals[0] if todos_vals else 0.0
            if credito <= 5000:
                continue

            if tipo_cota == "Geral":
                tipo_cota = "Imóvel" if credito > 250000 else "Automóvel"
            if tipo_selecionado not in ("Todos","Geral") and tipo_cota != tipo_selecionado:
                continue

            entrada = 0.0
            m = _RE_ENTRADA.search(bloco)
            if m:
                entrada = limpar_moeda(m.group(1))
            if entrada <= 0:
                candidatos = sorted(
                    [limpar_moeda(v) for v in _RE_MOEDA.findall(bloco)
                     if credito * 0.01 < limpar_moeda(v) < credito * 0.95],
                    reverse=True
                )
                entrada = candidatos[0] if candidatos else 0.0
            if entrada <= 0:
                continue

            saldo_devedor = 0.0
            parcela_teto  = 0.0
            todas_parcelas = _RE_PARCELA.findall(bloco)
            for pz_str, vlr_str in todas_parcelas:
                try:
                    pz  = int(pz_str)
                    vlr = limpar_moeda(vlr_str)
                    if pz > 0 and vlr > 0:
                        saldo_devedor += pz * vlr
                        if pz > 1 and vlr > parcela_teto:
                            parcela_teto = vlr
                        elif len(todas_parcelas) == 1:
                            parcela_teto = vlr
                except Exception:
                    continue

            if saldo_devedor <= 0:
                saldo_devedor = max(credito * 1.25 - entrada, credito * 0.20)

            lista_cotas.append({
                'ID':         id_cota,
                'Admin':      admin,
                'Tipo':       tipo_cota,
                'Crédito':    credito,
                'Entrada':    entrada,
                'Parcela':    parcela_teto,
                'Saldo':      saldo_devedor,
                'CustoTotal': entrada + saldo_devedor,
                'EntradaPct': entrada / credito,
            })
            id_cota += 1
        except Exception:
            continue
    return lista_cotas


# ════════════════════════════════════════════════════════════
#  MOTOR
# ════════════════════════════════════════════════════════════
def _status(custo_real: float) -> str:
    if   custo_real <= 0.20: return "💎 OURO"
    elif custo_real <= 0.35: return "🔥 IMPERDÍVEL"
    elif custo_real <= 0.45: return "✨ EXCELENTE"
    elif custo_real <= 0.50: return "✅ OPORTUNIDADE"
    return "⚠️ PADRÃO"


def processar_combinacoes(cotas, min_cred, max_cred, max_ent, max_parc, max_custo, tipo_filtro, admin_filtro):
    MAX_POR_ADMIN = 400
    ENT_TOL = PARC_TOL = 1.05

    filtradas = [
        c for c in cotas
        if (tipo_filtro  in ("Todos","Geral") or c['Tipo']  == tipo_filtro)
        and (admin_filtro == "Todas"           or c['Admin'] == admin_filtro)
        and c['Admin']   != "OUTROS"
        and c['Entrada'] <= max_ent * ENT_TOL
        and c['Crédito'] <= max_cred
        # SEM filtro de crédito mínimo individual — cotas pequenas combinam para atingir o mínimo
    ]
    if not filtradas:
        return pd.DataFrame()

    cotas_por_admin: dict = {}
    for c in filtradas:
        cotas_por_admin.setdefault(c['Admin'], []).append(c)

    resultados = []
    progress = st.progress(0)
    total_adm = len(cotas_por_admin)

    for adm_idx, (admin, grupo) in enumerate(cotas_por_admin.items()):
        progress.progress(int((adm_idx + 1) / total_adm * 100))
        grupo.sort(key=lambda x: x['Entrada'])
        count_admin = 0

        for r in range(1, 7):
            if count_admin >= MAX_POR_ADMIN:
                break
            for combo in itertools.combinations(grupo, r):
                if count_admin >= MAX_POR_ADMIN:
                    break

                soma_ent = sum(c['Entrada'] for c in combo)
                if soma_ent > max_ent * ENT_TOL:
                    if r >= 2:
                        min_ent = sum(c['Entrada'] for c in grupo[:r])
                        if min_ent > max_ent * ENT_TOL:
                            break
                    continue

                soma_cred = sum(c['Crédito'] for c in combo)
                if soma_cred < min_cred or soma_cred > max_cred:
                    continue

                soma_parc = sum(c['Parcela'] for c in combo)
                if soma_parc > max_parc * PARC_TOL:
                    continue

                soma_saldo = sum(c['Saldo'] for c in combo)
                custo_total = soma_ent + soma_saldo
                if soma_cred <= 0:
                    continue
                custo_real = (custo_total / soma_cred) - 1
                if custo_real > max_custo:
                    continue

                ids      = " + ".join(str(c['ID']) for c in combo)
                detalhes = " || ".join(
                    f"[ID {c['ID']}] {c['Admin']} · {fmt_brl(c['Crédito'])}" for c in combo
                )
                prazo = int(soma_saldo / soma_parc) if soma_parc > 0 else 0

                resultados.append({
                    'STATUS':          _status(custo_real),
                    'ADMINISTRADORA':  admin,
                    'TIPO':            combo[0]['Tipo'],
                    'IDS':             ids,
                    'CRÉDITO TOTAL':   soma_cred,
                    'ENTRADA TOTAL':   soma_ent,
                    'ENTRADA %':       (soma_ent / soma_cred) * 100,
                    'SALDO DEVEDOR':   soma_saldo,
                    'CUSTO TOTAL':     custo_total,
                    'PRAZO (meses)':   prazo,
                    'PARCELA MENSAL':  soma_parc,
                    'CUSTO EFETIVO %': custo_real * 100,
                    'DETALHES':        detalhes,
                })
                count_admin += 1

    progress.empty()
    if not resultados:
        return pd.DataFrame()
    return pd.DataFrame(resultados).sort_values('CUSTO EFETIVO %').reset_index(drop=True)


# ════════════════════════════════════════════════════════════
#  CACHE
# ════════════════════════════════════════════════════════════
@st.cache_data(max_entries=30, ttl=600, show_spinner=False)
def buscar_cached(_hash, texto, min_cred, max_cred, max_ent, max_parc, max_custo, tipo, admin):
    cotas = extrair_dados_universal(texto, tipo)
    if not cotas:
        return pd.DataFrame()
    return processar_combinacoes(cotas, min_cred, max_cred, max_ent, max_parc, max_custo, tipo, admin)


def gerar_hash(texto, *args):
    payload = texto + "|".join(str(a) for a in args)
    return hashlib.md5(payload.encode()).hexdigest()


# ════════════════════════════════════════════════════════════
#  PDF
# ════════════════════════════════════════════════════════════
def _san(texto: str) -> str:
    return texto.encode('latin-1','replace').decode('latin-1')


class RelatorioPDF(FPDF):
    def header(self):
        self.set_fill_color(132, 117, 78)
        self.rect(0, 0, 297, 20, 'F')
        if os.path.exists("logo_pdf.png"):
            self.image('logo_pdf.png', 4, 2, 30)
        self.set_font('Arial','B',14)
        self.set_text_color(255,255,255)
        self.set_xy(38, 5)
        self.cell(0, 10, 'JBS SNIPER  |  RELATORIO DE OPORTUNIDADES', 0, 1, 'L')
        self.set_font('Arial','',7)
        self.set_xy(38, 13)
        self.cell(0, 5, f'Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'L')
        self.ln(4)

    def footer(self):
        self.set_y(-12)
        self.set_font('Arial','I',7)
        self.set_text_color(150,150,150)
        self.cell(0, 8, f'JBS SNIPER  |  Pagina {self.page_no()}', 0, 0, 'C')


def gerar_pdf_bytes(df: pd.DataFrame) -> bytes:
    pdf = RelatorioPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    pdf.set_fill_color(236,236,228)
    pdf.set_text_color(30,30,30)
    pdf.set_font('Arial','B',7)

    cols = ["STS","ADMIN","TIPO","CREDITO","ENTRADA","ENT%","SALDO","CUSTO TOT","PRZ","PARCELA","EFETIVO%","DETALHES"]
    wids = [18,    20,     14,    28,        28,       10,    28,     28,         8,    24,        13,        70]

    for h, w in zip(cols, wids):
        pdf.cell(w, 7, h, 1, 0, 'C', True)
    pdf.ln()
    pdf.set_font('Arial','',6.5)

    for i, (_, row) in enumerate(df.iterrows()):
        fill = (i % 2 == 0)
        pdf.set_fill_color(245,245,240) if fill else pdf.set_fill_color(255,255,255)
        pdf.cell(wids[0],  6, _san(str(row['STATUS']))[:8],                      1,0,'C',fill)
        pdf.cell(wids[1],  6, _san(str(row['ADMINISTRADORA']))[:14],              1,0,'C',fill)
        pdf.cell(wids[2],  6, _san(str(row['TIPO']))[:10],                        1,0,'C',fill)
        pdf.cell(wids[3],  6, _san(fmt_brl(row['CRÉDITO TOTAL'])),                1,0,'R',fill)
        pdf.cell(wids[4],  6, _san(fmt_brl(row['ENTRADA TOTAL'])),                1,0,'R',fill)
        pdf.cell(wids[5],  6, _san(fmt_pct(row['ENTRADA %'])),                    1,0,'C',fill)
        pdf.cell(wids[6],  6, _san(fmt_brl(row['SALDO DEVEDOR'])),                1,0,'R',fill)
        pdf.cell(wids[7],  6, _san(fmt_brl(row['CUSTO TOTAL'])),                  1,0,'R',fill)
        pdf.cell(wids[8],  6, str(int(row['PRAZO (meses)'])),                     1,0,'C',fill)
        pdf.cell(wids[9],  6, _san(fmt_brl(row['PARCELA MENSAL'])),               1,0,'R',fill)
        pdf.cell(wids[10], 6, _san(fmt_pct(row['CUSTO EFETIVO %'])),              1,0,'C',fill)
        pdf.cell(wids[11], 6, _san(str(row['DETALHES']))[:55],                    1,1,'L',fill)

    return bytes(pdf.output(dest='S'))


# ════════════════════════════════════════════════════════════
#  EXCEL
# ════════════════════════════════════════════════════════════
def gerar_excel_bytes(df: pd.DataFrame, cotas: list) -> bytes:
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    GOLD_HEX  = "84754e"
    ZEBRA_HEX = "f5f5f0"
    FMT_BRL   = '"R$" #.##0,00'          # formato BR para Excel
    FMT_PCT   = '0,00"%"'
    FMT_NUM   = '#.##0'

    borda = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC'),
    )

    col_names  = list(df.columns)
    col_widths = {
        'STATUS':18,'ADMINISTRADORA':16,'TIPO':12,'IDS':24,
        'CRÉDITO TOTAL':20,'ENTRADA TOTAL':20,'ENTRADA %':13,
        'SALDO DEVEDOR':20,'CUSTO TOTAL':20,'PRAZO (meses)':14,
        'PARCELA MENSAL':20,'CUSTO EFETIVO %':17,'DETALHES':55,
    }
    fmt_map = {}
    for i, col in enumerate(col_names, start=1):
        if col in ('CRÉDITO TOTAL','ENTRADA TOTAL','SALDO DEVEDOR','CUSTO TOTAL','PARCELA MENSAL'):
            fmt_map[i] = FMT_BRL
        elif col in ('ENTRADA %','CUSTO EFETIVO %'):
            fmt_map[i] = FMT_PCT
        elif col == 'PRAZO (meses)':
            fmt_map[i] = FMT_NUM

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Oportunidades')
        ws = writer.sheets['Oportunidades']

        # cabeçalho
        for cell in ws[1]:
            cell.fill      = PatternFill("solid", fgColor=GOLD_HEX)
            cell.font      = Font(bold=True, color="FFFFFF", size=10)
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border    = borda
            cn = col_names[cell.column - 1]
            ws.column_dimensions[get_column_letter(cell.column)].width = col_widths.get(cn, 14)
        ws.row_dimensions[1].height = 22

        # dados
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, max_row=ws.max_row), start=2):
            zebra = (row_idx % 2 == 0)
            for cell in row:
                cell.border = borda
                cell.font   = Font(size=9)
                if zebra:
                    cell.fill = PatternFill("solid", fgColor=ZEBRA_HEX)
                ci = cell.column
                cn = col_names[ci - 1]
                # numérico com formato BR
                if ci in fmt_map:
                    cell.number_format = fmt_map[ci]
                    try:
                        cell.value = float(cell.value) if cell.value not in (None,'') else cell.value
                    except (ValueError, TypeError):
                        pass
                    cell.alignment = Alignment(horizontal='right', vertical='center')
                elif cn in ('DETALHES','IDS'):
                    cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=False)
                else:
                    cell.alignment = Alignment(horizontal='center', vertical='center')

        ws.freeze_panes = 'A2'
        ws.auto_filter.ref = ws.dimensions

        # aba Cotas Lidas
        if cotas:
            df_c = pd.DataFrame(cotas)
            df_c.to_excel(writer, index=False, sheet_name='Cotas Lidas')
            ws2 = writer.sheets['Cotas Lidas']
            c_widths = {'ID':6,'Admin':16,'Tipo':12,'Crédito':20,'Entrada':20,
                        'Parcela':20,'Saldo':20,'CustoTotal':20,'EntradaPct':14}
            c_fmt = {'Crédito':FMT_BRL,'Entrada':FMT_BRL,'Parcela':FMT_BRL,
                     'Saldo':FMT_BRL,'CustoTotal':FMT_BRL,'EntradaPct':FMT_PCT}
            c_cols = list(df_c.columns)
            for cell in ws2[1]:
                cell.fill      = PatternFill("solid", fgColor=GOLD_HEX)
                cell.font      = Font(bold=True, color="FFFFFF", size=10)
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border    = borda
                cn = c_cols[cell.column - 1]
                ws2.column_dimensions[get_column_letter(cell.column)].width = c_widths.get(cn, 14)
            for row_idx, row in enumerate(ws2.iter_rows(min_row=2, max_row=ws2.max_row), start=2):
                zebra = (row_idx % 2 == 0)
                for cell in row:
                    cell.border = borda
                    cell.font   = Font(size=9)
                    cell.alignment = Alignment(horizontal='center', vertical='center')
                    if zebra:
                        cell.fill = PatternFill("solid", fgColor=ZEBRA_HEX)
                    cn = c_cols[cell.column - 1]
                    if cn in c_fmt:
                        cell.number_format = c_fmt[cn]
                        try:
                            cell.value = float(cell.value) if cell.value not in (None,'') else cell.value
                        except (ValueError, TypeError):
                            pass
                        cell.alignment = Alignment(horizontal='right', vertical='center')
            ws2.freeze_panes = 'A2'

    return buf.getvalue()


# ════════════════════════════════════════════════════════════
#  SESSION STATE
# ════════════════════════════════════════════════════════════
for key, default in [
    ('df_resultado',       None),
    ('admins_disponiveis', ["Todas"]),
    ('cotas_lidas',        []),
    ('pdf_bytes',          None),
    ('excel_bytes',        None),
    ('export_ts',          ""),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ════════════════════════════════════════════════════════════
#  ENTRADA DE DADOS
# ════════════════════════════════════════════════════════════
with st.expander("📋  DADOS DO SITE  —  Cole o texto das cotas aqui", expanded=True):
    texto_site = st.text_area(
        "Texto copiado do portal / WhatsApp",
        height=130,
        placeholder="Cole aqui o texto com as cotas de consórcio...",
        key="input_texto",
    )
    if texto_site:
        cotas_preview = extrair_dados_universal(texto_site, "Todos")
        st.session_state.cotas_lidas        = cotas_preview
        st.session_state.admins_disponiveis = ["Todas"] + sorted(
            list(set(c['Admin'] for c in cotas_preview if c['Admin'] != "OUTROS"))
        )
        if cotas_preview:
            total_por_tipo = {}
            for c in cotas_preview:
                total_por_tipo[c['Tipo']] = total_por_tipo.get(c['Tipo'], 0) + 1
            resumo = " · ".join(f"{v} {k}" for k,v in sorted(total_por_tipo.items()))
            st.success(f"✅  **{len(cotas_preview)} cotas lidas** — {resumo}")
        else:
            st.warning("⚠️  Nenhuma cota identificada. Verifique o formato do texto.")
    else:
        st.session_state.cotas_lidas        = []
        st.session_state.admins_disponiveis = ["Todas"]


# ════════════════════════════════════════════════════════════
#  FILTROS
# ════════════════════════════════════════════════════════════
st.markdown(f"<h3 style='margin-top:8px'>⚙️ FILTROS DE BUSCA</h3>", unsafe_allow_html=True)

r1c1, r1c2, r1c3, r1c4 = st.columns(4)
tipo_bem     = r1c1.selectbox("Tipo de bem",    ["Todos","Imóvel","Automóvel","Pesados"])
admin_filtro = r1c2.selectbox("Administradora", st.session_state.admins_disponiveis)
min_c        = r1c3.number_input("Crédito mínimo (R$)", 0.0, step=1000.0, value=60_000.0,  format="%.2f")
max_c        = r1c4.number_input("Crédito máximo (R$)", 0.0, step=1000.0, value=710_000.0, format="%.2f")

r2c1, r2c2, r2c3 = st.columns(3)
max_e  = r2c1.number_input("Entrada máxima (R$)", 0.0, step=1000.0, value=200_000.0, format="%.2f")
max_p  = r2c2.number_input("Parcela máxima (R$)", 0.0, step=100.0,  value=4_500.0,   format="%.2f")
max_k  = r2c3.slider("Custo efetivo máximo (%)", 0.0, 100.0, 55.0, 0.5, format="%.1f%%")
max_k_dec = max_k / 100.0

st.markdown("")

# ════════════════════════════════════════════════════════════
#  BOTÃO DE BUSCA
# ════════════════════════════════════════════════════════════
col_btn, col_info = st.columns([2, 3])
with col_btn:
    buscar = st.button("🔍  LOCALIZAR OPORTUNIDADES", type="primary")
with col_info:
    if st.session_state.cotas_lidas:
        n = len(st.session_state.cotas_lidas)
        st.markdown(
            f"<p style='color:{GOLD};font-size:.85rem;margin-top:10px'>"
            f"🎯 {n} cota{'s' if n!=1 else ''} disponível{'is' if n!=1 else ''} para análise</p>",
            unsafe_allow_html=True
        )

if buscar:
    if not texto_site:
        st.error("❌  Cole os dados das cotas antes de buscar.")
    elif not st.session_state.cotas_lidas:
        st.error("❌  Nenhuma cota identificada no texto.")
    else:
        with st.spinner("🔍  Analisando combinações..."):
            _hash = gerar_hash(texto_site, min_c, max_c, max_e, max_p, max_k_dec, tipo_bem, admin_filtro)
            df = buscar_cached(_hash, texto_site, min_c, max_c, max_e, max_p, max_k_dec, tipo_bem, admin_filtro)

        st.session_state.df_resultado = df

        # gera exportações logo após a busca, enquanto df está fresco
        if df is not None and not df.empty:
            ts = datetime.now().strftime('%Y%m%d_%H%M')
            st.session_state.export_ts = ts
            # PDF
            try:
                st.session_state.pdf_bytes = gerar_pdf_bytes(df.head(200))
            except Exception as ex:
                st.session_state.pdf_bytes = None
                st.warning(f"PDF: {ex}")
            # Excel
            try:
                st.session_state.excel_bytes = gerar_excel_bytes(df, st.session_state.cotas_lidas)
            except Exception as ex:
                st.session_state.excel_bytes = None
                st.warning(f"Excel: {ex}")
        else:
            st.session_state.pdf_bytes   = None
            st.session_state.excel_bytes = None


# ════════════════════════════════════════════════════════════
#  RESULTADOS
# ════════════════════════════════════════════════════════════
if st.session_state.df_resultado is not None:
    df_show = st.session_state.df_resultado

    if df_show.empty:
        st.warning("🔎  Nenhuma combinação encontrada. Tente ampliar os filtros.")
    else:
        st.markdown(f"<h3 style='margin-top:24px'>📊 RESULTADO DA ANÁLISE</h3>", unsafe_allow_html=True)

        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("Oportunidades",    f"{len(df_show)}")
        m2.metric("Menor custo",      fmt_pct(df_show['CUSTO EFETIVO %'].min()))
        m3.metric("Menor entrada",    fmt_brl(df_show['ENTRADA TOTAL'].min()))
        m4.metric("Maior crédito",    fmt_brl(df_show['CRÉDITO TOTAL'].max()))
        ouro = len(df_show[df_show['STATUS'].str.contains("OURO|IMPERDÍVEL")])
        m5.metric("💎 Ouro/Imperdível", str(ouro))

        st.markdown("")

        # colunas formatadas em BR para exibição na tabela
        df_exib = df_show.copy()
        for col in ('CRÉDITO TOTAL','ENTRADA TOTAL','SALDO DEVEDOR','CUSTO TOTAL','PARCELA MENSAL'):
            df_exib[col] = df_exib[col].apply(fmt_brl)
        for col in ('ENTRADA %','CUSTO EFETIVO %'):
            df_exib[col] = df_exib[col].apply(fmt_pct)

        colunas_tabela = [c for c in df_exib.columns if c != 'DETALHES']
        st.dataframe(df_exib[colunas_tabela], hide_index=True, use_container_width=True, height=420)

        with st.expander("🔎  Ver detalhes das combinações (IDs das cotas)"):
            st.dataframe(
                df_exib[['STATUS','ADMINISTRADORA','IDS','CUSTO EFETIVO %','DETALHES']],
                hide_index=True, use_container_width=True,
            )

        if st.session_state.cotas_lidas:
            with st.expander("📋  Ver cotas lidas individualmente"):
                df_c = pd.DataFrame(st.session_state.cotas_lidas).copy()
                for col in ('Crédito','Entrada','Parcela','Saldo','CustoTotal'):
                    df_c[col] = df_c[col].apply(fmt_brl)
                df_c['EntradaPct'] = df_c['EntradaPct'].apply(fmt_pct)
                st.dataframe(df_c, hide_index=True, use_container_width=True)

        # ── DOWNLOADS ──
        st.markdown(f"<h3 style='margin-top:20px'>⬇️ EXPORTAR</h3>", unsafe_allow_html=True)
        dl1, dl2, dl3 = st.columns(3)
        ts = st.session_state.export_ts or datetime.now().strftime('%Y%m%d_%H%M')

        csv_bytes = df_show.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
        dl1.download_button(
            label="📄  Baixar CSV",
            data=csv_bytes,
            file_name=f"sniper_{ts}.csv",
            mime="text/csv",
            use_container_width=True,
        )

        if st.session_state.excel_bytes:
            dl2.download_button(
                label="📊  Baixar Excel",
                data=st.session_state.excel_bytes,
                file_name=f"sniper_{ts}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        else:
            dl2.warning("⚠️ Excel não gerado.")

        if st.session_state.pdf_bytes:
            dl3.download_button(
                label="📑  Baixar PDF",
                data=st.session_state.pdf_bytes,
                file_name=f"sniper_{ts}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            dl3.warning("⚠️ PDF não gerado.")


# ════════════════════════════════════════════════════════════
#  RODAPÉ
# ════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    f"<hr style='border:1px solid {BORDER}'>"
    f"<p style='text-align:center;color:{BORDER};font-size:.72rem;letter-spacing:2px'>"
    f"JBS SNIPER · FERRAMENTA EXCLUSIVA · {datetime.now().year}</p>",
    unsafe_allow_html=True
)
