import streamlit as st
import pandas as pd

from datetime import datetime
from streamlit_geolocation import streamlit_geolocation

# =====================================================
# CONFIGURAÇÃO
# =====================================================

st.set_page_config(
    page_title="Registro de Eventos",
    layout="wide"
)

st.title(
    "Registro Manual de Eventos em Campo"
)

# =====================================================
# SESSION STATE
# =====================================================

if "jornada_ativa" not in st.session_state:
    st.session_state.jornada_ativa = False

if "eventos" not in st.session_state:
    st.session_state.eventos = []

# =====================================================
# INICIAR / ENCERRAR
# =====================================================

c1, c2 = st.columns(2)

with c1:

    if st.button(
        "▶ Iniciar Jornada"
    ):

        st.session_state.jornada_ativa = True
        st.session_state.eventos = []

        st.success(
            "Jornada iniciada."
        )

with c2:

    if st.button(
        "⏹ Encerrar Jornada"
    ):

        st.session_state.jornada_ativa = False

# =====================================================
# BLOCO PRINCIPAL
# =====================================================

if st.session_state.jornada_ativa:

    st.subheader(
        "Registrar Evento"
    )

    descricao = st.text_input(
        "Descrição do evento"
    )

    st.info(
        "Toque na mira para atualizar sua posição antes de registrar o evento."
    )

    # --------------------------------------------
    # BOTÃO GPS
    # --------------------------------------------

    location = streamlit_geolocation()

    # --------------------------------------------
    # EXIBIÇÃO GPS
    # --------------------------------------------

    st.subheader(
        "Última posição obtida"
    )

    if (
        location
        and location.get("latitude") is not None
    ):

        st.write(
            "Latitude:",
            location["latitude"]
        )

        st.write(
            "Longitude:",
            location["longitude"]
        )

        st.write(
            "Precisão GPS (m):",
            round(
                location["accuracy"],
                1
            )
        )

    else:

        st.write(
            "GPS ainda não obtido."
        )

    # --------------------------------------------
    # REGISTRAR EVENTO
    # --------------------------------------------

    st.write(
        "GPS disponível para gravação:"
    )

    st.write(location)

    if st.button(
        "✅ Registrar Evento"
    ):

        if not descricao.strip():

            st.warning(
                "Informe a descrição."
            )

        elif (
        location is None
        or location.get("latitude") is None
    ):

            st.warning(
                "Primeiro obtenha a posição GPS."
            )

        else:

            agora = datetime.now()

            st.session_state.eventos.append(
                {
                    "Data":
                        agora.strftime(
                            "%Y-%m-%d"
                        ),

                    "Hora":
                        agora.strftime(
                            "%H:%M:%S"
                        ),

                    "Descrição do Evento":
                        descricao,

                    "Latitude":
                        location["latitude"],

                    "Longitude":
                        location["longitude"],

                    "PrecisaoGPS":
                        round(
                            location["accuracy"],
                            1
                        )
                }
            )

            st.success(
                "Evento registrado."
            )

# =====================================================
# EVENTOS REGISTRADOS
# =====================================================

if len(st.session_state.eventos) > 0:

    st.subheader(
        "Eventos Registrados"
    )

    df = pd.DataFrame(
        st.session_state.eventos
    )

    st.dataframe(
        df,
        use_container_width=True
    )

# =====================================================
# EXPORTAÇÃO
# =====================================================

if (
    not st.session_state.jornada_ativa
    and len(st.session_state.eventos) > 0
):

    df = pd.DataFrame(
        st.session_state.eventos
    )

    csv = df.to_csv(
        index=False,
        sep=";"
    ).encode(
        "utf-8"
    )

    st.download_button(
        label="⬇ Baixar CSV da Jornada",
        data=csv,
        file_name=
        f"jornada_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )