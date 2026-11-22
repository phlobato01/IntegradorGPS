import io

import folium
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.stats import norm
from streamlit_folium import st_folium


st.set_page_config(
    page_title="Análise Estatística AccZ",
    layout="wide"
)

st.title("Análise Estatística GPS x Acelerômetro")


def ler_txt(arquivo):
    arquivo.seek(0)
    conteudo = arquivo.read()

    for enc in ["utf-8", "cp1252", "latin1"]:
        try:
            texto = conteudo.decode(enc)
            return pd.read_csv(io.StringIO(texto), sep="\t")
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue

    raise ValueError("Erro ao ler arquivo TXT do acelerômetro.")


def ler_csv(arquivo):
    arquivo.seek(0)
    conteudo = arquivo.read()

    for enc in ["utf-8", "cp1252", "latin1"]:
        try:
            texto = conteudo.decode(enc)
        except UnicodeDecodeError:
            continue

        for separador in [";", ","]:
            try:
                dados = pd.read_csv(io.StringIO(texto), sep=separador)
            except pd.errors.ParserError:
                continue

            if len(dados.columns) > 1:
                return dados

    raise ValueError("Não foi possível interpretar o CSV GPS.")


def processar_dados(arquivo_acc, arquivo_gps):
    acc = ler_txt(arquivo_acc)
    acc.columns = acc.columns.str.strip()

    colunas_acc = ["time", "AccX(g)", "AccY(g)", "AccZ(g)"]
    faltando_acc = [coluna for coluna in colunas_acc if coluna not in acc.columns]
    if faltando_acc:
        raise ValueError(
            "Colunas ausentes no TXT do acelerômetro: "
            f"{', '.join(faltando_acc)}."
        )

    acc = acc[colunas_acc].copy()
    acc.columns = ["data_hora_acc", "accx", "accy", "accz"]
    for eixo in ["accx", "accy", "accz"]:
        acc[eixo] = pd.to_numeric(acc[eixo], errors="coerce")

    acc["datetime"] = pd.to_datetime(
        acc["data_hora_acc"],
        errors="coerce"
    )
    acc = acc.dropna(subset=["datetime", "accx", "accy", "accz"])
    acc["datetime_acc"] = acc["datetime"]

    gps = ler_csv(arquivo_gps)
    gps.columns = gps.columns.str.strip()

    if "local_time" in gps.columns:
        coluna_tempo = "local_time"
    elif "time" in gps.columns:
        coluna_tempo = "time"
    else:
        raise ValueError(
            "O CSV GPS precisa conter uma coluna 'local_time' ou 'time'."
        )

    colunas_gps = [coluna_tempo, "latitude", "longitude"]
    faltando_gps = [coluna for coluna in colunas_gps if coluna not in gps.columns]
    if faltando_gps:
        raise ValueError(
            f"Colunas ausentes no CSV GPS: {', '.join(faltando_gps)}."
        )

    gps = gps[colunas_gps].copy()
    gps.columns = ["data_hora_gps", "latitude", "longitude"]

    for coordenada in ["latitude", "longitude"]:
        gps[coordenada] = pd.to_numeric(
            gps[coordenada].astype(str).str.replace(",", ".", regex=False),
            errors="coerce"
        )

    gps["datetime"] = pd.to_datetime(
        gps["data_hora_gps"].astype(str).str.slice(0, 23),
        errors="coerce"
    )
    gps = gps.dropna(subset=["datetime", "latitude", "longitude"])
    gps = gps[
        gps["latitude"].between(-90, 90)
        & gps["longitude"].between(-180, 180)
    ].copy()
    gps["datetime_gps"] = gps["datetime"]

    if acc.empty:
        raise ValueError("O TXT não contém leituras válidas dos três eixos.")
    if gps.empty:
        raise ValueError("O CSV não contém coordenadas GPS válidas.")

    acc = acc.sort_values("datetime")
    gps = gps.sort_values("datetime")

    return pd.merge_asof(
        acc,
        gps,
        on="datetime",
        direction="nearest"
    )


def criar_mapa_inspecao(resultado, limites):
    rota = resultado[["latitude", "longitude"]].dropna()
    if rota.empty:
        return None, 0

    coordenadas = list(zip(rota["latitude"], rota["longitude"]))
    mapa = folium.Map(
        location=[rota["latitude"].mean(), rota["longitude"].mean()],
        zoom_start=16,
        control_scale=True
    )

    if len(coordenadas) > 1:
        folium.PolyLine(
            coordenadas,
            color="blue",
            weight=4,
            opacity=0.75,
            tooltip="Trajeto inspecionado"
        ).add_to(mapa)

    colunas_eixos = {
        "X": "accx",
        "Y": "accy",
        "Z": "accz"
    }

    eventos = pd.Series(False, index=resultado.index)
    for eixo, coluna in colunas_eixos.items():
        minimo, maximo = limites[eixo]
        eventos |= (
            (resultado[coluna] > maximo)
            | (resultado[coluna] < minimo)
        )

    leituras_evento = resultado.loc[eventos]
    for _, leitura in leituras_evento.iterrows():
        detalhes = []
        excedeu_maximo = False
        excedeu_minimo = False

        for eixo, coluna in colunas_eixos.items():
            valor = leitura[coluna]
            minimo, maximo = limites[eixo]

            if valor > maximo:
                excedeu_maximo = True
                detalhes.append(
                    f"Acc{eixo} acima do máximo: {valor:.3f} g"
                )
            elif valor < minimo:
                excedeu_minimo = True
                detalhes.append(
                    f"Acc{eixo} abaixo do mínimo: {valor:.3f} g"
                )

        if not detalhes:
            continue

        if excedeu_maximo and excedeu_minimo:
            cor = "orange"
        elif excedeu_maximo:
            cor = "red"
        else:
            cor = "purple"

        detalhes.insert(
            0,
            f"Data/hora: {leitura['datetime_acc']}"
        )
        folium.CircleMarker(
            location=[leitura["latitude"], leitura["longitude"]],
            radius=6,
            color=cor,
            fill=True,
            fill_color=cor,
            fill_opacity=0.9,
            popup=folium.Popup("<br>".join(detalhes), max_width=350)
        ).add_to(mapa)

    if coordenadas:
        folium.Marker(
            coordenadas[0],
            tooltip="Início da inspeção",
            icon=folium.Icon(color="green")
        ).add_to(mapa)
        folium.Marker(
            coordenadas[-1],
            tooltip="Fim da inspeção",
            icon=folium.Icon(color="blue")
        ).add_to(mapa)

    return mapa, len(leituras_evento)


