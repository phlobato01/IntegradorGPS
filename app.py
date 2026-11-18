import io

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

# ======================================================
# CONFIGURAÇÃO
# ======================================================

st.set_page_config(
    page_title="GPS x Acelerômetro",
    layout="wide"
)

st.title("Integração GPS x Acelerômetro")

# ======================================================
# FUNÇÕES
# ======================================================

def ler_txt_acelerometro(arquivo):

    arquivo.seek(0)

    conteudo = arquivo.read()

    for encoding in [
        "utf-8",
        "cp1252",
        "latin1"
    ]:

        try:

            texto = conteudo.decode(
                encoding
            )

            df = pd.read_csv(
                io.StringIO(texto),
                sep="\t"
            )

            return df

        except:
            pass

    raise Exception(
        "Não foi possível ler o TXT do acelerômetro."
    )

def ler_csv_gps(arquivo):

    arquivo.seek(0)

    conteudo = arquivo.read()

    for encoding in [
        "utf-8",
        "cp1252",
        "latin1"
    ]:

        try:

            texto = conteudo.decode(
                encoding
            )

            # tentativa 1
            df = pd.read_csv(
                io.StringIO(texto),
                sep=";"
            )

            if len(df.columns) > 1:
                return df

            # tentativa 2
            df = pd.read_csv(
                io.StringIO(texto),
                sep=","
            )

            if len(df.columns) > 1:
                return df

            # tentativa 3
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

        except:
            pass

    raise Exception(
        "Não foi possível ler o CSV GPS."
    )

def obter_eventos_filtrados(
    df,
    limite_superior,
    limite_inferior
):

    return df[
        (
            df["aceleracao_z"]
            >= limite_superior
        )
        |
        (
            df["aceleracao_z"]
            <= limite_inferior
        )
    ].copy()

