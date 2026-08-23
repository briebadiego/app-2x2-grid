# Mapeo colaborativo de actores (influencia × interés)

App de Streamlit para que un equipo puntúe actores en dos ejes (influencia / interés,
escala configurable) y obtenga un mapa único de cuadrantes con el promedio de todos.

Los datos viven en una base de datos Postgres (gratis, en [Supabase](https://supabase.com)),
que creas tú en el paso 1.

## Cómo funciona

- **Vista monitor** (URL base, sin protección): agrega actores, ajusta la configuración
  del mapa (nombres de ejes, escala, punto de corte, etiquetas de cuadrantes), revisa
  cuántas respuestas han llegado, genera el gráfico y descarga CSV/PDF.
- **Vista participante**: `<url>?vista=participante`. Cada persona escribe su nombre y
  recorre los actores uno a uno con dos sliders (influencia / interés), estilo Kahoot.
  Al llegar al último, un botón "Enviar" manda todas sus respuestas de una vez.

La primera vez que la app se conecta a la base de datos, crea automáticamente las tablas
`actores`, `respuestas` y `config` con sus valores por defecto.

## 1. Crear la base de datos (una sola vez, ~2 minutos)

1. Ve a [supabase.com](https://supabase.com) y crea una cuenta gratis (el botón de
   "Continue with GitHub" es el más rápido — no pide tarjeta).
2. **New project**: elige un nombre, define una contraseña de base de datos (guárdala,
   la necesitas en el paso siguiente) y una región cercana. Plan **Free**. Crear.
3. Espera a que el proyecto termine de aprovisionarse (~1-2 min).
4. Ve a **Project Settings → Database → Connection string**, pestaña **URI**, y copia
   el string de tipo **Session pooler** (puerto `6543`). Se ve así:
   ```
   postgresql://postgres.xxxxxxxx:[YOUR-PASSWORD]@aws-0-xxxxxxxx.pooler.supabase.com:6543/postgres
   ```
5. Reemplaza `[YOUR-PASSWORD]` por la contraseña que definiste en el paso 2.

Eso es todo — sin consola de Google, sin OAuth, sin cuentas de servicio.

## 2. Configurar la credencial en la app

Ese string de conexión no se sube al repo. Se coloca como "secret":

- **Local**: copia `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` y
  pega ahí tu `database_url`.
- **Streamlit Cloud**: en el panel de la app → **Settings → Secrets**, pega una línea:
  ```toml
  database_url = "postgresql://postgres.xxxxxxxx:tu-password@aws-0-xxxxxxxx.pooler.supabase.com:6543/postgres"
  ```

## 3. Correr localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

Abre `http://localhost:8501` para la vista monitor, y
`http://localhost:8501/?vista=participante` para probar la vista participante.

## 4. Desplegar en Streamlit Community Cloud

1. Sube este código al repo de GitHub (ver más abajo).
2. Entra a [share.streamlit.io](https://share.streamlit.io/), conecta tu cuenta de
   GitHub y selecciona el repo `briebadiego/app-2x2-grid`, rama `main`, archivo
   `app.py`.
3. Antes de desplegar (o justo después, en **Settings → Secrets**), pega el
   `database_url` del paso 2.
4. Deploy. La URL pública que te da Streamlit es la que compartes:
   - tal cual, para el monitor.
   - con `?vista=participante` al final, para los participantes (por QR o link directo).

## Estructura de la base de datos

- **`actores`**: una columna, `nombre`. La administra el monitor.
- **`respuestas`**: una fila por cada calificación individual — `timestamp`,
  `participante`, `actor`, `influencia`, `interes`. Si alguien reenvía, se agregan
  filas nuevas (no se sobrescribe) y el promedio las considera todas.
- **`config`**: pares `clave`/`valor` con los nombres de ejes, escala, punto de corte
  y etiquetas de los 4 cuadrantes. Editable desde la pestaña "Configuración" del
  monitor.

## Archivos

- `app.py` — routing entre vistas + UI de ambas.
- `db_client.py` — toda la lectura/escritura a la base Postgres.
- `chart.py` — construcción del mapa de cuadrantes en matplotlib.
