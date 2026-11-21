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
# BLOCO PRINCIPAL
# =====================================================

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

    eventos_por_id = {
        int(evento["id"]): evento
        for evento in df.to_dict(orient="records")
    }

    evento_id = st.selectbox(
        "Selecione um evento para editar ou excluir",
        options=list(eventos_por_id),
        format_func=lambda id_evento: (
            f"#{id_evento} - {eventos_por_id[id_evento]['data']} "
            f"{eventos_por_id[id_evento]['hora']} - "
            f"{eventos_por_id[id_evento]['descricao']}"
        )
    )
    evento = eventos_por_id[evento_id]

    st.subheader(
        "Editar evento selecionado"
    )

    with st.form(key=f"form_editar_evento_{evento_id}"):
        descricao_editada = st.text_input(
            "Descrição",
            value=evento["descricao"],
            key=f"descricao_evento_{evento_id}"
        )
        data_editada = st.date_input(
            "Data",
            value=datetime.strptime(
                evento["data"],
                "%Y-%m-%d"
            ).date(),
            key=f"data_evento_{evento_id}"
        )
        hora_editada = st.time_input(
            "Hora",
            value=datetime.strptime(
                evento["hora"],
                "%H:%M:%S"
            ).time(),
            format="HH:mm:ss",
            key=f"hora_evento_{evento_id}"
        )

        col_latitude, col_longitude, col_precisao = st.columns(3)

        with col_latitude:
            latitude_editada = st.number_input(
                "Latitude",
                min_value=-90.0,
                max_value=90.0,
                value=float(evento["latitude"]),
                key=f"latitude_evento_{evento_id}"
            )

        with col_longitude:
            longitude_editada = st.number_input(
                "Longitude",
                min_value=-180.0,
                max_value=180.0,
                value=float(evento["longitude"]),
                key=f"longitude_evento_{evento_id}"
            )

        with col_precisao:
            precisao_editada = st.number_input(
                "Precisão GPS (m)",
                min_value=0.0,
                value=float(evento["precisao"]),
                key=f"precisao_evento_{evento_id}"
            )

        salvar_edicao = st.form_submit_button(
            "Salvar alterações"
        )

    if salvar_edicao:
        if not descricao_editada.strip():
            st.warning("Informe a descrição.")
        else:
            cursor.execute(
                """
                UPDATE eventos
                SET data = ?, hora = ?, descricao = ?, latitude = ?,
                    longitude = ?, precisao = ?
                WHERE id = ?
                """,
                (
                    data_editada.strftime("%Y-%m-%d"),
                    hora_editada.strftime("%H:%M:%S"),
                    descricao_editada.strip(),
                    latitude_editada,
                    longitude_editada,
                    precisao_editada,
                    evento_id
                )
            )
            conn.commit()
            st.success("Evento atualizado.")
            st.rerun()

    if st.button(
        "🗑 Excluir evento selecionado",
        key=f"solicitar_exclusao_{evento_id}"
    ):
        st.session_state.evento_pendente_exclusao = evento_id
        st.rerun()

    if "evento_pendente_exclusao" in st.session_state:
        evento_pendente = st.session_state.evento_pendente_exclusao
        st.warning(
            f"Confirma a exclusão permanente do evento #{evento_pendente}?"
        )

        confirmar, cancelar = st.columns(2)

        with confirmar:
            confirmar_exclusao = st.button(
                "Confirmar exclusão",
                key="confirmar_exclusao"
            )

        with cancelar:
            cancelar_exclusao = st.button(
                "Cancelar",
                key="cancelar_exclusao"
            )

        if confirmar_exclusao:
            cursor.execute(
                "DELETE FROM eventos WHERE id = ?",
                (evento_pendente,)
            )
            conn.commit()
            del st.session_state.evento_pendente_exclusao
            st.success(f"Evento #{evento_pendente} excluído.")
            st.rerun()

        if cancelar_exclusao:
            del st.session_state.evento_pendente_exclusao
            st.rerun()

# =====================================================
# EXPORTAÇÃO
# =====================================================

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