def criar_mapa(
    df,
    limite_superior,
    limite_inferior
):

    if df.empty:
        return None

    # remove coordenadas repetidas

    rota = (
        df[
            [
                "latitude",
                "longitude"
            ]
        ]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    lat_media = rota["latitude"].mean()
    lon_media = rota["longitude"].mean()

    mapa = folium.Map(
        location=[lat_media, lon_media],
        zoom_start=16
    )

    coordenadas = list(
        zip(
            rota["latitude"],
            rota["longitude"]
        )
    )

    # rota

    if len(coordenadas) > 1:

        folium.PolyLine(
            coordenadas,
            color="blue",
            weight=3,
            opacity=0.7
        ).add_to(mapa)

    # apenas eventos > 1.5g

    eventos = obter_eventos_filtrados(
        df,
        limite_superior,
        limite_inferior
    ).copy()

    eventos_pos = eventos[
        eventos["aceleracao_z"]
        >= limite_superior
    ].copy()

    eventos_neg = eventos[
        eventos["aceleracao_z"]
        <= limite_inferior
    ].copy()

    eventos_pos = (
        eventos_pos
        .sort_values(
            "aceleracao_z",
            ascending=False
        )
        .drop_duplicates(
            subset=[
                "latitude",
                "longitude"
            ]
        )
    )

    eventos_neg = (
        eventos_neg
        .sort_values(
            "aceleracao_z",
            ascending=True
        )
        .drop_duplicates(
            subset=[
                "latitude",
                "longitude"
            ]
        )
    )

    eventos = pd.concat(
        [
            eventos_pos,
            eventos_neg
        ],
        ignore_index=True
    )

    # limita quantidade para evitar travamentos

    st.write(
        f"Eventos encontrados: {len(eventos)}"
    )

    # sem limitação

    st.write(
        f"Marcadores exibidos no mapa: {len(eventos)}"
)

    for _, row in eventos.iterrows():

        if row["aceleracao_z"] >= limite_superior:

            cor = "red"

        else:

            cor = "purple"

        folium.CircleMarker(
            location=[
                row["latitude"],
                row["longitude"]
            ],
            radius=7,
            color=cor,
            fill=True,
            fill_color=cor,
            fill_opacity=0.9,
            popup=(
                f"Aceleração: "
                f"{row['aceleracao_z']:.2f} g"
            )
        ).add_to(mapa)

    if len(coordenadas):

        folium.Marker(
            coordenadas[0],
            tooltip="Início",
            icon=folium.Icon(
                color="green"
            )
        ).add_to(mapa)

        folium.Marker(
            coordenadas[-1],
            tooltip="Fim",
            icon=folium.Icon(
                color="blue"
            )
        ).add_to(mapa)

    return mapa

def gerar_kml_eventos(
    eventos,
    rota
):

    kml = []

    kml.append(
        '<?xml version="1.0" encoding="UTF-8"?>'
    )

    kml.append(
        '<kml xmlns="http://www.opengis.net/kml/2.2">'
    )

    kml.append("<Document>")

    # ====================================
    # ROTA
    # ====================================

    kml.append("""
    <Placemark>

        <name>Rota Completa</name>

        <Style>
            <LineStyle>
                <color>ffff0000</color>
                <width>4</width>
            </LineStyle>
        </Style>

        <LineString>

            <tessellate>1</tessellate>

            <coordinates>
    """)

    for _, row in rota.iterrows():

        kml.append(
            f"{row['longitude']},{row['latitude']},0"
        )

    kml.append("""
            </coordinates>
        </LineString>
    </Placemark>
    """)

    for _, row in eventos.iterrows():

        if row["aceleracao_z"] >= 0:

            cor = "ff0000ff"  # vermelho

        else:

            cor = "ffff00ff"  # roxo

        descricao = f"""
        <![CDATA[
        <b>Aceleração:</b> {row['aceleracao_z']:.3f} g<br>
        <b>Timestamp GPS:</b> {row['timestamp_gps']}<br>
        <b>Timestamp ACC:</b> {row['timestamp_acelerometro']}<br>
        <b>Diferença:</b> {row['diferenca_ms']:.1f} ms<br>
        <b>Latitude:</b> {row['latitude']}<br>
        <b>Longitude:</b> {row['longitude']}
        ]]>
        """

        kml.append(f"""
        <Placemark>

            <name>
            {row['aceleracao_z']:.2f} g
            </name>

            <description>
            {descricao}
            </description>

            <Style>
                <IconStyle>
                    <color>{cor}</color>
                    <scale>1.2</scale>
                </IconStyle>
            </Style>

            <Point>
                <coordinates>
                {row['longitude']},
                {row['latitude']},
                0
                </coordinates>
            </Point>

        </Placemark>
        """)

    kml.append("</Document>")
    kml.append("</kml>")

    return "\n".join(kml)

# ======================================================
# ENTRADA
# ======================================================

arquivo_acc = st.file_uploader(
    "TXT do acelerômetro",
    type=["txt"]
)

arquivo_gps = st.file_uploader(
    "CSV do GPS",
    type=["csv"]
)

tolerancia_ms = st.sidebar.number_input(
    "Tolerância (ms)",
    min_value=0,
    value=1000
)

limite_superior = st.sidebar.number_input(
    "Destacar aceleração acima de (g)",
    value=1.5,
    step=0.1
)

limite_inferior = st.sidebar.number_input(
    "Destacar aceleração abaixo de (g)",
    value=-1.5,
    step=0.1
)

# ======================================================
# PROCESSAMENTO
# ======================================================

if st.button("Processar"):

    try:

        if arquivo_acc is None:

            st.error(
                "Selecione o TXT do acelerômetro."
            )

            st.stop()

        if arquivo_gps is None:

            st.error(
                "Selecione o CSV GPS."
            )

            st.stop()

        # ==========================================
        # ACELERÔMETRO
        # ==========================================

        acc = ler_txt_acelerometro(
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
            "aceleracao_z"
        ]

        acc["aceleracao_z"] = pd.to_numeric(
            acc["aceleracao_z"],
            errors="coerce"
        )

        acc["datetime"] = pd.to_datetime(
            acc["data_hora_acc"],
            format="%Y-%m-%dT%H:%M:%S.%f",
            errors="coerce"
        )

        acc = acc.dropna()

        acc["timestamp_acelerometro"] = (
            acc["datetime"]
            .dt.strftime(
                "%H:%M:%S.%f"
            )
            .str[:-3]
        )

        # ==========================================
        # GPS
        # ==========================================

        gps = ler_csv_gps(
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

            raise Exception(
                f"Colunas encontradas: {gps.columns.tolist()}"
            )

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
            .str.replace(
                ",",
                ".",
                regex=False
            )
            .astype(float)
        )

        gps["longitude"] = (
            gps["longitude"]
            .astype(str)
            .str.replace(
                ",",
                ".",
                regex=False
            )
            .astype(float)
        )

        gps["datetime"] = pd.to_datetime(
            gps["data_hora_gps"]
            .str.slice(0, 23),
            format="%Y-%m-%dT%H:%M:%S.%f",
            errors="coerce"
        )

        gps = gps.dropna()

        gps["timestamp_gps"] = (
            gps["datetime"]
            .dt.strftime(
                "%H:%M:%S.%f"
            )
            .str[:-3]
        )

        # ==========================================
        # INTEGRAÇÃO
        # ==========================================

        acc = acc.sort_values(
            "datetime"
        )

        gps = gps.sort_values(
            "datetime"
        )

        acc["datetime_acc"] = acc["datetime"]

        gps["datetime_gps"] = gps["datetime"]

        resultado = pd.merge_asof(
            left=acc,
            right=gps,
            on="datetime",
            direction="nearest"
        )

        resultado["diferenca_ms"] = (
            (
                resultado["datetime_acc"]
                -
                resultado["datetime_gps"]
            )
            .abs()
            .dt.total_seconds()
            * 1000
        )

        resultado["status"] = (
            resultado["diferenca_ms"]
            <= tolerancia_ms
        )
        
        eventos_positivos = len(
            resultado[
                resultado["aceleracao_z"]
                >= limite_superior
            ]
        )

        eventos_negativos = len(
            resultado[
                resultado["aceleracao_z"]
                <= limite_inferior
            ]
        )

        st.write(
            "Maior aceleração:",
            resultado["aceleracao_z"].max()
        )

        st.write(
            "Menor aceleração:",
            resultado["aceleracao_z"].min()
        )

        st.write(
            "Eventos positivos:",
            eventos_positivos
        )

        st.write(
            "Eventos negativos:",
            eventos_negativos
        )

        # ==========================================
        # ESTATÍSTICAS
        # ==========================================

        st.subheader(
            "Resumo"
        )

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric(
            "Acelerômetro",
            len(acc)
        )

        c2.metric(
            "GPS",
            len(gps)
        )

        c3.metric(
            "Integrados",
            len(resultado)
        )

        c4.metric(
            "Eventos positivos",
            eventos_positivos
        )

        c5.metric(
            "Eventos negativos",
            eventos_negativos
        )

        eventos_kml = obter_eventos_filtrados(
            resultado,
            limite_superior,
            limite_inferior
        )

        # ==========================================
        # MAPA
        # ==========================================
        st.subheader("Mapa")

        mapa = criar_mapa(
            resultado,
            limite_superior,
            limite_inferior
        )

        if mapa:
            
            st_folium(
                mapa,
                use_container_width=True,
                height=750,
                returned_objects=[]
            )
        
        # ==========================================
        # DOWNLOAD
        # ==========================================
           
        resultado_exportar = resultado[
            [
                "data_hora_acc",
                "timestamp_acelerometro",
                "aceleracao_z",
                "data_hora_gps",
                "timestamp_gps",
                "latitude",
                "longitude",
                "diferenca_ms"
            ]
        ]

        csv = resultado_exportar.to_csv(
            index=False,
            sep=";"
        ).encode(
            "utf-8"
        )

        rota_kml = resultado[
            [
                "latitude",
                "longitude"
            ]
        ].drop_duplicates().reset_index(drop=True)

        kml = gerar_kml_eventos(
            eventos_kml,
            rota_kml
        )

        st.write(
            f"Eventos exportados para KML: {len(eventos_kml)}"
        )

        st.download_button(
            label="🌎 Baixar KML para Google Earth",
            data=kml,
            file_name="eventos_aceleracao.kml",
            mime="application/vnd.google-earth.kml+xml"
        )

        st.download_button(
            label="Baixar CSV Integrado",
            data=csv,
            file_name="dados_integrados.csv",
            mime="text/csv"
        )
        
    except Exception as erro:

        st.error(
            "Erro durante o processamento."
        )

        st.exception(
            erro
        )