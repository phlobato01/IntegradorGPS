import io
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from scipy.stats import norm

# =========================================================
# CONFIGURAÇÃO
# =========================================================

st.set_page_config(
    page_title="Análise Estatística AccZ",
    layout="wide"
)

st.title(
    "Análise Estatística GPS x Acelerômetro"
)

# =========================================================
# LEITURA TXT
# =========================================================

def ler_txt(arquivo):

    conteudo = arquivo.read()

    for enc in [
        "utf-8",
        "cp1252",
        "latin1"
    ]:

        try:

            texto = conteudo.decode(enc)

            return pd.read_csv(
                io.StringIO(texto),
                sep="\t"
            )

        except Exception:
            pass

    raise Exception(
        "Erro ao ler arquivo TXT."
    )

# =========================================================
# LEITURA CSV
# =========================================================

def ler_csv(arquivo):

    conteudo = arquivo.read()

    for enc in [
        "utf-8",
        "cp1252",
        "latin1"
    ]:

        try:

            texto = conteudo.decode(enc)

            df = pd.read_csv(
                io.StringIO(texto),
                sep=";"
            )

            if len(df.columns) > 1:
                return df

            df = pd.read_csv(
                io.StringIO(texto),
                sep=","
            )

            if len(df.columns) > 1:
                return df

            linhas = texto.splitlines()

            cabecalho = linhas[0].split(",")

            dados = [
                linha.split(",")
                for linha in linhas[1:]
            ]

            return pd.DataFrame(
                dados,
                columns=cabecalho
            )

        except Exception:
            pass

    raise Exception(
        "Não foi possível interpretar o CSV GPS."
    )

# =========================================================
# DETECTOR DE CONSTANTES
# =========================================================

def detectar_constantes(
    serie,
    timestamps,
    minimo_repeticoes=5
):

    resultado = []

    valor_atual = None
    inicio = None
    contador = 0

    for i, valor in enumerate(serie):

        if valor == valor_atual:

            contador += 1

        else:

            if contador >= minimo_repeticoes:

                resultado.append(
                    {
                        "inicio": timestamps.iloc[inicio],
                        "fim": timestamps.iloc[i - 1],
                        "valor": valor_atual,
                        "repeticoes": contador
                    }
                )

            valor_atual = valor
            inicio = i
            contador = 1

    return pd.DataFrame(resultado)

# =========================================================
# ENTRADA
# =========================================================

arquivo_acc = st.file_uploader(
    "TXT do acelerômetro",
    type=["txt"]
)

arquivo_gps = st.file_uploader(
    "CSV GPS",
    type=["csv"]
)

# =========================================================
# PROCESSAMENTO
# =========================================================

