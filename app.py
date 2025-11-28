import pandas as pd
import streamlit as st
from io import BytesIO

from ponto_parser import processar_espelho_ponto_bytes


st.set_page_config(page_title="Resumo de Ponto", layout="wide")

st.title("Resumo de Ponto – Planilha Mãe")
st.write(
    """
    Envie um ou mais PDFs de espelho de ponto (um por escola).
    O sistema vai ler cada funcionário, contar dias trabalhados e outros tipos de dia
    e gerar uma **planilha mãe detalhada** em Excel, com todas as escolas e meses enviados.
    """
)

# Upload de vários arquivos
arquivos_pdf = st.file_uploader(
    "Selecione os arquivos de ponto em PDF",
    type=["pdf"],
    accept_multiple_files=True,
)

if arquivos_pdf:
    st.info(f"{len(arquivos_pdf)} arquivo(s) carregado(s).")

    dfs = []
    for arquivo_pdf in arquivos_pdf:
        st.write(f"Processando: **{arquivo_pdf.name}**")
        pdf_bytes = arquivo_pdf.read()

        df_resumo = processar_espelho_ponto_bytes(pdf_bytes)

        if df_resumo.empty:
            st.warning(f"⚠️ Não foi possível extrair dados de {arquivo_pdf.name}.")
            continue

        # coluna com nome do arquivo (útil para auditoria)
        df_resumo["Arquivo"] = arquivo_pdf.name
        dfs.append(df_resumo)

    if not dfs:
        st.error("Nenhum dos PDFs pôde ser processado. Verifique se o layout é o esperado.")
    else:
        # concatena tudo em uma "planilha mãe"
        df_master = pd.concat(dfs, ignore_index=True)

        # remove coluna Pagina se existir (não precisamos mais dela)
        if "Pagina" in df_master.columns:
            df_master = df_master.drop(columns=["Pagina"])

        # cria coluna de Mês de referência a partir do Periodo_Fim
        df_master["Mes_Referencia"] = pd.to_datetime(
            df_master["Periodo_Fim"], format="%d/%m/%Y"
        ).dt.to_period("M").astype(str)  # ex: '2025-11'

        st.success("Processamento concluído com sucesso!")

        st.subheader("Planilha mãe – Detalhado (todas as escolas e meses desta carga)")
        st.dataframe(df_master, use_container_width=True)

        # Gera Excel com uma aba só (Detalhado)
        def gerar_excel_bytes(df_detalhado: pd.DataFrame) -> bytes:
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_detalhado.to_excel(writer, index=False, sheet_name="Detalhado")
            return output.getvalue()

        excel_bytes = gerar_excel_bytes(df_master)

        st.download_button(
            label="⬇️ Baixar Excel (Planilha mãe detalhada)",
            data=excel_bytes,
            file_name="planilha_mae_ponto.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )
else:
    st.warning("Envie um ou mais PDFs para começar.")

