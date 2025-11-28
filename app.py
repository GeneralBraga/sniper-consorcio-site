
import streamlit as st
import pandas as pd
import re
import itertools
from io import BytesIO
from fpdf import FPDF
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# --- CONFIGURAÇÃO DA PÁGINA E MARCA ---
# Cores da JBS Contempladas
COLOR_PRIMARY = "#84754e"  # Ouro/Bronze
COLOR_BG = "#ecece4"       # Bege Claro
COLOR_TEXT = "#000000"     # Preto

st.set_page_config(page_title="JBS Contempladas | Sistema Sniper", page_icon="🏛️", layout="wide")

# CSS PERSONALIZADO (BRANDING)
st.markdown(f"""
<style>
    /* Fundo da Aplicação */
    .stApp {{
        background-color: {COLOR_BG};
    }}
    
    /* Botões */
    .stButton>button {{
        width: 100%;
        background-color: {COLOR_PRIMARY};
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        padding: 0.5rem 1rem;
        text-transform: uppercase;
        transition: all 0.3s ease;
    }}
    .stButton>button:hover {{
        background-color: #6b5e3d; /* Um tom mais escuro do ouro */
        color: white;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }}
    
    /* Inputs */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {{
        border: 1px solid {COLOR_PRIMARY};
        border-radius: 5px;
    }}
    
    /* Títulos e Textos */
    h1, h2, h3 {{
        color: {COLOR_PRIMARY} !important;
        font-family: 'Helvetica', sans-serif;
    }}
    
    /* Expander */
    .streamlit-expanderHeader {{
        background-color: white;
        color: {COLOR_PRIMARY};
        border-radius: 5px;
    }}
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO COM LOGO ---
col_logo, col_title = st.columns([1, 4])
with col_logo:
    # Tenta carregar a logo se existir, senão mostra texto
    if os.path.exists("logo.png"):
        st.image("logo.png", width=150)
    else:
        st.markdown(f"## JBS")
with col_title:
    st.markdown(f"# Sistema de Oportunidades")
    st.markdown(f"**JBS Contempladas Consórcios** | Ferramenta Exclusiva")

st.divider()

# --- FUNÇÕES DE LÓGICA (MOTOR V24) ---
def limpar_moeda(texto):
    if not texto: return 0.0
    texto = str(texto).lower().strip().replace('\xa0', '').replace('&nbsp;', '')
    texto = re.sub(r'[^\d\.,]', '', texto)
    if not texto: return 0.0
    try:
        if ',' in texto and '.' in texto: return float(texto.replace('.', '').replace(',', '.'))
        elif ',' in texto: return float(texto.replace(',', '.'))
        elif '.' in texto:
             if len(texto.split('.')[1]) == 2: return float(texto)
             return float(texto.replace('.', ''))
        return float(texto)
    except: return 0.0

def extrair_dados_universal(texto_copiado):
    lista_cotas = []
    texto_limpo = "\n".join([line.strip() for line in texto_copiado.split('\n') if line.strip()])
    blocos = re.split(r'(?i)(?=imóvel|imovel|automóvel|automovel|veículo)', texto_limpo)
    if len(blocos) < 2: blocos = texto_limpo.split('\n\n')

    id_cota = 1
    for bloco in blocos:
        if len(bloco) < 20: continue
        bloco_lower = bloco.lower()
        
        admins = ['BRADESCO', 'SANTANDER', 'ITAÚ', 'ITAU', 'PORTO', 'CAIXA', 'BANCO DO BRASIL', 'BB', 'RODOBENS', 'EMBRACON', 'ANCORA', 'ÂNCORA', 'MYCON', 'SICREDI', 'SICOOB', 'MAPFRE', 'HS', 'YAMAHA', 'ZEMA', 'BANCORBRÁS', 'BANCORBRAS', 'SERVOPA']
        admin_encontrada = "OUTROS"
        for adm in admins:
            if adm.lower() in bloco_lower:
                admin_encontrada = adm.upper()
                break
        
        if admin_encontrada == "OUTROS" and "r$" not in bloco_lower: continue

        credito = 0.0
        match_cred = re.search(r'(?:crédito|credito|bem|valor)[^\d\n]*?R\$\s?([\d\.,]+)', bloco_lower)
        if match_cred: credito = limpar_moeda(match_cred.group(1))
        else:
            valores = re.findall(r'R\$\s?([\d\.,]+)', bloco)
            vals = sorted([limpar_moeda(v) for v in valores], reverse=True)
            if vals: credito = vals[0]

        entrada = 0.0
        match_ent = re.search(r'(?:entrada|ágio|agio|quero|pago)[^\d\n]*?R\$\s?([\d\.,]+)', bloco_lower)
        if match_ent: entrada = limpar_moeda(match_ent.group(1))
        else:
            valores = re.findall(r'R\$\s?([\d\.,]+)', bloco)
            vals = sorted([limpar_moeda(v) for v in valores], reverse=True)
            if len(vals) > 1: entrada = vals[1]

        regex_parc = r'(\d+)\s*[xX]\s*R?\$\s?([\d\.,]+)'
        todas_parcelas = re.findall(regex_parc, bloco)
        
        saldo_devedor = 0.0
        parcela_teto = 0.0
        for pz_str, vlr_str in todas_parcelas:
            pz = int(pz_str)
            vlr = limpar_moeda(vlr_str)
            saldo_devedor += (pz * vlr)
            if pz > 1 and vlr > parcela_teto: parcela_teto = vlr
            elif len(todas_parcelas) == 1: parcela_teto = vlr

        if credito > 0 and entrada > 0:
            if saldo_devedor == 0: saldo_devedor = (credito * 1.3) - entrada
            custo_total = entrada + saldo_devedor
            if credito > 5000: 
                lista_cotas.append({
                    'ID': id_cota, 'Admin': admin_encontrada, 'Crédito': credito, 'Entrada': entrada,
                    'Parcela': parcela_teto, 'Saldo': saldo_devedor, 'CustoTotal': custo_total,
                    'EntradaPct': (entrada/credito) if credito else 0
                })
                id_cota += 1
    return lista_cotas

def processar_combinacoes(cotas, min_cred, max_cred, max_ent, max_parc, max_custo):
    combinacoes_validas = []
    cotas_por_admin = {}
    for cota in cotas:
        adm = cota['Admin']
        if adm not in cotas_por_admin: cotas_por_admin[adm] = []
        cotas_por_admin[adm].append(cota)
    
    progress_bar = st.progress(0)
    total_admins = len(cotas_por_admin)
    current = 0

    for admin, grupo in cotas_por_admin.items():
        if admin == "OUTROS": continue
        current += 1
        progress_bar.progress(int((current / total_admins) * 100))
        
        if sum(c['Crédito'] for c in grupo) < min_cred: continue
        grupo.sort(key=lambda x: x['EntradaPct'])
        
        count = 0
        max_ops = 3000000 
        
        for r in range(1, 7):
            iterator = itertools.combinations(grupo, r)
            while True:
                try:
                    combo = next(iterator)
                    count += 1
                    if count > max_ops: break
                    
                    soma_ent = sum(c['Entrada'] for c in combo)
                    if soma_ent > (max_ent * 1.05): continue
                    
                    soma_cred = sum(c['Crédito'] for c in combo)
                    if soma_cred < min_cred or soma_cred > max_cred: continue
                    
                    soma_parc = sum(c['Parcela'] for c in combo)
                    if soma_parc > (max_parc * 1.05): continue
                    
                    soma_custo = sum(c['CustoTotal'] for c in combo)
                    custo_real = (soma_custo / soma_cred) - 1
                    if custo_real > max_custo: continue
                    
                    ids = " + ".join([str(c['ID']) for c in combo])
                    detalhes = " || ".join([f"[ID {c['ID']}] Cr: R$ {c['Crédito']:,.2f}" for c in combo])
                    
                    # === TERMÔMETRO JBS ===
                    status = "⚠️ PADRÃO"
                    if custo_real <= 0.20: status = "💎 OURO"
                    elif custo_real <= 0.35: status = "🔥 IMPERDÍVEL"
                    elif custo_real <= 0.45: status = "✨ EXCELENTE"
                    elif custo_real <= 0.50: status = "✅ OPORTUNIDADE"
                    
                    combinacoes_validas.append({
                        'Admin': admin, 'Status': status, 'IDs': ids,
                        'Crédito Total': soma_cred, 'Entrada Total': soma_ent,
                        'Parcela Total': soma_parc, 'Custo Real (%)': custo_real,
                        'Detalhes': detalhes
                    })
                    
                    if len([x for x in combinacoes_validas if x['Admin'] == admin]) > 150: break
                except StopIteration:
                    break
            if count > max_ops: break
            
    progress_bar.empty()
    return pd.DataFrame(combinacoes_validas)

# --- FUNÇÃO: GERAR PDF PREMIUM (PAISAGEM) ---
class PDF(FPDF):
    def header(self):
        # Cor de fundo do cabeçalho (Ouro da JBS)
        self.set_fill_color(132, 117, 78) # #84754e
        self.rect(0, 0, 297, 25, 'F') # Largura A4 Paisagem
        
        self.set_font('Arial', 'B', 15)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, 'JBS CONTEMPLADAS - RELATÓRIO DE OPORTUNIDADES', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, f'Gerado em: {datetime.now().strftime("%d/%m/%Y")}', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def gerar_pdf_premium(df):
    pdf = PDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Cabeçalho da Tabela
    pdf.set_fill_color(236, 236, 228) # Bege #ecece4
    pdf.set_text_color(0)
    pdf.set_font("Arial", 'B', 10)
    
    cols = [40, 40, 40, 40, 40, 30, 47] # Larguras
    headers = ["Admin", "Status", "Crédito", "Entrada", "Parcela", "Custo %", "Detalhes (Resumo)"]
    
    for i, h in enumerate(headers):
        pdf.cell(cols[i], 10, h, 1, 0, 'C', True)
    pdf.ln()
    
    # Linhas
    pdf.set_font("Arial", size=9)
    for index, row in df.iterrows():
        # Cores para o Status
        pdf.set_text_color(0)
        if "OURO" in row['Status']: pdf.set_text_color(0, 100, 0)
        elif "IMPERDÍVEL" in row['Status']: pdf.set_text_color(200, 0, 0)
        
        pdf.cell(cols[0], 10, str(row['Admin']), 1, 0, 'C')
        pdf.cell(cols[1], 10, str(row['Status']), 1, 0, 'C')
        
        pdf.set_text_color(0) # Volta para preto
        pdf.cell(cols[2], 10, f"R$ {row['Crédito Total']:,.2f}", 1, 0, 'R')
        pdf.cell(cols[3], 10, f"R$ {row['Entrada Total']:,.2f}", 1, 0, 'R')
        pdf.cell(cols[4], 10, f"R$ {row['Parcela Total']:,.2f}", 1, 0, 'R')
        pdf.cell(cols[5], 10, f"{row['Custo Real (%)']*100:.2f}%", 1, 0, 'C')
        
        # Detalhes (Corta se for muito grande para caber na linha)
        detalhe_curto = row['Detalhes'][:30] + "..." if len(row['Detalhes']) > 30 else row['Detalhes']
        pdf.cell(cols[6], 10, detalhe_curto, 1, 1, 'L')
        
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- FUNÇÃO: GOOGLE SHEETS ---
def exportar_para_google_sheets(df, nome_planilha="JBS_Oportunidades"):
    # ATENÇÃO: Requer arquivo de credenciais 'secrets.toml' ou configuração no Streamlit Cloud
    # Se não tiver configurado, retorna None
    try:
        if "gcp_service_account" not in st.secrets:
            return None, "Configuração de API do Google não encontrada."
            
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        
        # Cria ou abre a planilha
        try:
            sh = client.open(nome_planilha)
        except:
            sh = client.create(nome_planilha)
            
        worksheet = sh.get_worksheet(0)
        worksheet.clear()
        
        # Prepara dados para GSheets (converte números para string com vírgula se necessário, ou float direto)
        # O GSpread aceita DataFrames direto
        set_with_dataframe(worksheet, df)
        
        # Retorna URL
        return sh.url, "Sucesso"
    except Exception as e:
        return None, str(e)

# --- INTERFACE PRINCIPAL ---

with st.expander("📋 COLE OS DADOS AQUI", expanded=True):
    texto_site = st.text_area("Dados do Site:", height=100)

st.subheader("Filtros JBS")
c1, c2, c3 = st.columns(3)
min_c = c1.number_input("Crédito Mín", 640000, step=10000)
max_c = c1.number_input("Crédito Máx", 710000, step=10000)
max_e = c2.number_input("Entrada Máx", 280000, step=5000)
max_p = c2.number_input("Parcela Máx", 4500, step=100)
max_k = c3.slider("Custo Máx (%)", 0.0, 1.0, 0.55, 0.01)

if st.button("🔍 LOCALIZAR OPORTUNIDADES", type="primary"):
    if texto_site:
        cotas = extrair_dados_universal(texto_site)
        if len(cotas) > 0:
            df = processar_combinacoes(cotas, min_c, max_c, max_e, max_p, max_k)
            if not df.empty:
                df_show = df.sort_values(by='Custo Real (%)')
                st.success(f"{len(df_show)} Oportunidades Encontradas!")
                
                # Mostra na tela
                st.dataframe(
                    df_show,
                    column_config={
                        "Crédito Total": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Entrada Total": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Parcela Total": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Custo Real (%)": st.column_config.NumberColumn(format="%.2f %%"),
                    }, hide_index=True
                )
                
                col_pdf, col_sheet = st.columns(2)
                
                # 1. BOTÃO PDF (Funciona sempre)
                pdf_bytes = gerar_pdf_premium(df_show)
                col_pdf.download_button(
                    label="📄 Baixar PDF Premium (Paisagem)",
                    data=pdf_bytes,
                    file_name="JBS_Oportunidades.pdf",
                    mime="application/pdf"
                )
                
                # 2. BOTÃO GOOGLE SHEETS (Requer Configuração)
                if col_sheet.button("googlesheets Gerar Link Google Sheets"):
                    url, msg = exportar_para_google_sheets(df_show)
                    if url:
                        col_sheet.success(f"Planilha Criada! [Clique aqui]({url})")
                    else:
                        col_sheet.warning(f"Não foi possível gerar o link automático (Requer API Key). Use o PDF ou Excel.")
                        # Fallback Excel
                        buf = BytesIO()
                        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                            df_show.to_excel(writer, index=False)
                        col_sheet.download_button("📥 Baixar Excel (Alternativa)", buf.getvalue(), "JBS.xlsx")
            else:
                st.warning("Nenhuma oportunidade no perfil.")
    else:
        st.error("Cole os dados.")
