# Mapeo colaborativo de actores (influencia × interés)

App de Streamlit para que un equipo puntúe actores en dos ejes (influencia / interés,
escala configurable) y obtenga un mapa único de cuadrantes con el promedio de todos.

Los datos viven en este Google Sheets:
https://docs.google.com/spreadsheets/d/1Ms-QKhhr_V8IPe8iHesxU4QWGMQIfVtKoCwNoRvAcRM/edit

## Cómo funciona

- **Vista monitor** (URL base, sin protección): agrega actores, ajusta la configuración
  del mapa (nombres de ejes, escala, punto de corte, etiquetas de cuadrantes), revisa
  cuántas respuestas han llegado, genera el gráfico y descarga CSV/PDF.
- **Vista participante**: `<url>?vista=participante`. Cada persona escribe su nombre y
  recorre los actores uno a uno con dos sliders (influencia / interés), estilo Kahoot.
  Al llegar al último, un botón "Enviar" manda todas sus respuestas de una vez.

La primera vez que la app se conecta al Sheets, crea automáticamente las pestañas
`actores`, `respuestas` y `config` con sus encabezados y valores por defecto.

## 1. Autorizar tu cuenta de Google (una sola vez)

Muchas cuentas de Google (incluidas personales) tienen bloqueada la creación de
claves de cuenta de servicio (`iam.disableServiceAccountKeyCreation`). Por eso la
app se autentica como **tu propia cuenta** vía OAuth, en vez de una cuenta de
servicio — de paso, ya no hace falta compartir el Sheets con nadie, porque usa tu
acceso normal como dueño del documento.

1. Ve a [console.cloud.google.com](https://console.cloud.google.com/) y crea un
   proyecto (o usa uno existente).
2. En **APIs y servicios → Biblioteca**, busca y habilita **Google Sheets API**.
3. En **APIs y servicios → Pantalla de consentimiento de OAuth**: tipo **Externo**,
   completa nombre de la app y tu correo. Guarda.
   - Importante: en **Publicar aplicación**, pásala a estado **En producción** (no
     dejarla en "Prueba"). Si se queda en "Prueba", el permiso caduca a los 7 días
     y la app deja de poder escribir en el Sheets. No hace falta la verificación de
     Google para esto — puede quedar "en producción sin verificar" (al autorizar te
     va a salir un aviso de "app no verificada", das clic en Avanzado → Ir a la app).
4. En **APIs y servicios → Credenciales → Crear credenciales → ID de cliente de
   OAuth**, tipo de aplicación **Aplicación de escritorio**. Descarga el JSON
   (`client_secret_....json`).
5. En tu compu, con Python instalado:
   ```bash
   pip install google-auth-oauthlib
   python get_refresh_token.py ruta/al/client_secret_....json
   ```
   Se abre el navegador: inicia sesión con la cuenta de Google que es dueña del
   Sheets y acepta el permiso. La terminal imprime un bloque `[gcp_oauth]` con
   `client_id`, `client_secret` y `refresh_token`.

## 2. Configurar las credenciales en la app

Ese bloque `[gcp_oauth]` no se sube al repo. Se coloca como "secret":

- **Local**: copia `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` y
  pega ahí los tres valores que imprimió el script.
- **Streamlit Cloud**: en el panel de la app → **Settings → Secrets**, pega el mismo
  bloque (formato TOML).

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
3. Antes de desplegar (o justo después, en **Settings → Secrets**), pega las
   credenciales del paso 2.
4. Deploy. La URL pública que te da Streamlit es la que compartes:
   - tal cual, para el monitor.
   - con `?vista=participante` al final, para los participantes (por QR o link directo).

## Estructura del Sheets

- **`actores`**: una columna, `nombre`. La administra el monitor.
- **`respuestas`**: una fila por cada calificación individual — `timestamp`,
  `participante`, `actor`, `influencia`, `interes`. Si alguien reenvía, se agregan
  filas nuevas (no se sobrescribe) y el promedio las considera todas.
- **`config`**: pares `clave`/`valor` con los nombres de ejes, escala, punto de corte
  y etiquetas de los 4 cuadrantes. Editable desde la pestaña "Configuración" del
  monitor.

## Archivos

- `app.py` — routing entre vistas + UI de ambas.
- `sheets_client.py` — toda la lectura/escritura al Google Sheets.
- `chart.py` — construcción del mapa de cuadrantes en matplotlib.
- `get_refresh_token.py` — script de setup, se corre una sola vez en tu compu (ver
  sección 1), no se despliega ni se usa en producción.
