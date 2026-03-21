# ============================================================
#  JBS SNIPER — app.py  (versão refatorada)
#  Melhorias: motor otimizado, regex defensivo, cache,
#             UI polida, PDF corrigido, multi-usuário seguro
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

# ── Favicon / ícone ─────────────────────────────────────────
_favicon = "logo_pdf.png" if os.path.exists("logo_pdf.png") else "🎯"

st.set_page_config(
    page_title="JBS SNIPER",
    page_icon=_favicon,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Paleta ──────────────────────────────────────────────────
GOLD   = "#84754e"
BEIGE  = "#ecece4"
BG     = "#0e1117"
CARD   = "#1c1f26"
BORDER = "#2e3340"

# ── CSS global ──────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@300;400;600;700&family=Barlow+Condensed:wght@400;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Barlow', sans-serif;
}}
.stApp {{
    background-color: {BG};
    color: {BEIGE};
}}

/* ── Botão principal ── */
.stButton > button {{
    width: 100%;
    background: linear-gradient(135deg, {GOLD} 0%, #6b5e3d 100%);
    color: #fff;
    border: none;
    border-radius: 8px;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 14px 0;
    transition: all .2s ease;
    box-shadow: 0 4px 15px rgba(132,117,78,.3);
}}
.stButton > button:hover {{
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(132,117,78,.45);
}}
.stButton > button:active {{
    transform: translateY(0);
}}

/* ── Inputs ── */
.stTextArea textarea,
.stNumberInput input,
.stSelectbox > div > div {{
    background-color: {CARD} !important;
    color: {BEIGE} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
    font-family: 'Barlow', sans-serif !important;
}}
.stTextArea textarea:focus,
.stNumberInput input:focus {{
    border-color: {GOLD} !important;
    box-shadow: 0 0 0 2px rgba(132,117,78,.25) !important;
}}

/* ── Labels ── */
label, .stSelectbox label, .stNumberInput label, .stTextArea label {{
    color: {BEIGE} !important;
    font-size: .78rem !important;
    font-weight: 600 !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
}}

/* ── Slider ── */
.stSlider .stSlider > div {{
    color: {GOLD};
}}
.stSlider [data-baseweb="slider"] div[role="slider"] {{
    background-color: {GOLD} !important;
}}

/* ── Títulos ── */
h1, h2, h3, h4 {{
    font-family: 'Barlow Condensed', sans-serif !important;
    color: {GOLD} !important;
    letter-spacing: 1px;
}}

/* ── Dataframe ── */
.stDataFrame {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    overflow: hidden;
}}
.stDataFrame [data-testid="stDataFrameContainer"] {{
    border-radius: 8px;
}}

