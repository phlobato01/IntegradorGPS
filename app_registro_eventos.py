import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_geolocation import streamlit_geolocation
from streamlit_js_eval import get_geolocation

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
# INICIAR JORNADA
# =====================================================

col1, col2 = st.columns(2)

with col1:

    if st.button(
        "▶ Iniciar Jornada"
    ):

        st.session_state.jornada_ativa = True
        st.session_state.eventos = []

        st.success(
            "Jornada iniciada."
        )

with col2:

    if st.button(
        "⏹ Encerrar Jornada"
    ):

        st.session_state.jornada_ativa = False

# =====================================================
# REGISTRO
# =====================================================

if st.session_state.jornada_ativa:

    st.subheader(
        "Registrar Evento"
    )

    descricao = st.text_input(
        "Descrição do evento"
    )

    st.write(
        "Ao registrar o evento, o navegador solicitará acesso à localização."
    )
# início teste

    if st.button(
        "📍 Registrar Evento"
    ):

        try:

            location = get_geolocation()

            st.subheader(
                "DEBUG GPS"
            )

            st.write(
                "Tipo:"
            )

            st.write(
                str(type(location))
            )

            st.write(
                "Conteúdo:"
            )

            st.write(
                location
            )

        except Exception as erro:

            st.error(
                f"ERRO GPS: {erro}"
            )

            st.exception(
                erro
            )

#fim teste

        if not descricao.strip():

            st.warning(
                "Informe a descrição."
            )

        elif (
            location is None
            or location["latitude"] is None
        ):

            st.warning(
                "Localização não disponível."
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
                        location["longitude"]
                }
            )

            st.success(
                "Evento registrado."
            )

# =====================================================
# VISUALIZAÇÃO
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
        file_name=f"jornada_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )