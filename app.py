"""Mapeo colaborativo de actores (influencia x interés).

Vista participante: agrega `?vista=participante` a la URL.
Vista monitor: URL base, sin protección.
"""

import io
from datetime import datetime

import pandas as pd
import streamlit as st

import db_client as sc
from chart import build_figure

st.set_page_config(page_title="Mapeo de actores", layout="centered")

try:
    sc.ensure_setup()
except KeyError:
    st.error(
        "Falta `database_url` en `st.secrets`. "
        "Configúralo en `.streamlit/secrets.toml` (local) o en los Secrets de Streamlit Cloud. "
        "Ver README.md, sección 1."
    )
    st.stop()
except Exception as e:
    st.error(f"No se pudo conectar con la base de datos: {e}")
    st.stop()


# ---------- Vista participante ----------

def participant_view():
    st.title("Mapeo de actores")

    actores = sc.read_actores()
    if not actores:
        st.info("El monitor todavía no ha cargado actores. Espera un momento y recarga la página.")
        return

    cfg = sc.read_config()
    escala_min = int(float(cfg["escala_min"]))
    escala_max = int(float(cfg["escala_max"]))
    punto_medio = int(float(cfg["punto_medio"]))
    eje_x = cfg["eje_x_label"]
    eje_y = cfg["eje_y_label"]

    ss = st.session_state
    ss.setdefault("participante_nombre", "")
    ss.setdefault("actor_idx", 0)
    ss.setdefault("respuestas_actual", {})
    ss.setdefault("enviado", False)

    if ss.enviado:
        st.success("¡Gracias! Tus respuestas fueron enviadas.")
        if st.button("Enviar otra ronda de respuestas"):
            ss.participante_nombre = ""
            ss.actor_idx = 0
            ss.respuestas_actual = {}
            ss.enviado = False
            st.rerun()
        return

    if not ss.participante_nombre:
        nombre = st.text_input("Tu nombre")
        if st.button("Comenzar", type="primary") and nombre.strip():
            ss.participante_nombre = nombre.strip()
            st.rerun()
        return

    idx = ss.actor_idx
    idx = min(idx, len(actores) - 1)
    actor = actores[idx]

    st.progress((idx + 1) / len(actores))
    st.caption(f"Actor {idx + 1} de {len(actores)}")
    st.subheader(actor)

    prev = ss.respuestas_actual.get(actor, (punto_medio, punto_medio))
    influencia = st.slider(eje_x, escala_min, escala_max, prev[0])
    interes = st.slider(eje_y, escala_min, escala_max, prev[1])

    is_last = idx == len(actores) - 1
    col1, col2 = st.columns([1, 1])
    with col1:
        if idx > 0 and st.button("Atrás"):
            ss.respuestas_actual[actor] = (influencia, interes)
            ss.actor_idx -= 1
            st.rerun()
    with col2:
        if st.button("Enviar" if is_last else "Siguiente", type="primary"):
            ss.respuestas_actual[actor] = (influencia, interes)
            if is_last:
                timestamp = datetime.now().isoformat(timespec="seconds")
                rows = [
                    [timestamp, ss.participante_nombre, a, val[0], val[1]]
                    for a, val in ss.respuestas_actual.items()
                ]
                sc.append_respuestas(rows)
                ss.enviado = True
            else:
                ss.actor_idx += 1
            st.rerun()


# ---------- Vista monitor ----------

def render_config_tab():
    st.subheader("Configuración del mapa")
    cfg = sc.read_config()
    with st.form("form_config"):
        eje_x = st.text_input("Nombre eje X (horizontal)", cfg["eje_x_label"])
        eje_y = st.text_input("Nombre eje Y (vertical)", cfg["eje_y_label"])

        c1, c2, c3 = st.columns(3)
        with c1:
            escala_min = st.number_input("Escala mínima", value=int(float(cfg["escala_min"])), step=1)
        with c2:
            escala_max = st.number_input("Escala máxima", value=int(float(cfg["escala_max"])), step=1)
        with c3:
            punto_medio = st.number_input("Punto medio (corte cuadrantes)", value=int(float(cfg["punto_medio"])), step=1)

        st.markdown("**Etiquetas de cuadrantes**")
        label_aa = st.text_input(f"Alta {eje_x} / Alto {eje_y}", cfg["label_alta_alta"])
        label_ab = st.text_input(f"Alta {eje_x} / Bajo {eje_y}", cfg["label_alta_baja"])
        label_ba = st.text_input(f"Baja {eje_x} / Alto {eje_y}", cfg["label_baja_alta"])
        label_bb = st.text_input(f"Baja {eje_x} / Bajo {eje_y}", cfg["label_baja_baja"])

        if st.form_submit_button("Guardar configuración"):
            if escala_min >= escala_max:
                st.error("La escala mínima debe ser menor que la máxima.")
            elif not (escala_min <= punto_medio <= escala_max):
                st.error("El punto medio debe estar dentro del rango de la escala.")
            else:
                sc.save_config({
                    "eje_x_label": eje_x,
                    "eje_y_label": eje_y,
                    "escala_min": escala_min,
                    "escala_max": escala_max,
                    "punto_medio": punto_medio,
                    "label_alta_alta": label_aa,
                    "label_alta_baja": label_ab,
                    "label_baja_alta": label_ba,
                    "label_baja_baja": label_bb,
                })
                st.success("Configuración guardada.")
                st.rerun()