/* ── Expander ── */
.streamlit-expanderHeader {{
    background-color: {CARD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
    color: {BEIGE} !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: 1px !important;
}}

/* ── Métricas ── */
[data-testid="metric-container"] {{
    background-color: {CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 14px 18px;
}}
[data-testid="metric-container"] label {{
    color: {GOLD} !important;
    font-size: .72rem !important;
    letter-spacing: 1.5px !important;
}}
[data-testid="metric-container"] [data-testid="stMetricValue"] {{
    color: {BEIGE} !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 1.6rem !important;
}}

/* ── Separador ── */
hr {{ border-color: {BORDER}; margin: 8px 0 20px; }}

/* ── Mensagens ── */
.stSuccess, .stError, .stWarning, .stInfo {{
    border-radius: 8px !important;
    font-family: 'Barlow', sans-serif !important;
}}

/* ── Progress bar ── */
.stProgress > div > div > div {{
    background-color: {GOLD} !important;
}}

/* ── Scrollbar ── */
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
            Ferramenta Exclusiva de Análise de Consórcio · JBS
        </p>
    </div>
    """, unsafe_allow_html=True)

st.markdown(f"<hr style='border:1px solid {GOLD};margin-top:4px'>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
#  UTILITÁRIOS
# ════════════════════════════════════════════════════════════

def limpar_moeda(texto: str) -> float:
    """Converte string de moeda BR/US para float de forma segura."""
    if not texto:
        return 0.0
    try:
        t = (str(texto)
             .lower().strip()
             .replace('\xa0', '').replace('&nbsp;', '')
             .replace('r$', '').replace(' ', ''))
        t = re.sub(r'[^\d\.,]', '', t)
        if not t:
            return 0.0
        if ',' in t and '.' in t:
            return float(t.replace('.', '').replace(',', '.'))
        if ',' in t:
            partes = t.split(',')
            if len(partes) == 2 and len(partes[1]) <= 2:
                return float(t.replace(',', '.'))
            return float(t.replace(',', ''))
        if '.' in t:
            partes = t.split('.')
            if len(partes) == 2 and len(partes[1]) == 2:
                return float(t)
            return float(t.replace('.', ''))
        return float(t)
    except Exception:
        return 0.0


def _detectar_tipo(bloco_lower: str) -> str:
    if any(k in bloco_lower for k in ('imóvel', 'imovel', 'apartamento', 'casa', 'terreno', 'comercial')):
        return "Imóvel"
    if any(k in bloco_lower for k in ('caminhão', 'caminhao', 'pesado', 'truck', 'ônibus', 'onibus')):
        return "Pesados"
    if any(k in bloco_lower for k in ('automóvel', 'automovel', 'veículo', 'veiculo', 'carro', 'moto')):
        return "Automóvel"
    return "Geral"


# ════════════════════════════════════════════════════════════
#  EXTRAÇÃO — regex defensivo + compilado
# ════════════════════════════════════════════════════════════

_RE_CREDITO = re.compile(
    r'(?:cr[eé]dito|bem|valor[\s_]do[\s_]bem|valor[\s_]carta)[^\d\n]{0,25}?R\$\s*([\d\.,]+)',
    re.IGNORECASE
)
_RE_ENTRADA = re.compile(
    r'(?:entrada|[aá]gio|lance[\s_]fixo|pago|quero)[^\d\n]{0,25}?R\$\s*([\d\.,]+)',
    re.IGNORECASE
)
_RE_PARCELA = re.compile(r'(\d+)\s*[xX]\s*R?\$?\s*([\d\.,]+)', re.IGNORECASE)
_RE_MOEDA   = re.compile(r'R\$\s*([\d\.,]+)', re.IGNORECASE)

_ADMINS = [
    'BRADESCO','SANTANDER','ITAÚ','ITAU','PORTO SEGURO','PORTO',
    'CAIXA','BANCO DO BRASIL','BB','RODOBENS','EMBRACON',
    'ANCORA','ÂNCORA','MYCON','SICREDI','SICOOB','MAPFRE',
    'HS','YAMAHA','ZEMA','BANCORBRÁS','BANCORBRAS','SERVOPA',
    'WOOP','SOMPO','MAGALU','EMBRACON',
]


def extrair_dados_universal(texto_copiado: str, tipo_selecionado: str) -> list:
    """
    Extrai cotas de consórcio de texto livre.
    Robusto a falhas: cada bloco tem try/except independente.
    """
    lista_cotas = []
    if not texto_copiado or not texto_copiado.strip():
        return lista_cotas

    # normaliza quebras de linha e espaços
    texto_limpo = "\n".join(
        ln.strip() for ln in texto_copiado.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        if ln.strip()
    )

    # tenta dividir por palavras-chave de tipo
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

            # ── Administradora ──────────────────────────────
            admin = next(
                (adm.upper() for adm in _ADMINS if adm.lower() in bloco_lower),
                "OUTROS"
            )
            if admin == "OUTROS" and "r$" not in bloco_lower:
                continue

            # ── Tipo de bem ─────────────────────────────────
            tipo_cota = _detectar_tipo(bloco_lower)

            # ── Crédito ─────────────────────────────────────
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

            # tipo por valor quando ambíguo
            if tipo_cota == "Geral":
                tipo_cota = "Imóvel" if credito > 250000 else "Automóvel"

            # aplica filtro de tipo selecionado (se não for "Todos" / "Geral")
            if tipo_selecionado not in ("Todos", "Geral") and tipo_cota != tipo_selecionado:
                continue

            # ── Entrada ─────────────────────────────────────
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

            # ── Parcelas ────────────────────────────────────
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

            # fallback saldo: estimativa conservadora
            if saldo_devedor <= 0:
                saldo_devedor = max(credito * 1.25 - entrada, credito * 0.20)

            custo_total = entrada + saldo_devedor

            lista_cotas.append({
                'ID':         id_cota,
                'Admin':      admin,
                'Tipo':       tipo_cota,
                'Crédito':    credito,
                'Entrada':    entrada,
                'Parcela':    parcela_teto,
                'Saldo':      saldo_devedor,
                'CustoTotal': custo_total,
                'EntradaPct': entrada / credito,
            })
            id_cota += 1

        except Exception:
            # bloco problemático: segue para o próximo sem quebrar o app
            continue

    return lista_cotas


# ════════════════════════════════════════════════════════════
#  MOTOR DE BUSCA — otimizado com pruning precoce
# ════════════════════════════════════════════════════════════

def _classificar_status(custo_real: float) -> str:
    if   custo_real <= 0.20: return "💎 OURO"
    elif custo_real <= 0.35: return "🔥 IMPERDÍVEL"
    elif custo_real <= 0.45: return "✨ EXCELENTE"
    elif custo_real <= 0.50: return "✅ OPORTUNIDADE"
    return "⚠️ PADRÃO"


def processar_combinacoes(
    cotas: list,
    min_cred: float, max_cred: float,
    max_ent: float,  max_parc: float,
    max_custo: float,
    tipo_filtro: str, admin_filtro: str
) -> pd.DataFrame:
    """
    Motor combinatório otimizado:
    - pré-filtra cotas individualmente antes de combinar
    - ordena por EntradaPct para pruning mais eficiente
    - early-exit por administradora (MAX_POR_ADMIN)
    - tolerância de 5% nos filtros de entrada e parcela
    """
    MAX_POR_ADMIN = 400
    ENT_TOL       = 1.05
    PARC_TOL      = 1.05

    # ── pré-filtro individual ────────────────────────────────
    filtradas = [
        c for c in cotas
        if (tipo_filtro  in ("Todos", "Geral") or c['Tipo']  == tipo_filtro)
        and (admin_filtro == "Todas"            or c['Admin'] == admin_filtro)
        and c['Admin']   != "OUTROS"
        and c['Entrada'] <= max_ent * ENT_TOL
        and c['Crédito'] <= max_cred
        and c['Crédito'] >= min_cred * 0.5   # permite combinar cotas menores
    ]

    if not filtradas:
        return pd.DataFrame()

    cotas_por_admin: dict = {}
    for c in filtradas:
        cotas_por_admin.setdefault(c['Admin'], []).append(c)

    resultados = []
    progress   = st.progress(0)
    total_adm  = len(cotas_por_admin)

    for adm_idx, (admin, grupo) in enumerate(cotas_por_admin.items()):
        progress.progress(int((adm_idx + 1) / total_adm * 100))

        # ordena por entrada ascendente → pruning mais agressivo
        grupo.sort(key=lambda x: x['Entrada'])
        n = len(grupo)
        count_admin = 0

        for r in range(1, 7):
            if count_admin >= MAX_POR_ADMIN:
                break

            for combo in itertools.combinations(grupo, r):
                if count_admin >= MAX_POR_ADMIN:
                    break

                soma_ent = sum(c['Entrada'] for c in combo)

                # ── PRUNING PRINCIPAL ────────────────────────
                # Como grupo está ordenado por entrada ascendente,
                # os primeiros r elementos são os menores.
                # Se já estouram, qualquer outra combinação de tamanho r
                # com índices maiores também estouraria → break da sub-árvore.
                if soma_ent > max_ent * ENT_TOL:
                    # verifica se é impossível melhorar nessa profundidade
                    min_combo_ent = sum(c['Entrada'] for c in grupo[:r])
                    if min_combo_ent > max_ent * ENT_TOL:
                        break  # sai do loop de combinações para este r
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

                # ── monta resultado ──────────────────────────
                ids      = " + ".join(str(c['ID']) for c in combo)
                detalhes = " || ".join(
                    f"[ID {c['ID']}] {c['Admin']} · R$ {c['Crédito']:,.0f}" for c in combo
                )
                prazo = int(soma_saldo / soma_parc) if soma_parc > 0 else 0

                resultados.append({
                    'STATUS':         _classificar_status(custo_real),
                    'ADMINISTRADORA': admin,
                    'TIPO':           combo[0]['Tipo'],
                    'IDS':            ids,
                    'CRÉDITO TOTAL':  soma_cred,
                    'ENTRADA TOTAL':  soma_ent,
                    'ENTRADA %':      (soma_ent / soma_cred) * 100,
                    'SALDO DEVEDOR':  soma_saldo,
                    'CUSTO TOTAL':    custo_total,
                    'PRAZO (meses)':  prazo,
                    'PARCELA MENSAL': soma_parc,
                    'CUSTO EFETIVO %':custo_real * 100,
                    'DETALHES':       detalhes,
                })
                count_admin += 1

    progress.empty()

    if not resultados:
        return pd.DataFrame()

    return (pd.DataFrame(resultados)
              .sort_values('CUSTO EFETIVO %')
              .reset_index(drop=True))


# ════════════════════════════════════════════════════════════
#  CACHE — evita recomputação para o mesmo input
# ════════════════════════════════════════════════════════════

@st.cache_data(max_entries=30, ttl=600, show_spinner=False)
def buscar_cached(
    _hash: str,
    texto: str,
    min_cred: float, max_cred: float,
    max_ent: float,  max_parc: float,
    max_custo: float,
    tipo: str, admin: str
) -> pd.DataFrame:
    """
    Wrapper cacheado do motor de busca.
    _hash é a chave; parâmetros reais são passados para a função.
    Cache compartilhado entre sessões: dois usuários com mesmo
    input+filtros recebem resultado instantaneamente.
    """
    cotas = extrair_dados_universal(texto, tipo)
    if not cotas:
        return pd.DataFrame()
    return processar_combinacoes(cotas, min_cred, max_cred, max_ent, max_parc, max_custo, tipo, admin)


def gerar_hash(texto: str, *args) -> str:
    payload = texto + "|".join(str(a) for a in args)
    return hashlib.md5(payload.encode()).hexdigest()


# ════════════════════════════════════════════════════════════
#  PDF — geração limpa sem crash de encoding
# ════════════════════════════════════════════════════════════

def _sanitizar(texto: str) -> str:
    """Remove emojis e caracteres fora do latin-1 para o FPDF."""
    return texto.encode('latin-1', 'replace').decode('latin-1')


class RelatorioPDF(FPDF):
    def header(self):
        self.set_fill_color(132, 117, 78)
        self.rect(0, 0, 297, 20, 'F')
        if os.path.exists("logo_pdf.png"):
            self.image('logo_pdf.png', 4, 2, 30)
        self.set_font('Arial', 'B', 14)
        self.set_text_color(255, 255, 255)
        self.set_xy(38, 5)
        self.cell(0, 10, 'JBS SNIPER  |  RELATÓRIO DE OPORTUNIDADES', 0, 1, 'L')
        self.set_font('Arial', '', 7)
        self.set_xy(38, 13)
        self.cell(0, 5, f'Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'L')
        self.ln(4)

    def footer(self):
        self.set_y(-12)
        self.set_font('Arial', 'I', 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, f'JBS SNIPER  |  Página {self.page_no()}', 0, 0, 'C')


def gerar_pdf(df: pd.DataFrame) -> bytes:
    pdf = RelatorioPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    # cabeçalho da tabela
    pdf.set_fill_color(236, 236, 228)
    pdf.set_text_color(30, 30, 30)
    pdf.set_font('Arial', 'B', 7)

    cols = ["STS", "ADMIN", "TIPO", "CRÉDITO", "ENTRADA", "ENT%", "SALDO", "CUSTO TOT", "PRZ", "PARCELA", "EFETIVO%", "DETALHES"]
    wids = [18,    20,      16,     26,         26,        10,     26,      26,          8,     22,        13,         76]

    for h, w in zip(cols, wids):
        pdf.cell(w, 7, h, 1, 0, 'C', True)
    pdf.ln()

    pdf.set_font('Arial', '', 6.5)
    pdf.set_fill_color(245, 245, 240)

    for i, (_, row) in enumerate(df.iterrows()):
        fill = (i % 2 == 0)
        pdf.set_fill_color(245, 245, 240) if fill else pdf.set_fill_color(255, 255, 255)

        pdf.cell(wids[0],  6, _sanitizar(str(row['STATUS']))[:8],           1, 0, 'C', fill)
        pdf.cell(wids[1],  6, _sanitizar(str(row['ADMINISTRADORA']))[:12],   1, 0, 'C', fill)
        pdf.cell(wids[2],  6, _sanitizar(str(row['TIPO']))[:10],             1, 0, 'C', fill)
        pdf.cell(wids[3],  6, f"R$ {row['CRÉDITO TOTAL']:,.0f}",             1, 0, 'R', fill)
        pdf.cell(wids[4],  6, f"R$ {row['ENTRADA TOTAL']:,.0f}",             1, 0, 'R', fill)
        pdf.cell(wids[5],  6, f"{row['ENTRADA %']:.1f}%",                    1, 0, 'C', fill)
        pdf.cell(wids[6],  6, f"R$ {row['SALDO DEVEDOR']:,.0f}",             1, 0, 'R', fill)
        pdf.cell(wids[7],  6, f"R$ {row['CUSTO TOTAL']:,.0f}",               1, 0, 'R', fill)
        pdf.cell(wids[8],  6, str(int(row['PRAZO (meses)'])),                1, 0, 'C', fill)
        pdf.cell(wids[9],  6, f"R$ {row['PARCELA MENSAL']:,.0f}",            1, 0, 'R', fill)
        pdf.cell(wids[10], 6, f"{row['CUSTO EFETIVO %']:.1f}%",              1, 0, 'C', fill)
        pdf.cell(wids[11], 6, _sanitizar(str(row['DETALHES']))[:55],         1, 1, 'L', fill)

    return bytes(pdf.output(dest='S'))


# ════════════════════════════════════════════════════════════
#  ESTADO DA SESSÃO
# ════════════════════════════════════════════════════════════
if 'df_resultado'       not in st.session_state: st.session_state.df_resultado       = None
if 'admins_disponiveis' not in st.session_state: st.session_state.admins_disponiveis = ["Todas"]
if 'cotas_lidas'        not in st.session_state: st.session_state.cotas_lidas        = []


# ════════════════════════════════════════════════════════════
#  BLOCO DE ENTRADA DE DADOS
# ════════════════════════════════════════════════════════════
with st.expander("📋  DADOS DO SITE  —  Cole o texto das cotas aqui", expanded=True):
    texto_site = st.text_area(
        "Texto copiado do portal / WhatsApp / planilha",
        height=130,
        placeholder="Cole aqui o texto com as cotas de consórcio...\n\nEx:\nBradesco Imóvel\nCrédito: R$ 400.000\nEntrada: R$ 80.000\n180x R$ 2.100,00",
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

            resumo = " · ".join(f"{v} {k}" for k, v in sorted(total_por_tipo.items()))
            st.success(f"✅  **{len(cotas_preview)} cotas lidas** — {resumo}")
        else:
            st.warning("⚠️  Nenhuma cota identificada. Verifique o formato do texto colado.")
    else:
        st.session_state.cotas_lidas        = []
        st.session_state.admins_disponiveis = ["Todas"]


# ════════════════════════════════════════════════════════════
#  FILTROS
# ════════════════════════════════════════════════════════════
st.markdown(f"<h3 style='margin-top:8px'>⚙️ FILTROS DE BUSCA</h3>", unsafe_allow_html=True)

row1_c1, row1_c2, row1_c3, row1_c4 = st.columns(4)

tipo_bem     = row1_c1.selectbox("Tipo de bem",      ["Todos", "Imóvel", "Automóvel", "Pesados"])
admin_filtro = row1_c2.selectbox("Administradora",   st.session_state.admins_disponiveis)
min_c        = row1_c3.number_input("Crédito mínimo (R$)", 0.0, step=1000.0, value=60_000.0,  format="%.2f")
max_c        = row1_c4.number_input("Crédito máximo (R$)", 0.0, step=1000.0, value=710_000.0, format="%.2f")

row2_c1, row2_c2, row2_c3 = st.columns(3)
max_e  = row2_c1.number_input("Entrada máxima (R$)",  0.0, step=1000.0, value=200_000.0, format="%.2f")
max_p  = row2_c2.number_input("Parcela máxima (R$)",  0.0, step=100.0,  value=4_500.0,   format="%.2f")
max_k  = row2_c3.slider(
    "Custo efetivo máximo (%)",
    min_value=0.0, max_value=100.0, value=55.0, step=0.5,
    format="%.1f%%"
)
max_k_decimal = max_k / 100.0

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
            f"🎯 {n} cota{'s' if n!=1 else ''} disponível{'is' if n!=1 else ''} para análise combinatória</p>",
            unsafe_allow_html=True
        )

if buscar:
    if not texto_site:
        st.error("❌  Cole os dados das cotas antes de buscar.")
    elif not st.session_state.cotas_lidas:
        st.error("❌  Nenhuma cota identificada no texto. Verifique o formato.")
    else:
        with st.spinner("🔍  Analisando combinações..."):
            _hash = gerar_hash(texto_site, min_c, max_c, max_e, max_p, max_k_decimal, tipo_bem, admin_filtro)
            df = buscar_cached(
                _hash, texto_site,
                min_c, max_c, max_e, max_p, max_k_decimal,
                tipo_bem, admin_filtro
            )
        st.session_state.df_resultado = df


# ════════════════════════════════════════════════════════════
#  RESULTADOS
# ════════════════════════════════════════════════════════════
if st.session_state.df_resultado is not None:
    df_show = st.session_state.df_resultado

    if df_show.empty:
        st.warning("🔎  Nenhuma combinação encontrada com os filtros atuais. Tente ampliar os limites.")
    else:
        # ── métricas de resumo ───────────────────────────────
        st.markdown(f"<h3 style='margin-top:24px'>📊 RESULTADO DA ANÁLISE</h3>", unsafe_allow_html=True)

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Oportunidades",    f"{len(df_show)}")
        m2.metric("Menor custo",      f"{df_show['CUSTO EFETIVO %'].min():.1f}%")
        m3.metric("Menor entrada",    f"R$ {df_show['ENTRADA TOTAL'].min():,.0f}")
        m4.metric("Maior crédito",    f"R$ {df_show['CRÉDITO TOTAL'].max():,.0f}")

        ouro = len(df_show[df_show['STATUS'].str.contains("OURO|IMPERDÍVEL")])
        m5.metric("💎 Ouro/Imperdível", str(ouro))

        st.markdown("")

        # ── tabela ──────────────────────────────────────────
        col_config = {
            "CRÉDITO TOTAL":   st.column_config.NumberColumn("Crédito",    format="R$ %.0f"),
            "ENTRADA TOTAL":   st.column_config.NumberColumn("Entrada",    format="R$ %.0f"),
            "ENTRADA %":       st.column_config.NumberColumn("Entrada %",  format="%.1f %%"),
            "SALDO DEVEDOR":   st.column_config.NumberColumn("Saldo Dev.", format="R$ %.0f"),
            "CUSTO TOTAL":     st.column_config.NumberColumn("Custo Tot.", format="R$ %.0f"),
            "PARCELA MENSAL":  st.column_config.NumberColumn("Parcela",    format="R$ %.0f"),
            "PRAZO (meses)":   st.column_config.NumberColumn("Prazo",      format="%d m"),
            "CUSTO EFETIVO %": st.column_config.NumberColumn("Custo Ef.%", format="%.2f %%"),
        }

        # oculta coluna de detalhes para deixar tabela limpa;
        # exibe num expander abaixo
        colunas_tabela = [c for c in df_show.columns if c != 'DETALHES']

        st.dataframe(
            df_show[colunas_tabela],
            column_config=col_config,
            hide_index=True,
            use_container_width=True,
            height=420,
        )

        # ── detalhes das cotas ───────────────────────────────
        with st.expander("🔎  Ver detalhes das combinações (IDs das cotas)"):
            st.dataframe(
                df_show[['STATUS', 'ADMINISTRADORA', 'IDS', 'CUSTO EFETIVO %', 'DETALHES']],
                column_config={
                    "CUSTO EFETIVO %": st.column_config.NumberColumn(format="%.2f %%"),
                },
                hide_index=True,
                use_container_width=True,
            )

        # ── cotas lidas ──────────────────────────────────────
        if st.session_state.cotas_lidas:
            with st.expander("📋  Ver cotas lidas individualmente"):
                df_cotas = pd.DataFrame(st.session_state.cotas_lidas)
                st.dataframe(
                    df_cotas,
                    column_config={
                        "Crédito":    st.column_config.NumberColumn(format="R$ %.0f"),
                        "Entrada":    st.column_config.NumberColumn(format="R$ %.0f"),
                        "Parcela":    st.column_config.NumberColumn(format="R$ %.0f"),
                        "Saldo":      st.column_config.NumberColumn(format="R$ %.0f"),
                        "CustoTotal": st.column_config.NumberColumn("Custo Total", format="R$ %.0f"),
                        "EntradaPct": st.column_config.NumberColumn("Entrada %",   format="%.1f %%"),
                    },
                    hide_index=True,
                    use_container_width=True,
                )

        # ── downloads ────────────────────────────────────────
        st.markdown(f"<h3 style='margin-top:20px'>⬇️ EXPORTAR</h3>", unsafe_allow_html=True)
        dl1, dl2, dl3 = st.columns(3)

        # CSV
        csv_bytes = df_show.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
        dl1.download_button(
            label="📄  Baixar CSV",
            data=csv_bytes,
            file_name=f"sniper_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

        # Excel
        try:
            excel_buf = BytesIO()
            with pd.ExcelWriter(excel_buf, engine='openpyxl') as writer:
                df_show.to_excel(writer, index=False, sheet_name='Oportunidades')
                if st.session_state.cotas_lidas:
                    pd.DataFrame(st.session_state.cotas_lidas).to_excel(
                        writer, index=False, sheet_name='Cotas Lidas'
                    )
            dl2.download_button(
                label="📊  Baixar Excel",
                data=excel_buf.getvalue(),
                file_name=f"sniper_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception:
            dl2.info("Excel indisponível. Instale openpyxl.")

        # PDF
        try:
            pdf_bytes = gerar_pdf(df_show.head(200))  # limita a 200 linhas no PDF
            dl3.download_button(
                label="📑  Baixar PDF",
                data=pdf_bytes,
                file_name=f"sniper_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            dl3.warning(f"PDF: {e}")


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
