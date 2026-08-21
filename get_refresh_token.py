"""Script de setup, se corre UNA sola vez en tu máquina (no se despliega).

Autoriza tu cuenta personal de Google para que la app pueda leer/escribir el
Sheets en tu nombre, sin necesitar una clave de cuenta de servicio.

Uso:
    pip install google-auth-oauthlib
    python get_refresh_token.py [ruta-al-client_secret.json]

Se abre el navegador para que inicies sesión y aceptes el permiso de Sheets.
Al terminar, imprime el bloque [gcp_oauth] listo para pegar en
`.streamlit/secrets.toml` o en los Secrets de Streamlit Cloud.
"""

import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def main():
    client_secret_path = sys.argv[1] if len(sys.argv) > 1 else "client_secret.json"
    flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
    creds = flow.run_local_server(port=0)

    print("\nCopia esto en .streamlit/secrets.toml o en los Secrets de Streamlit Cloud:\n")
    print("[gcp_oauth]")
    print(f'client_id = "{creds.client_id}"')
    print(f'client_secret = "{creds.client_secret}"')
    print(f'refresh_token = "{creds.refresh_token}"')


if __name__ == "__main__":
    main()
