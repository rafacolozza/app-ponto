import re
from datetime import datetime
from io import BytesIO

import pdfplumber
import pandas as pd


# ---------------------------------------------------------
# Classificação de linha de dia
# ---------------------------------------------------------

def _classificar_linha_dia(linha: str):
    """
    Recebe a linha completa de um dia e devolve:
    (tipo, info_extra)

    tipo:
        - "trabalhado"
        - "abono"
        - "ferias"
        - "falta"
        - "domingo"
        - "afastamento"

    info_extra pode marcar: atestado / feriado / folga
    """

    if not re.match(r"^\d{2}/\d{2}/\d{4}", linha):
        return None, {}

    texto = linha.upper()

    tem_domingo = "DOMINGO" in texto
    tem_ferias = "FÉRIAS" in texto or "FERIAS" in texto
    tem_abono = "ABONO APROVADO" in texto
    tem_feriado = "FERIADO" in texto
    tem_atestado = "ATESTADO" in texto
    tem_folga = "FOLGA" in texto
    tem_palavra_falta = "FALTA" in texto
    tem_afastamento = "AFASTAMENTO" in texto

    # horários capturados
    horarios = re.findall(r"\b(\d{2}):(\d{2})\b", linha)
    num_horarios_reais = sum(1 for h, m in horarios if h != "00" or m != "00")
    tem_horas_reais = num_horarios_reais >= 2

    if tem_domingo:
        return "domingo", {}

    if tem_ferias:
        return "ferias", {}

    # NOVO: afastamento separado
    if tem_afastamento:
        return "afastamento", {}

    if tem_abono or tem_feriado:
        info = {
            "atestado": tem_atestado,
            "feriado": tem_feriado,
            "folga": tem_folga,
        }
        return "abono", info

    if tem_palavra_falta:
        return "falta", {}

    if tem_horas_reais:
        return "trabalhado", {}

    return "falta", {}


# ---------------------------------------------------------
# Extração de Nome / Centro de Custo
# ---------------------------------------------------------

def _extrair_nome(linhas):
    for i, l in enumerate(linhas):
        if "Nome:" in l:
            parte = l.split("Nome:", 1)[-1].strip()
            if parte:
                return parte
            if i + 1 < len(linhas):
                return linhas[i + 1].strip()
    return "DESCONHECIDO"


def _extrair_centro_custo(linhas):
    for l in linhas:
        if "Centro de Custo:" in l:
            return l.split("Centro de Custo:", 1)[-1].strip()
    return "DESCONHECIDO"


# ---------------------------------------------------------
# Processar 1 página (1 funcionário)
# ---------------------------------------------------------

def _processar_pagina(texto_pagina: str) -> dict:
    linhas = texto_pagina.splitlines()

    nome = _extrair_nome(linhas)
    centro = _extrair_centro_custo(linhas)

    dias_trab = dias_abono = dias_ferias = dias_falta = dias_afastamento = 0
    ab_atestado = ab_feriado = ab_folga = 0
    datas = []

    for linha in linhas:
        if not re.match(r"^\d{2}/\d{2}/\d{4}", linha):
            continue

        data_str = linha[:10]
        try:
            datas.append(datetime.strptime(data_str, "%d/%m/%Y"))
        except ValueError:
            pass

        tipo, info = _classificar_linha_dia(linha)
        if not tipo:
            continue

        if tipo == "trabalhado":
            dias_trab += 1

        elif tipo == "abono":
            dias_abono += 1
            if info.get("atestado"):
                ab_atestado += 1
            if info.get("feriado"):
                ab_feriado += 1
            if info.get("folga"):
                ab_folga += 1

        elif tipo == "ferias":
            dias_ferias += 1

        elif tipo == "falta":
            dias_falta += 1

        elif tipo == "afastamento":
            dias_afastamento += 1

        # domingo é ignorado

    if datas:
        periodo_inicio = min(datas).strftime("%d/%m/%Y")
        periodo_fim = max(datas).strftime("%d/%m/%Y")
    else:
        periodo_inicio = ""
        periodo_fim = ""

    return {
        "Centro de Custo": centro,
        "Nome": nome,
        "Periodo_Inicio": periodo_inicio,
        "Periodo_Fim": periodo_fim,
        "Dias_trabalhados": dias_trab,
        "Dias_abono": dias_abono,
        "Dias_ferias": dias_ferias,
        "Dias_falta": dias_falta,
        "Dias_afastamento": dias_afastamento,   # NOVO
        "Abono_Atestado": ab_atestado,
        "Abono_Feriado": ab_feriado,
        "Abono_Folga": ab_folga,
    }


# ---------------------------------------------------------
# Função pública para o Streamlit
# ---------------------------------------------------------

def processar_espelho_ponto_bytes(pdf_bytes: bytes) -> pd.DataFrame:
    buffer = BytesIO(pdf_bytes)
    resultados = []

    with pdfplumber.open(buffer) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text() or ""
            if "Nome:" not in texto:
                continue
            info = _processar_pagina(texto)
            resultados.append(info)

    colunas = [
        "Centro de Custo",
        "Nome",
        "Periodo_Inicio",
        "Periodo_Fim",
        "Dias_trabalhados",
        "Dias_abono",
        "Dias_ferias",
        "Dias_falta",
        "Dias_afastamento",  # NOVO
        "Abono_Atestado",
        "Abono_Feriado",
        "Abono_Folga",
    ]

    if not resultados:
        return pd.DataFrame(columns=colunas)

    return pd.DataFrame(resultados, columns=colunas)

