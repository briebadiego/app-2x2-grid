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

    sets = sc.read_sets()
    if not sets:
        st.info("El monitor todavía no ha cargado sets de actores. Espera un momento y recarga la página.")
        return

    cfg = sc.read_config()
    escala_min = int(float(cfg["escala_min"]))
    escala_max = int(float(cfg["escala_max"]))
    punto_medio = int(float(cfg["punto_medio"]))
    eje_x = cfg["eje_x_label"]
    eje_y = cfg["eje_y_label"]

    ss = st.session_state
    ss.setdefault("participante_nombre", "")
    ss.setdefault("set_actual", None)
    ss.setdefault("actor_idx", 0)
    ss.setdefault("respuestas_actual", {})
    ss.setdefault("enviado", False)

    if ss.enviado:
        st.success("¡Gracias! Tus respuestas fueron enviadas.")
        if st.button("Calificar otro set"):
            ss.set_actual = None
            ss.actor_idx = 0
            ss.respuestas_actual = {}
            ss.enviado = False
            st.rerun()
        return

    if not ss.participante_nombre:
        st.caption(
            "Vas a calificar un grupo de actores en dos dimensiones: influencia e interés. "
            "Escribe tu nombre, elige el set que te corresponde calificar y para cada actor "
            "ajusta los dos sliders según lo que creas. Al terminar todos los actores del set, "
            "presiona Enviar."
        )
        nombre = st.text_input("Tu nombre")
        if st.button("Comenzar", type="primary") and nombre.strip():
            ss.participante_nombre = nombre.strip()
            st.rerun()
        return

    if not ss.set_actual:
        st.markdown(f"**Hola, {ss.participante_nombre}.** Elige qué set de actores vas a calificar:")
        nombres_sets = [s["nombre"] for s in sets]
        elegido = st.selectbox("Set", nombres_sets)
        if st.button("Comenzar a calificar", type="primary"):
            ss.set_actual = elegido
            st.rerun()
        return

    set_obj = next((s for s in sets if s["nombre"] == ss.set_actual), None)
    actores = sc.read_actores(set_obj["id"]) if set_obj else []
    if not actores:
        st.warning(f"El set '{ss.set_actual}' todavía no tiene actores.")
        if st.button("Elegir otro set"):
            ss.set_actual = None
            st.rerun()
        return

    idx = ss.actor_idx
    idx = min(idx, len(actores) - 1)
    actor = actores[idx]

    st.caption(f"Set: {ss.set_actual}")
    if st.button("← Elegir otro set"):
        ss.set_actual = None
        ss.actor_idx = 0
        ss.respuestas_actual = {}
        st.rerun()

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
                    [timestamp, ss.participante_nombre, ss.set_actual, a, val[0], val[1]]
                    for a, val in ss.respuestas_actual.items()
                ]
                sc.append_respuestas(rows)
                ss.enviado = True
            else:
                ss.actor_idx += 1
            st.rerun()


# ---------- Vista monitor ----------

