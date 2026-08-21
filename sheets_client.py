"""Capa de datos: lee y escribe en el Google Sheets que respalda la app."""

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

SHEET_ID = "1Ms-QKhhr_V8IPe8iHesxU4QWGMQIfVtKoCwNoRvAcRM"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

ACTORES_HEADER = ["nombre"]
RESPUESTAS_HEADER = ["timestamp", "participante", "actor", "influencia", "interes"]
CONFIG_HEADER = ["clave", "valor"]

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
def _get_client():
    info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_resource
def _get_spreadsheet():
    return _get_client().open_by_key(SHEET_ID)


def _get_or_create_worksheet(title, header):
    sh = _get_spreadsheet()
    try:
        ws = sh.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows=200, cols=max(len(header), 2))
        ws.append_row(header)
        return ws
    if not ws.row_values(1):
        ws.append_row(header)
    return ws


@st.cache_resource
def ensure_setup():
    """Crea las pestañas necesarias (si faltan) y siembra la configuración por defecto."""
    _get_or_create_worksheet("actores", ACTORES_HEADER)
    _get_or_create_worksheet("respuestas", RESPUESTAS_HEADER)
    config_ws = _get_or_create_worksheet("config", CONFIG_HEADER)
    existentes = {r["clave"] for r in config_ws.get_all_records()}
    faltantes = [[k, v] for k, v in DEFAULT_CONFIG.items() if k not in existentes]
    if faltantes:
        config_ws.append_rows(faltantes)
    return True


def _ws(title):
    ensure_setup()
    return _get_spreadsheet().worksheet(title)


@st.cache_data(ttl=5)
def read_actores():
    ws = _ws("actores")
    return [r["nombre"].strip() for r in ws.get_all_records() if r.get("nombre", "").strip()]


@st.cache_data(ttl=5)
def read_respuestas():
    ws = _ws("respuestas")
    records = ws.get_all_records()
    df = pd.DataFrame(records, columns=RESPUESTAS_HEADER)
    if not df.empty:
        df["influencia"] = pd.to_numeric(df["influencia"], errors="coerce")
        df["interes"] = pd.to_numeric(df["interes"], errors="coerce")
    return df


@st.cache_data(ttl=5)
def read_config():
    ws = _ws("config")
    cfg = dict(DEFAULT_CONFIG)
    for r in ws.get_all_records():
        if r.get("clave"):
            cfg[r["clave"]] = r["valor"]
    return cfg


def add_actores(nombres):
    ws = _ws("actores")
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
        nuevos.append([n])
    if nuevos:
        ws.append_rows(nuevos)
    read_actores.clear()


def clear_actores():
    ws = _ws("actores")
    ws.clear()
    ws.append_row(ACTORES_HEADER)
    read_actores.clear()


def clear_respuestas():
    ws = _ws("respuestas")
    ws.clear()
    ws.append_row(RESPUESTAS_HEADER)
    read_respuestas.clear()


def append_respuestas(rows):
    ws = _ws("respuestas")
    ws.append_rows(rows)
    read_respuestas.clear()


def save_config(valores):
    ws = _ws("config")
    filas = [CONFIG_HEADER] + [[k, str(v)] for k, v in valores.items()]
    ws.clear()
    ws.update(filas)
    read_config.clear()
