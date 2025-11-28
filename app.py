import pandas as pd
import streamlit as st
from io import BytesIO

from ponto_parser import processar_espelho_ponto_bytes

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Resumo de Ponto - Alva Serv",
    page_icon="🕒",
    layout="wide",
)

# ============================================================
# ESTADO – usado para limpar uploads
# ============================================================
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

# ============================================================
# CSS – TEMA AZUL PREMIUM
# ============================================================
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f0f5ff;
        /* azul clarinho elegante */
    }

    .alva-header {
        background: linear-gradient(90deg, #1e3a8a, #3b82f6);
        padding: 30px 40px;
        border-radius: 12px;
        margin-bottom: 30px;
        color: white;
    }

    .alva-title {
        font-size: 34px;
        font-weight: 700;
        margin-bottom: 0;
    }

    .alva-subtitle {
        font-size: 15px;
        margin-top: 6px;
        opacity: 0.9;
    }

    .alva-card {
        background: white;
        padding: 24px;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-bottom: 24px;
    }

    .stDownloadButton button {
        background: #1e3a8a !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
    }

    .stButton button {
        background: #3b82f6 !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 8px 20px !important;
    }

    .metric {
        background: #ffffff;
        padding: 16px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# HEADER (com logo + título)
# ============================================================
with st.container():
    st.markdown("<div class='alva-header'>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 4])

    with col1:
        st.image("logo_alvaserv.png", use_container_width=True)
    with col2:
        st.markdown("<div class='alva-title'>Resumo de Ponto - Alva Serv</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='alva-subtitle'>Envie os espelhos de ponto em PDF (um por escola). O sistema consolida todos os funcionários e gera uma planilha detalhada para conferência.</div>",
            unsafe_allow_html=True
        )

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# UPLOAD DE ARQUIVOS
# ============================================================
with st.container():
    st.markdown("<div class='alva-card'>", unsafe_allow_html=True)

    st.markdown("### 📂 Upload de espelhos de ponto")

    arquivos_pdf = st.file_uploader(
        "Selecione os arquivos de ponto (PDF)",
        type=["pdf"],
        accept_multiple_files=True,
        key=f"upload_pdf_{st.session_state['uploader_key']}",
    )

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# PROCESSAMENTO
# ============================================================
if arquivos_pdf:

    with st.container():
        st.markdown("<div class='alva-card'>", unsafe_allow_html=True)
        st.markdown("### ⚙️ Processando arquivos...")

        dfs = []

        for f in arquivos_pdf:
            st.info(f"Processando: **{f.name}**...")
            pdf_bytes = f.read()
            df_parse = processar_espelho_ponto_bytes(pdf_bytes)

            if df_parse.empty:
                st.warning(f"⚠️ Não foi possível extrair dados de: {f.name}")
                continue

            df_parse["Arquivo"] = f.name
            dfs.append(df_parse)

        if not dfs:
            st.error("Nenhum PDF pôde ser processado.")
            st.stop()

        df_master = pd.concat(dfs, ignore_index=True)

        # Remover coluna técnica
        if "Pagina" in df_master.columns:
            df_master = df_master.drop(columns=["Pagina"])

        df_master["Mes_Referencia"] = pd.to_datetime(
            df_master["Periodo_Fim"], format="%d/%m/%Y"
        ).dt.to_period("M").astype(str)

        st.success("Pronto! Todos os PDFs foram processados com sucesso 🎉")

        st.markdown("</div>", unsafe_allow_html=True)

    # ============================================================
    # METRICS RESUMO
    # ============================================================
    with st.container():
        st.markdown("<div class='alva-card'>", unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Funcionários", df_master["Nome"].nunique())
        col2.metric("Escolas", df_master["Centro de Custo"].nunique())
        col3.metric("Meses", df_master["Mes_Referencia"].nunique())
        col4.metric("Registros", len(df_master))

        st.markdown("</div>", unsafe_allow_html=True)

    # ============================================================
    # TABELA DETALHADA
    # ============================================================
    df_display = df_master.rename(
        columns={
            "Centro de Custo": "Centro de Custo",
            "Nome": "Nome",
            "Periodo_Inicio": "Período Início",
            "Periodo_Fim": "Período Fim",
            "Dias_trabalhados": "Dias Trabalhados",
            "Dias_abono": "Dias Abono",
            "Dias_ferias": "Dias Férias",
            "Dias_falta": "Dias Falta",
            "Abono_Atestado": "Abono Atestado",
            "Abono_Feriado": "Abono Feriado",
            "Abono_Folga": "Abono Folga",
            "Arquivo": "Arquivo Origem",
            "Mes_Referencia": "Mês Referência",
        }
    )

    with st.container():
        st.markdown("<div class='alva-card'>", unsafe_allow_html=True)
        st.markdown("### 📊 Planilha detalhada")
        st.dataframe(df_display, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ============================================================
    # DOWNLOAD DO EXCEL + BOTÃO LIMPAR
    # ============================================================
    def gerar_excel_bytes(df):
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Detalhado")
        return buffer.getvalue()

    excel_bytes = gerar_excel_bytes(df_master)

    with st.container():
        st.markdown("<div class='alva-card'>", unsafe_allow_html=True)

        colA, colB = st.columns([2, 1])
        with colA:
            st.download_button(
                "⬇️ Baixar Excel",
                data=excel_bytes,
                file_name="resumo_ponto_alvaserv.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        with colB:
            if st.button("🧹 Limpar e enviar novos PDFs"):
                st.session_state["uploader_key"] += 1
                st.experimental_rerun()

        st.markdown("</div>", unsafe_allow_html=True)


