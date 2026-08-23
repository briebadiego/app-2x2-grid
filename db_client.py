"""Capa de datos: lee y escribe en la base Postgres (Supabase) que respalda la app."""

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

DEFAULT_CONFIG = {
    "eje_x_label": "Influencia",
    "eje_y_label": "Interés",
    "escala_min": "1",
    "escala_max": "7",
    "punto_medio": "4",
    "label_alta_alta": "Aliados clave",
    "label_alta_baja": "Referentes a activar",
    "label_baja_alta": "Mantener informados",
    "label_baja_baja": "Monitorear",
}


@st.cache_resource
def _get_engine():
    return create_engine(st.secrets["database_url"], pool_pre_ping=True)


@st.cache_resource
def ensure_setup():
    engine = _get_engine()
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS actores (nombre TEXT PRIMARY KEY)"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS respuestas (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ NOT NULL,
                participante TEXT NOT NULL,
                actor TEXT NOT NULL,
                influencia INT NOT NULL,
                interes INT NOT NULL
            )
        """))
        conn.execute(text("CREATE TABLE IF NOT EXISTS config (clave TEXT PRIMARY KEY, valor TEXT NOT NULL)"))
        for k, v in DEFAULT_CONFIG.items():
            conn.execute(
                text("INSERT INTO config (clave, valor) VALUES (:k, :v) ON CONFLICT (clave) DO NOTHING"),
                {"k": k, "v": v},
            )
    return True


def _ws():
    ensure_setup()
    return _get_engine()


@st.cache_data(ttl=5)
def read_actores():
    engine = _ws()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT nombre FROM actores ORDER BY nombre")).fetchall()
    return [r[0] for r in rows]


@st.cache_data(ttl=5)
def read_respuestas():
    engine = _ws()
    return pd.read_sql(
        text("SELECT timestamp, participante, actor, influencia, interes FROM respuestas"), engine
    )


@st.cache_data(ttl=5)
def read_config():
    engine = _ws()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT clave, valor FROM config")).fetchall()
    cfg = dict(DEFAULT_CONFIG)
    cfg.update({k: v for k, v in rows})
    return cfg


def add_actores(nombres):
    engine = _ws()
    existentes = {n.strip().lower() for n in read_actores()}
    vistos = set()
    nuevos = []
    for n in nombres:
        n = n.strip()
        if not n:
            continue
        clave = n.lower()
        if clave in existentes or clave in vistos:
            continue
        vistos.add(clave)
        nuevos.append(n)
    if nuevos:
        with engine.begin() as conn:
            for n in nuevos:
                conn.execute(text("INSERT INTO actores (nombre) VALUES (:n)"), {"n": n})
    read_actores.clear()


def clear_actores():
    engine = _ws()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM actores"))
    read_actores.clear()


def clear_respuestas():
    engine = _ws()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM respuestas"))
    read_respuestas.clear()


def append_respuestas(rows):
    engine = _ws()
    with engine.begin() as conn:
        for timestamp, participante, actor, influencia, interes in rows:
            conn.execute(
                text("""
                    INSERT INTO respuestas (timestamp, participante, actor, influencia, interes)
                    VALUES (:timestamp, :participante, :actor, :influencia, :interes)
                """),
                {
                    "timestamp": timestamp,
                    "participante": participante,
                    "actor": actor,
                    "influencia": influencia,
                    "interes": interes,
                },
            )
    read_respuestas.clear()


def save_config(valores):
    engine = _ws()
    with engine.begin() as conn:
        for k, v in valores.items():
            conn.execute(
                text("""
                    INSERT INTO config (clave, valor) VALUES (:k, :v)
                    ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor
                """),
                {"k": k, "v": str(v)},
            )
    read_config.clear()