if st.button("Analisar"):

    if arquivo_acc is None:

        st.warning(
            "Selecione o TXT do acelerômetro."
        )

        st.stop()

    if arquivo_gps is None:

        st.warning(
            "Selecione o CSV GPS."
        )

        st.stop()

    # =====================================================
    # ACELERÔMETRO
    # =====================================================

    acc = ler_txt(
        arquivo_acc
    )

    acc = acc[
        [
            "time",
            "AccZ(g)"
        ]
    ].copy()

    acc.columns = [
        "data_hora_acc",
        "accz"
    ]

    acc["accz"] = pd.to_numeric(
        acc["accz"],
        errors="coerce"
    )

    acc["datetime"] = pd.to_datetime(
        acc["data_hora_acc"],
        format="%Y-%m-%dT%H:%M:%S.%f",
        errors="coerce"
    )

    acc = acc.dropna()

    acc["datetime_acc"] = acc["datetime"]

    # =====================================================
    # GPS
    # =====================================================

    gps = ler_csv(
        arquivo_gps
    )

    gps.columns = (
        gps.columns
        .str.strip()
    )

    if "local_time" in gps.columns:

        coluna_tempo = "local_time"

    elif "time" in gps.columns:

        coluna_tempo = "time"

    else:

        st.error(
            f"Colunas encontradas: {gps.columns.tolist()}"
        )

        st.stop()

    colunas_obrigatorias = [
        coluna_tempo,
        "latitude",
        "longitude"
    ]

    faltando = [
        c
        for c in colunas_obrigatorias
        if c not in gps.columns
    ]

    if faltando:

        st.error(
            f"Colunas ausentes: {faltando}"
        )

        st.write(
            gps.columns.tolist()
        )

        st.stop()

    gps = gps[
        [
            coluna_tempo,
            "latitude",
            "longitude"
        ]
    ].copy()

    gps.columns = [
        "data_hora_gps",
        "latitude",
        "longitude"
    ]

    gps["latitude"] = (
        gps["latitude"]
        .astype(str)
        .str.replace(",", ".", regex=False)
    )

    gps["longitude"] = (
        gps["longitude"]
        .astype(str)
        .str.replace(",", ".", regex=False)
    )

    gps["latitude"] = pd.to_numeric(
        gps["latitude"],
        errors="coerce"
    )

    gps["longitude"] = pd.to_numeric(
        gps["longitude"],
        errors="coerce"
    )

    gps["datetime"] = pd.to_datetime(
        gps["data_hora_gps"]
            .astype(str)
            .str.slice(0, 23),
        errors="coerce"
    )

    gps = gps.dropna()

    gps["datetime_gps"] = gps["datetime"]

    # =====================================================
    # INTEGRAÇÃO
    # =====================================================

    acc = acc.sort_values(
        "datetime"
    )

    gps = gps.sort_values(
        "datetime"
    )

    resultado = pd.merge_asof(
        acc,
        gps,
        on="datetime",
        direction="nearest"
    )

    # =====================================================
    # ESTATÍSTICAS
    # =====================================================

    st.header(
        "Resumo Estatístico"
    )

    dados = resultado["accz"]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Média",
        round(dados.mean(), 4)
    )

    c2.metric(
        "Desvio Padrão",
        round(dados.std(), 4)
    )

    c3.metric(
        "Mínimo",
        round(dados.min(), 4)
    )

    c4.metric(
        "Máximo",
        round(dados.max(), 4)
    )

    # =====================================================
    # CURVA DE GAUSS
    # =====================================================

    st.header(
        "Curva de Gauss"
    )

    media = dados.mean()
    sigma = dados.std()

    hist_y, hist_x = np.histogram(
        dados,
        bins=80,
        density=True
    )

    centro = (
        hist_x[:-1] +
        hist_x[1:]
    ) / 2

    curva = norm.pdf(
        centro,
        media,
        sigma
    )

    fig_gauss = go.Figure()

    fig_gauss.add_trace(
        go.Bar(
            x=centro,
            y=hist_y,
            name="Histograma"
        )
    )

    fig_gauss.add_trace(
        go.Scatter(
            x=centro,
            y=curva,
            mode="lines",
            name="Gauss"
        )
    )

    st.plotly_chart(
        fig_gauss,
        use_container_width=True
    )

    # =====================================================
    # SÉRIE TEMPORAL
    # =====================================================

    st.header(
        "AccZ ao longo do tempo"
    )

    fig_tempo = go.Figure()

    fig_tempo.add_trace(
        go.Scatter(
            x=resultado["datetime_acc"],
            y=resultado["accz"],
            mode="lines",
            name="AccZ"
        )
    )

    fig_tempo.update_xaxes(
        rangeslider_visible=True
    )

    st.plotly_chart(
        fig_tempo,
        use_container_width=True
    )

    # =====================================================
    # CONGELAMENTOS
    # =====================================================

    st.header(
        "Possíveis Falhas / Congelamentos"
    )

    acc_constante = detectar_constantes(
        resultado["accz"],
        resultado["datetime_acc"]
    )

    gps_constante = detectar_constantes(
        resultado["data_hora_gps"],
        resultado["datetime_acc"]
    )

    tempo_acc_constante = detectar_constantes(
        resultado["data_hora_acc"],
        resultado["datetime_acc"]
    )

    st.subheader(
        "AccZ constante"
    )

    if acc_constante.empty:

        st.success(
            "Nenhum período encontrado."
        )

    else:

        st.dataframe(
            acc_constante
        )

    st.subheader(
        "Timestamp GPS constante"
    )

    if gps_constante.empty:

        st.success(
            "Nenhum período encontrado."
        )

    else:

        st.dataframe(
            gps_constante
        )

    st.subheader(
        "Timestamp acelerômetro constante"
    )

    if tempo_acc_constante.empty:

        st.success(
            "Nenhum período encontrado."
        )

    else:

        st.dataframe(
            tempo_acc_constante
        )

    # =====================================================
    # EXPORTAÇÃO
    # =====================================================

    relatorio = pd.concat(
        [
            acc_constante.assign(
                tipo="ACCZ"
            ),
            gps_constante.assign(
                tipo="GPS"
            ),
            tempo_acc_constante.assign(
                tipo="TIMESTAMP_ACC"
            )
        ],
        ignore_index=True
    )

    csv = relatorio.to_csv(
        index=False,
        sep=";"
    ).encode(
        "utf-8"
    )

    st.download_button(
        "Baixar Relatório de Anomalias",
        csv,
        "anomalias.csv",
        "text/csv"
    )