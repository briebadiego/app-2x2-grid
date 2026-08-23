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
        conn.execute(text("CREATE TABLE IF NOT EXISTS sets (id SERIAL PRIMARY KEY, nombre TEXT UNIQUE NOT NULL)"))

        tiene_set_id = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'actores' AND column_name = 'set_id'
            )
        """)).scalar()
        if not tiene_set_id:
            conn.execute(text("DROP TABLE IF EXISTS actores"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS actores (
                id SERIAL PRIMARY KEY,
                set_id INTEGER NOT NULL REFERENCES sets(id) ON DELETE CASCADE,
                nombre TEXT NOT NULL,
                UNIQUE (set_id, nombre)
            )
        """))

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
        conn.execute(text(
            "ALTER TABLE respuestas ADD COLUMN IF NOT EXISTS set_nombre TEXT NOT NULL DEFAULT 'Sin set'"
        ))

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
def read_sets():
    engine = _ws()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, nombre FROM sets ORDER BY id")).fetchall()
    return [{"id": r[0], "nombre": r[1]} for r in rows]


def create_set(nombre):
    engine = _ws()
    nombre = nombre.strip()
    if not nombre:
        return
    existentes = {s["nombre"].lower() for s in read_sets()}
    if nombre.lower() not in existentes:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO sets (nombre) VALUES (:n)"), {"n": nombre})
    read_sets.clear()


def rename_set(set_id, nuevo_nombre):
    engine = _ws()
    nuevo_nombre = nuevo_nombre.strip()
    if not nuevo_nombre:
        return
    anterior = next((s["nombre"] for s in read_sets() if s["id"] == set_id), None)
    with engine.begin() as conn:
        conn.execute(text("UPDATE sets SET nombre = :n WHERE id = :id"), {"n": nuevo_nombre, "id": set_id})
        if anterior:
            conn.execute(
                text("UPDATE respuestas SET set_nombre = :n WHERE set_nombre = :old"),
                {"n": nuevo_nombre, "old": anterior},
            )
    read_sets.clear()
    read_respuestas.clear()


def delete_set(set_id):
    engine = _ws()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM sets WHERE id = :id"), {"id": set_id})
    read_sets.clear()
    read_actores.clear()
    read_todos_actores.clear()


@st.cache_data(ttl=5)
def read_actores(set_id):
    engine = _ws()
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT nombre FROM actores WHERE set_id = :id ORDER BY id"), {"id": set_id}
        ).fetchall()
    return [r[0] for r in rows]


@st.cache_data(ttl=5)
def read_todos_actores():
    engine = _ws()
    return pd.read_sql(
        text("""
            SELECT s.nombre AS set, a.nombre AS actor
            FROM actores a JOIN sets s ON a.set_id = s.id
            ORDER BY s.id, a.id
        """),
        engine,
    )


@st.cache_data(ttl=5)
def read_respuestas():
    engine = _ws()
    return pd.read_sql(
        text("SELECT timestamp, participante, set_nombre, actor, influencia, interes FROM respuestas"), engine
    )


@st.cache_data(ttl=5)
def read_config():
    engine = _ws()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT clave, valor FROM config")).fetchall()
    cfg = dict(DEFAULT_CONFIG)
    cfg.update({k: v for k, v in rows})
    return cfg


def add_actores(set_id, nombres):
    engine = _ws()
    existentes = {n.strip().lower() for n in read_actores(set_id)}
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
                conn.execute(
                    text("INSERT INTO actores (set_id, nombre) VALUES (:sid, :n)"),
                    {"sid": set_id, "n": n},
                )
    read_actores.clear()
    read_todos_actores.clear()


def remove_actores(set_id, nombres):
    engine = _ws()
    if not nombres:
        return
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM actores WHERE set_id = :sid AND nombre = ANY(:ns)"),
            {"sid": set_id, "ns": list(nombres)},
        )
    read_actores.clear()
    read_todos_actores.clear()


def clear_respuestas():
    engine = _ws()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM respuestas"))
    read_respuestas.clear()


def append_respuestas(rows):
    engine = _ws()
    with engine.begin() as conn:
        for timestamp, participante, set_nombre, actor, influencia, interes in rows:
            conn.execute(
                text("""
                    INSERT INTO respuestas (timestamp, participante, set_nombre, actor, influencia, interes)
                    VALUES (:timestamp, :participante, :set_nombre, :actor, :influencia, :interes)
                """),
                {
                    "timestamp": timestamp,
                    "participante": participante,
                    "set_nombre": set_nombre,
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