def render_actores_tab():
    st.subheader("Actores")
    actores = sc.read_actores()
    st.write(f"{len(actores)} actor(es) cargados." if actores else "Aún no hay actores cargados.")
    if actores:
        st.dataframe(pd.DataFrame({"actor": actores}), hide_index=True, use_container_width=True)

    texto = st.text_area("Agregar actores (uno por línea)", height=150, placeholder="Ministerio X\nONG Y\nGremio Z")
    if st.button("Agregar actores"):
        nombres = texto.splitlines()
        if any(n.strip() for n in nombres):
            sc.add_actores(nombres)
            st.success("Actores agregados.")
            st.rerun()
        else:
            st.warning("Escribe al menos un nombre.")

    st.divider()
    st.warning("Esto elimina TODOS los actores de la lista (no borra las respuestas ya recibidas).")
    confirmar = st.checkbox("Confirmo que quiero borrar la lista de actores", key="confirm_actores")
    if st.button("Limpiar actores", disabled=not confirmar):
        sc.clear_actores()
        st.success("Lista de actores eliminada.")
        st.rerun()


def render_respuestas_tab():
    st.subheader("Respuestas recibidas")
    if st.button("Actualizar"):
        sc.read_respuestas.clear()
        st.rerun()

    df = sc.read_respuestas()
    participantes = sorted(df["participante"].dropna().unique()) if not df.empty else []
    st.write(f"{len(participantes)} participante(s) han enviado respuestas ({len(df)} calificaciones en total).")
    if participantes:
        st.write(", ".join(participantes))

    st.divider()
    st.warning("Esto elimina TODAS las respuestas registradas (no borra la lista de actores).")
    confirmar = st.checkbox("Confirmo que quiero borrar las respuestas", key="confirm_respuestas")
    if st.button("Limpiar respuestas", disabled=not confirmar):
        sc.clear_respuestas()
        st.success("Respuestas eliminadas.")
        st.rerun()


def render_grafico_tab():
    st.subheader("Mapa de actores")
    df = sc.read_respuestas()
    if df.empty:
        st.info("Todavía no hay respuestas para graficar.")
        return

    cfg = sc.read_config()
    df_avg = df.groupby("actor", as_index=False)[["influencia", "interes"]].mean()
    fig = build_figure(df_avg, cfg)
    st.pyplot(fig)

    buf = io.BytesIO()
    fig.savefig(buf, format="pdf", bbox_inches="tight")
    st.download_button(
        "Descargar PDF del gráfico", buf.getvalue(),
        file_name="mapa_actores.pdf", mime="application/pdf",
    )


def render_datos_tab():
    st.subheader("Descargar datos")
    df = sc.read_respuestas()
    st.download_button(
        "Descargar respuestas (CSV)", df.to_csv(index=False).encode("utf-8"),
        file_name="respuestas.csv", mime="text/csv", disabled=df.empty,
    )
    actores = sc.read_actores()
    df_actores = pd.DataFrame({"actor": actores})
    st.download_button(
        "Descargar actores (CSV)", df_actores.to_csv(index=False).encode("utf-8"),
        file_name="actores.csv", mime="text/csv", disabled=df_actores.empty,
    )


def monitor_view():
    st.title("Panel del monitor — Mapeo de actores")

    tab_config, tab_actores, tab_respuestas, tab_grafico, tab_datos = st.tabs(
        ["Configuración", "Actores", "Respuestas", "Gráfico", "Datos"]
    )
    with tab_config:
        render_config_tab()
    with tab_actores:
        render_actores_tab()
    with tab_respuestas:
        render_respuestas_tab()
    with tab_grafico:
        render_grafico_tab()
    with tab_datos:
        render_datos_tab()

    st.divider()
    st.caption(
        "Link para participantes: agrega `?vista=participante` a la URL de esta app "
        "(por ejemplo, para compartir por QR)."
    )


vista = st.query_params.get("vista", "monitor")
if vista == "participante":
    participant_view()
else:
    monitor_view()