arquivo_acc = st.file_uploader(
    "TXT do acelerômetro",
    type=["txt"]
)
arquivo_gps = st.file_uploader(
    "CSV GPS",
    type=["csv"]
)

if st.button("Analisar"):
    st.session_state.pop("resultado_estatistica", None)
    if arquivo_acc is None:
        st.error("Selecione o TXT do acelerômetro.")
    elif arquivo_gps is None:
        st.error("Selecione o CSV GPS.")
    else:
        try:
            st.session_state["resultado_estatistica"] = processar_dados(
                arquivo_acc,
                arquivo_gps
            )
        except (ValueError, KeyError) as erro:
            st.error(str(erro))

if "resultado_estatistica" in st.session_state:
    resultado = st.session_state["resultado_estatistica"]

    st.header("Resumo Estatístico AccZ")
    dados = resultado["accz"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Média", round(dados.mean(), 4))
    c2.metric("Desvio Padrão", round(dados.std(), 4))
    c3.metric("Mínimo", round(dados.min(), 4))
    c4.metric("Máximo", round(dados.max(), 4))

    st.header("Curva de Gauss AccZ")
    media = dados.mean()
    sigma = dados.std()
    hist_y, hist_x = np.histogram(dados, bins=80, density=True)
    centro = (hist_x[:-1] + hist_x[1:]) / 2
    curva = norm.pdf(centro, media, sigma)

    fig_gauss = go.Figure()
    fig_gauss.add_trace(
        go.Bar(x=centro, y=hist_y, name="Histograma")
    )
    fig_gauss.add_trace(
        go.Scatter(x=centro, y=curva, mode="lines", name="Gauss")
    )
    st.plotly_chart(fig_gauss, width="stretch")

    st.header("Acelerações ao longo do tempo")
    for eixo in ["x", "y", "z"]:
        fig_tempo = go.Figure()
        fig_tempo.add_trace(
            go.Scatter(
                x=resultado["datetime_acc"],
                y=resultado[f"acc{eixo}"],
                mode="lines",
                name=f"Acc{eixo.upper()}"
            )
        )
        fig_tempo.update_xaxes(rangeslider_visible=True)
        fig_tempo.update_layout(
            title=f"Acc{eixo.upper()} ao longo do tempo",
            uirevision=f"acc-{eixo}"
        )
        st.plotly_chart(
            fig_tempo,
            width="stretch",
            key=f"grafico_acc_{eixo}"
        )

    st.header("Limites de aceleração para os eventos")
    st.caption(
        "Os eventos são marcados quando a aceleração fica acima do máximo "
        "ou abaixo do mínimo definido para cada eixo."
    )
    colunas_limites = st.columns(3)
    limites = {}

    for coluna, eixo in zip(colunas_limites, ["X", "Y", "Z"]):
        with coluna:
            st.subheader(f"Eixo {eixo}")
            minimo = st.number_input(
                f"Mínimo Acc{eixo} (g)",
                value=-1.5,
                step=0.1,
                key=f"limite_minimo_{eixo.lower()}"
            )
            maximo = st.number_input(
                f"Máximo Acc{eixo} (g)",
                value=1.5,
                step=0.1,
                key=f"limite_maximo_{eixo.lower()}"
            )
            limites[eixo] = (minimo, maximo)

    eixos_invalidos = [
        eixo for eixo, (minimo, maximo) in limites.items()
        if minimo >= maximo
    ]

    if eixos_invalidos:
        st.error(
            "Em cada eixo, o valor mínimo deve ser menor que o máximo: "
            + ", ".join(eixos_invalidos)
            + "."
        )
    else:
        st.header("Mapa da inspeção")
        mapa, total_eventos = criar_mapa_inspecao(resultado, limites)
        st.write(f"Leituras no trajeto: {len(resultado)}")
        st.write(f"Eventos fora dos limites: {total_eventos}")

        if mapa is None:
            st.warning("Não há coordenadas válidas para exibir no mapa.")
        else:
            st_folium(
                mapa,
                use_container_width=True,
                height=600,
                key="mapa_inspecao"
            )