def render_instrucciones_tab():
    st.subheader("Cómo usar este panel")
    st.markdown("""
Esta app arma un mapa colaborativo de actores por **influencia** e **interés**, calificado en equipo.

**1. Configuración** — define los nombres de los ejes (por defecto Influencia/Interés), el rango de
la escala (por defecto 1 a 7) y el punto medio que separa los cuadrantes, además de las 4 etiquetas
de cuadrante. Aplica por igual a todos los sets.

**2. Actores** — acá organizas los actores en **sets** (grupos temáticos, por ejemplo "Audiencias" u
"Organizaciones puente"). Por cada set puedes:
- Crear un set nuevo.
- Elegir un set existente y agregarle actores (uno por línea).
- Eliminar actores específicos de ese set.
- Renombrar el set (las respuestas ya recibidas se actualizan al nuevo nombre).
- Eliminar el set completo (no borra las respuestas ya recibidas de ese set).

**3. Respuestas** — cuántas personas han respondido y cuántas calificaciones hay por set. "Limpiar
respuestas" borra TODAS las respuestas de TODOS los sets — úsalo con cuidado.

**4. Gráfico** — elige el set que quieres visualizar y genera el mapa de cuadrantes con el promedio
de las respuestas de ese set. Se puede descargar en PDF.

**5. Datos** — descarga en Excel (.xlsx) todas las respuestas (con su set) y todos los actores
(con su set).

### Cómo compartir con los participantes

Comparte la URL de esta app agregando `?vista=participante` al final (por ejemplo por QR). Cada
participante escribe su nombre, elige el set que le corresponde calificar, y califica actor por
actor con dos sliders. Puede calificar más de un set si repite el proceso.
""")


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
    st.subheader("Sets de actores")

    sets = sc.read_sets()

    with st.expander("Crear nuevo set", expanded=not sets):
        nuevo_set = st.text_input("Nombre del nuevo set", key="nuevo_set_nombre")
        if st.button("Crear set"):
            if nuevo_set.strip():
                sc.create_set(nuevo_set)
                st.success("Set creado.")
                st.rerun()
            else:
                st.warning("Escribe un nombre.")

    if not sets:
        st.info("Aún no hay sets creados. Crea uno arriba para empezar a agregar actores.")
        return

    nombres_sets = [s["nombre"] for s in sets]
    set_sel_nombre = st.selectbox("Set a editar", nombres_sets, key="set_actores_editar")
    set_sel = next(s for s in sets if s["nombre"] == set_sel_nombre)

    actores = sc.read_actores(set_sel["id"])
    st.write(f"{len(actores)} actor(es) en este set." if actores else "Este set todavía no tiene actores.")
    if actores:
        st.dataframe(pd.DataFrame({"actor": actores}), hide_index=True, width="stretch")

    texto = st.text_area(
        "Agregar actores a este set (uno por línea)", height=150,
        placeholder="Ministerio X\nONG Y\nGremio Z", key=f"add_actores_{set_sel['id']}",
    )
    if st.button("Agregar actores", key=f"btn_add_{set_sel['id']}"):
        nombres = texto.splitlines()
        if any(n.strip() for n in nombres):
            sc.add_actores(set_sel["id"], nombres)
            st.success("Actores agregados.")
            st.rerun()
        else:
            st.warning("Escribe al menos un nombre.")

    if actores:
        a_eliminar = st.multiselect("Eliminar actores específicos", actores, key=f"del_actores_{set_sel['id']}")
        if st.button("Eliminar seleccionados", disabled=not a_eliminar, key=f"btn_del_{set_sel['id']}"):
            sc.remove_actores(set_sel["id"], a_eliminar)
            st.success("Actores eliminados.")
            st.rerun()

    st.divider()
    nuevo_nombre = st.text_input("Renombrar este set", value=set_sel["nombre"], key=f"rename_{set_sel['id']}")
    if st.button("Guardar nombre", key=f"btn_rename_{set_sel['id']}"):
        if nuevo_nombre.strip() and nuevo_nombre.strip() != set_sel["nombre"]:
            sc.rename_set(set_sel["id"], nuevo_nombre)
            st.success("Set renombrado.")
            st.rerun()

    st.divider()
    st.warning("Esto elimina el set completo y todos sus actores (no borra las respuestas ya recibidas).")
    confirmar = st.checkbox("Confirmo que quiero borrar este set completo", key=f"confirm_del_set_{set_sel['id']}")
    if st.button("Eliminar set completo", disabled=not confirmar, key=f"btn_del_set_{set_sel['id']}"):
        sc.delete_set(set_sel["id"])
        st.success("Set eliminado.")
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

    if not df.empty:
        conteo = df.groupby("set_nombre").size().reset_index(name="respuestas")
        st.dataframe(conteo, hide_index=True, width="stretch")

    st.divider()
    st.warning("Esto elimina TODAS las respuestas registradas de TODOS los sets (no borra los sets ni sus actores).")
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

    sets_con_datos = sorted(df["set_nombre"].dropna().unique())
    set_sel = st.selectbox("Set a graficar", sets_con_datos)
    df_set = df[df["set_nombre"] == set_sel]

    cfg = sc.read_config()
    df_avg = df_set.groupby("actor", as_index=False)[["influencia", "interes"]].mean()
    fig = build_figure(df_avg, cfg, titulo=f"Mapa de actores — {set_sel}")
    st.pyplot(fig)

    buf = io.BytesIO()
    fig.savefig(buf, format="pdf", bbox_inches="tight")
    st.download_button(
        "Descargar PDF del gráfico", buf.getvalue(),
        file_name=f"mapa_actores_{set_sel}.pdf", mime="application/pdf",
    )


def _to_xlsx(df, sheet_name):
    df = df.copy()
    for col in df.columns:
        df[col] = df[col].apply(
            lambda v: v.replace(tzinfo=None) if isinstance(v, datetime) and v.tzinfo else v
        )
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return buf.getvalue()


def render_datos_tab():
    st.subheader("Descargar datos")
    df = sc.read_respuestas()
    st.download_button(
        "Descargar respuestas (XLSX)", _to_xlsx(df, "respuestas"),
        file_name="respuestas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=df.empty,
    )
    df_actores = sc.read_todos_actores()
    st.download_button(
        "Descargar actores (XLSX)", _to_xlsx(df_actores, "actores"),
        file_name="actores.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=df_actores.empty,
    )


def monitor_view():
    st.title("Panel del monitor — Mapeo de actores")

    tab_instrucciones, tab_config, tab_actores, tab_respuestas, tab_grafico, tab_datos = st.tabs(
        ["Instrucciones", "Configuración", "Actores", "Respuestas", "Gráfico", "Datos"]
    )
    with tab_instrucciones:
        render_instrucciones_tab()
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
