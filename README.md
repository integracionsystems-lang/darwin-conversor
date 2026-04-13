# Darwin Conversor v2.0 🛃

Convierte facturas PDF al formato Darwin con dos modos de uso.

## Modos de uso

### 👤 Modo Usuario / Capturista
Solo necesita:
1. Código de su empresa en Darwin
2. Código del proveedor
3. Cómo llega la mercancía (barco/camión/avión)
4. Subir el PDF

### 🏛️ Modo Agente Aduanal
Acceso completo a todos los campos del Layout de Factura Electrónica de Vanguardia Tecnologías:
- Selección de registros (CCC, 501, 502, 503, 504, 506, 511, PPP, 505, 551, 999)
- Control de longitudes máximas por campo
- Validación de campos OBL
- Campos incrementables/deducibles
- Observaciones al pedimento

## Despliegue en Streamlit Cloud (GRATIS)

### Paso 1 — Crear repositorio en GitHub
1. Ve a https://github.com → "New repository"
2. Nombre: `darwin-conversor`
3. Público o privado (ambos funcionan)
4. Sube los 3 archivos: `app.py`, `requirements.txt`, `README.md`

### Paso 2 — Desplegar
1. Ve a https://share.streamlit.io
2. "New app" → selecciona tu repo → `app.py`
3. "Deploy" → espera ~2 minutos
4. Tu URL queda: `https://usuario-darwin-conversor.streamlit.app`

### Paso 3 — Configurar API Key (opcional)
Para que todos los usuarios usen la misma API Key sin tener que ingresarla:
1. En Streamlit Cloud → tu app → "Settings" → "Secrets"
2. Agrega:
```toml
ANTHROPIC_API_KEY = "sk-ant-api03-..."
```
3. En app.py cambia la línea del text_input por:
```python
api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
```

## Archivos necesarios
- `app.py` — aplicación principal
- `requirements.txt` — dependencias Python
- `README.md` — este archivo

## Costo estimado por factura
~$0.01-0.02 USD con Claude Sonnet (API de Anthropic)
