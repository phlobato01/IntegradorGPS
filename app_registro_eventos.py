import sqlite3
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
# SQLITE
# =====================================================

conn = sqlite3.connect(
    "eventos.db",
    check_same_thread=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT,
    hora TEXT,
    descricao TEXT,
    latitude REAL,
    longitude REAL,
    precisao REAL
)
""")

conn.commit()

# =====================================================
# SESSION STATE
# =====================================================

if "jornada_ativa" not in st.session_state:
    st.session_state.jornada_ativa = False

# =====================================================
# INICIAR / ENCERRAR
# =====================================================

c1, c2 = st.columns(2)

with c1:

    if st.button(
        "▶ Iniciar Jornada"
    ):

        st.session_state.jornada_ativa = True
        
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

            cursor.execute(
                """
                INSERT INTO eventos (
                    data,
                    hora,
                    descricao,
                    latitude,
                    longitude,
                    precisao
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    agora.strftime("%Y-%m-%d"),
                    agora.strftime("%H:%M:%S"),
                    descricao,
                    location["latitude"],
                    location["longitude"],
                    round(
                        location["accuracy"],
                        1
                    )
                )
            )

            conn.commit()

            st.success(
                "Evento registrado."
            )

# =====================================================
# EVENTOS REGISTRADOS
# =====================================================

df = pd.read_sql_query(
    """
    SELECT *
    FROM eventos
    ORDER BY id
    """,
    conn
)

if len(df) > 0:

    st.subheader(
        "Eventos Registrados"
    )

    st.dataframe(
        df,
        use_container_width=True
    )

# =====================================================
# EXPORTAÇÃO
# =====================================================

df = pd.read_sql_query(
    """
    SELECT *
    FROM eventos
    ORDER BY id
    """,
    conn
)

if len(df) > 0:

    csv = df.to_csv(
        index=False,
        sep=";"
    ).encode("utf-8")

    st.download_button(
        label="⬇ Baixar CSV",
        data=csv,
        file_name=
        f"eventos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

    if st.button(
        "🗑 Limpar Eventos"
    ):

        cursor.execute(
            "DELETE FROM eventos"
        )

        conn.commit()

        st.success(
            "Todos os eventos foram apagados."
        )

        st.rerun()