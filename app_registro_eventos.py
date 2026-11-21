import sqlite3
import streamlit as st
import pandas as pd

from datetime import datetime
from streamlit_geolocation import streamlit_geolocation


def parse_hora(value):
    for formato in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(str(value), formato).time()
        except (TypeError, ValueError):
            pass
    return datetime.now().time().replace(microsecond=0)

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

    df_editado = st.data_editor(
        df,
        use_container_width=True,
        num_rows="fixed",
        key="tabela_eventos_editavel",
        column_config={
            "id": st.column_config.NumberColumn(
                "ID",
                disabled=True
            ),
            "data": st.column_config.TextColumn(
                "Data",
                help="Formato: AAAA-MM-DD"
            ),
            "hora": st.column_config.TextColumn(
                "Hora",
                help="Formato: HH:MM:SS"
            ),
            "descricao": st.column_config.TextColumn(
                "Descrição"
            ),
            "latitude": st.column_config.NumberColumn(
                "Latitude",
                format="%.6f",
                min_value=-90.0,
                max_value=90.0
            ),
            "longitude": st.column_config.NumberColumn(
                "Longitude",
                format="%.6f",
                min_value=-180.0,
                max_value=180.0
            ),
            "precisao": st.column_config.NumberColumn(
                "Precisão GPS (m)",
                format="%.1f",
                min_value=0.0
            )
        }
    )

    if st.button(
        "Salvar alterações da tabela",
        key="salvar_tabela_eventos"
    ):
        erros = []
        alterações = 0

        for indice, evento_editado in df_editado.iterrows():
            evento_original = df.loc[indice]

            if evento_editado.to_dict() == evento_original.to_dict():
                continue

            if not str(evento_editado["descricao"]).strip():
                erros.append(f"Evento #{evento_editado['id']}: descrição vazia.")
                continue

            try:
                datetime.strptime(
                    str(evento_editado["data"]),
                    "%Y-%m-%d"
                )
                datetime.strptime(
                    str(evento_editado["hora"]),
                    "%H:%M:%S"
                )
            except ValueError:
                erros.append(
                    f"Evento #{evento_editado['id']}: data ou hora inválida."
                )
                continue

            cursor.execute(
                """
                UPDATE eventos
                SET data = ?, hora = ?, descricao = ?, latitude = ?,
                    longitude = ?, precisao = ?
                WHERE id = ?
                """,
                (
                    str(evento_editado["data"]).strip(),
                    str(evento_editado["hora"]).strip(),
                    str(evento_editado["descricao"]).strip(),
                    float(evento_editado["latitude"]),
                    float(evento_editado["longitude"]),
                    float(evento_editado["precisao"]),
                    int(evento_editado["id"])
                )
            )
            alterações += 1

        conn.commit()

        if erros:
            for erro in erros:
                st.error(erro)

        if alterações > 0:
            st.success(f"{alterações} evento(s) atualizado(s).")
            st.rerun()

    eventos_por_id = {
        int(evento["id"]): evento
        for evento in df.to_dict(orient="records")
    }

    evento_id = st.selectbox(
        "Selecione um evento para excluir",
        options=list(eventos_por_id),
        format_func=lambda id_evento: (
            f"#{id_evento} - {eventos_por_id[id_evento]['data']} "
            f"{eventos_por_id[id_evento]['hora']} - "
            f"{eventos_por_id[id_evento]['descricao']}"
        )
    )

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